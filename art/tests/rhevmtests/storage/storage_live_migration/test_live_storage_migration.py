"""
Storage live migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
import config
import logging
from time import sleep
from multiprocessing import Process, Queue

from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest

from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611

from utilities.machine import Machine

from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.rhevm_api.utils.test_utils import (
    get_api, setPersistentNetwork, restartVdsmd, wait_for_tasks,
)
from art.rhevm_api.tests_lib.high_level.datacenters import (
    clean_datacenter, build_setup,
)
from art.rhevm_api.tests_lib.high_level.storagedomains import (
    addISCSIDataDomain, remove_storage_domain,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.disks import (
    wait_for_disks_status, get_other_storage_domain, attachDisk,
    deleteDisk, getVmDisk, get_disk_storage_domain_name,
    addDisk, detachDisk, getObjDisks, updateDisk, checkDiskExists,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, rebootHost, getHSMHost, getHostIP, waitForHostsStates,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate, waitForTemplatesStates,
    wait_for_template_disks_state, copy_template_disks,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    deactivateStorageDomain, waitForStorageDomainStatus,
    activateStorageDomain, extendStorageDomain, getDomainAddress,
    get_free_space, getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    waitForVMState, deactivateVmDisk, removeDisk, start_vms, live_migrate_vm,
    remove_all_vm_lsm_snapshots, addVm, suspendVm,
    live_migrate_vm_disk, move_vm_disk, waitForVmsStates, getVmDisks,
    stopVm, migrateVm, verify_vm_disk_moved, updateVm, getVmHost, removeVms,
    shutdownVm, runVmOnce, startVm, get_vm_snapshots, safely_remove_vms,
    stop_vms_safely, activateVmDisk, cloneVmFromTemplate, removeVm,
    waitForVmsDisks, addSnapshot, wait_for_vm_snapshots,
    get_vm_disk_logical_name,
)

from rhevmtests.storage.storage_live_migration import helpers
from rhevmtests.helpers import get_golden_template_name

import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.settings import opts


logger = logging.getLogger(__name__)

VM_API = get_api('vm', 'vms')

ENUMS = config.ENUMS

CREATE_VM_TIMEOUT = 15 * 60
VM_SHUTDOWN_TIMEOUT = 2 * 60
MIGRATION_TIMEOUT = 10 * 60
TASK_TIMEOUT = 1500
LIVE_MIGRATION_TIMEOUT = 30 * 60
DISK_TIMEOUT = 900
LIVE_MIGRATE_LARGE_SIZE = 3600

# After the deletion of a snapshot, vdsm allocates around 128MB of data for
# the extent metadata
EXTENT_METADATA_SIZE = 128 * config.MB

FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"

SDK_ENGINE = 'sdk'
VMS_PID_LIST = 'pgrep qemu'

vmArgs = {'positive': True,
          'vmDescription': config.VM_NAME % "description",
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.COW_DISK,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.VM_DISK_SIZE,
          'nic': config.NIC_NAME[0],
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.OS_TYPE,
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }

LOCAL_LUN = []
LOCAL_LUN_ADDRESS = []
LOCAL_LUN_TARGET = []
ISCSI = config.STORAGE_TYPE_ISCSI

# TOOD: Once the patch for test_failure is merged and tested change the
# tearDown of the test to only log during the execution and raise the
# exceptions at the end.


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats

    for this test plan, we need 2 SD but only two of them should be created on
    setup. the other SD will be created manually in test case 5975.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only two lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    global LOCAL_LUN, LOCAL_LUN_ADDRESS, LOCAL_LUN_TARGET
    if not config.GOLDEN_ENV:
        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)

        if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
            luns = config.LUNS
            LOCAL_LUN = config.LUNS[3:]
            LOCAL_LUN_ADDRESS = config.LUN_ADDRESS[3:]
            LOCAL_LUN_TARGET = config.LUN_TARGET[3:]

            config.PARAMETERS['lun'] = luns[0:3]
        build_setup(config=config.PARAMETERS,
                    storage=config.PARAMETERS,
                    storage_type=config.STORAGE_TYPE)

        if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
            config.PARAMETERS['lun'] = luns

        storage_type = config.STORAGE_SELECTOR[0]
        logger.info(
            "For non-golden env run create a template to clone the vm from",
        )
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]

        vm_name = config.VM_NAME % storage_type
        vmArgs['storageDomainName'] = storage_domain
        vmArgs['vmName'] = vm_name

        logger.info('Creating vm and installing OS on it')

        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException('Unable to create vm %s for test'
                                         % vm_name)

        startVm(True, vm_name, config.VM_UP, wait_for_ip=False)
        ip_addr = storage_helpers.get_vm_ip(vm_name)
        setPersistentNetwork(ip_addr, config.VM_PASSWORD)
        stopVm(True, vm_name)
        assert createTemplate(
            True, True, vm=vm_name, name=config.TEMPLATE_NAME_LSM,
            cluster=config.CLUSTER_NAME, storagedomain=storage_domain
        )

        logger.info('Deleting VM %s', vm_name)
        safely_remove_vms([vm_name])

    else:
        LOCAL_LUN = config.UNUSED_LUNS[:]
        LOCAL_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES[:]
        LOCAL_LUN_TARGET = config.UNUSED_LUN_TARGETS[:]


def teardown_module():
    """
    Clean datacenter
    """
    if not config.GOLDEN_ENV:
        logger.info('Cleaning datacenter')
        clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


class BaseTestCase(StorageTest):
    """
    A class with a simple setUp
    """
    vm_sd = None

    # VM's bootable disk default parameters
    sparse = True
    interface = config.VIRTIO
    disk_format = config.DISK_FORMAT_COW

    def setUp(self):
        """
        Get all the storage domains from a specific domain type
        """
        self.vm_name = config.VM_NAME % self.storage
        self.storage_domains = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)
        if config.GOLDEN_ENV:
            template = get_golden_template_name(config.CLUSTER_NAME)
        else:
            template = config.TEMPLATE_NAME_LSM
        if self.vm_sd:
            self.disk_sd = self.vm_sd
        else:
            self.disk_sd = self.storage_domains[0]

        # For each test, create a vm and remove it once the test completes
        # execution. This is faster than removing snapshots
        assert cloneVmFromTemplate(
            True, self.vm_name, template, config.CLUSTER_NAME,
            storagedomain=self.disk_sd, vol_sparse=self.sparse,
            vol_format=self.disk_format, virtio_scsi=True,
        )
        disk_obj = getVmDisks(self.vm_name)[0]
        self.vm_disk_name = "{0}_Disk1".format(self.vm_name)
        updateDisk(
            True, vmName=self.vm_name, id=disk_obj.get_id(),
            alias=self.vm_disk_name, interface=self.interface,
        )

    def tearDown(self):
        """
        Clean environment
        """
        wait_for_jobs()
        safely_remove_vms([self.vm_name])


class CommonUsage(BaseTestCase):
    """
    A class with common method
    """
    __test__ = False

    def _remove_disks(self, disks_names):
        """
        Removes created disks
        """
        for disk in disks_names:
            logger.info("Deleting disk %s", disk)
            if not deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)


class AllPermutationsDisks(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    __test__ = False

    spm = None
    master_sd = None
    shared = False

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        super(AllPermutationsDisks, self).setUp()
        helpers.start_creating_disks_for_test(
            shared=self.shared, sd_name=self.disk_sd,
            sd_type=self.storage
        )
        if not wait_for_disks_status(
            helpers.DISK_NAMES[self.storage], timeout=TASK_TIMEOUT,
        ):
            logger.error(
                "Disks %s are not in status OK",
                helpers.DISK_NAMES[self.storage],
            )
        storage_helpers.prepare_disks_for_vm(
            self.vm_name, helpers.DISK_NAMES[self.storage],
        )

    def verify_lsm(self, moved=True):
        """
        Verifies if the disks have been moved
        """
        if moved:
            failure_str = "Failed"
        else:
            failure_str = "Succeeded"

        for disk in helpers.DISK_NAMES[self.storage]:
            self.assertTrue(
                moved == verify_vm_disk_moved(
                    self.vm_name, disk, self.disk_sd,
                ),
                "%s to live migrate vm disk %s" % (disk, failure_str),
            )


@attr(tier=0)
class TestCase6004(AllPermutationsDisks):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '6004'
    bz = {'1230270': {'engine': ['cli'], 'version': ["3.5", "3.6"]}}

    @polarion("RHEVM3-6004")
    def test_vms_live_migration(self):
        """
        Actions:
            - move vm's images to different SD
        Expected Results:
            - move should succeed
        """
        live_migrate_vm(self.vm_name)
        self.verify_lsm()


@attr(tier=1)
class TestCase5990(BaseTestCase):
    """
    vm in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5990'

    @polarion("RHEVM3-5990")
    def test_vms_live_migration(self):
        """
        Actions:
            - run a vm with run-once in pause mode
            - try to move images
        Expected Results:
            - VM has running qemu process so LSM should succeed
        """
        logger.info("Running vm in paused state")
        assert runVmOnce(True, self.vm_name, pause='true')
        waitForVMState(self.vm_name, config.VM_PAUSED)
        live_migrate_vm(self.vm_name)
        wait_for_jobs()
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        self.assertTrue(
            verify_vm_disk_moved(self.vm_name, vm_disk, self.disk_sd),
            "Failed to live migrate disk %s" % vm_disk,
        )


@attr(tier=1)
class TestCase5994(BaseTestCase):
    """
    different vm status
        https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration

    __test__ = False : A race situation can occur here. Manual test only
    """
    # TODO: Make sure this is really a problem
    __test__ = False
    polarion_test_case = '5994'

    @polarion("RHEVM3-5994")
    def test_lsm_during_waiting_for_launch_state(self):
        """
        Actions:
            - try to live migrate while vm is waiting for launch
        Expected Results:
            - live migration should fail
        """
        startVm(True, self.vm_name, wait_for_status=None)
        waitForVMState(self.vm_name, config.VM_WAIT_FOR_LAUNCH)
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          self.vm_name)

    @polarion("RHEVM3-5994")
    def test_lsm_during_powering_up_state(self):
        """
        Actions:
            - try to live migrate while vm is powering up
        Expected Results:
            - migration should fail
        """
        startVm(True, self.vm_name, wait_for_status=None)
        waitForVMState(self.vm_name, config.VM_POWERING_UP)
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          self.vm_name)

    @polarion("RHEVM3-5994")
    def test_lsm_during_powering_off_state(self):
        """
        Actions:
            - try to live migrate while vm is powering off
        Expected Results:
            - migration should fail
        """
        startVm(True, self.vm_name, wait_for_status=None)
        waitForVMState(self.vm_name)
        shutdownVm(True, self.vm_name)
        waitForVMState(self.vm_name, ENUMS['vm_state_powering_down'])
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          self.vm_name)


@attr(tier=1)
class TestCase5993(StorageTest):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: This has not been verified since the bz prevents to run it,
    # make sure it works properly
    __test__ = False
    polarion_test_case = '5993'
    test_templates = ['template_single', 'template_both']
    base_vm = config.VM_NAME % BaseTestCase.storage
    vm_names = ['vm_from_both', 'vm_from_single']
    bz = {'1110798': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    def _prepare_templates(self):
        """
        Creates two templates
            - one has disk on first storage domain
            - second has disks on both storage domains
        """
        start_vms([self.base_vm], 1, wait_for_ip=False)
        waitForVMState(self.base_vm)
        ip_addr = storage_helpers.get_vm_ip(self.base_vm)
        setPersistentNetwork(ip_addr, config.VM_PASSWORD)
        stop_vms_safely([self.base_vm])

        disks_objs = getObjDisks(self.base_vm, get_href=False)

        target_domain = get_disk_storage_domain_name(
            disks_objs[0].get_alias(), self.base_vm)

        logger.info("Creating template %s from vm %s to storage domain %s",
                    self.test_templates[0], self.base_vm, target_domain)
        assert createTemplate(
            True, True, vm=self.base_vm, name=self.test_templates[0],
            cluster=config.CLUSTER_NAME, storagedomain=target_domain)

        second_domain = get_other_storage_domain(
            disks_objs[0].get_alias(), storage_type=self.storage)

        target_domain = filter(
            lambda w: w != second_domain, self.storage_domains)[0]

        logger.info("Creating second template %s from vm %s to storage domain "
                    "%s",
                    self.test_templates[1], self.base_vm, target_domain)
        assert createTemplate(True, True, vm=self.base_vm,
                              name=self.test_templates[1],
                              cluster=config.CLUSTER_NAME,
                              storagedomain=target_domain)

        copy_template_disks(
            True, self.test_templates[1], "%s_Disk1" % self.base_vm,
            second_domain)
        assert waitForTemplatesStates(
            names=",".join(self.test_templates))

        for templ in self.test_templates:
            wait_for_template_disks_state(templ)

    def setUp(self):
        """
        Prepares templates test_templates and vms based on that templates
        """
        self.storage_domains = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )
        self._prepare_templates()
        for template, vm_name in zip(self.test_templates, self.vm_names):
            dsks = getObjDisks(
                template, get_href=False, is_template=True)

            target_sd = dsks[0].storage_domains.storage_domain[0].get_name()

            if not addVm(True, name=vm_name, cluster=config.CLUSTER_NAME,
                         storagedomain=target_sd,
                         template=template):
                raise exceptions.VMException(
                    "Cannot create vm %s from template %s on storage "
                    "domain %s" % (vm_name, template, target_sd))

        start_vms(self.base_vm, 1)
        waitForVMState(self.base_vm)

    @polarion("RHEVM3-5993")
    def test_thin_provision_copy_template_on_both_domains(self):
        """
        template is copied to both domains:
        - create a vm from template and run the vm
        - move vm to target domain
        """
        live_migrate_vm(self.vm_names[0], LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()

    @polarion("RHEVM3-5993")
    def test_thin_provision_copy_template_on_one_domain(self):
        """
        template is copied on only one domain
        - create vm from template and run the vm
        - move the vm to second domain
        """
        live_migrate_vm(self.vm_names[1], LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()

    def tearDown(self):
        """
        Removes vms and templates
        """
        for vm in self.vm_names:
            if not removeVm(True, vm, stopVM='true'):
                raise exceptions.VMException(
                    "Cannot remove or stop vm %s" % vm)

        for template in self.test_templates:
            if not removeTemplate(True, template):
                raise exceptions.TemplateException(
                    "Failed to remove template %s" % template)


@attr(tier=1)
class TestCase5992(BaseTestCase):
    """
    snapshots and move vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5992'
    snapshot_desc = 'snap1'

    def _prepare_snapshots(self, vm_name):
        """
        Creates one snapshot on the input vm
        """
        wait_for_jobs()
        logger.info("Add snapshot to vm %s", vm_name)
        if not addSnapshot(True, vm_name, self.snapshot_desc):
            raise exceptions.VMException(
                "Add snapshot to vm %s failed" % vm_name)
        wait_for_vm_snapshots(
            vm_name, config.SNAPSHOT_OK,
        )
        start_vms([vm_name], 1,  wait_for_ip=False)
        waitForVMState(vm_name)

    def setUp(self):
        """
        Creates snapshot
        """
        super(TestCase5992, self).setUp()
        self._prepare_snapshots(self.vm_name)

    @polarion("RHEVM3-5992")
    def test_snapshot(self):
        """
        Tests live migrating vm containing snapshot
        - vm with snapshots
        - run the vm
        - migrate the vm to second domain
        """
        live_migrate_vm(self.vm_name)


@attr(tier=1)
class TestCase5991(BaseTestCase):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '5991'
    test_vm_name = 'test_vm_%s' % polarion_test_case
    permutation = {}
    disk_name = "disk_%s" % polarion_test_case

    def _prepare_shared_disk_environment(self):
            """
            Creates second vm and shared disk for both of vms
            """
            logger.info('Creating vm')
            if not addVm(True, wait=True, name=self.test_vm_name,
                         cluster=config.CLUSTER_NAME):
                raise exceptions.VMException("Failed to create vm %s"
                                             % self.test_vm_name)
            disk_args = {
                'alias': self.disk_name,
                'provisioned_size': config.DISK_SIZE,
                'interface': config.VIRTIO,
                'format': config.RAW_DISK,
                'sparse': False,
                'active': True,
                'storagedomain': self.storage_domains[0],
                'shareable': True
            }
            logger.info("Adding new disk %s" % self.disk_name)
            addDisk(True, **disk_args)
            wait_for_disks_status(self.disk_name)
            storage_helpers.prepare_disks_for_vm(
                self.test_vm_name, [self.disk_name],
            )
            storage_helpers.prepare_disks_for_vm(
                self.vm_name, [self.disk_name],
            )

    def setUp(self):
        """
        Prepare environment with shared disk
        """
        super(TestCase5991, self).setUp()
        self._prepare_shared_disk_environment()

    @polarion("RHEVM3-5991")
    def test_lsm_with_shared_disk(self):
        """
        create and run several vm's with the same shared disk
        - try to move one of the vm's images
        """
        target_sd = get_other_storage_domain(
            self.disk_name, self.vm_name, self.storage,
        )
        live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd)
        wait_for_jobs()

    def tearDown(self):
        """
        Removed created snapshots
        """
        stop_vms_safely([self.vm_name, self.test_vm_name])
        waitForVmsStates(
            True, [self.vm_name, self.test_vm_name], config.VM_DOWN,
        )
        if checkDiskExists(True, self.disk_name):
            if not removeDisk(True, self.vm_name, self.disk_name):
                logger.error(
                    "Cannot remove disk %s from vm %s", self.disk_name,
                    self.vm_name,
                )
        if not removeVm(True, self.test_vm_name):
            logger.error("Cannot remove vm %s", self.vm_name)
        super(TestCase5991, self).tearDown()


@attr(tier=1)
class TestCase5989(BaseTestCase):
    """
    suspended vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5989'

    def setUp(self):
        super(TestCase5989, self).setUp()
        startVm(True, self.vm_name, config.VM_UP)

    def _suspended_vm_and_wait_for_state(self, state):
        """
        Suspending vm and perform LSM after vm is in desired state
        """
        assert suspendVm(True, self.vm_name, wait=False)
        assert waitForVMState(self.vm_name, state)
        live_migrate_vm(
            self.vm_name, LIVE_MIGRATION_TIMEOUT, ensure_on=False,
        )
        wait_for_jobs()

    @polarion("RHEVM3-5989")
    def test_lsm_while_saving_state(self):
        """
        1) saving state
            - create and run a vm
            - suspend the vm
            - try to move vm's images while vm is in saving state
        * We should not be able to migrate images
        """
        self.assertRaises(exceptions.DiskException,
                          self._suspended_vm_and_wait_for_state,
                          config.VM_SAVING)

    @polarion("RHEVM3-5989")
    def test_lsm_while_suspended_state(self):
        """
        2) suspended state
            - create and run a vm
            - suspend the vm
            - try to migrate the vm's images once the vm is suspended
        * We should not be able to migrate images
        """
        self.assertRaises(exceptions.DiskException,
                          self._suspended_vm_and_wait_for_state,
                          config.VM_SUSPENDED)

    def tearDown(self):
        """Stop the vm in suspend state"""
        # Make sure the vm is in suspended state before stopping it
        waitForVMState(self.vm_name, config.VM_SUSPENDED)
        stopVm(True, self.vm_name)
        super(TestCase5989, self).tearDown()


@attr(tier=1)
class TestCase5988(AllPermutationsDisks):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5988'
    snapshot_desc = 'snap_%s' % polarion_test_case
    snap_created = None

    def setUp(self):
        """Start the vm"""
        super(TestCase5988, self).setUp()
        startVm(True, self.vm_name, config.VM_UP)

    def _prepare_snapshots(self, vm_name):
        """
        Creates one snapshot on the vm vm_name
        """
        logger.info("Creating new snapshot for vm %s", vm_name)
        if not addSnapshot(True, vm_name, self.snapshot_desc):
            raise exceptions.VMException(
                "Add snapshot to vm %s failed" % vm_name,
            )
        wait_for_vm_snapshots(
            vm_name, config.SNAPSHOT_OK, self.snapshot_desc,
        )

    @polarion("RHEVM3-5988")
    def test_lsm_before_snapshot(self):
        """
        1) move -> create snapshot
            - create and run a vm
            - move vm's
            - try to create a live snapshot
        * we should succeed to create a live snapshot
        """
        live_migrate_vm(self.vm_name, LIVE_MIGRATION_TIMEOUT)
        self.verify_lsm()
        self._prepare_snapshots(self.vm_name)

    @polarion("RHEVM3-5988")
    def test_lsm_after_snapshot(self):
        """
        2) create snapshot -> move
            - create and run a vm
            - create a live snapshot
            - move the vm's images
        * we should succeed to move the vm
        """
        self._prepare_snapshots(self.vm_name)
        live_migrate_vm(self.vm_name, LIVE_MIGRATION_TIMEOUT)
        self.verify_lsm()

    @polarion("RHEVM3-5988")
    def test_lsm_while_snapshot(self):
        """
        3) move + create snapshots
            - create and run a vm
            - try to create a live snapshot + move
        * we should block move+create live snapshot in backend.
        """
        for disk in helpers.DISK_NAMES[self.storage]:
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage,
            )
            live_migrate_vm_disk(
                self.vm_name, disk, target_sd,
                timeout=LIVE_MIGRATION_TIMEOUT, wait=False,
            )
            self.assertRaises(
                exceptions.VMException, self._prepare_snapshots, self.vm_name,
            )


@attr(tier=1)
class TestCase5986(CommonUsage):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5986'
    disk_name = "disk_%s" % polarion_test_case

    def setUp(self):
        """
        Prepares a floating disk
        """
        super(TestCase5986, self).setUp()
        helpers.add_new_disk_for_test(self.vm_name, self.disk_name,
                                      provisioned_size=(60 * config.GB),
                                      wipe_after_delete=True, attach=True,
                                      sd_name=self.storage_domains[0])
        wait_for_disks_status(self.disk_name)
        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5986")
    def test_vms_live_migration(self):
        """
        Actions:
            - create a vm with large preallocated+wipe after
              delete disk
            - run vm
            - move vm's images to second domain
        Expected Results:
            - move should succeed
        """
        target_sd = get_other_storage_domain(
            self.disk_name, self.vm_name, self.storage,
        )
        live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd,
                             timeout=LIVE_MIGRATE_LARGE_SIZE, wait=True)
        wait_for_jobs(timeout=LIVE_MIGRATE_LARGE_SIZE)

    def tearDown(self):
        """
        Restore environment
        """
        super(TestCase5986, self).tearDown()
        self._remove_disks([self.disk_name])


@attr(tier=1)
class TestCase5955(AllPermutationsDisks):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5955'
    snapshot_desc = 'snap_%s' % polarion_test_case
    disk_to_move = ''

    def _perform_action(self, vm_name, disk_name):
        """
        Move one disk to second storage domain
        """
        self.disk_to_move = disk_name
        target_sd = get_other_storage_domain(
            self.disk_to_move, vm_name, self.storage,
        )
        move_vm_disk(vm_name, self.disk_to_move, target_sd)
        wait_for_jobs()
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
        target_sd = get_other_storage_domain(
            self.disk_to_move, vm_name, self.storage,
        )
        live_migrate_vm_disk(
            self.vm_name, self.disk_to_move, target_sd,
            LIVE_MIGRATION_TIMEOUT,
        )
        wait_for_jobs()

    @polarion("RHEVM3-5955")
    def test_lsm_with_image_on_target(self):
        """
        move disk images to a domain that already has one of the images on it
        """
        for disk in helpers.DISK_NAMES[self.storage]:
            self._perform_action(self.vm_name, disk)


@attr(tier=1)
class TestCase5996(CommonUsage):
    """
    hot plug disk
    1) inactive disk
    - create and run a vm
    - hot plug a floating disk and keep it inactive
    - move the disk images to a different domain
    2) active disk
    - create and run a vm
    - hot plug a disk and activate it
    - move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5996'
    disk_name_pattern = "floating_%s_%s"

    def setUp(self):
        """
        Prepares a floating disk
        """
        super(TestCase5996, self).setUp()
        self.disk_name_pattern = self.disk_name_pattern \
            % (self.polarion_test_case, self.__class__.__name__)
        startVm(True, self.vm_name, config.VM_UP)
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name_pattern, sparse=True,
            disk_format=config.COW_DISK,
            sd_name=self.storage_domains[0],
        )

    def _test_plugged_disk(self, vm_name, activate=True):
        """
        Performs migration with hotplugged disk
        """
        disk_name = self.disk_name_pattern
        logger.info("Attaching disk %s to vm %s", disk_name, vm_name)
        if not attachDisk(True, disk_name, vm_name, active=activate):
            raise exceptions.DiskException(
                "Cannot attach floating disk %s to vm %s" %
                (disk_name, vm_name))
        inactive_disk = getVmDisk(vm_name, disk_name)
        if activate and not inactive_disk.get_active():
            logger.warning("Disk %s in vm %s is not active after attaching",
                           disk_name, vm_name)
            assert activateVmDisk(True, vm_name, disk_name)

        elif not activate and inactive_disk.get_active():
            logger.warning("Disk %s in vm %s is active after attaching",
                           disk_name, vm_name)
            assert deactivateVmDisk(True, vm_name, disk_name)
        logger.info("%s disks active: %s %s", disk_name,
                    inactive_disk.get_active(),
                    type(inactive_disk.get_active()))
        waitForVmsDisks(vm_name)
        live_migrate_vm(vm_name, LIVE_MIGRATION_TIMEOUT)
        logger.info("Migration completed, cleaning snapshots")
        remove_all_vm_lsm_snapshots(vm_name)
        wait_for_jobs()
        if not detachDisk(True, disk_name, vm_name):
            raise exceptions.DiskException(
                "Cannot detach floating disk %s from vm %s" %
                (disk_name, vm_name))
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)

    @polarion("RHEVM3-5996")
    def test_inactive_disk(self):
        """
        Tests storage live migration with one disk in inactive status
        """
        self._test_plugged_disk(self.vm_name, False)

    @polarion("RHEVM3-5996")
    def test_active_disk(self):
        """
        Tests storage live migration with floating disk in active status
        """
        self._test_plugged_disk(self.vm_name)

    def tearDown(self):
        """Remove floating disk"""
        if not deleteDisk(True, self.disk_name_pattern):
            logger.error("Failure to remove disk %s", self.disk_name_pattern)
        super(TestCase5996, self).tearDown()


@attr(tier=1)
class TestCase6003(BaseTestCase):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '6003'
    disk_alias = 'disk_%s' % polarion_test_case

    def setUp(self):
        """
        Prepares a floating disk
        """
        super(TestCase6003, self).setUp()
        startVm(True, self.vm_name, config.VM_UP)
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_alias, sparse=True,
            disk_format=config.COW_DISK,
            sd_name=self.storage_domains[0])

    @polarion("RHEVM3-6003")
    def test_attach_disk_during_lsm(self):
        """
        migrate vm's images -> try to attach a disk during migration
        * we should fail to attach disk
        """
        live_migrate_vm(self.vm_name, timeout=LIVE_MIGRATION_TIMEOUT,
                        wait=False)
        status = attachDisk(True, self.disk_alias, self.vm_name)
        self.assertFalse(status, "Succeeded to attach disk during LSM")

    def tearDown(self):
        """Remove floating disk"""
        if not deleteDisk(True, self.disk_alias):
            logger.error("Failure to remove disk %s", self.disk_alias)
        super(TestCase6003, self).tearDown()


@attr(tier=1)
class TestCase6001(BaseTestCase):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '6001'
    disk_alias = 'disk_%s' % polarion_test_case
    succeeded = False

    def setUp(self):
        """
        Prepares one domain in maintenance
        """
        super(TestCase6001, self).setUp()
        startVm(True, self.vm_name, config.VM_UP)
        self.vm_disk = getVmDisks(self.vm_name)[0]
        self.target_sd = get_other_storage_domain(
            self.vm_disk.get_alias(), self.vm_name, self.storage,
        )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        deactivateStorageDomain(True, config.DATA_CENTER_NAME, self.target_sd)
        assert waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            ENUMS['storage_domain_state_maintenance'])

    @polarion("RHEVM3-6001")
    def test_lsm_to_maintenance_domain(self):
        """
        try to migrate to a domain in maintenance
        * we should fail to attach disk
        """
        self.assertRaises(exceptions.DiskException, live_migrate_vm_disk,
                          self.vm_name, self.vm_disk.get_alias(),
                          self.target_sd, LIVE_MIGRATION_TIMEOUT, True)
        self.succeeded = True

    def tearDown(self):
        wait_for_jobs()
        assert activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.target_sd)
        super(TestCase6001, self).tearDown()


@attr(tier=1)
class TestCase5972(CommonUsage):
    """
    live migrate vm with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5972'
    disk_name = "disk_%s_%s"
    disk_count = 3

    def setUp(self):
        """
        Prepares disks on different domains
        """
        super(TestCase5972, self).setUp()
        self.disks_names = []
        stop_vms_safely([self.vm_name])
        self._prepare_disks_for_vm(self.vm_name)
        startVm(True, self.vm_name, config.VM_UP)

    def _prepare_disks_for_vm(self, vm_name):
            """
            Prepares disk for given vm
            """
            disk_params = {
                'alias': self.disk_name,
                'provisioned_size': 1 * config.GB,
                'interface': config.VIRTIO,
                'format': config.RAW_DISK,
                'sparse': False,
                'wipe_after_delete': False,
                'storagedomain': None
            }

            for index in range(self.disk_count):
                disk_params['alias'] = \
                    self.disk_name % (index, self.polarion_test_case)
                disk_params['storagedomain'] = self.storage_domains[index]
                if not addDisk(True, **disk_params):
                    raise exceptions.DiskException(
                        "Can't create disk with params: %s" % disk_params)
                logger.info("Waiting for disk %s to be ok",
                            disk_params['alias'])
                wait_for_disks_status(disk_params['alias'])
                self.disks_names.append(disk_params['alias'])
                assert attachDisk(True, disk_params['alias'], vm_name)

    @polarion("RHEVM3-5972")
    def test_live_migration_with_multiple_disks(self):
        """
        Actions:
            - 1 vm with disks on 3 of the 3 domains
            - live migrate the vm to the 3rd domain
        Expected Results:
            - move should succeed
        """
        for disk in self.disks_names[:-1]:
            live_migrate_vm_disk(self.vm_name, disk, self.storage_domains[2])


@attr(tier=1)
class TestCase5970(CommonUsage):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    polarion_test_case = '5970'
    disk_name = "disk_%s" % polarion_test_case
    regex = 'dd oflag=direct if=/dev/zero of=.*/%s'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        super(TestCase5970, self).setUp()
        helpers.add_new_disk_for_test(self.vm_name, self.disk_name,
                                      wipe_after_delete=True, attach=True,
                                      sd_name=self.storage_domains[0])
        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5970")
    def test_live_migration_wipe_after_delete(self):
        """
        Actions:
            - create a vm with wipe after delete disk
            - run the vm
            - migrate the disk
        Expected Results:
            - move should succeed
            - make sure that we actually post zero when removing the source
              disk and snapshot
        """
        host = getSPMHost(config.HOSTS)
        self.host_ip = getHostIP(host)
        target_sd = get_other_storage_domain(
            self.disk_name, self.vm_name, self.storage)
        disk_obj = getVmDisk(self.vm_name, self.disk_name)
        self.regex = self.regex % disk_obj.get_image_id()

        def f(q):
            q.put(
                watch_logs(
                    files_to_watch=FILE_TO_WATCH, regex=self.regex,
                    time_out=LIVE_MIGRATION_TIMEOUT,
                    ip_for_files=self.host_ip,
                    username=config.HOSTS_USER, password=config.HOSTS_PW
                )
            )

        q = Queue()
        p = Process(target=f, args=(q,))
        p.start()
        sleep(5)
        live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd,
                             wait=False)
        p.join()
        wait_for_jobs()
        exception_code, output = q.get()
        self.assertTrue(
            exception_code,
            "Couldn't find regex %s, output: %s" % (self.regex, output),
        )


@attr(tier=1)
class TestCase5969(AllPermutationsDisks):
    """
    Power off/Shutdown of vm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5969'

    def setUp(self):
        """Start the vm"""
        super(TestCase5969, self).setUp()
        startVm(True, self.vm_name, config.VM_UP)

    def turn_off_method(self):
        raise NotImplemented("This should not be executed")

    def _perform_action_on_disk_and_wait_for_regex(self, disk_name, regex):
        host = getSPMHost(config.HOSTS)
        self.host_ip = getHostIP(host)
        target_sd = get_other_storage_domain(
            disk_name, self.vm_name, self.storage)

        def f(q):
            q.put(
                watch_logs(
                    files_to_watch=FILE_TO_WATCH, regex=regex,
                    time_out=MIGRATION_TIMEOUT, ip_for_files=self.host_ip,
                    username=config.HOSTS_USER, password=config.HOSTS_PW
                )
            )
        q = Queue()
        p = Process(target=f, args=(q,))
        p.start()
        sleep(5)
        live_migrate_vm_disk(self.vm_name, disk_name, target_sd,
                             wait=False)
        p.join()
        ex_code, output = q.get()
        self.assertTrue(
            ex_code,
            "Couldn't find regex %s, output: %s" % (regex, output)
        )
        self.turn_off_method()
        # Is need to wait for the rollback after the LSM fails
        wait_for_jobs()
        self.assertFalse(
            verify_vm_disk_moved(self.vm_name, disk_name, self.disk_sd),
            "Succeeded to live migrate vm disk %s" % disk_name,
        )

    @polarion("RHEVM3-5969")
    def test_power_off_createVolume(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'createVolume' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISK_NAMES[self.storage]:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'createVolume',
            )

    @polarion("RHEVM3-5969")
    def test_power_off_cloneImageStructure(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'cloneImageStructure' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISK_NAMES[self.storage]:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'cloneImageStructure',
            )

    @polarion("RHEVM3-5969")
    def test_power_off_syncImageData(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'syncImageData' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISK_NAMES[self.storage]:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'syncImageData',
            )

    @polarion("RHEVM3-5969")
    def test_power_off_deleteImage(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'deleteImage' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISK_NAMES[self.storage]:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'deleteImage'
            )


class TestCase5969PowerOff(TestCase5969):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        stopVm(True, self.vm_name, 'false')


class TestCase5969Shutdown(TestCase5969):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        shutdownVm(True, self.vm_name, 'false')


@attr(tier=1)
class TestCase5968(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5968'

    @polarion("RHEVM3-5968")
    def test_live_migration_auto_shrink(self):
        """
        Actions:
            - 2 data storage domains
            - create -> run the vm -> move the vm
            - shut down the vm once the move is finished
            - delete the Live migration snapshot

        Expected Results:
            - the image actual size should not exceed the disks
              virtual size once we delete the snapshot
        """
        for disk in helpers.DISK_NAMES[self.storage]:
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage,
            )
            startVm(True, self.vm_name, config.VM_UP)
            live_migrate_vm_disk(self.vm_name, disk, target_sd)
            assert stopVm(True, self.vm_name)
            remove_all_vm_lsm_snapshots(self.vm_name)
            wait_for_jobs()
            disk_obj = getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info("Actual size after live migrate disk %s is: %s",
                        disk, actual_size)
            logger.info("Virtual size after live migrate disk %s is: %s",
                        disk, virtual_size)
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            self.assertTrue(
                actual_size <= virtual_size,
                "Actual size exceeded to virtual size",
            )


@attr(tier=1)
class TestCase5967(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5967'

    @polarion("RHEVM3-5967")
    def test_live_migration_auto_shrink(self):
        """
        Actions:
            - 2 data storage domains
            - create -> run the vm -> move the vm
            - shut down the vm once the move is finished
            - delete the Live migration snapshot

        Expected Results:
            - the image actual size should not exceed the disks
              virtual size once we delete the snapshot
            - make sure that we can delete the snapshot and run the vm
        """
        for disk in helpers.DISK_NAMES[self.storage]:
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage,
            )
            startVm(True, self.vm_name, config.VM_UP)
            live_migrate_vm_disk(
                self.vm_name, disk, target_sd, wait=True,
            )
            assert stopVm(True, self.vm_name)
            remove_all_vm_lsm_snapshots(self.vm_name)
            wait_for_jobs()
            disk_obj = getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info("Actual size after live migrate disk %s is: %s",
                        disk, actual_size)
            logger.info("Virtual size after live migrate disk %s is: %s",
                        disk, virtual_size)
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            self.assertTrue(
                actual_size <= virtual_size,
                "Actual size exceeded virtual size"
            )


@attr(tier=1)
class TestCase5982(AllPermutationsDisks):
    """
    merge snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5982'

    @polarion("RHEVM3-5982")
    def test_merge_snapshot_live_migration(self):
        """
        Actions:
            - LSM the vm's disk -> write to the vm during the migration
            - after the LSM finished stop the vm
            - delete the LSM snapshot
            - run the vm
        Expected Results:
            - we should succeed to delete the snapshot
            - we should succeed to run the vm
        """
        for index, disk in enumerate(helpers.DISK_NAMES[self.storage]):
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage,
            )
            startVm(True, self.vm_name, config.VM_UP)
            live_migrate_vm_disk(self.vm_name, disk, target_sd, wait=False)

            status, _ = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk, size=int(config.DISK_SIZE * 0.9),
                write_to_file=True,
            )
            if not status:
                raise exceptions.DiskException(
                    "Failed to perform dd operation on disk %s" % disk
                )

            wait_for_jobs()
            stop_vms_safely([self.vm_name])
            remove_all_vm_lsm_snapshots(self.vm_name)
            wait_for_jobs()


@attr(tier=1)
class TestCase5979(BaseTestCase):
    """
    offline migration for disk attached to running vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5979'
    disk_name = "disk_%s" % polarion_test_case
    expected_lsm_snap_count = 0

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        # If any LSM snapshot exists --> remove them to be able to check if
        # the disk movement in this case is cold move and not live storage
        # migration

        super(TestCase5979, self).setUp()
        remove_all_vm_lsm_snapshots(self.vm_name)
        wait_for_jobs()
        helpers.add_new_disk_for_test(self.vm_name, self.disk_name,
                                      attach=True,
                                      sd_name=self.storage_domains[0])
        assert deactivateVmDisk(True, self.vm_name, self.disk_name)
        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5979")
    def test_offline_migration(self):
        """
        Actions:
            - create a vm with 1 disk and start the vm
            - attach a disk but remove the "active" tag so that the disk
              will be inactive
            - move the inactive disk
        Expected Results:
            - we should succeed to migrate the disk offline
              (as in not with LSM command)
        """
        target_sd = get_other_storage_domain(
            self.disk_name, self.vm_name, self.storage,
        )
        live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd)
        wait_for_jobs()

        snapshots = get_vm_snapshots(self.vm_name)
        LSM_snapshots = [s for s in snapshots if
                         (s.get_description() ==
                          config.LIVE_SNAPSHOT_DESCRIPTION)]
        logger.info("Verify that the migration was not live migration")
        self.assertEqual(len(LSM_snapshots), self.expected_lsm_snap_count)


@attr(tier=1)
class TestCase5976(BaseTestCase):
    """
    Deactivate vm disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5976'
    disk_name = "disk_%s" % polarion_test_case

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        super(TestCase5976, self).setUp()
        helpers.add_new_disk_for_test(self.vm_name, self.disk_name,
                                      attach=True,
                                      sd_name=self.storage_domains[0])
        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5976")
    def test_deactivate_disk_during_lsm(self):
        """
        Actions:
            - create a vm with two disks and run it
            - start a LSM on the vm disk
            - deactivate the non-boot disk.
        Expected Results:
            - we should block with canDoAction
        """
        target_sd = get_other_storage_domain(
            self.disk_name, self.vm_name, self.storage)
        live_migrate_vm_disk(self.vm_name, self.disk_name,
                             target_sd=target_sd, wait=False)
        sleep(5)
        status = deactivateVmDisk(False, self.vm_name, self.disk_name)
        self.assertTrue(status, "Succeeded to deactivate vm disk %s during "
                                "live storage migration" % self.disk_name)

    def tearDown(self):
        """Remove the extra disk"""
        wait_for_jobs()
        wait_for_disks_status([self.disk_name])
        if not removeDisk(True, self.vm_name, self.disk_name):
            logger.error("Unable to remove disk %s", self.disk_name)
        super(TestCase5976, self).tearDown()


@attr(tier=1)
class TestCase5977(BaseTestCase):
    """
    migrate a vm between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5977'

    def _migrate_vm_during_lsm_ops(self, wait):
        live_migrate_vm(self.vm_name, wait=wait)
        status = migrateVm(True, self.vm_name, wait=False)
        wait_for_jobs()
        return status

    @polarion("RHEVM3-5977")
    def test_LSM_during_vm_migration(self):
        """
        Actions:
            - create and run a vm
            - migrate the vm between the hosts
            - try to LSM the vm disk during the vm migration
        Expected Results:
            - we should be stopped by CanDoAction
        """
        disk_name = getVmDisks(self.vm_name)[0].get_alias()
        target_sd = get_other_storage_domain(
            disk_name, self.vm_name, self.storage,
        )
        startVm(True, self.vm_name, config.VM_UP)
        migrateVm(True, self.vm_name, wait=False)
        self.assertRaises(exceptions.DiskException, live_migrate_vm_disk,
                          self.vm_name, disk_name, target_sd)

    @polarion("RHEVM3-5977")
    def test_migrate_vm_during_snap_creation_of_LSM(self):
        """
        Actions:
            - create and run a vm
            - start a LSM for the vm disk
            - try to migrate the vm between hosts during the create snapshot
              step
        Expected Results:
            - we should be stopped by CanDoAction
        """
        status = self._migrate_vm_during_lsm_ops(wait=False)
        self.assertFalse(status, "Succeeded to migrate vm during LSM")

    @polarion("RHEVM3-5977")
    def test_migrate_vm_after_LSM(self):
        """
        Actions:
            - create a vm and run it
            - start a LSM
            - when the LSM is finishes
            - try to migrate the vm
        Expected Results:
            - we should succeed
        """
        status = self._migrate_vm_during_lsm_ops(wait=True)
        self.assertTrue(status, "Succeeded to migrate vm during LSM")


@attr(tier=1)
class TestCase5975(BaseTestCase):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False  # Needs 4 iscsi storage domains (only on block device)
    polarion_test_case = '5975'

    def generate_sd_dict(self, index):
        return {
            'storage_type': BaseTestCase.storage,
            'host': config.HOSTS[0],
            'lun': LOCAL_LUN[index],
            'lun_address': LOCAL_LUN_ADDRESS[index],
            'lun_target': LOCAL_LUN_TARGET[index],
            'lun_port': config.LUN_PORT
        }

    def setUp(self):
        """Set the args with luns"""
        self.sd_src = "src_domain_%s" % self.polarion_test_case
        self.sd_target = "target_domain_%s" % self.polarion_test_case
        for index, sd_name in [self.sd_src, self.sd_target]:
            sd_name_dict = self.generate_sd_dict(index)
            sd_name_dict.update(
                {"storage": sd_name, "data_center": config.DATA_CENTER_NAME}
            )
            if not addISCSIDataDomain(**sd_name_dict):
                logger.error("Error adding storage %s", sd_name_dict)

            wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                           config.DATA_CENTER_NAME)

        self.vm_sd = self.sd_src
        super(TestCase5975, self).setUp()

    @polarion("RHEVM3-5975")
    def test_extend_domains_during_LSM(self):
        """
        Actions:
            - create and run a vm
            - Live migrate the VM disk to the second iSCSI domain
            - While LSM is running, try to extend both the SRC and the DST
              domains

        Expected Results:
            - LSM should succeed
            - Extend storage domain to both domains should succeed
        """
        disk_name = getVmDisks(self.vm_name)[0].get_alias()
        startVm(True, self.vm_name, config.VM_UP)
        live_migrate_vm_disk(
            self.vm_name, disk_name, self.sd_target, wait=False,
        )
        extendStorageDomain(True, self.sd_src, **self.generate_sd_dict(2))
        extendStorageDomain(True, self.sd_target, **self.generate_sd_dict(3))

    def tearDown(self):
        """Remove the added storage domains"""
        super(TestCase5975, self).tearDown()
        for sd_name in [self.sd_src, self.sd_target]:
            remove_storage_domain(sd_name, config.HOSTS[0], True)
            wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                           config.DATA_CENTER_NAME)


@attr(tier=3)
class TestCase6000(BaseTestCase):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
    bz = {'1106593': {'engine': None, 'version': ["3.5"]}}
    polarion_test_case = '6000'

    def _migrate_vm_disk_and_block_connection(self, disk, source, username,
                                              password, target,
                                              target_ip):

        startVm(True, self.vm_name, config.VM_UP)
        live_migrate_vm_disk(self.vm_name, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password,
                                         target_ip)
        self.assertTrue(status, "Failed to block connection")
        wait_for_jobs()

    @polarion("RHEVM3-6000")
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        spm_host = getSPMHost(config.HOSTS)
        host_ip = getHostIP(spm_host)
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        target_sd = get_other_storage_domain(
            vm_disk, self.vm_name, self.storage)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, host_ip, config.HOSTS_USER, config.HOSTS_PW, target_sd,
            target_sd_ip)
        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)

        super(TestCase6000, self).setUp()


@attr(tier=3)
class TestCase6002(BaseTestCase):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '6002'
    bz = {'1210771': {'engine': None, 'version': ["3.5", "3.6"]}}

    @polarion("RHEVM3-6002")
    def test_restart_spm_during_lsm(self):
        """
        Actions:
            - run vm's on host
            - start a live migrate of vm
            - restart vdsm
        Expected Results:
            - live migrate should fail
        """
        spm_host = getHostIP(getSPMHost(config.HOSTS))
        live_migrate_vm(self.vm_name, wait=False)
        restartVdsmd(spm_host, config.HOSTS_PW)


@attr(tier=1)
class TestCase5999(BaseTestCase):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5999'
    bz = {'1210771': {'engine': None, 'version': ["3.5", "3.6"]}}

    @polarion("RHEVM3-5999")
    def test_reboot_spm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (spm)
        Expected Results:
            - we should fail migration
        """
        spm_host = getSPMHost(config.HOSTS)
        assert updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=spm_host,
        )
        startVm(True, self.vm_name, config.VM_UP)
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        live_migrate_vm(self.vm_name, wait=False)
        logger.info("Rebooting host (SPM) %s", spm_host)
        assert rebootHost(
            True, spm_host, config.HOSTS_USER, config.HOSTS_PW,
        )
        logger.info("Waiting for host %s to come back up", spm_host)
        waitForHostsStates(True, spm_host)
        wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        self.assertFalse(
            status,
            "Succeeded to live migrate vm disk %s during SPM host reboot" %
            vm_disk,
        )

    @polarion("RHEVM3-5999")
    def test_reboot_hsm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (hsm)
        Expected Results:
            - we should fail migration
        """
        spm_host = [getSPMHost(config.HOSTS)]
        hsm_host = [x for x in config.HOSTS if x not in spm_host][0]
        assert updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=hsm_host,
        )
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        live_migrate_vm(self.vm_name, wait=False)
        logger.info("Rebooting host (HSM) %s", hsm_host)
        assert rebootHost(
            True, hsm_host, config.HOSTS_USER, config.HOSTS_PW)
        logger.info("Waiting for host %s to be UP", hsm_host)
        waitForHostsStates(True, hsm_host)

        wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)


@attr(tier=3)
class TestCase5998(BaseTestCase):
    """
    reboot host during live migration on HA vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    bz = {'1210771': {'engine': None, 'version': ["3.5", "3.6"]}}
    polarion_test_case = '5998'

    def _perform_action(self, host):
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)

        live_migrate_vm(self.vm_name, wait=False)
        logger.info("Rebooting host %s", host)
        assert rebootHost(True, host, config.HOSTS_USER, config.HOSTS_PW)
        logger.info("Waiting for host %s to be UP", host)
        waitForHostsStates(True, host)
        wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

    @polarion("RHEVM3-5998")
    def test_reboot_spm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (spm)
        Expected Results:
            - we should fail migration
        """
        spm_host = getSPMHost(config.HOSTS)
        assert updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=spm_host
        )
        startVm(True, self.vm_name, config.VM_UP)
        self._perform_action(spm_host)

    @polarion("RHEVM3-5998")
    def test_reboot_hsm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (hsm)
        Expected Results:
            - we should fail migration
        """
        spm_host = [getSPMHost(config.HOSTS)]
        hsm_host = [host for host in config.HOSTS if host not in spm_host][0]
        assert updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=hsm_host
        )
        startVm(True, self.vm_name, config.VM_UP)
        self._perform_action(hsm_host)


@attr(tier=3)
class TestCase5997(BaseTestCase):
    """
    kill vm's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
    polarion_test_case = '5997'

    def _kill_vm_pid(self):
        host = getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')
        host_machine.kill_qemu_process(self.vm_name)

    def perform_action(self):
        startVm(True, self.vm_name, config.VM_UP)

        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        live_migrate_vm(self.vm_name, wait=False)
        logger.info("Killing vms %s pid", self.vm_name)
        self._kill_vm_pid()

        wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

        wait_for_jobs()

    @polarion("RHEVM3-5997")
    def test_kill_ha_vm_pid_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - kill -9 vm's pid
        Expected Results:
            - we should fail migration
        """
        stop_vms_safely([self.vm_name], async=False)
        wait_for_jobs()
        assert updateVm(True, self.vm_name, highly_available='true')
        self.perform_action()

    @polarion("RHEVM3-5997")
    def test_kill_regular_vm_pid_during_lsm(self):
        """
        Actions:
            - run vm on host
            - start a live migrate of vm
            - kill -9 vm's pid
        Expected Results:
            - we should fail migration
        """
        stop_vms_safely([self.vm_name], async=True)
        assert updateVm(True, self.vm_name, highly_available='false')
        self.perform_action()


@attr(tier=1)
class TestCase5985(BaseTestCase):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # disks
    __test__ = False
    polarion_test_case = '5985'
    disk_name = "disk_%s" % polarion_test_case

    @polarion("RHEVM3-5985")
    def test_no_space_disk_during_lsm(self):
        """
        Actions:
            - start a live migration
            - while migration is running, create a large preallocated disk
        Expected Results:
            - migration or create disk should fail nicely.
        """
        startVm(True, self.vm_name, config.VM_UP)
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        target_sd = get_other_storage_domain(
            vm_disk, self.vm_name, self.storage)
        sd_size = get_free_space(target_sd)
        live_migrate_vm_disk(self.vm_name, vm_disk, target_sd, wait=False)
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name,
            provisioned_size=sd_size - (1 * config.GB),
            sd_name=target_sd)

        wait_for_disks_status([self.disk_name], timeout=TASK_TIMEOUT)
        wait_for_jobs()
        self.assertFalse(verify_vm_disk_moved(self.vm_name, vm_disk,
                                              source_sd, target_sd),
                         "Succeeded to live migrate vm disk %s" % vm_disk)

    def tearDown(self):
        """Remove created disk"""
        wait_for_jobs()
        wait_for_disks_status(self.disk_name)
        assert deleteDisk(True, self.disk_name)
        super(TestCase5985, self).tearDown()


@attr(tier=1)
class TestCase5971(CommonUsage):
    """
    multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5971'
    disk_count = 3

    def _prepare_disks_for_vm(self, vm_name):
            """
            Prepares disk for given vm
            """
            disk_params = {
                'provisioned_size': 1 * config.GB,
                'active': True,
                'interface': config.VIRTIO,
                'format': config.COW_DISK,
                'sparse': True,
                'wipe_after_delete': False,
                'storagedomain': None
            }

            for index in range(self.disk_count):

                disk_params['alias'] = "disk_%s_%s" % \
                                       (index, self.polarion_test_case)
                disk_params['storagedomain'] = self.storage_domains[index]
                if index == 2:
                    disk_params['active'] = False
                if not addDisk(True, **disk_params):
                    raise exceptions.DiskException(
                        "Can't create disk with params: %s" % disk_params)
                logger.info("Waiting for disk %s to be ok",
                            disk_params['alias'])
                wait_for_disks_status(disk_params['alias'])
                self.disks_names.append(disk_params['alias'])
                assert attachDisk(True, disk_params['alias'], vm_name,
                                  active=disk_params['active'])

    def setUp(self):
        """
        Prepares disks on different domains
        """
        self.disks_names = []
        super(TestCase5971, self).setUp()
        stop_vms_safely([self.vm_name])
        self._prepare_disks_for_vm(self.vm_name)
        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        assert deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.storage_domains[2],
        )

        waitForStorageDomainStatus(True, config.DATA_CENTER_NAME,
                                   self.storage_domains[2],
                                   config.SD_MAINTENANCE)
        wait_for_jobs()

        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5971")
    def test_lsm_with_multiple_disks_one_sd_in_maintenance(self):
        """
        Actions:
            - 1 vm with disks on 3 of the 3 domains
            - put the domain with the inactive disk in maintenance
            - start live migrate
        Expected Results:
            - we should fail migrate
        """
        for index, disk in enumerate(self.disks_names):
            src_sd = get_disk_storage_domain_name(disk, self.vm_name)
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage,
            )

            if index == 2:
                self.assertRaises(exceptions.DiskException,
                                  live_migrate_vm_disk, self.vm_name, disk,
                                  target_sd)

                self.assertFalse(verify_vm_disk_moved(self.vm_name,
                                                      disk, src_sd),
                                 "Succeeded to live migrate disk %s" % disk)
            else:
                live_migrate_vm_disk(self.vm_name, disk, target_sd=target_sd)
                self.assertTrue(verify_vm_disk_moved(self.vm_name,
                                                     disk, src_sd),
                                "Failed to live migrate disk %s" % disk)

        wait_for_jobs()

    def tearDown(self):
        """
        Removes disks and snapshots
        """
        activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.storage_domains[2],
        )
        waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.storage_domains[2],
            ENUMS['storage_domain_state_active'])
        super(TestCase5971, self).tearDown()


@attr(tier=1)
class TestCase5980(BaseTestCase):
    """
    offline migration + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5980'
    disk_name = "disk_%s" % polarion_test_case

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        super(TestCase5980, self).setUp()
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, sd_name=self.storage_domains[0],
        )
        startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5980")
    def test_offline_migration_and_lsm(self):
        """
        Actions:
            - create a vm with 1 disk
            - run the vm
            - live migrate the disk
            - try to attach a floating disk (attach as deactivate)
        Expected Results:
            - we should either not be able to attach the disk to a vm
              which is in the middle of LSM
        """
        live_migrate_vm(self.vm_name, wait=False)
        status = attachDisk(True, self.disk_name, self.vm_name)
        self.assertFalse(status, "Attache operation succeeded during LSM")

    def tearDown(self):
        """Remove the floating disk"""
        wait_for_jobs()
        super(TestCase5980, self).tearDown()
        assert deleteDisk(True, self.disk_name)


@attr(tier=3)
class TestCase5966(BaseTestCase):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
    polarion_test_case = '5966'

    @polarion("RHEVM3-5966")
    def test_kill_vdsm_during_lsm(self):
        """
        Actions:
            - run vm's on host
            - start a live migrate of vm
            - kill vdsm
        Expected Results:
            - LSM should fail nicely
        """
        startVm(True, self.vm_name, config.VM_UP)
        host = getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')

        live_migrate_vm(self.vm_name, wait=False)
        sleep(5)
        host_machine.kill_vdsm_service()
        wait_for_jobs()

    @polarion("RHEVM3-5966")
    def test_kill_vdsm_during_second_lsm(self):
        """
        Actions:
            - run vm's on host
            - start a live migrate of vm
            - once the move is finished repeat step2
            - kill vdsm
        Expected Results:
            - LSM should fail nicely
        """
        startVm(True, self.vm_name, config.VM_UP)
        host = getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')

        live_migrate_vm(self.vm_name, wait=True)
        live_migrate_vm(self.vm_name, wait=False)
        sleep(5)
        host_machine.kill_vdsm_service()

        wait_for_jobs()


@attr(tier=1)
class TestCase5981(AllPermutationsDisks):
    """
    merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5981'

    @polarion("RHEVM3-5981")
    def test_merge_snapshot_live_migration_failure(self):
        """
        Actions:
            - create a vm with OS installed
            - run the vm on hsm
            - start LSM and write to the vm -> fail LSM (power off the vm)
            - power off the vm
            - delete the snapshot
            - run the vm
        Expected Results:
            - LSM should fail nicely
            - we should be able to merge the snapshot
            - we should be able to run the vm
        """
        spm_host = [getSPMHost(config.HOSTS)]
        hsm_host = [x for x in config.HOSTS if x not in spm_host][0]
        updateVm(True, self.vm_name, placement_host=hsm_host)
        startVm(True, self.vm_name, config.VM_UP, True)
        for index, disk in enumerate(helpers.DISK_NAMES[self.storage]):
            source_sd = get_disk_storage_domain_name(disk, self.vm_name)
            target_sd = get_other_storage_domain(
                disk, self.vm_name, self.storage)
            logger.info("Make sure disk is accesible")
            assert get_vm_disk_logical_name(self.vm_name, disk)
            live_migrate_vm_disk(self.vm_name, disk, target_sd, wait=False)

            def f():
                status, _ = storage_helpers.perform_dd_to_disk(
                    self.vm_name, disk, size=int(config.DISK_SIZE * 0.9),
                    write_to_file=True,
                )

            logger.info("Writing to disk")
            p = Process(target=f, args=())
            p.start()
            status = storage_helpers.wait_for_dd_to_start(self.vm_name)
            self.assertTrue(status, "dd didn't start writing to disk")
            logger.info(
                "Stop the vm while the live storage migration is running",
            )
            stop_vms_safely([self.vm_name])
            waitForVMState(self.vm_name, config.VM_DOWN)
            wait_for_jobs()
            remove_all_vm_lsm_snapshots(self.vm_name)
            startVm(True, self.vm_name, config.VM_UP, True)
            self.assertFalse(
                verify_vm_disk_moved(
                    self.vm_name, disk, source_sd, target_sd
                ), "Disk moved but shouldn't have",
            )
            logger.info("Disk %s done", disk)


@attr(tier=1)
class TestCase5983(BaseTestCase):
    """
    migrate multiple vm's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = True
    polarion_test_case = '5983'
    vm_name_format = 'vm_%s_%s'
    vm_count = 5
    vm_names = None
    vm_args = vmArgs.copy()

    def setUp(self):
        super(TestCase5983, self).setUp()
        self.vm_names = []
        self.vm_args['installation'] = False
        for index in range(self.vm_count):
            self.vm_args['storageDomainName'] = self.storage_domains[0]
            self.vm_args['vmName'] = self.vm_name_format % (
                index, self.polarion_test_case,
            )

            logger.info('Creating vm %s', self.vm_args['vmName'])

            if not storage_helpers.create_vm_or_clone(**self.vm_args):
                raise exceptions.VMException('Unable to create vm %s for test'
                                             % self.vm_args['vmName'])
            self.vm_names.append(self.vm_args['vmName'])

    def _perform_action(self, host):
        for vm in self.vm_names:
            updateVm(True, vm, placement_host=host)
            start_vms([vm], 1, wait_for_ip=False)
            waitForVMState(vm)

        for vm in self.vm_names:
            live_migrate_vm(vm)

    @polarion("RHEVM3-5983")
    def test_migrate_multiple_vms_on_spm(self):
        """
        Actions:
            - create 5 vms and run them on spm host only
            - LSM the disks
        Expected Results:
            - we should succeed to migrate all disks
        """
        spm = getSPMHost(config.HOSTS)
        self._perform_action(spm)

    @polarion("RHEVM3-5983")
    def test_migrate_multiple_vms_on_hsm(self):
        """
        Actions:
            - create 5 vms and run them on hsm host only
            - LSM the disks
        Expected Results:
            - we should succeed to migrate all disks
        """
        hsm = getHSMHost(config.HOSTS)
        self._perform_action(hsm)

    def tearDown(self):
        """Remove created vms"""
        stop_vms_safely(self.vm_names)
        removeVms(True, self.vm_names)
        super(TestCase5983, self).tearDown()


@attr(tier=3)
class TestCase5984(BaseTestCase):
    """
    connectivity issues to pool
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    - https://bugzilla.redhat.com/show_bug.cgi?id=1078095
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
    bz = {'1106593': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}
    polarion_test_case = '5984'

    def _migrate_vm_disk_and_block_connection(self, disk, source, username,
                                              password, target,
                                              target_ip):

        startVm(True, self.vm_name, config.VM_UP)
        live_migrate_vm_disk(self.vm_name, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password,
                                         target_ip)
        self.assertTrue(status, "Failed to block connection")
        wait_for_jobs()

    @polarion("RHEVM3-5984")
    def test_LSM_block_from_hsm_to_domain(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        hsm = getHSMHost(config.HOSTS)
        hsm_ip = getHostIP(hsm)
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        target_sd = get_other_storage_domain(
            vm_disk, self.vm_name, self.storage)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = hsm_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, hsm_ip, config.HOSTS_USER, config.HOSTS_PW, target_sd,
            target_sd_ip)
        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        wait_for_jobs()
        super(TestCase5984, self).tearDown()


@attr(tier=3)
class TestCase5974(BaseTestCase):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier3 jobs have not been verified
    __test__ = False
    polarion_test_case = '5974'
    source_ip = ''
    username = ''
    password = ''

    @polarion("RHEVM3-5974")
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - block connectivity to the storage from the hsm host
            - start LSM
        Expected Results:
            - we should no be able to LSM a vm which is paused on EIO
        """
        startVm(True, self.vm_name, config.VM_UP)
        host = getHSMHost(config.HOSTS)
        host_ip = getHostIP(host)
        vm_disk = getVmDisks(self.vm_name)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, self.vm_name)
        target_sd = get_other_storage_domain(
            vm_disk, self.vm_name, self.storage)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip

        status = blockOutgoingConnection(host_ip, self.username, self.password,
                                         target_sd_ip)
        self.assertTrue(status, "Failed to block connection")
        waitForVMState(self.vm_name, ENUMS['vm_state_paused'])
        live_migrate_vm(self.vm_name)
        wait_for_jobs()

        status = verify_vm_disk_moved(self.vm_name, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        wait_for_jobs()
        super(TestCase5974, self).tearDown()
