"""
Storage live migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
import logging
from multiprocessing import Process, Queue
from time import sleep


import config
import helpers
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)

from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.rhevm_api.utils.test_utils import (
    get_api, restartVdsmd, wait_for_tasks,
)
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest, testflow

import rhevmtests.helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers
from utilities.machine import Machine
import pytest

logger = logging.getLogger(__name__)

VM_API = get_api('vm', 'vms')

ENUMS = config.ENUMS

MIGRATION_TIMEOUT = 10 * 60
TASK_TIMEOUT = 1500
LIVE_MIGRATION_TIMEOUT = 30 * 60
DISK_TIMEOUT = 900
LIVE_MIGRATE_LARGE_SIZE = 3600
DD_TIMEOUT = 40

# After the deletion of a snapshot, vdsm allocates around 128MB of data for
# the extent metadata
EXTENT_METADATA_SIZE = 128 * config.MB
FILE_TO_WATCH = "/var/log/vdsm/vdsm.log"
DISK_NAMES = dict()
LOCAL_LUN = []
LOCAL_LUN_ADDRESS = []
LOCAL_LUN_TARGET = []
ISCSI = config.STORAGE_TYPE_ISCSI

# Bugzilla history:
# 1251956: Live storage migration is broken
# 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with id'
# after live migrate a Virtio RAW disk, job stays in status STARTED
# Live Migration is broken, skip


def setup_module():
    """
    Sets up the environment - creates vms with all disk types and formats

    for this test plan, we need 2 SD but only two of them should be created on
    setup. the other SD will be created manually in test case 5975.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only two lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    logger.info("Running setup_module for %s", config.TESTNAME)
    config.MIGRATE_SAME_TYPE = True
    global LOCAL_LUN, LOCAL_LUN_ADDRESS, LOCAL_LUN_TARGET
    LOCAL_LUN = config.UNUSED_LUNS[:]
    LOCAL_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES[:]
    LOCAL_LUN_TARGET = config.UNUSED_LUN_TARGETS[:]


class BaseTestCase(StorageTest):
    """
    A class with a simple setUp
    """
    vm_sd = None

    # VM's bootable disk default parameters
    sparse = True
    interface = config.VIRTIO
    disk_format = config.DISK_FORMAT_COW
    polarion_test_case = None
    vm_name = None
    storage_domains = None

    def setUp(self):
        """
        Get all the storage domains from a specific domain type
        """
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.snapshot_desc = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        if self.vm_sd:
            self.disk_sd = self.vm_sd
        else:
            self.disk_sd = self.storage_domains[0]

        vm_args_copy = config.create_vm_args.copy()
        vm_args_copy['vmName'] = self.vm_name
        vm_args_copy['vmDescription'] = (
            "{0}_{1}".format(self.vm_name, "description")
        )
        vm_args_copy['storageDomainName'] = self.disk_sd
        # For each test, create a vm and remove it once the test completes
        # execution. This is faster than removing snapshots
        assert storage_helpers.create_vm_or_clone(**vm_args_copy)
        disk_obj = ll_vms.getVmDisks(self.vm_name)[0]
        self.vm_disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.updateDisk(
            True, vmName=self.vm_name, id=disk_obj.get_id(),
            alias=self.vm_disk_name, interface=self.interface
        )

    def teardown_wait_for_disks_and_snapshots(self, vm_names=[]):
        """
        In order to clean up the VMs and disks created, we need to wait until
        the VM snapshots and disks are in the OK state, wait for this and
        continue even on timeouts
        """
        for vm_name in vm_names:
            try:
                disks = [d.get_id() for d in ll_vms.getVmDisks(vm_name)]
                ll_disks.wait_for_disks_status(disks, key='id')
                ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
            except APITimeout:
                logger.error(
                    "Snapshots failed to reach OK state on VM '%s'", vm_name
                )
                BaseTestCase.test_failed = True

    def tearDown(self):
        """
        Clean environment
        """
        ll_jobs.wait_for_jobs([
            config.JOB_REMOVE_SNAPSHOT, config.JOB_LIVE_MIGRATE_DISK
        ])
        self.teardown_wait_for_disks_and_snapshots([self.vm_name])
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove VM %s", self.vm_name)
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        # teardown_exception is called from individual test cases


class AllPermutationsDisks(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    __test__ = False

    spm = None
    master_sd = None
    shared = False
    polarion_test_case = None

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        global DISK_NAMES
        super(AllPermutationsDisks, self).setUp()
        DISK_NAMES[self.storage] = (
            storage_helpers.create_disks_from_requested_permutations(
                domain_to_use=self.disk_sd, size=config.DISK_SIZE,
                shared=self.shared,
                test_name=storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_DISK
                )
            )
        )
        if not ll_disks.wait_for_disks_status(
            DISK_NAMES[self.storage], timeout=TASK_TIMEOUT
        ):
            logger.error(
                "Disks %s are not in status OK", DISK_NAMES[self.storage]
            )
        storage_helpers.prepare_disks_for_vm(
            self.vm_name, DISK_NAMES[self.storage]
        )

    def verify_lsm(self, moved=True):
        """
        Verifies if the disks have been moved
        """
        if moved:
            failure_str = "Failed"
        else:
            failure_str = "Succeeded"

        for disk in DISK_NAMES[self.storage]:
            assert moved == ll_vms.verify_vm_disk_moved(
                self.vm_name, disk, self.disk_sd
            ), "%s to live migrate vm disk %s" % (disk, failure_str)


@attr(tier=1)
class TestCase6004(AllPermutationsDisks):
    """
    live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6004'

    @polarion("RHEVM3-6004")
    def test_vms_live_migration(self):
        """
        Actions:
            - move vm's images to different SD
        Expected Results:
            - move should succeed
        """
        testflow.step(
            "Live migrate vm's %s disks to another storage domain "
            "with %s storage type",
            self.vm_name, "the same" if config.MIGRATE_SAME_TYPE else
            "a different"
        )
        ll_vms.live_migrate_vm(
            self.vm_name, same_type=config.MIGRATE_SAME_TYPE
        )
        self.verify_lsm()


@attr(tier=2)
class TestCase5990(BaseTestCase):
    """
    vm in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
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
        ll_vms.runVmOnce(True, self.vm_name, pause=True)
        ll_vms.waitForVMState(self.vm_name, config.VM_PAUSED)
        ll_vms.live_migrate_vm(
            self.vm_name, same_type=config.MIGRATE_SAME_TYPE
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, self.disk_sd
        ), "Failed to live migrate disk %s" % vm_disk


@attr(tier=2)
class TestCase5994(BaseTestCase):
    """
    different vm status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Verify this case works properly. Previous comment state a
    # race condition could occur, in that case remove
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
        ll_vms.startVm(True, self.vm_name, config.VM_WAIT_FOR_LAUNCH)
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm(
                self.vm_name, TASK_TIMEOUT, True, True,
                config.MIGRATE_SAME_TYPE
            )

    @polarion("RHEVM3-5994")
    def test_lsm_during_powering_up_state(self):
        """
        Actions:
            - try to live migrate while vm is powering up
        Expected Results:
            - migration should fail
        """
        ll_vms.startVm(True, self.vm_name, config.VM_POWERING_UP)
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm(
                self.vm_name, TASK_TIMEOUT, True, True,
                config.MIGRATE_SAME_TYPE
            )

    @polarion("RHEVM3-5994")
    def test_lsm_during_powering_off_state(self):
        """
        Actions:
            - try to live migrate while vm is powering off
        Expected Results:
            - migration should fail
        """
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.shutdownVm(True, self.vm_name)
        ll_vms.waitForVMState(self.vm_name, ENUMS['vm_state_powering_down'])
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm(
                self.vm_name, TASK_TIMEOUT, True, True,
                config.MIGRATE_SAME_TYPE
            )


@bz({'1361838': {}})
@attr(tier=2)
class TestCase5993(BaseTestCase):
    """
    live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5993'

    def _prepare_templates(self):
        """
        Creates two templates
            - one has disk on first storage domain
            - second has disks on both storage domains
        """
        disks_objs = ll_disks.getObjDisks(self.base_vm, get_href=False)

        target_domain = ll_disks.get_disk_storage_domain_name(
            disks_objs[0].get_alias(), self.base_vm
        )

        logger.info(
            "Creating template %s from vm %s to storage domain %s",
            self.test_templates[0], self.base_vm, target_domain
        )
        if not ll_templates.createTemplate(
            True, True, vm=self.base_vm, name=self.test_templates[0],
            cluster=config.CLUSTER_NAME, storagedomain=target_domain,
        ):
            raise exceptions.TemplateException(
                "Failed to create template '%s'" % self.test_templates[0]
            )
        # ISCSI -> GLUSTER: Detail: [Cannot move Virtual Disk. Disk Profile
        # test_gluster_1 with id b9711b73-7ed7-4b30-a8d7-e749a328b937 is not
        # assigned to Storage Domain iscsi_0.]
        # TODO: after https://bugzilla.redhat.com/show_bug.cgi?id=1361838
        # is fixed remove the ignore_type=[config.STORAGE_TYPE_GLUSTER]
        self.second_domain = ll_disks.get_other_storage_domain(
            disk=disks_objs[0].get_id(), force_type=config.MIGRATE_SAME_TYPE,
            key='id', ignore_type=[config.STORAGE_TYPE_GLUSTER]
        )
        target_domain = filter(
            lambda w: w != self.second_domain, self.storage_domains)[0]

        logger.info(
            "Creating second template %s from vm %s to storage domain %s",
            self.test_templates[1], self.base_vm, target_domain
        )
        if not ll_templates.createTemplate(
            True, True, vm=self.base_vm, name=self.test_templates[1],
            cluster=config.CLUSTER_NAME, storagedomain=target_domain
        ):
            raise exceptions.TemplateException(
                "Failed to create template '%s'" % self.test_templates[1]
            )
        template_disks = ll_disks.getObjDisks(
            self.test_templates[1], get_href=False, is_template=True
        )
        ll_templates.copy_template_disks(
            True, self.test_templates[1], template_disks[0].get_alias(),
            self.second_domain
        )
        if not ll_templates.waitForTemplatesStates(
            names=",".join(self.test_templates)
        ):
            raise exceptions.TemplateException(
                "Template '%s' failed to reach OK status" %
                ",".join(self.test_templates)
            )

        for template in self.test_templates:
            ll_templates.wait_for_template_disks_state(template)

    def setUp(self):
        """
        Prepares templates test_templates and vms based on that templates
        """
        self.test_templates = [
            "{0}_{1}".format(
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
                )[:33], "single"
            ),
            "{0}_{1}".format(
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
                )[:35], "both"
            )
        ]
        self.vm_names = [
            "{0}_{1}".format(
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_VM
                ), "from_single"
            ),
            "{0}_{1}".format(
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_VM
                ), "from_both"
            )
        ]

        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        super(TestCase5993, self).setUp()
        self.base_vm = self.vm_name
        self._prepare_templates()
        for template, vm_name in zip(self.test_templates, self.vm_names):
            template_disks = ll_disks.getObjDisks(
                template, get_href=False, is_template=True
            )
            sd_obj = ll_sd.get_storage_domain_obj(
                template_disks[0].storage_domains.storage_domain[0].get_id(),
                key='id'
            )
            target_sd = sd_obj.get_name()
            if target_sd == self.second_domain:
                sd_obj = ll_sd.get_storage_domain_obj(
                    (template_disks[0].storage_domains.storage_domain[1].
                     get_id()), key='id'
                )
                target_sd = sd_obj.get_name()

            if not ll_vms.addVm(
                True, name=vm_name, cluster=config.CLUSTER_NAME,
                storagedomain=target_sd, template=template
            ):
                raise exceptions.VMException(
                    "Cannot create vm %s from template %s on storage "
                    "domain %s" % (vm_name, template, target_sd)
                )

        ll_vms.start_vms(self.vm_names, 2, config.VM_UP, False)

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_LIVE_MIGRATE_DISK])
    @polarion("RHEVM3-5993")
    def test_thin_provision_copy_template_on_both_domains(self):
        """
        template is copied to both domains:
        - create a vm from template and run the vm
        - move vm to target domain
        template is copied on only one domain:
        - create vm from template and run the vm
        - move the vm to second domain
        """
        ll_vms.live_migrate_vm(
            self.vm_names[1], LIVE_MIGRATION_TIMEOUT,
            target_domain=self.second_domain
        )
        ll_vms.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

        logger.info(
            "Moving VM with disks on both domain has finished successfully"
        )

        # Second test - template is copied on only one domain:
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm(
                self.vm_names[0], LIVE_MIGRATION_TIMEOUT,
                same_type=config.MIGRATE_SAME_TYPE
            )

    def tearDown(self):
        """
        Removes disks, vms and templates
        """
        self.vm_names.append(self.vm_name)
        self.teardown_wait_for_disks_and_snapshots(
            [self.vm_names[0], self.vm_names[1]]
        )
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error("Failed to remove VMs %s", ', '.join(self.vm_names))
            BaseTestCase.test_failed = True
        if not ll_templates.removeTemplates(True, self.test_templates):
            logger.error(
                "Failed to remove templates %s", ', '.join(self.test_templates)
            )
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs(
            [config.JOB_REMOVE_VM, config.JOB_REMOVE_TEMPLATE]
        )
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5992(BaseTestCase):
    """
    snapshots and move vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5992'

    def _prepare_snapshots(self, vm_name):
        """
        Creates one snapshot on the input vm
        """
        ll_vms.waitForVmsDisks(vm_name)
        logger.info("Add snapshot to vm %s", vm_name)
        if not ll_vms.addSnapshot(True, vm_name, self.snapshot_desc):
            raise exceptions.VMException(
                "Add snapshot to vm %s failed" % vm_name
            )
        ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
        ll_vms.start_vms([vm_name], 1, config.VM_UP, False)

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
        ll_vms.live_migrate_vm(
            self.vm_name, same_type=config.MIGRATE_SAME_TYPE
        )


@attr(tier=2)
class TestCase5991(BaseTestCase):
    """
    live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages'] or
        config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '5991'
    test_vm_name = None
    permutation = {}
    disk_name = None

    def _prepare_shared_disk_environment(self):
        """
        Creates second vm and shared disk for both of vms
        """
        logger.info('Creating vm')
        if not ll_vms.addVm(
            True, True, name=self.test_vm_name, cluster=config.CLUSTER_NAME,
            display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
            type=config.VM_TYPE
        ):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.test_vm_name
            )
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
        ll_disks.addDisk(True, **disk_args)
        ll_disks.wait_for_disks_status(self.disk_name)
        storage_helpers.prepare_disks_for_vm(
            self.test_vm_name, [self.disk_name]
        )
        storage_helpers.prepare_disks_for_vm(self.vm_name, [self.disk_name])

    def setUp(self):
        """
        Prepare environment with shared disk
        """
        super(TestCase5991, self).setUp()
        self.test_vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        self._prepare_shared_disk_environment()

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_LIVE_MIGRATE_DISK])
    @polarion("RHEVM3-5991")
    def test_lsm_with_shared_disk(self):
        """
        create and run several vm's with the same shared disk
        - try to move one of the vm's images
        """
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE,
            ignore_type=[config.STORAGE_TYPE_GLUSTER]
        )
        ll_vms.live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd)

    def tearDown(self):
        """
        Removed created snapshots
        """
        self.teardown_wait_for_disks_and_snapshots(
            [self.vm_name, self.test_vm_name]
        )
        if not ll_vms.safely_remove_vms([self.test_vm_name]):
            logger.error("Failed to remove VM %s", self.test_vm_name)
            BaseTestCase.test_failed = True

        if not ll_disks.deleteDisk(True, self.disk_name):
            logger.error(
                "Failed to remove disk %s", self.disk_name
            )
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM, config.JOB_REMOVE_DISK])
        super(TestCase5991, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5989(BaseTestCase):
    """
    suspended vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5989'

    def setUp(self):
        super(TestCase5989, self).setUp()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    def _suspended_vm_and_wait_for_state(self, state):
        """
        Suspending vm and perform LSM after vm is in desired state
        """
        if not ll_vms.suspendVm(True, self.vm_name, wait=False):
            raise exceptions.VMException(
                "Failed to suspend VM '%s'" % self.vm_name
            )
        if not ll_vms.waitForVMState(self.vm_name, state):
            raise exceptions.VMException(
                "VM '%s' failed to reach state '%s'" % (self.vm_name, state)
            )
        ll_vms.live_migrate_vm(
            self.vm_name, LIVE_MIGRATION_TIMEOUT, ensure_on=False,
            same_type=config.MIGRATE_SAME_TYPE
        )

    @polarion("RHEVM3-5989")
    def test_lsm_while_suspended_state(self):
        """
        2) suspended state
            - create and run a vm
            - suspend the vm
            - try to migrate the vm's images once the vm is suspended
        * We should not be able to migrate images
        """
        with pytest.raises(exceptions.DiskException):
            self._suspended_vm_and_wait_for_state(config.VM_SUSPENDED)

    def tearDown(self):
        """Stop the vm in suspend state"""
        # Make sure the vm is in suspended state before stopping it
        if not ll_vms.waitForVMState(self.vm_name, config.VM_SUSPENDED):
            logger.error("Failed to suspend VM '%s'", self.vm_name)
            BaseTestCase.test_failed = True
        super(TestCase5989, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5988(AllPermutationsDisks):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5988'
    snap_created = None

    def setUp(self):
        """
        Start the vm
        """
        super(TestCase5988, self).setUp()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    def _prepare_snapshots(self, vm_name, expected_status=True):
        """
        Creates one snapshot on the vm vm_name
        """
        logger.info("Creating new snapshot for vm %s", vm_name)
        status = ll_vms.addSnapshot(
            expected_status, vm_name, self.snapshot_desc
        )
        ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
        return status

    @polarion("RHEVM3-5988")
    def test_lsm_before_snapshot(self):
        """
        1) move -> create snapshot
            - create and run a vm
            - move vm's
            - try to create a live snapshot
        * we should succeed to create a live snapshot
        """
        ll_vms.live_migrate_vm(
            self.vm_name, LIVE_MIGRATION_TIMEOUT,
            same_type=config.MIGRATE_SAME_TYPE
        )
        self.verify_lsm()
        assert self._prepare_snapshots(self.vm_name)

    @polarion("RHEVM3-" + polarion_test_case)
    def test_lsm_after_snapshot(self):
        """
        2) create snapshot -> move
            - create and run a vm
            - create a live snapshot
            - move the vm's images
        * we should succeed to move the vm
        """
        assert self._prepare_snapshots(self.vm_name)
        ll_vms.live_migrate_vm(
            self.vm_name, LIVE_MIGRATION_TIMEOUT,
            same_type=config.MIGRATE_SAME_TYPE
        )
        self.verify_lsm()

    @polarion("RHEVM3-5988")
    def test_lsm_while_snapshot(self):
        """
        3) move + create snapshots
            - create and run a vm
            - try to create a live snapshot + move
        * we should block move+create live snapshot in backend.
        """
        for disk in DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk, target_sd, timeout=LIVE_MIGRATION_TIMEOUT,
                wait=False
            )
            ll_disks.wait_for_disks_status([disk], status=config.DISK_LOCKED)
            assert self._prepare_snapshots(self.vm_name, expected_status=False)
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            # TODO: Investigate. For some reason the remove of the
            # aut-generated snapshot job doesn't start immediately,
            # wait until the job starts and then wait until it finishes
            sampler = TimeoutingSampler(
                30, 5, ll_jobs.get_active_jobs, [config.JOB_REMOVE_SNAPSHOT]
            )
            for jobs in sampler:
                if jobs:
                    # Wait until the remove of auto-generated snapshot starts
                    break
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


@attr(tier=2)
class TestCase5986(BaseTestCase):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case

    __test__ = False
    polarion_test_case = '5986'

    def setUp(self):
        """
        Prepares a floating disk
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase5986, self).setUp()
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, provisioned_size=(60 * config.GB),
            wipe_after_delete=True, attach=True,
            sd_name=self.storage_domains[0]
        )
        ll_disks.wait_for_disks_status([self.disk_name])
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5986")
    def test_vms_live_migration(self):
        """
        Actions:
            - create a vm with large preallocated+wipe after
              delete disk
            - run vm
            - move vm's images to second domain
        Expected Results:
            - move should failed, rollback should occurs
        """
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.live_migrate_vm_disk(
            self.vm_name, self.disk_name, target_sd, LIVE_MIGRATE_LARGE_SIZE,
            wait=True
        )

    def tearDown(self):
        """
        Restore environment
        """
        super(TestCase5986, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5995(AllPermutationsDisks):
    """
    Images located on different domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5995'
    disk_to_move = ''

    def _perform_action(self, vm_name, disk_name):
        """
        Move one disk to second storage domain
        """
        self.disk_to_move = disk_name
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_to_move, vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.move_vm_disk(vm_name, self.disk_to_move, target_sd)
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_to_move, vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.start_vms([vm_name], 1, config.VM_UP, False)
        ll_vms.live_migrate_vm_disk(
            self.vm_name, self.disk_to_move, target_sd, LIVE_MIGRATION_TIMEOUT
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        ll_vms.stop_vms_safely([self.vm_name])

    @polarion("RHEVM3-5995")
    def test_lsm_with_image_on_target(self):
        """
        move disk images to a domain that already has one of the images on it
        """
        for disk in DISK_NAMES[self.storage]:
            self._perform_action(self.vm_name, disk)


@attr(tier=2)
class TestCase5996(BaseTestCase):
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
    __test__ = False
    polarion_test_case = '5996'

    def setUp(self):
        """
        Prepares a floating disk
        """
        super(TestCase5996, self).setUp()
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, sparse=True,
            disk_format=config.COW_DISK, sd_name=self.storage_domains[0]
        )

    def _test_plugged_disk(self, vm_name, activate=True):
        """
        Performs migration with hotplugged disk
        """
        disk_name = self.disk_name
        logger.info("Attaching disk %s to vm %s", disk_name, vm_name)
        if not ll_disks.attachDisk(True, disk_name, vm_name, active=activate):
            raise exceptions.DiskException(
                "Cannot attach floating disk %s to vm %s" %
                (disk_name, vm_name)
            )
        ll_vms.is_active_disk(vm_name, disk_name, 'alias')
        inactive_disk = ll_vms.is_active_disk(vm_name, disk_name, 'alias')
        if activate and not inactive_disk:
            logger.warning("Disk %s in vm %s is not active after attaching",
                           disk_name, vm_name)
            assert ll_vms.activateVmDisk(True, vm_name, disk_name)

        elif not activate and inactive_disk:
            logger.warning("Disk %s in vm %s is active after attaching",
                           disk_name, vm_name)
            assert ll_vms.deactivateVmDisk(True, vm_name, disk_name)
        logger.info("%s disks active: %s %s", disk_name,
                    inactive_disk, type(inactive_disk))
        ll_vms.waitForVmsDisks(vm_name)
        ll_vms.live_migrate_vm(
            vm_name, LIVE_MIGRATION_TIMEOUT, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Live migration completed")

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
        super(TestCase5996, self).tearDown()
        self.teardown_exception()


@attr(tier=2)
class TestCase6003(BaseTestCase):
    """
    Attach disk during migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6003'

    def setUp(self):
        """
        Prepares a floating disk
        """
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase6003, self).setUp()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_alias, sparse=True,
            disk_format=config.COW_DISK, sd_name=self.storage_domains[0]
        )

    @polarion("RHEVM3-6003")
    def test_attach_disk_during_lsm(self):
        """
        migrate vm's images -> try to attach a disk during migration
        * we should fail to attach disk
        """
        ll_vms.live_migrate_vm(
            self.vm_name, LIVE_MIGRATION_TIMEOUT, False,
            same_type=config.MIGRATE_SAME_TYPE
        )

        logger.info("Wait until the LSM locks disk '%s'", self.vm_disk_name)
        ll_disks.wait_for_disks_status(
            [self.vm_disk_name], status=config.DISK_LOCKED
        )
        status = ll_disks.attachDisk(False, self.disk_alias, self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_disks.wait_for_disks_status([self.vm_disk_name, self.disk_alias])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        assert status, "Succeeded to attach disk during LSM"

    def tearDown(self):
        """
        Remove VM and disk
        """
        super(TestCase6003, self).tearDown()
        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Failed to delete disk '%s'", self.disk_alias)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase6001(BaseTestCase):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6001'
    succeeded = False

    def setUp(self):
        """
        Prepares one domain in maintenance
        """
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase6001, self).setUp()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        self.vm_disk = ll_vms.getVmDisks(self.vm_name)[0]
        self.target_sd = ll_disks.get_other_storage_domain(
            self.vm_disk.get_alias(), self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )

        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.target_sd
        )
        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            ENUMS['storage_domain_state_maintenance']
        ):
            raise exceptions.StorageDomainException(
                "Storage domain '%s' failed to reach maintenance mode" %
                self.target_sd
            )

    @polarion("RHEVM3-6001")
    def test_lsm_to_maintenance_domain(self):
        """
        try to migrate to a domain in maintenance
        * we should fail to attach disk
        """
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm_disk(
                self.vm_name, self.vm_disk.get_alias(), self.target_sd,
                LIVE_MIGRATION_TIMEOUT, True
            )
        self.succeeded = True

    def tearDown(self):
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        if not ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.target_sd
        ):
            logger.error(
                "Failed to activate storage domain '%s'", self.target_sd
            )
            BaseTestCase.test_failed = True
        super(TestCase6001, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5972(BaseTestCase):
    """
    live migrate vm with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5972'
    disk_count = 3

    def setUp(self):
        """
        Prepares disks on different domains
        """
        super(TestCase5972, self).setUp()
        self.disks_names = []
        self._prepare_disks_for_vm(self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    def _prepare_disks_for_vm(self, vm_name):
        """
        Prepares disk for given vm
        """
        disk_params = config.disk_args.copy()
        disk_params['provisioned_size'] = 1 * config.GB
        disk_params['format'] = config.RAW_DISK
        disk_params['sparse'] = False

        for index in range(self.disk_count):
            disk_params['alias'] = (
                storage_helpers.create_unique_object_name(
                    self.__class__.__name__, config.OBJECT_TYPE_DISK
                )
            )
            disk_params['storagedomain'] = self.storage_domains[index]
            if not ll_disks.addDisk(True, **disk_params):
                raise exceptions.DiskException(
                    "Can't create disk with params: %s" % disk_params
                )
            logger.info(
                "Waiting for disk %s to be ok", disk_params['alias']
            )
            ll_disks.wait_for_disks_status(disk_params['alias'])
            self.disks_names.append(disk_params['alias'])
            assert ll_disks.attachDisk(True, disk_params['alias'], vm_name)

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
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk, self.storage_domains[2]
            )


@attr(tier=2)
class TestCase5970(BaseTestCase):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '5970'
    regex = config.REGEX_DD_WIPE_AFTER_DELETE

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase5970, self).setUp()
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, wipe_after_delete=True, attach=True,
            sd_name=self.storage_domains[0]
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

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
        host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(host)
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        disk_obj = ll_disks.getVmDisk(self.vm_name, self.disk_name)
        self.regex = self.regex % disk_obj.get_image_id()

        def f(q):
            q.put(
                watch_logs(
                    files_to_watch=FILE_TO_WATCH, regex=self.regex,
                    time_out=LIVE_MIGRATION_TIMEOUT, ip_for_files=self.host_ip,
                    username=config.HOSTS_USER, password=config.HOSTS_PW
                )
            )

        q = Queue()
        p = Process(target=f, args=(q,))
        p.start()
        sleep(5)
        ll_vms.live_migrate_vm_disk(
            self.vm_name, self.disk_name, target_sd, wait=False
        )
        p.join()
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        exception_code, output = q.get()
        assert exception_code, "Couldn't find regex %s, output: %s" % (
            self.regex, output
        )


@attr(tier=2)
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
        """
        Start the vm
        """
        super(TestCase5969, self).setUp()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    def turn_off_method(self):
        raise NotImplemented("This should not be executed")

    def _perform_action_on_disk_and_wait_for_regex(self, disk_name, regex):
        disk_id = ll_disks.get_disk_obj(disk_name).get_id()
        host = ll_hosts.getSPMHost(config.HOSTS)
        self.host_ip = ll_hosts.getHostIP(host)
        target_sd = ll_disks.get_other_storage_domain(
            disk=disk_id, vm_name=self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE, key='id'
        )

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
        ll_vms.live_migrate_vm_disk(
            self.vm_name, disk_name, target_sd, wait=False
        )
        p.join()
        ex_code, output = q.get()
        assert ex_code, "Couldn't find regex %s, output: %s" % (regex, output)
        self.turn_off_method()
        # Is need to wait for the rollback after the LSM fails
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, disk_name, self.disk_sd
        ), "Succeeded to live migrate vm disk %s" % disk_name

    @polarion("RHEVM3-5969")
    def test_power_off_createVolume(self):
        """
        Actions:
            - Live migrate vm disks and wait for 'createVolume' command
            - power off vm
        Expected Results:
            - we should fail the LSM nicely
        """
        for disk_name in DISK_NAMES[self.storage]:
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
        for disk_name in DISK_NAMES[self.storage]:
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
        for disk_name in DISK_NAMES[self.storage]:
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
        for disk_name in DISK_NAMES[self.storage]:
            self._perform_action_on_disk_and_wait_for_regex(
                disk_name, 'deleteImage'
            )


class TestCase5969PowerOff(TestCase5969):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        ll_vms.stopVm(True, self.vm_name, 'false')


class TestCase5969Shutdown(TestCase5969):
    # TODO: Fix this case
    __test__ = False

    def turn_off_method(self):
        ll_vms.shutdownVm(True, self.vm_name, 'false')


@attr(tier=2)
class TestCase5968(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
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
        for disk in DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            ll_vms.startVm(True, self.vm_name, config.VM_UP)
            ll_vms.live_migrate_vm_disk(self.vm_name, disk, target_sd)
            assert ll_vms.stopVm(True, self.vm_name)
            ll_vms.remove_all_vm_lsm_snapshots(self.vm_name)
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
            disk_obj = ll_disks.getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info(
                "Actual size after live migrate disk %s is: %s",
                disk, actual_size
            )
            logger.info(
                "Virtual size after live migrate disk %s is: %s",
                disk, virtual_size
            )
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            assert actual_size <= virtual_size, (
                "Actual size exceeded to virtual size"
            )


@bz({'1368203': {}})
@attr(tier=2)
class TestCase5967(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5967'

    @polarion("RHEVM3-5967")
    def test_live_migration_auto_shrink(self):
        """
        Actions:
            - 2 data storage domains
            - create -> run the vm -> move the vm
            - Stop the VM while the Live migration is in progress, causing
              a failure
            - delete the Live migration snapshot

        Expected Results:
            - the image actual size should not exceed the disks
              virtual size once we delete the snapshot
            - make sure that we can delete the snapshot and run the vm
        """
        for disk in DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            ll_vms.startVm(True, self.vm_name, config.VM_UP)
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk, target_sd, wait=False
            )
            ll_disks.wait_for_disks_status(
                [self.vm_disk_name], status=config.DISK_LOCKED
            )
            ll_vms.stopVm(True, self.vm_name)
            ll_vms.waitForVmsDisks(self.vm_name)
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
            disk_obj = ll_disks.getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info(
                "Actual size after live migrate disk %s is: %s",
                disk, actual_size
            )
            logger.info(
                "Virtual size after live migrate disk %s is: %s",
                disk, virtual_size
            )
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            assert actual_size <= virtual_size, (
                "Actual size exceeded virtual size"
            )


@attr(tier=2)
class TestCase5979(BaseTestCase):
    """
    offline migration for disk attached to running vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5979'
    expected_lsm_snap_count = 0

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        # If any LSM snapshot exists --> remove them to be able to check if
        # the disk movement in this case is cold move and not live storage
        # migration
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase5979, self).setUp()
        ll_vms.remove_all_vm_lsm_snapshots(self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, attach=True,
            sd_name=self.storage_domains[0]
        )
        if not ll_vms.deactivateVmDisk(True, self.vm_name, self.disk_name):
            raise exceptions.VMException(
                "Failed to deactivate disk '%s' from VM '%s'" %
                (self.disk_name, self.vm_name)
            )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

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
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.live_migrate_vm_disk(self.vm_name, self.disk_name, target_sd)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

        snapshots = ll_vms.get_vm_snapshots(self.vm_name)
        LSM_snapshots = [s for s in snapshots if
                         (s.get_description() ==
                          config.LIVE_SNAPSHOT_DESCRIPTION)]
        logger.info("Verify that the migration was not live migration")
        assert len(LSM_snapshots) == self.expected_lsm_snap_count


@attr(tier=2)
class TestCase5976(BaseTestCase):
    """
    Deactivate vm disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5976'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase5976, self).setUp()
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, attach=True,
            sd_name=self.storage_domains[0]
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

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
        disk_id = ll_disks.get_disk_obj(self.disk_name).get_id()

        target_sd = ll_disks.get_other_storage_domain(
            disk_id, self.vm_name, force_type=config.MIGRATE_SAME_TYPE,
            key='id'
        )
        ll_vms.live_migrate_vm_disk(
            self.vm_name, self.disk_name, target_sd=target_sd, wait=False
        )
        sleep(5)
        status = ll_vms.deactivateVmDisk(False, self.vm_name, self.disk_name)
        assert status, (
            "Succeeded to deactivate vm disk %s during live storage migration"
            % self.disk_name
        )

    def tearDown(self):
        """
        Remove the extra disk
        """
        super(TestCase5976, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5977(BaseTestCase):
    """
    migrate a vm between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5977'

    def _migrate_vm_during_lsm_ops(self, wait):
        ll_vms.live_migrate_vm(
            self.vm_name, wait=wait, same_type=config.MIGRATE_SAME_TYPE
        )
        status = ll_vms.migrateVm(True, self.vm_name, wait=False)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        return status

    @polarion("RHEVM3-5977")
    @bz({'1258219': {}})
    def test_LSM_during_vm_migration(self):
        """
        Actions:
            - create and run a vm
            - migrate the vm between the hosts
            - try to LSM the vm disk during the vm migration
        Expected Results:
            - we should be stopped by CanDoAction
        """
        disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        target_sd = ll_disks.get_other_storage_domain(
            disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.migrateVm(True, self.vm_name, wait=False)
        with pytest.raises(exceptions.DiskException):
            ll_vms.live_migrate_vm_disk(self.vm_name, disk_name, target_sd)

    @polarion("RHEVM3-5977")
    @bz({'1258219': {}})
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
        assert not status, "Succeeded to migrate vm during LSM"

    @polarion("RHEVM3-5977")
    @bz({'1258219': {}})
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
        assert status, "Succeeded to migrate vm during LSM"


@attr(tier=2)
class TestCase5975(BaseTestCase):
    """
    Extend storage domain while lsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Needs 4 iscsi storage domains (only on block device)
    __test__ = False
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
        """
        Set the args with luns
        """
        self.sd_src = "{0}_{1}".format(
            "source_domain_", storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SD
            )
        )
        self.sd_target = "{0}_{1}".format(
            "target_domain_", storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SD
            )
        )
        for index, sd_name in [self.sd_src, self.sd_target]:
            sd_name_dict = self.generate_sd_dict(index)
            sd_name_dict.update(
                {"storage": sd_name, "data_center": config.DATA_CENTER_NAME}
            )
            if not hl_sd.addISCSIDataDomain(**sd_name_dict):
                logger.error("Error adding storage %s", sd_name_dict)

            wait_for_tasks(
                config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
            )

        self.vm_sd = self.sd_src
        super(TestCase5975, self).setUp()

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_LIVE_MIGRATE_DISK])
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
        disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.live_migrate_vm_disk(
            self.vm_name, disk_name, self.sd_target, wait=False
        )
        if not ll_sd.extendStorageDomain(
            True, self.sd_src, **self.generate_sd_dict(2)
        ):
            raise exceptions.StorageDomainException(
                "Failed to extend source storage domain '%s'" % self.sd_src
            )
        if not ll_sd.extendStorageDomain(
            True, self.sd_target, **self.generate_sd_dict(3)
        ):
            raise exceptions.StorageDomainException(
                "Failed to extend target storage domain '%s'" % self.sd_target
            )

    def tearDown(self):
        """Remove the added storage domains"""
        super(TestCase5975, self).tearDown()
        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        if not ll_sd.removeStorageDomains(
            True, [self.sd_src, self.sd_target], spm_host
        ):
            logger.error("Failed to remove storage domains")
            BaseTestCase.test_failed = True
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        BaseTestCase.teardown_exception()


@attr(tier=4)
class TestCase6000(BaseTestCase):
    """
    live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    # Bugzilla history:
    # 1106593: Failed recovering from crash or initializing after blocking
    # connection from host to target storage domain during LSM (marked as
    # Won't Fix)

    polarion_test_case = '6000'

    def _migrate_vm_disk_and_block_connection(
        self, disk, source, username, password, target, target_ip
    ):
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.live_migrate_vm_disk(self.vm_name, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password, target_ip)
        assert status, "Failed to block connection"
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

    @polarion("RHEVM3-6000")
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        host_ip = ll_hosts.getHostIP(spm_host)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        status, target_sd_ip = ll_sd.getDomainAddress(True, self.target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.target_sd, target_sd_ip
        )
        status = ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd, self.target_sd
        )
        assert not status, "Disk moved but shouldn't have"

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(
            self.source_ip, self.username, self.password, self.target_sd_ip
        )
        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            config.SD_STATE_ACTIVE
        ):
            logger.error("Domain '%s' is not active", self.target_sd)
            BaseTestCase.test_failed = True
        super(TestCase6000, self).setUp()
        BaseTestCase.teardown_exception()


@attr(tier=4)
class TestCase6002(BaseTestCase):
    """
    VDSM restart during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6002'
    # Bugzilla history:
    # 1210771: After rebooting the spm job "Handling non responsive Host" is
    # stuck in STARTED (even if the host is back up)

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
        spm_host = ll_hosts.getHostIP(ll_hosts.getSPMHost(config.HOSTS))
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        restartVdsmd(spm_host, config.HOSTS_PW)


@attr(tier=4)
class TestCase5999(BaseTestCase):
    """
    live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    # Bugzilla history:
    # 1210771: After rebooting the spm job "Handling non responsive Host" is
    # stuck in STARTED (even if the host is back up)
    polarion_test_case = '5999'

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
        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=spm_host
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Rebooting host (SPM) %s", spm_host)
        assert ll_hosts.rebootHost(
            True, spm_host, config.HOSTS_USER, config.HOSTS_PW
        )
        logger.info("Waiting for host %s to come back up", spm_host)
        ll_hosts.waitForHostsStates(True, spm_host)
        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = ll_vms.verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        assert not status, (
            "Succeeded to live migrate vm disk %s during SPM host reboot" %
            vm_disk
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
        spm_host = [ll_hosts.getSPMHost(config.HOSTS)]
        hsm_host = [x for x in config.HOSTS if x not in spm_host][0]
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=hsm_host
        )
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Rebooting host (HSM) %s", hsm_host)
        assert ll_hosts.rebootHost(
            True, hsm_host, config.HOSTS_USER, config.HOSTS_PW
        )
        logger.info("Waiting for host %s to be UP", hsm_host)
        ll_hosts.waitForHostsStates(True, hsm_host)

        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = ll_vms.verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        assert not status, "Succeeded to live migrate vm disk %s" % vm_disk


@attr(tier=4)
class TestCase5998(BaseTestCase):
    """
    reboot host during live migration on HA vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    # Bugzilla history:
    # 1210771: After rebooting the spm job "Handling non responsive Host" is
    # stuck in STARTED (even if the host is back up)
    polarion_test_case = '5998'

    def _perform_action(self, host):
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )

        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Rebooting host %s", host)
        assert ll_hosts.rebootHost(
            True, host, config.HOSTS_USER, config.HOSTS_PW
        )
        logger.info("Waiting for host %s to be UP", host)
        ll_hosts.waitForHostsStates(True, host)
        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = ll_vms.verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        assert not status, "Succeeded to live migrate vm disk %s" % vm_disk

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
        spm_host = ll_hosts.getSPMHost(config.HOSTS)
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=spm_host
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
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
        spm_host = [ll_hosts.getSPMHost(config.HOSTS)]
        hsm_host = [host for host in config.HOSTS if host not in spm_host][0]
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=hsm_host
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        self._perform_action(hsm_host)


@attr(tier=4)
class TestCase5997(BaseTestCase):
    """
    kill vm's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    polarion_test_case = '5997'

    def _kill_vm_pid(self):
        host = ll_vms.getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(
            host=host, user=config.HOSTS_USER,
            password=config.HOSTS_PW
        ).util('linux')
        host_machine.kill_qemu_process(self.vm_name)

    def perform_action(self):
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Killing vms %s pid", self.vm_name)
        self._kill_vm_pid()

        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = ll_vms.verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        assert not status, "Succeeded to live migrate vm disk %s" % vm_disk

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
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        assert ll_vms.updateVm(True, self.vm_name, highly_available='true')
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
        ll_vms.stopVm(True, self.vm_name, async=False)
        assert ll_vms.updateVm(True, self.vm_name, highly_available='false')
        self.perform_action()


@attr(tier=2)
class TestCase5985(BaseTestCase):
    """
    no space left
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix, our storage domains are too big for creating preallocated
    # TODO: this cases is disabled due to ticket RHEVM-2524
    # disks, wait for threshold feature Bug 1288862

    __test__ = False
    polarion_test_case = '5985'

    @polarion("RHEVM3-5985")
    @bz({'1288862': {}})
    def test_no_space_disk_during_lsm(self):
        """
        Actions:
            - start a live migration
            - while migration is running, create a large preallocated disk
        Expected Results:
            - migration or create disk should fail nicely.
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        sd_size = ll_sd.get_free_space(target_sd)
        ll_vms.live_migrate_vm_disk(
            self.vm_name, vm_disk, target_sd, wait=False
        )
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name,
            provisioned_size=sd_size - (1 * config.GB), sd_name=target_sd
        )

        ll_disks.wait_for_disks_status([self.disk_name], timeout=TASK_TIMEOUT)
        ll_jobs.wait_for_jobs(
            [config.JOB_LIVE_MIGRATE_DISK, config.JOB_ADD_DISK]
        )
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd, target_sd
        ), "Succeeded to live migrate vm disk %s" % vm_disk

    def tearDown(self):
        """
        Remove created VM and disk
        """
        super(TestCase5985, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5971(BaseTestCase):
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
        disk_params = config.disk_args.copy()
        disk_params['provisioned_size'] = 1 * config.GB

        for index in range(self.disk_count):
            disk_params['alias'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
            disk_params['storagedomain'] = self.storage_domains[index]
            if index == 2:
                disk_params['active'] = False
            if not ll_disks.addDisk(True, **disk_params):
                raise exceptions.DiskException(
                    "Can't create disk with params: %s" % disk_params)
            logger.info(
                "Waiting for disk %s to be OK", disk_params['alias']
            )
            ll_disks.wait_for_disks_status(disk_params['alias'])
            self.disks_names.append(disk_params['alias'])
            assert ll_disks.attachDisk(
                True, disk_params['alias'], vm_name, disk_params['active']
            )

    def setUp(self):
        """
        Prepares disks on different domains
        """
        self.disks_names = []
        super(TestCase5971, self).setUp()
        ll_vms.stop_vms_safely([self.vm_name])
        self._prepare_disks_for_vm(self.vm_name)
        logger.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.storage_domains[2],
        )

        ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.storage_domains[2],
            config.SD_MAINTENANCE
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

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
            src_sd = ll_disks.get_disk_storage_domain_name(disk, self.vm_name)
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )

            if index == 2:
                with pytest.raises(exceptions.DiskException):
                    ll_vms.live_migrate_vm_disk(self.vm_name, disk, target_sd)

                assert not ll_vms.verify_vm_disk_moved(
                    self.vm_name, disk, src_sd
                ), "Succeeded to live migrate disk %s" % disk
            else:
                ll_vms.live_migrate_vm_disk(
                    self.vm_name, disk, target_sd=target_sd
                )
                assert ll_vms.verify_vm_disk_moved(
                    self.vm_name, disk, src_sd
                ), "Failed to live migrate disk %s" % disk

    def tearDown(self):
        """
        Removes disks and snapshots
        """
        if not ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.storage_domains[2]
        ):
            logger.error(
                "Failed to activate storage domain '%s'",
                self.storage_domains[2]
            )
            BaseTestCase.test_failed = True
        if not BaseTestCase.test_failed:
            if not ll_sd.waitForStorageDomainStatus(
                True, config.DATA_CENTER_NAME, self.storage_domains[2],
                config.SD_STATE_ACTIVE
            ):
                logger.error(
                    "Domain '%s' is not active", self.storage_domains[2]
                )
                BaseTestCase.test_failed = True
        super(TestCase5971, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase5980(BaseTestCase):
    """
    offline migration + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5980'

    def setUp(self):
        """
        Prepares disk with wipe_after_delete=True for VM
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        super(TestCase5980, self).setUp()
        helpers.add_new_disk_for_test(
            self.vm_name, self.disk_name, sd_name=self.storage_domains[0]
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5980")
    def test_offline_migration_and_lsm(self):
        """
        Actions:
            - create a vm with 1 disk
            - run the vm
            - live migrate the disk
            - try to attach a floating disk (attach as deactivated)
        Expected Results:
            - we should not be able to attach the disk to a vm which is in
            the middle of a LSM
        """
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        logger.info("Wait until the LSM locks disk '%s'", self.vm_disk_name)
        ll_disks.wait_for_disks_status(
            [self.vm_disk_name], status=config.DISK_LOCKED
        )
        status = ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, active=False
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_disks.wait_for_disks_status([self.vm_disk_name, self.disk_name])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        assert status, "Attach operation succeeded during a LSM"

    def tearDown(self):
        """
        Remove the floating disk
        """
        super(TestCase5980, self).tearDown()
        if not ll_disks.deleteDisk(True, self.disk_name):
            logger.error("Failed to delete disk '%s'", self.disk_name)
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        BaseTestCase.teardown_exception()


@attr(tier=4)
class TestCase5966(BaseTestCase):
    """
    kill vdsm during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
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
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        host = ll_vms.getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(
            host=host, user=config.HOSTS_USER, password=config.HOSTS_PW
        ).util('linux')

        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        sleep(5)
        host_machine.kill_vdsm_service()

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
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        host = ll_vms.getVmHost(self.vm_name)[1]['vmHoster']
        host_machine = Machine(
            host=host, user=config.HOSTS_USER, password=config.HOSTS_PW
        ).util('linux')

        ll_vms.live_migrate_vm(
            self.vm_name, wait=True, same_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.live_migrate_vm(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        sleep(5)
        host_machine.kill_vdsm_service()


@attr(tier=2)
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
        spm_host = [ll_hosts.getSPMHost(config.HOSTS)]
        hsm_host = [x for x in config.HOSTS if x not in spm_host][0]
        ll_vms.updateVm(True, self.vm_name, placement_host=hsm_host)
        ll_vms.startVm(True, self.vm_name, config.VM_UP, True)
        for index, disk in enumerate(DISK_NAMES[self.storage]):
            source_sd = ll_disks.get_disk_storage_domain_name(
                disk, self.vm_name
            )
            disk_id = ll_disks.get_disk_obj(disk).get_id()
            target_sd = ll_disks.get_other_storage_domain(
                disk=disk_id, vm_name=self.vm_name,
                force_type=config.MIGRATE_SAME_TYPE, key='id'
            )
            logger.info("Ensure sure disk is accessible")
            assert ll_vms.get_vm_disk_logical_name(
                self.vm_name, disk_id, key='id'
            )
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk, target_sd, wait=False
            )

            def f():
                status, _ = storage_helpers.perform_dd_to_disk(
                    self.vm_name, disk, size=int(config.DISK_SIZE * 0.9),
                    write_to_file=True
                )

            logger.info("Writing to disk")
            p = Process(target=f, args=())
            p.start()
            status = storage_helpers.wait_for_dd_to_start(
                self.vm_name, timeout=DD_TIMEOUT
            )
            assert status, "dd didn't start writing to disk"
            logger.info(
                "Stop the vm while the live storage migration is running",
            )
            ll_vms.stop_vms_safely([self.vm_name])
            ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            ll_vms.remove_all_vm_lsm_snapshots(self.vm_name)
            ll_vms.startVm(True, self.vm_name, config.VM_UP, True)
            assert not ll_vms.verify_vm_disk_moved(
                self.vm_name, disk, source_sd, target_sd
            ), "Disk moved but shouldn't have"
            logger.info("Disk %s done", disk)


@attr(tier=2)
class TestCase5983(BaseTestCase):
    """
    migrate multiple vm's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5983'
    vm_count = 2
    vm_names = None

    def setUp(self):
        """
        Create VMs to use for test
        """
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.vm_names = []
        self.vm_args = config.create_vm_args.copy()
        self.vm_args['installation'] = False
        for index in range(self.vm_count):
            self.vm_args['storageDomainName'] = self.storage_domains[0]
            self.vm_args['vmName'] = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_VM
            )
            self.vm_args['vmDescription'] = (
                "{0}_{1}".format(self.vm_args['vmName'], "description")
            )

            logger.info('Creating vm %s', self.vm_args['vmName'])
            if not storage_helpers.create_vm_or_clone(**self.vm_args):
                raise exceptions.VMException(
                    "Unable to create vm %s for test" % self.vm_args['vmName']
                )
            self.vm_names.append(self.vm_args['vmName'])

    def _perform_action(self, host):
        """
        Place VMs on requested, power them on amd then run live migration
        """
        for vm in self.vm_names:
            ll_vms.updateVm(True, vm, placement_host=host)
        ll_vms.start_vms(self.vm_names, 1, config.VM_UP, False)
        for vm in self.vm_names:
            ll_vms.live_migrate_vm(vm, same_type=config.MIGRATE_SAME_TYPE)

    @polarion("RHEVM3-5983")
    def test_migrate_multiple_vms_on_spm(self):
        """
        Actions:
            - create 2 vms and run them on spm host only
            - LSM the disks
        Expected Results:
            - we should succeed in migrating all disks
        """
        spm = ll_hosts.getSPMHost(config.HOSTS)
        self._perform_action(spm)

    @polarion("RHEVM3-5983")
    def test_migrate_multiple_vms_on_hsm(self):
        """
        Actions:
            - create 2 vms and run them on hsm host only
            - LSM the disks
        Expected Results:
            - We should succeed in migrating all disks
        """
        hsm = ll_hosts.getHSMHost(config.HOSTS)
        self._perform_action(hsm)

    def tearDown(self):
        """Remove created vms"""
        # In order to clean up the VMs and disks created, we need to wait
        # until the VM snapshots and disks are in the OK state, wait for
        # this and continue even on timeouts
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        self.teardown_wait_for_disks_and_snapshots(self.vm_names)
        if not ll_vms.safely_remove_vms(self.vm_names):
            logger.error(
                "Failed to power off and remove VMs '%s'", ', '.join(
                    self.vm_names
                )
            )
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=4)
class TestCase5984(BaseTestCase):
    """
    connectivity issues to pool
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    - https://bugzilla.redhat.com/show_bug.cgi?id=1078095
    """
    # TODO: tier4 jobs have not been verified
    __test__ = False
    # Bugzilla history:
    # 1106593: Failed recovering from crash or initializing after blocking
    # connection from host to target storage domain during LSM (marked as
    # Won't Fix)
    polarion_test_case = '5984'

    def _migrate_vm_disk_and_block_connection(
        self, disk, source, username, password, target, target_ip
    ):
        if not ll_vms.startVm(True, self.vm_name, config.VM_UP):
            raise exceptions.VMException(
                "Failed to power on VM '%s'" % self.vm_name
            )

        ll_vms.live_migrate_vm_disk(self.vm_name, disk, target, wait=False)
        status = blockOutgoingConnection(source, username, password,
                                         target_ip)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        assert status, "Failed to block connection"

    @polarion("RHEVM3-5984")
    def test_LSM_block_from_hsm_to_domain(self):
        """
        Actions:
            - live migrate a vm
            - block connectivity to target domain from host using iptables
        Expected Results:
            - we should fail migrate and roll back
        """
        hsm = ll_hosts.getHSMHost(config.HOSTS)
        hsm_ip = ll_hosts.getHostIP(hsm)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        status, target_sd_ip = ll_sd.getDomainAddress(True, self.target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = hsm_ip
        self._migrate_vm_disk_and_block_connection(
            vm_disk, hsm_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.target_sd, target_sd_ip
        )
        status = ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd, self.target_sd
        )
        assert not status, "Disk moved but shouldn't have"

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(
            self.source_ip, self.username, self.password, self.target_sd_ip
        )

        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            config.SD_STATE_ACTIVE
        ):
            logger.error("Domain '%s' is not active", self.target_sd)
            BaseTestCase.test_failed = True

        super(TestCase5984, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=4)
class TestCase5974(BaseTestCase):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: tier4 jobs have not been verified
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
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        host = ll_hosts.getHSMHost(config.HOSTS)
        host_ip = ll_hosts.getHostIP(host)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        status, target_sd_ip = ll_sd.getDomainAddress(True, self.target_sd)
        assert status
        self.target_sd_ip = target_sd_ip['address']
        self.username = config.HOSTS_USER
        self.password = config.HOSTS_PW
        self.source_ip = host_ip

        status = blockOutgoingConnection(
            host_ip, self.username, self.password, target_sd_ip
        )
        assert status, "Failed to block connection"
        ll_vms.waitForVMState(self.vm_name, ENUMS['vm_state_paused'])
        ll_vms.live_migrate_vm(
            self.vm_name, same_type=config.MIGRATE_SAME_TYPE
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

        status = ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd, self.target_sd
        )
        assert not status, "Disk moved but shouldn't have"

    def tearDown(self):
        """
        Restore environment
        """
        unblockOutgoingConnection(self.source_ip, self.username,
                                  self.password, self.target_sd_ip)
        if not ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.target_sd,
            config.SD_STATE_ACTIVE
        ):
            logger.error("Domain '%s' is not active", self.target_sd)
            BaseTestCase.test_failed = True
        super(TestCase5974, self).tearDown()
        BaseTestCase.teardown_exception()
