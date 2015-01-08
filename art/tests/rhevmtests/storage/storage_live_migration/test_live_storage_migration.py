"""
Storage live migration sanity test - 6128
https://tcms.engineering.redhat.com/plan/6128/
"""

import logging
from time import sleep
from utilities.machine import Machine
from utilities.utils import getIpAddressByHostName

from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState, get_other_storage_domain, attachDisk,
    deleteDisk, getVmDisk, get_disk_storage_domain_name,
    getObjDisks, detachDisk, addDisk,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    get_master_storage_domain_name, cleanDataCenter, deactivateStorageDomain,
    waitForStorageDomainStatus, activateStorageDomain, extendStorageDomain,
    getDomainAddress, get_free_space,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    createVm, stop_vms_safely, waitForVMState, deactivateVmDisk, removeDisk,
    start_vms, live_migrate_vm, remove_all_vm_lsm_snapshots, addVm,
    suspendVm, removeSnapshot, live_migrate_vm_disk, move_vm_disk,
    waitForVmsStates, getVmDisks, stopVm, migrateVm, verify_vm_disk_moved,
    updateVm, getVmHost, removeVms, shutdownVm, runVmOnce, startVm,
    get_vm_snapshots, get_vm_state,
    waitForVmsDisks, wait_for_vm_snapshots, addSnapshot, removeVm,
    activateVmDisk,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, rebootHost, getHSMHost,
)
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.high_level.datacenters import (
    build_setup, clean_all_disks_from_dc,
)
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from rhevmtests.storage.helpers import get_vm_ip
from rhevmtests.storage.storage_live_migration import helpers
from art.unittest_lib.common import StorageTest as BaseTestCase

from art.rhevm_api.utils.test_utils import (
    get_api, setPersistentNetwork, restartVdsmd,
)
from art.test_handler import exceptions
from art.test_handler.tools import tcms  # pylint: disable=E0611
import config

logger = logging.getLogger(__name__)

VM_API = get_api('vm', 'vms')

ENUMS = config.ENUMS

BLOCK_TYPES = (ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp'])

TCMS_PLAN_ID = '6128'

CREATE_VM_TIMEOUT = 15 * 60
VM_SHUTDOWN_TIMEOUT = 2 * 60
MIGRATION_TIMEOUT = 10 * 60
TASK_TIMEOUT = 1500
LIVE_MIGRATION_TIMEOUT = 30 * 60
DISK_TIMEOUT = 900
LIVE_MIGRATE_LARGE_SIZE = 3600

FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"

SD_NAME_0 = config.SD_NAME_0
SD_NAME_1 = config.SD_NAME_1
SD_NAME_2 = config.SD_NAME_2

SDK_ENGINE = 'sdk'
VMS_PID_LIST = 'pgrep qemu'

vm_names = list()

vmArgs = {'positive': True,
          'vmName': config.VM_NAME,
          'vmDescription': config.VM_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.COW_DISK,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.DISK_SIZE,
          'nic': config.HOST_NICS[0],
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.OS_TYPE,
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats

    for this TCMS plan we need 2 SD but only two of them should be created on
    setup. the other SD will be created manually in the test case 334923.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only two lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)

    if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
        luns = config.LUNS
        config.PARAMETERS['lun'] = luns[0:3]

    build_setup(config=config.PARAMETERS,
                storage=config.PARAMETERS,
                storage_type=config.STORAGE_TYPE)

    if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
        config.PARAMETERS['lun'] = luns

    vmArgs['storageDomainName'] = \
        get_master_storage_domain_name(config.DATA_CENTER_NAME)

    logger.info('Creating vm and installing OS on it')

    if not createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    stop_vms_safely([config.VM_NAME])


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class SimpleCase(BaseTestCase):
    """
    A class with common teardown method
    """
    __test__ = False

    def tearDown(self):
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class CommonUsage(BaseTestCase):
    """
    A class with common method
    """
    __test__ = False

    def _remove_disks(self, disks_names):
        """
        Removes created disks
        """
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)

        for disk in disks_names:
            logger.info("Deleting disk %s", disk)
            if not deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)


class AllPermutationsDisks(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    apis = set('rest')
    __test__ = False

    spm = None
    master_sd = None
    vm = config.VM_NAME
    shared = False

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        helpers.start_creating_disks_for_test(shared=self.shared)
        assert waitForDisksState(helpers.DISKS_NAMES, timeout=TASK_TIMEOUT)
        stop_vms_safely([self.vm])
        waitForVMState(vm=self.vm, state=ENUMS['vm_state_down'])
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    def tearDown(self):
        """
        Clean environment
        """
        stop_vms_safely([self.vm])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        logger.info("Removing all disks")
        for disk in helpers.DISKS_NAMES:
            deactivateVmDisk(True, self.vm, disk)
            if not removeDisk(True, self.vm, disk):
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk)
            logger.info("Disk %s removed successfully", disk)
        vm_disks = getVmDisks(self.vm)
        boot_disk = [d.get_alias() for d in vm_disks if d.get_bootable()][0]

        clean_all_disks_from_dc(config.DATA_CENTER_NAME, [boot_disk])
        remove_all_vm_lsm_snapshots(self.vm)
        logger.info("Finished testCase")


class TestCase165965(AllPermutationsDisks):
    """
    live migrate
    https://tcms.engineering.redhat.com/case/165965/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '165965'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_vms_live_migration(self):
        """
        Actions:
            - move vm's images to different SD
        Expected Results:
            - move should succeed
        """
        live_migrate_vm(self.vm)
        wait_for_jobs()


class TestCase166167(BaseTestCase):
    """
    vm in paused mode
    https://tcms.engineering.redhat.com/case/166167/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '166167'

    def setUp(self):
        stop_vms_safely([config.VM_NAME])

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_vms_live_migration(self):
        """
        Actions:
            - run a vm with run-once in pause mode
            - try to move images
        Expected Results:
            - VM has running qemu process so LSM should succeed
        """
        logger.info("Running vm in paused state")
        assert runVmOnce(True, config.VM_NAME, pause='true')
        waitForVMState(config.VM_NAME, config.VM_PAUSED)
        live_migrate_vm(config.VM_NAME)
        wait_for_jobs()

    def tearDown(self):
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        assert startVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME)


class TestCase166089(SimpleCase):
    """
    different vm status
    https://tcms.engineering.redhat.com/case/166089/?from_plan=6128


    __test__ = False : A race situation can occur here. Manual test only
    """
    __test__ = False
    tcms_test_case = '166089'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_during_waiting_for_launch_state(self):
        """
        Actions:
            - try to live migrate while vm is waiting for launch
        Expected Results:
            - live migration should fail
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME, config.VM_WAIT_FOR_LAUNCH)
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_during_powering_up_state(self):
        """
        Actions:
            - try to live migrate while vm is powering up
        Expected Results:
            - migration should fail
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME, config.VM_POWERING_UP)
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_during_powering_off_state(self):
        """
        Actions:
            - try to live migrate while vm is powering off
        Expected Results:
            - migration should fail
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        shutdownVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME, ENUMS['vm_state_powering_down'])
        self.assertRaises(exceptions.DiskException, live_migrate_vm,
                          config.VM_NAME)


class TestCase166090(BaseTestCase):
    """
    live migration with thin provision copy
    https://tcms.engineering.redhat.com/case/166090/?from_plan=6128

    __test__ = False due to bug:
    https://bugzilla.redhat.com/show_bug.cgi?id=1110798
    """
    __test__ = False
    tcms_test_case = '166090'
    test_templates = ['template_single', 'template_both']
    base_vm = config.VM_NAME
    vm_names = ['vm_from_both', 'vm_from_single']

    def _prepare_templates(self):
        """
        Creates two templates
            - one has disk on first storage domain
            - second has disks on both storage domains
        """
        start_vms([self.base_vm], 1, wait_for_ip=False)
        waitForVMState(self.base_vm)
        ip_addr = get_vm_ip(self.base_vm)
        setPersistentNetwork(ip_addr, config.VM_PASSWORD)
        stop_vms_safely([self.base_vm])

        disks_objs = getObjDisks(self.base_vm, get_href=False)

        target_domain = get_disk_storage_domain_name(
            disks_objs[0].get_alias(), self.base_vm)

        logger.info("Creating template %s from vm %s to storage domain %s",
                    self.test_templates[0], self.base_vm, target_domain)
        assert templates.createTemplate(
            True, True, vm=self.base_vm, name=self.test_templates[0],
            cluster=config.CLUSTER_NAME, storagedomain=target_domain)

        second_domain = get_other_storage_domain(
            disks_objs[0].get_alias())

        target_domain = SD_NAME_1 if (second_domain == SD_NAME_0) \
            else SD_NAME_0

        logger.info("Creating second template %s from vm %s to storage domain "
                    "%s",
                    self.test_templates[1], self.base_vm, target_domain)
        assert templates.createTemplate(True, True, vm=self.base_vm,
                                        name=self.test_templates[1],
                                        cluster=config.CLUSTER_NAME,
                                        storagedomain=target_domain)

        templates.copy_template_disks(
            True, self.test_templates[1], "%s_Disk1" % self.base_vm,
            second_domain)
        assert templates.waitForTemplatesStates(
            names=",".join(self.test_templates))

        for templ in self.test_templates:
            templates.wait_for_template_disks_state(templ)

    def setUp(self):
        """
        Prepares templates test_templates and vms based on that templates
        """
        self._prepare_templates()
        for template, vm_name in zip(self.test_templates, vm_names):
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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_thin_provision_copy_template_on_both_domains(self):
        """
        template is copied to both domains:
        - create a vm from template and run the vm
        - move vm to target domain
        """
        live_migrate_vm(vm_names[0], LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_thin_provision_copy_template_on_one_domain(self):
        """
        template is copied on only one domain
        - create vm from template and run the vm
        - move the vm to second domain
        """
        live_migrate_vm(vm_names[1], LIVE_MIGRATION_TIMEOUT)
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
            if not templates.removeTemplate(True, template):
                raise exceptions.TemplateException(
                    "Failed to remove template %s" % template)


class TestCase166137(BaseTestCase):
    """
    snapshots and move vm
    https://tcms.engineering.redhat.com/case/166137/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '166137'
    snapshot_desc = 'snap1'

    def _prepare_snapshots(self, vm_name):
            """
            Creates one snapshot on the vm vm_name
            """
            stop_vms_safely([vm_name])
            logger.info("Add snapshot to vm %s", vm_name)
            if not addSnapshot(True, vm_name, self.snapshot_desc):
                raise exceptions.VMException(
                    "Add snapshot to vm %s failed" % vm_name)
            wait_for_vm_snapshots(vm_name, ENUMS['snapshot_state_ok'])
            start_vms([vm_name], 1,  wait_for_ip=False)
            waitForVMState(vm_name)

    def setUp(self):
        """
        Creates snapshot
        """
        self._prepare_snapshots(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_snapshot(self):
        """
        Tests live migrating vm containing snapshot
        - vm with snapshots
        - run the vm
        - migrate the vm to second domain
        """
        live_migrate_vm(config.VM_NAME)
        wait_for_jobs()

    def tearDown(self):
        """
        Removed created snapshots
        """
        stop_vms_safely([config.VM_NAME])
        logger.info("Deleting snapshot %s", self.snapshot_desc)
        if not removeSnapshot(True, config.VM_NAME, self.snapshot_desc):
            raise exceptions.VMException("Cannot delete snapshot %s "
                                         "of vm %s" %
                                         (self.snapshot_desc, config.VM_NAME))
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase166166(BaseTestCase):
    """
    live migration with shared disk
    https://tcms.engineering.redhat.com/case/166166
    """
    __test__ = True
    tcms_test_case = '166166'
    test_vm_name = 'test_vm_%s' % tcms_test_case
    permutation = {}

    def _prepare_shared_disk_environment(self):
            """
            Creates second vm and shared disk for both of vms
            """
            logger.info('Creating vm')
            if not addVm(True, wait=True, name=self.test_vm_name,
                         cluster=config.CLUSTER_NAME):
                raise exceptions.VMException("Failed to create vm %s"
                                             % self.test_vm_name)
            self.permutation['alias'] = 'disk_for_test'
            self.permutation['interface'] = config.VIRTIO
            self.permutation['format'] = config.RAW_DISK
            self.permutation['sparse'] = False
            logger.info('Adding new disk')
            helpers.add_new_disk(sd_name=config.SD_NAME_0,
                                 permutation=self.permutation, shared=True)
            helpers.prepare_disks_for_vm(self.test_vm_name,
                                         helpers.DISKS_NAMES)
            helpers.prepare_disks_for_vm(config.VM_NAME,
                                         helpers.DISKS_NAMES)

    def setUp(self):
        """
        Prepare environment with shared disk
        """
        helpers.DISKS_NAMES = []
        self._prepare_shared_disk_environment()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_with_shared_disk(self):
        """
        create and run several vm's with the same shared disk
        - try to move one of the vm's images
        """
        target_sd = get_other_storage_domain(helpers.DISKS_NAMES[0],
                                             config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, helpers.DISKS_NAMES[0], target_sd)
        wait_for_jobs()

    def tearDown(self):
        """
        Removed created snapshots
        """
        stop_vms_safely([config.VM_NAME, self.test_vm_name])
        waitForVmsStates(True, [config.VM_NAME, self.test_vm_name],
                         config.VM_DOWN)
        if not removeDisk(True, config.VM_NAME, helpers.DISKS_NAMES[0]):
            raise exceptions.DiskException("Cannot remove disk %s "
                                           "of vm %s"
                                           % (helpers.DISKS_NAMES[0],
                                              config.VM_NAME))
        if not removeVm(True, self.test_vm_name):
            raise exceptions.VMException("Cannot remove vm %s"
                                         % config.VM_NAME)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase166168(BaseTestCase):
    """
    suspended vm
    https://tcms.engineering.redhat.com/case/166168

    __test__ = False: https://projects.engineering.redhat.com/browse/RHEVM-1595
    """
    __test__ = False
    tcms_test_case = '166168'

    def setUp(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    def _ensure_vm_state_up(self):
        """
        Prepare vm state for test
        """
        state = get_vm_state(config.VM_NAME)
        if state == config.VM_DOWN:
            assert startVm(True, config.VM_NAME)
        elif state == config.VM_SAVING:
            waitForVMState(config.VM_NAME, config.VM_SUSPENDED)
            startVm(True, config.VM_NAME)
        elif state == config.VM_SUSPENDED:
            startVm(True, config.VM_NAME)

        waitForVMState(config.VM_NAME)
        wait_for_jobs()

    def _suspended_vm_and_wait_for_state(self, state):
        """
        Suspending vm and perform LSM after vm is in desired state
        """
        assert suspendVm(True, config.VM_NAME, wait=False)
        assert waitForVMState(config.VM_NAME, state)
        live_migrate_vm(config.VM_NAME, LIVE_MIGRATION_TIMEOUT,
                        ensure_on=False)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_while_saving_state(self):
        """
        1) saving state
            - create and run a vm
            - suspend the vm
            - try to move vm's images while vm is in saving state
        * We should not be able to migrate images
        """
        # self._ensure_vm_state_up()
        self.assertRaises(exceptions.DiskException,
                          self._suspended_vm_and_wait_for_state,
                          config.VM_SAVING)
        waitForVMState(config.VM_NAME, config.VM_SUSPENDED)
        startVm(True, config.VM_NAME)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_while_suspended_state(self):
        """
        2) suspended state
            - create and run a vm
            - suspend the vm
            - try to migrate the vm's images once the vm is suspended
        * We should not be able to migrate images
        """
        # self._ensure_vm_state_up()
        self.assertRaises(exceptions.DiskException,
                          self._suspended_vm_and_wait_for_state,
                          config.VM_SUSPENDED)
        waitForVMState(config.VM_NAME, config.VM_SUSPENDED)
        startVm(True, config.VM_NAME)
        wait_for_jobs()

    def tearDown(self):
        stopVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase166170(AllPermutationsDisks):
    """
    Create live snapshot during live storage migration
    https://tcms.engineering.redhat.com/case/166170
    """
    __test__ = True
    tcms_test_case = '166170'
    snapshot_desc = 'snap_%s' % tcms_test_case
    snap_created = None

    def _prepare_snapshots(self, vm_name):
        """
        Creates one snapshot on the vm vm_name
        """
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
        logger.info("Creating new snapshot for vm %s", vm_name)
        if not addSnapshot(True, vm_name, self.snapshot_desc):
            raise exceptions.VMException(
                "Add snapshot to vm %s failed" % vm_name)
        wait_for_vm_snapshots(vm_name, ENUMS['snapshot_state_ok'])

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_before_snapshot(self):
        """
        1) move -> create snapshot
            - create and run a vm
            - move vm's
            - try to create a live snapshot
        * we should succeed to create a live snapshot
        """
        self.snap_created = False
        live_migrate_vm(config.VM_NAME, LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()
        self._prepare_snapshots(config.VM_NAME)
        self.snap_created = True

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_after_snapshot(self):
        """
        2) create snapshot -> move
            - create and run a vm
            - create a live snapshot
            - move the vm's images
        * we should succeed to move the vm
        """
        self.snap_created = False
        self._prepare_snapshots(config.VM_NAME)
        live_migrate_vm(config.VM_NAME, LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()
        self.snap_created = True

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_while_snapshot(self):
        """
        3) move + create snapshots
            - create and run a vm
            - try to create a live snapshot + move
        * we should block move+create live snapshot in backend.
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        for disk in helpers.DISKS_NAMES:
            self.snap_created = True
            target_sd = get_other_storage_domain(disk, config.VM_NAME)
            live_migrate_vm_disk(config.VM_NAME, disk, target_sd,
                                 timeout=LIVE_MIGRATION_TIMEOUT, wait=False)
            self.assertRaises(exceptions.VMException, self._prepare_snapshots,
                              config.VM_NAME)
            self.snap_created = False
            wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        wait_for_jobs()
        super(TestCase166170, self).tearDown()
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        if self.snap_created:
            assert removeSnapshot(True, config.VM_NAME, self.snapshot_desc)
        wait_for_jobs()


class TestCase166173(CommonUsage):
    """
    Time out
    https://tcms.engineering.redhat.com/case/166173/?from_plan=6128
    """
    # TODO: Check results
    __test__ = False
    tcms_test_case = '166173'
    disk_name = "disk_%s" % tcms_test_case

    def setUp(self):
        """
        Prepares a floating disk
        """
        helpers.add_new_disk_for_test(config.VM_NAME, self.disk_name,
                                      provisioned_size=(60 * config.GB),
                                      wipe_after_delete=True, attach=True)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        live_migrate_vm_disk(config.VM_NAME, self.disk_name, SD_NAME_1,
                             timeout=LIVE_MIGRATE_LARGE_SIZE, wait=True)
        wait_for_jobs(timeout=LIVE_MIGRATE_LARGE_SIZE)

    def tearDown(self):
        """
        Restore environment
        """
        self._remove_disks([self.disk_name])
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase166177(AllPermutationsDisks):
    """
    Images located on different domain
    https://tcms.engineering.redhat.com/case/166177
    """
    __test__ = True
    tcms_test_case = '166177'
    snapshot_desc = 'snap_%s' % tcms_test_case
    disk_to_move = ''

    def _perform_action(self, vm_name, disk_name):
        """
        Move one disk to second storage domain
        """
        stop_vms_safely([vm_name])
        self.disk_to_move = disk_name
        target_sd = get_other_storage_domain(self.disk_to_move, vm_name)
        move_vm_disk(vm_name, self.disk_to_move, target_sd)
        wait_for_jobs()
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
        target_sd = get_other_storage_domain(self.disk_to_move, vm_name)
        live_migrate_vm_disk(config.VM_NAME, self.disk_to_move, target_sd,
                             LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_with_image_on_target(self):
        """
        move disk images to a domain that already has one of the images on it
        """
        for disk in helpers.DISKS_NAMES:
            self._perform_action(config.VM_NAME, disk)

    def tearDown(self):
        super(TestCase166177, self).tearDown()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase166180(CommonUsage):
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

    https://tcms.engineering.redhat.com/case/166180
    """
    __test__ = True
    tcms_test_case = '166180'
    disk_name_pattern = "floating_%s_%s"

    def setUp(self):
        """
        Prepares a floating disk
        """
        self.disk_name_pattern = self.disk_name_pattern \
            % (self.tcms_test_case, self.__class__.__name__)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        helpers.add_new_disk_for_test(
            config.VM_NAME, self.disk_name_pattern, sparse=True,
            disk_format=config.COW_DISK)

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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_inactive_disk(self):
        """
        Tests storage live migration with one disk in inactive status
        """
        self._test_plugged_disk(config.VM_NAME, False)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_active_disk(self):
        """
        Tests storage live migration with floating disk in active status
        """
        self._test_plugged_disk(config.VM_NAME)

    def tearDown(self):
        """
        Restore environment
        """
        self._remove_disks([self.disk_name_pattern])


class TestCase168768(BaseTestCase):
    """
    Attach disk during migration
    https://tcms.engineering.redhat.com/case/168768
    """
    __test__ = True
    tcms_test_case = '168768'
    disk_alias = 'disk_%s' % tcms_test_case

    def setUp(self):
        """
        Prepares a floating disk
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        helpers.add_new_disk_for_test(
            config.VM_NAME, self.disk_alias, sparse=True,
            disk_format=config.COW_DISK)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_attach_disk_during_lsm(self):
        """
        migrate vm's images -> try to attach a disk during migration
        * we should fail to attach disk
        """
        live_migrate_vm(config.VM_NAME, timeout=LIVE_MIGRATION_TIMEOUT,
                        wait=False)

        status = attachDisk(True, self.disk_alias, config.VM_NAME)
        self.assertFalse(status, "Succeeded to attach disk during LSM")
        wait_for_jobs()

    def tearDown(self):
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()


class TestCase168839(BaseTestCase):
    """
    LSM to domain in maintenance
    https://tcms.engineering.redhat.com/case/168839
    """
    __test__ = True
    tcms_test_case = '168839'
    disk_alias = 'disk_%s' % tcms_test_case
    succeeded = False

    def setUp(self):
        """
        Prepares one domain in maintenance
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        self.vm_disk = getVmDisks(config.VM_NAME)[0]
        self.target_sd = get_other_storage_domain(self.vm_disk.get_alias(),
                                                  config.VM_NAME)

        deactivateStorageDomain(True, config.DATA_CENTER_NAME, self.target_sd)
        assert waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            ENUMS['storage_domain_state_maintenance'])

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_lsm_to_maintenance_domain(self):
        """
        try to migrate to a domain in maintenance
        * we should fail to attach disk
        """
        self.assertRaises(exceptions.DiskException, live_migrate_vm_disk,
                          config.VM_NAME, self.vm_disk.get_alias(),
                          self.target_sd, LIVE_MIGRATION_TIMEOUT, True)
        self.succeeded = True

    def tearDown(self):
        wait_for_jobs()
        assert activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.target_sd)
        if self.succeeded:
            remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase174424(CommonUsage):
    """
    live migrate vm with multiple disks on multiple domains
    https://tcms.engineering.redhat.com/case/174424/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '174424'
    disk_name = "disk_%s_%s"
    disk_count = 3
    sd_list = [SD_NAME_0, SD_NAME_1, SD_NAME_2]

    def setUp(self):
        """
        Prepares disks on different domains
        """
        self.disks_names = []
        stop_vms_safely([config.VM_NAME])
        self._prepare_disks_for_vm(config.VM_NAME)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

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
                disk_params['alias'] = self.disk_name % (index,
                                                         self.tcms_test_case)
                disk_params['storagedomain'] = self.sd_list[index]
                if not addDisk(True, **disk_params):
                    raise exceptions.DiskException(
                        "Can't create disk with params: %s" % disk_params)
                logger.info("Waiting for disk %s to be ok",
                            disk_params['alias'])
                waitForDisksState(disk_params['alias'])
                self.disks_names.append(disk_params['alias'])
                assert attachDisk(True, disk_params['alias'], vm_name)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_live_migration_with_multiple_disks(self):
        """
        Actions:
            - 1 vm with disks on 3 of the 3 domains
            - live migrate the vm to the 3rd domain
        Expected Results:
            - move should succeed
        """
        for disk in self.disks_names[:-1]:
            live_migrate_vm_disk(config.VM_NAME, disk, SD_NAME_2)

            wait_for_jobs()

    def tearDown(self):
        """
        Removes disks and snapshots
        """
        self._remove_disks(self.disks_names)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase231544(CommonUsage):
    """
    Wipe after delete
    https://tcms.engineering.redhat.com/case/231544/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '231544'
    disk_name = "disk_%s" % tcms_test_case
    regex = 'dd oflag=direct if=/dev/zero of=.*/%s'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        helpers.add_new_disk_for_test(config.VM_NAME, self.disk_name,
                                      wipe_after_delete=True, attach=True)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        self.host_ip = getIpAddressByHostName(host)
        live_migrate_vm_disk(config.VM_NAME, self.disk_name, SD_NAME_1,
                             wait=False)
        disk_obj = getVmDisk(config.VM_NAME, self.disk_name)
        self.regex = self.regex % disk_obj.get_image_id()
        watch_logs(FILE_TO_WATCH, self.regex, '', LIVE_MIGRATION_TIMEOUT,
                   self.host_ip, config.HOSTS_USER, config.HOSTS_PW)
        wait_for_jobs()

    def tearDown(self):
        """
        Restore environment
        """
        self._remove_disks([self.disk_name])
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase232947(AllPermutationsDisks):
    """
    Power off of vm during LSM
    https://tcms.engineering.redhat.com/case/232947/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '232947'

    def _perform_action_on_disk_and_wait_for_regex(self, disk_name, regex):
        host = getSPMHost(config.HOSTS)
        self.host_ip = getIpAddressByHostName(host)
        target_sd = get_other_storage_domain(disk_name, config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, disk_name, target_sd,
                             wait=False)
        watch_logs(FILE_TO_WATCH, regex, '', MIGRATION_TIMEOUT,
                   self.host_ip, config.HOSTS_USER, config.HOSTS_PW)
        assert stopVm(True, config.VM_NAME)
        waitForDisksState(disk_name, timeout=LIVE_MIGRATION_TIMEOUT)
        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_power_off_createVolume(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'createVolume' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISKS_NAMES:
            self._perform_action_on_disk_and_wait_for_regex(disk_name,
                                                            'createVolume')

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_power_off_cloneImageStructure(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'cloneImageStructure' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISKS_NAMES:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'cloneImageStructure')

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_power_off_syncdData(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'syncdData' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISKS_NAMES:
            self._perform_action_on_disk_and_wait_for_regex(disk_name,
                                                            'syncdData')

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_power_off_deleteImage(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'deleteImage' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in helpers.DISKS_NAMES:
            self._perform_action_on_disk_and_wait_for_regex(disk_name,
                                                            'deleteImage')

    def tearDown(self):
        """
        Restore environment
        """
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        super(TestCase232947, self).tearDown()


class TestCase233434(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration
    https://tcms.engineering.redhat.com/case/233434/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '233434'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        status = False
        for disk in helpers.DISKS_NAMES:
            target_sd = get_other_storage_domain(disk, config.VM_NAME)
            live_migrate_vm_disk(config.VM_NAME, disk, target_sd)
            wait_for_jobs()
            remove_all_vm_lsm_snapshots(config.VM_NAME)
            wait_for_jobs()
            disk_obj = getVmDisk(config.VM_NAME, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info("Actual size after live migrate disk %s is: %s",
                        disk, actual_size)
            logger.info("Virtual size after live migrate disk %s is: %s",
                        disk, virtual_size)
            if disk_obj.get_sparse() is False:
                status = actual_size == virtual_size
            elif disk_obj.get_sparse() is True:
                status = actual_size < virtual_size
            self.assertTrue(status, "Actual size exceeded to virtual size")


class TestCase233436(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration failure
    https://tcms.engineering.redhat.com/case/233436/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '233436'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        status = False
        for disk in helpers.DISKS_NAMES:
            target_sd = get_other_storage_domain(disk, config.VM_NAME)
            host = getSPMHost(config.HOSTS)
            self.host_ip = getIpAddressByHostName(host)
            live_migrate_vm_disk(config.VM_NAME, disk, target_sd,
                                 wait=True)
            assert stopVm(True, config.VM_NAME)
            wait_for_jobs()

            remove_all_vm_lsm_snapshots(config.VM_NAME)
            wait_for_jobs()
            start_vms([config.VM_NAME], 1, wait_for_ip=False)
            waitForVMState(config.VM_NAME)
            disk_obj = getVmDisk(config.VM_NAME, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info("Actual size after live migrate disk %s is: %s",
                        disk, actual_size)
            logger.info("Virtual size after live migrate disk %s is: %s",
                        disk, virtual_size)
            if disk_obj.get_sparse() is False:
                status = actual_size == virtual_size
            elif disk_obj.get_sparse() is True:
                status = actual_size < virtual_size
            self.assertTrue(status, "Actual size exceeded to virtual size")


class TestCase281156(AllPermutationsDisks):
    """
    merge snapshot
    https://tcms.engineering.redhat.com/case/281156/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281156'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        for index, disk in enumerate(helpers.DISKS_NAMES):
            target_sd = get_other_storage_domain(disk, config.VM_NAME)
            start_vms([config.VM_NAME], 1, wait_for_ip=False)
            waitForVMState(config.VM_NAME)
            live_migrate_vm_disk(config.VM_NAME, disk, target_sd, wait=False)

            helpers.verify_write_operation_to_disk(config.VM_NAME, index,
                                                   ensure_vm_on=True)

            wait_for_jobs()
            stop_vms_safely([config.VM_NAME])
            remove_all_vm_lsm_snapshots(config.VM_NAME)
            wait_for_jobs()
            start_vms([config.VM_NAME], 1, wait_for_ip=False)

    def tearDown(self):
        super(TestCase281156, self).tearDown()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281168(BaseTestCase):
    """
    offline migration for disk attached to running vm
    https://tcms.engineering.redhat.com/case/281168/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281168'
    disk_name = "disk_%s" % tcms_test_case
    expected_lsm_snap_count = 0

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        # If any LSM snapshot exists --> remove them to be able to check if
        # the disk movement in this case is cold move and not live storage
        # migration

        remove_all_vm_lsm_snapshots(config.VM_NAME)
        wait_for_jobs()
        helpers.add_new_disk_for_test(config.VM_NAME, self.disk_name,
                                      attach=True)
        assert deactivateVmDisk(True, config.VM_NAME, self.disk_name)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        target_sd = get_other_storage_domain(self.disk_name, config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, self.disk_name, target_sd)
        wait_for_jobs()

        snapshots = get_vm_snapshots(config.VM_NAME)
        LSM_snapshots = [s for s in snapshots if
                         (s.get_description() ==
                          config.LIVE_SNAPSHOT_DESCRIPTION)]
        logger.info("Verify that the migration was not live migration")
        self.assertEqual(len(LSM_snapshots), self.expected_lsm_snap_count)

    def tearDown(self):
        assert removeDisk(True, config.VM_NAME, self.disk_name)
        wait_for_jobs()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281206(BaseTestCase):
    """
    Deactivate vm disk during live migrate
    https://tcms.engineering.redhat.com/case/281206/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281206'
    disk_name = "disk_%s" % tcms_test_case

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        helpers.add_new_disk_for_test(config.VM_NAME, self.disk_name,
                                      attach=True)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_deactivate_disk_during_lsm(self):
        """
        Actions:
            - create a vm with two disks and run it
            - start a LSM on the vm disk
            - deactivate the non-boot disk.
        Expected Results:
            - we should block with canDoAction
        """
        target_sd = get_other_storage_domain(self.disk_name, config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, self.disk_name,
                             target_sd=target_sd, wait=False)
        sleep(5)
        status = deactivateVmDisk(False, config.VM_NAME, self.disk_name)
        self.assertTrue(status, "Succeeded to deactivate vm disk %s during "
                                "live storage migration" % self.disk_name)
        waitForDisksState(self.disk_name)
        wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        assert removeDisk(True, config.VM_NAME, self.disk_name)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281203(SimpleCase):
    """
    migrate a vm between hosts + LSM
    https://tcms.engineering.redhat.com/case/281203/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281203'

    def _migrate_vm_during_lsm_ops(self, wait):
        spm_host = getSPMHost(config.HOSTS)
        self.host_ip = getIpAddressByHostName(spm_host)
        live_migrate_vm(config.VM_NAME, wait=wait)
        status = migrateVm(True, config.VM_NAME, wait=False)
        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        return status

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_LSM_during_vm_migration(self):
        """
        Actions:
            - create and run a vm
            - migrate the vm between the hosts
            - try to LSM the vm disk during the vm migration
        Expected Results:
            - we should be stopped by CanDoAction
        """
        spm_host = getSPMHost(config.HOSTS)
        self.host_ip = getIpAddressByHostName(spm_host)
        disk_name = getVmDisks(config.VM_NAME)[0].get_alias()
        target_sd = get_other_storage_domain(disk_name, config.VM_NAME)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        migrateVm(True, config.VM_NAME, wait=False)
        self.assertRaises(exceptions.DiskException, live_migrate_vm_disk,
                          config.VM_NAME, disk_name, target_sd)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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


class TestCase373597(SimpleCase):
    """
    Extend storage domain while lsm
    https://tcms.engineering.redhat.com/case/373597/?from_plan=6128
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '373597'

    sd_args = {'storage_type': config.STORAGE_TYPE,
               'host': config.HOSTS[0],
               'lun': config.LUNS[-1],
               'lun_address': config.LUN_ADDRESS[-1],
               'lun_target': config.LUN_TARGET[-1],
               'lun_port': config.LUN_PORT}

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        disk_name = getVmDisks(config.VM_NAME)[0].get_alias()
        target_sd = get_other_storage_domain(disk_name, config.VM_NAME)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        src_sd = get_disk_storage_domain_name(disk_name, config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, disk_name, target_sd, wait=False)
        extendStorageDomain(True, src_sd, **self.sd_args)

        self.sd_args['lun'] = config.LUNS[-2]
        self.sd_args['lun_address'] = config.LUN_ADDRESS[-2]
        self.sd_args['lun_target'] = config.LUN_TARGET[-2]

        extendStorageDomain(True, target_sd, **self.sd_args)
        waitForDisksState(disk_name)
        wait_for_jobs()


class TestCase168840(BaseTestCase):
    """
    live migrate - storage connectivity issues
    https://tcms.engineering.redhat.com/case/168840/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1106593
    - https://bugzilla.redhat.com/show_bug.cgi?id=1078095
    """
    __test__ = False
    tcms_test_case = '168840'

    def _migrate_vm_disk_and_block_connection(self, disk, source, username,
                                              password, target,
                                              target_ip):

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password,
                                         target_ip)
        self.assertTrue(status, "Failed to block connection")
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        spm_host = getSPMHost(config.HOSTS)
        host_ip = getIpAddressByHostName(spm_host)
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        target_sd = get_other_storage_domain(vm_disk, config.VM_NAME)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, host_ip, config.HOSTS_USER, config.HOSTS_PW, target_sd,
            target_sd_ip)
        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        wait_for_jobs()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase168836(SimpleCase):
    """
    VDSM restart during live migration
    https://tcms.engineering.redhat.com/case/168836/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '168836'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_restart_spm_during_lsm(self):
        """
        Actions:
            - run vm's on host
            - start a live migrate of vm
            - restart vdsm
        Expected Results:
            - live migrate should fail
        """
        spm_host = getSPMHost(config.HOSTS)
        live_migrate_vm(config.VM_NAME, wait=False)
        restartVdsmd(spm_host, config.HOSTS_PW)
        wait_for_jobs()


class TestCase174418(SimpleCase):
    """
    live migrate during host restart
    https://tcms.engineering.redhat.com/case/174418/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '174418'

    def setUp(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_reboot_spm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (spm)
        Expected Results:
            - we should fail migration
        """
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        spm_host = getSPMHost(config.HOSTS)
        live_migrate_vm(config.VM_NAME, wait=False)
        logger.info("Rebooting host (SPM) %s", spm_host)
        assert rebootHost(True, spm_host, config.HOSTS_USER, config.HOSTS_PW)
        waitForDisksState(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_reboot_hsm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (hsm)
        Expected Results:
            - we should fail migration
        """
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        spm_host = [getSPMHost(config.HOSTS)]
        hsm_host = [x for x in config.HOSTS if x not in spm_host][0]
        live_migrate_vm(config.VM_NAME, wait=False)
        logger.info("Rebooting host (SPM) %s", spm_host)
        assert rebootHost(True, hsm_host, config.HOSTS_USER, config.HOSTS_PW)

        waitForDisksState(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

        wait_for_jobs()


class TestCase174419(BaseTestCase):
    """
    reboot host during live migration on HA vm
    https://tcms.engineering.redhat.com/case/174419/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '174419'

    def setUp(self):
        assert updateVm(True, config.VM_NAME, highly_available='true')
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    def _perform_action(self, host):
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)

        live_migrate_vm(config.VM_NAME, wait=False)
        logger.info("Rebooting host %s", host)
        assert rebootHost(True, host, config.HOSTS_USER, config.HOSTS_PW)
        waitForDisksState(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        self._perform_action(spm_host)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_reboot_hsm_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - reboot the host (hsm)
        Expected Results:
            - we should fail migration
        """
        hsm_host = getHSMHost(config.HOSTS)
        self._perform_action(hsm_host)

    def tearDown(self):
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        assert updateVm(True, config.VM_NAME, highly_available='false')


class TestCase174420(BaseTestCase):
    """
    kill vm's pid during live migration
    https://tcms.engineering.redhat.com/case/174420/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '174420'

    def _kill_vm_pid(self):
        host = getVmHost(config.VM_NAME)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')
        host_machine.kill_qemu_process(config.VM_NAME)

    def perform_action(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        live_migrate_vm(config.VM_NAME, wait=False)
        logger.info("Killing vms %s pid", config.VM_NAME)
        self._kill_vm_pid()

        waitForDisksState(vm_disk, timeout=DISK_TIMEOUT)

        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd)
        self.assertFalse(status, "Succeeded to live migrate vm disk %s"
                                 % vm_disk)

        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_kill_ha_vm_pid_during_lsm(self):
        """
        Actions:
            - run HA vm on host
            - start a live migrate of vm
            - kill -9 vm's pid
        Expected Results:
            - we should fail migration
        """
        stop_vms_safely([config.VM_NAME], async=False)
        wait_for_jobs()
        assert updateVm(True, config.VM_NAME, highly_available='true')
        self.perform_action()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_kill_regular_vm_pid_during_lsm(self):
        """
        Actions:
            - run vm on host
            - start a live migrate of vm
            - kill -9 vm's pid
        Expected Results:
            - we should fail migration
        """
        stop_vms_safely([config.VM_NAME], async=True)
        assert updateVm(True, config.VM_NAME, highly_available='false')
        self.perform_action()

    def tearDown(self):
        remove_all_vm_lsm_snapshots(config.VM_NAME)
        assert updateVm(True, config.VM_NAME, highly_available='false')


class TestCase174421(BaseTestCase):
    """
    no space left
    https://tcms.engineering.redhat.com/case/174421/?from_plan=6128
    """
    __test__ = False
    tcms_test_case = '174421'
    disk_name = "disk_%s" % tcms_test_case

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_no_space_disk_during_lsm(self):
        """
        Actions:
            - start a live migration
            - while migration is running, create a large preallocated disk
        Expected Results:
            - migration or create disk should fail nicely.
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        sd_size = get_free_space(SD_NAME_0)
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        target_sd = get_other_storage_domain(vm_disk, config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, vm_disk, target_sd, wait=False)
        helpers.add_new_disk_for_test(
            config.VM_NAME, self.disk_name,
            provisioned_size=sd_size - (1 * config.GB))

        wait_for_jobs()
        self.assertFalse(verify_vm_disk_moved(config.VM_NAME, vm_disk,
                                              source_sd, target_sd),
                         "Succeeded to live migrate vm disk %s" % vm_disk)

    def tearDown(self):
        waitForDisksState(self.disk_name)
        assert deleteDisk(True, self.disk_name)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase174426(CommonUsage):
    """
    multiple domains - only one domain unreachable
    https://tcms.engineering.redhat.com/case/174426/?from_plan=6128
    """
    __test__ = False
    tcms_test_case = '174426'
    disk_name = ''
    disk_count = 3
    sd_list = [SD_NAME_0, SD_NAME_1, SD_NAME_2]

    def _prepare_disks_for_vm(self, vm_name):
            """
            Prepares disk for given vm
            """
            disk_params = {
                'alias': self.disk_name,
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
                                       (index, self.tcms_test_case)
                disk_params['storagedomain'] = self.sd_list[index]
                if index == 2:
                    disk_params['active'] = False
                if not addDisk(True, **disk_params):
                    raise exceptions.DiskException(
                        "Can't create disk with params: %s" % disk_params)
                logger.info("Waiting for disk %s to be ok",
                            disk_params['alias'])
                waitForDisksState(disk_params['alias'])
                self.disks_names.append(disk_params['alias'])
                assert attachDisk(True, disk_params['alias'], vm_name,
                                  active=disk_params['active'])

    def setUp(self):
        """
        Prepares disks on different domains
        """
        self.disks_names = []
        stop_vms_safely([config.VM_NAME])
        self._prepare_disks_for_vm(config.VM_NAME)
        assert deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, SD_NAME_2)

        waitForStorageDomainStatus(True, config.DATA_CENTER_NAME, SD_NAME_2,
                                   config.SD_MAINTENANCE)
        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
            src_sd = get_disk_storage_domain_name(disk, config.VM_NAME)
            target_sd = get_other_storage_domain(disk, config.VM_NAME)

            if index == 2:
                self.assertRaises(exceptions.DiskException,
                                  live_migrate_vm_disk, config.VM_NAME, disk,
                                  target_sd)

                self.assertFalse(verify_vm_disk_moved(config.VM_NAME,
                                                      disk, src_sd),
                                 "Succeeded to live migrate disk %s" % disk)
            else:
                live_migrate_vm_disk(config.VM_NAME, disk, target_sd=target_sd)
                self.assertTrue(verify_vm_disk_moved(config.VM_NAME,
                                                     disk, src_sd),
                                "Failed to live migrate disk %s" % disk)

        wait_for_jobs()

    def tearDown(self):
        """
        Removes disks and snapshots
        """
        assert activateStorageDomain(True, config.DATA_CENTER_NAME, SD_NAME_2)
        wait_for_jobs()
        waitForStorageDomainStatus(True, config.DATA_CENTER_NAME, SD_NAME_2,
                                   ENUMS['storage_domain_state_active'])
        self._remove_disks(self.disks_names)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281166(BaseTestCase):
    """
    offline migration + LSM
    https://tcms.engineering.redhat.com/case/281166/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281166'
    disk_name = "disk_%s" % tcms_test_case

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        helpers.add_new_disk_for_test(config.VM_NAME, self.disk_name)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        live_migrate_vm(config.VM_NAME, wait=False)
        status = attachDisk(True, self.disk_name, config.VM_NAME)
        self.assertFalse(status, "Attache operation succeeded during LSM")
        wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        assert deleteDisk(True, self.disk_name)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase280750(SimpleCase):
    """
    kill vdsm during LSM
    https://tcms.engineering.redhat.com/case/280750/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1107758
    """
    __test__ = False
    tcms_test_case = '280750'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_kill_vdsm_during_lsm(self):
        """
        Actions:
            - run vm's on host
            - start a live migrate of vm
            - kill vdsm
        Expected Results:
            - LSM should fail nicely
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        host = getVmHost(config.VM_NAME)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')

        live_migrate_vm(config.VM_NAME, wait=False)
        sleep(5)
        host_machine.kill_vdsm_service()
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        host = getVmHost(config.VM_NAME)[1]['vmHoster']
        host_machine = Machine(host=host, user=config.HOSTS_USER,
                               password=config.HOSTS_PW).util('linux')

        live_migrate_vm(config.VM_NAME, wait=True)
        live_migrate_vm(config.VM_NAME, wait=False)
        sleep(5)
        host_machine.kill_vdsm_service()

        wait_for_jobs()


class TestCase281162(AllPermutationsDisks):
    """
    merge after a failure in LSM
    https://tcms.engineering.redhat.com/case/281162/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281162'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        for index, disk in zip(range(len(helpers.DISKS_NAMES)),
                               helpers.DISKS_NAMES):
            target_sd = get_other_storage_domain(disk, config.VM_NAME)
            live_migrate_vm_disk(config.VM_NAME, disk, target_sd, wait=False)

            logger.info("Writing to disk")
            helpers.verify_write_operation_to_disk(config.VM_NAME, index)

            wait_for_jobs()
            stop_vms_safely([config.VM_NAME])
            remove_all_vm_lsm_snapshots(config.VM_NAME)
            wait_for_jobs()
            start_vms([config.VM_NAME], 1, wait_for_ip=False)
            waitForVMState(config.VM_NAME)
            logger.info("Disk %s done", disk)

    def tearDown(self):
        super(TestCase281162, self).tearDown()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281152(BaseTestCase):
    """
    migrate multiple vm's disks
    https://tcms.engineering.redhat.com/case/281152/?from_plan=6128
    """
    __test__ = True
    tcms_test_case = '281152'
    vm_name = 'vm_%s_%s'
    vm_count = 5
    vm_names = None
    vm_args = vmArgs.copy()

    def setUp(self):
        self.vm_names = []
        self.vm_args['installation'] = False
        for index in range(self.vm_count):
            self.vm_args['storageDomainName'] = \
                get_master_storage_domain_name(config.DATA_CENTER_NAME)
            self.vm_args['vmName'] = self.vm_name % (index,
                                                     self.tcms_test_case)

            logger.info('Creating vm %s', self.vm_args['vmName'])

            if not createVm(**self.vm_args):
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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_migrate_multiple_vms_on_spm(self):
        """
        Actions:
            - create 5 vms and run them on hsm host only
            - LSM the disks
        Expected Results:
            - we should succeed to migrate all disks
        """
        spm = getSPMHost(config.HOSTS)
        self._perform_action(spm)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
        stop_vms_safely(self.vm_names)
        removeVms(True, self.vm_names)
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281145(BaseTestCase):
    """
    connectivity issues to pool
    https://tcms.engineering.redhat.com/case/281145/?from_plan=6128

    __test__ = False due to:
    - https://bugzilla.redhat.com/show_bug.cgi?id=1106593
    - https://bugzilla.redhat.com/show_bug.cgi?id=1078095
    """
    __test__ = False
    tcms_test_case = '281145'

    def _migrate_vm_disk_and_block_connection(self, disk, source, username,
                                              password, target,
                                              target_ip):

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        live_migrate_vm_disk(config.VM_NAME, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password,
                                         target_ip)
        self.assertTrue(status, "Failed to block connection")
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_LSM_block_from_hsm_to_domain(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        hsm = getHSMHost(config.HOSTS)
        hsm_ip = getIpAddressByHostName(hsm)
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        target_sd = get_other_storage_domain(vm_disk, config.VM_NAME)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = hsm_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, hsm_ip, config.HOSTS_USER, config.HOSTS_PW, target_sd,
            target_sd_ip)
        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        wait_for_jobs()
        remove_all_vm_lsm_snapshots(config.VM_NAME)


class TestCase281142(BaseTestCase):
    """
    LSM during pause due to EIO
    https://tcms.engineering.redhat.com/case/281142/?from_plan=6128

    __test__ = False
    """
    __test__ = False
    tcms_test_case = '281142'
    source_ip = ''
    username = ''
    password = ''

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - block connectivity to the storage from the hsm host
            - start LSM
        Expected Results:
            - we should no be able to LSM a vm which is paused on EIO
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        host = getHSMHost(config.HOSTS)
        host_ip = getIpAddressByHostName(host)
        vm_disk = getVmDisks(config.VM_NAME)[0].get_alias()
        source_sd = get_disk_storage_domain_name(vm_disk, config.VM_NAME)
        target_sd = get_other_storage_domain(vm_disk, config.VM_NAME)
        status, target_sd_ip = getDomainAddress(True, target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip

        status = blockOutgoingConnection(host_ip, self.username, self.password,
                                         target_sd_ip)
        self.assertTrue(status, "Failed to block connection")
        waitForVMState(config.VM_NAME, ENUMS['vm_state_paused'])
        live_migrate_vm(config.VM_NAME)
        wait_for_jobs()

        status = verify_vm_disk_moved(config.VM_NAME, vm_disk, source_sd,
                                      target_sd)
        self.assertFalse(status, "Disk moved but shouldn't have")

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        wait_for_jobs()
        remove_all_vm_lsm_snapshots(config.VM_NAME)
