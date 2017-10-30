"""
Storage migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
from multiprocessing import Process, Queue
from time import sleep
import shlex
import logging
import pytest
import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils.log_listener import watch_logs
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.utils.test_utils import (
    restartVdsmd,
)
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib.common import StorageTest, testflow
from art.rhevm_api.utils import test_utils
import rhevmtests.helpers as rhevm_helpers
from rhevmtests.storage.fixtures import (
    create_snapshot, delete_disks, deactivate_domain,
    add_disk_permutations, remove_templates, remove_vms, restart_vdsmd,
    unblock_connectivity_storage_domain_teardown, wait_for_disks_and_snapshots,
    initialize_storage_domains, initialize_variables_block_domain, create_vm,
    start_vm, create_second_vm, poweroff_vm, init_vm_executor
)
from rhevmtests.storage.storage_migration.fixtures import (
    initialize_params, add_disk, attach_disk_to_vm,
    initialize_domain_to_deactivate, create_disks_for_vm, create_templates,
    prepare_disks_for_vm, initialize_vm_and_template_names,
    create_vms_from_templates, add_two_storage_domains,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)

MIGRATION_TIMEOUT = 10 * 60
TASK_TIMEOUT = 1500
LIVE_MIGRATION_TIMEOUT = 5 * 60
WATCH_LOG_TIMEOUT = 180
DISK_TIMEOUT = 900
LIVE_MIGRATE_LARGE_SIZE = 3600
DD_TIMEOUT = 40

# After the deletion of a snapshot, vdsm allocates around 128MB of data for
# the extent metadata
EXTENT_METADATA_SIZE = 128 * config.MB

# Bugzilla history:
# 1251956: Live storage migration is broken
# 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with id'
# after live migrate a Virtio RAW disk, job stays in status STARTED
# Live Migration is broken, skip


@pytest.fixture(scope='module', autouse=True)
def inizialize_tests_params(request):
    """
    Determine whether to run plan on same storage type or on different types
    of storage
    """
    config.MIGRATE_SAME_TYPE = True


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    initialize_params.__name__,
    create_vm.__name__,
)
class BaseTestCase(StorageTest):
    """
    A class with a simple setUp
    """
    vm_sd = None
    vm_name = None
    storage_domains = None

    def check_if_live_move(self, vms):
        """
        Start VM in case of live move
        """
        if config.LIVE_MOVE:
            testflow.step("Start VM %s", vms)
            ll_vms.start_vms(vm_list=vms, wait_for_status=config.VM_UP)


@pytest.mark.usefixtures(
    add_disk_permutations.__name__,
    prepare_disks_for_vm.__name__
)
class AllPermutationsDisks(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    __test__ = False

    def verify_lsm(self, source_sd, target_sd=None, moved=True):
        """
        Verifies if the disks have been moved
        """
        if moved:
            failure_str = "Failed"
        else:
            failure_str = "Succeeded"
        for disk in config.DISK_NAMES[self.storage]:
            assert moved == ll_vms.verify_vm_disk_moved(
                self.vm_name, disk, source_sd, target_sd
            ), "%s to migrate vm disk %s" % (failure_str, disk)


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class TestCase6004(AllPermutationsDisks):
    """
    Live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6004'

    @tier1
    @polarion("RHEVM3-6004")
    def test_vms_live_migration(self):
        """
        Actions:
            - Move VM's images to different SD
        Expected Results:
            - Move should succeed
        """
        testflow.step(
            "Migrate vm's %s disks to another storage domain", self.vm_name
        )
        ll_vms.migrate_vm_disks(
            self.vm_name, ensure_on=config.LIVE_MOVE,
            same_type=config.MIGRATE_SAME_TYPE
        )
        self.verify_lsm(source_sd=self.storage_domain)


@pytest.mark.usefixtures(
    delete_disks.__name__,
    wait_for_disks_and_snapshots.__name__
)
class BaseConcurrentlyTests(AllPermutationsDisks):
    """
    Base class for migrating multiple disks concurrently
    """
    disk_count = 4
    disks_size = 10 * config.GB

    def basic_flow(self):
        """
        Migrate VM's disks to different storage-domain and verify that the
        move succeeded
        """
        target_sd = ll_disks.get_other_storage_domain(
            disk=self.disk_names[0], vm_name=self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE,
            ignore_type=[config.STORAGE_TYPE_GLUSTER]
        )

        testflow.step(
            "Migrate VM's %s disks to storage domain %s concurrently",
            self.vm_name, target_sd
        )

        for disk in self.disk_names:
            testflow.step(
                "Migrating disk %s to storage domain %s", disk, target_sd
            )
            try:
                ll_vms.migrate_vm_disk(
                    vm_name=self.vm_name, disk_name=disk, target_sd=target_sd,
                    wait=False, verify_no_snapshot_operation_occur=True
                )

            except exceptions.DiskException:
                # in case VM was preforming snapshot operation, try migrate the
                # disk again, could cause when previous disk finish to migrate
                # and the live snapshot removal initiated
                ll_vms.migrate_vm_disk(
                    vm_name=self.vm_name, disk_name=disk, target_sd=target_sd,
                    wait=False, verify_no_snapshot_operation_occur=True
                )

            testflow.step(
                "Wait for %s to create", config.LIVE_SNAPSHOT_DESCRIPTION
            )
            ll_disks.wait_for_disks_status([disk], status=config.DISK_LOCKED)

            ll_vms.wait_for_snapshot_creation(
                self.vm_name, config.LIVE_SNAPSHOT_DESCRIPTION,
                include_disk_alias=disk
            )

            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)

        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        self.verify_lsm(source_sd=self.storage_domain)


@pytest.mark.usefixtures(
    create_disks_for_vm.__name__,
    start_vm.__name__
)
class BaseTestCase21798(BaseConcurrentlyTests):
    """
    Concurrent Live migration of multiple VM disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '21798'
    create_on_same_domain = True

    @tier2
    @polarion("RHEVM-21798")
    def test_vm_disks_concurrent_live_migration(self):
        """
        Actions:
            - Create a VM with 9 disks from all the disks permutations
            - Run the VM
            - Move all the VM disks concurrently to different storage domain
            - Verify all disks moved successfully
        Expected Results:
            - Move should succeed
        """
        self.basic_flow()


@pytest.mark.usefixtures(
    start_vm.__name__,
    init_vm_executor.__name__,
)
class BaseTestCase21907(BaseConcurrentlyTests):
    """
    Concurrent Live migration of multiple VM disks during dd operation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '21907'

    @tier2
    @polarion("RHEVM-21907")
    def test_vm_disks_concurrent_live_migration_during_dd(self):
        """
        Actions:
            - Create a VM with 5 disks from all the disks permutations
            - Run the VM
            - Start dd operation to all the disks
            - Move all the VM disks concurrently to different storage domain
            - Verify all disks moved successfully
        Expected Results:
            - Move should succeed
        """
        for disk in self.disk_names:
            testflow.step("Start writing data to disk %s", disk)
            status, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk, vm_executor=self.vm_executor
            )
            assert status, (
                "Error while trying to write data to disk %s: %s" % (disk, out)
            )
        self.basic_flow()


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class TestCase5990(BaseTestCase):
    """
    VM in paused mode
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5990'

    @tier3
    @polarion("RHEVM3-5990")
    def test_vms_live_migration(self):
        """
        Actions:
            - Run a VM with run-once in pause mode
            - Try to move images
        Expected Results:
            - VM has running qemu process so LSM should succeed
        """
        testflow.step("Running VM %s in paused state", self.vm_name)
        ll_vms.runVmOnce(True, self.vm_name, pause=True)
        ll_vms.waitForVMState(self.vm_name, config.VM_PAUSED)
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, same_type=config.MIGRATE_SAME_TYPE
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step("Verify VM %s disks moved", self.vm_name)
        assert ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, self.storage_domain
        ), "Failed to migrate disk %s" % vm_disk


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5994(BaseTestCase):
    """
    Different VM status
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5994'


class TestCase5994_wait_for_lunch(BaseTestCase5994):

    @polarion("RHEVM3-5994")
    @tier2
    def test_lsm_during_waiting_for_launch_state(self):
        """
        Actions:
            - Try to live migrate while VM is waiting for launch
        Expected Results:
            - Live migration should fail
        """
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_WAIT_FOR_LAUNCH)
        with pytest.raises(exceptions.DiskException):
            testflow.step("Try to migrate VM %s disks", self.vm_name)
            ll_vms.migrate_vm_disks(
                vm_name=self.vm_name, timeout=TASK_TIMEOUT, wait=True,
                ensure_on=False, same_type=config.MIGRATE_SAME_TYPE
            )


class TestCase5994_powering_up(BaseTestCase5994):

    @polarion("RHEVM3-5994")
    @tier2
    def test_lsm_during_powering_up_state(self):
        """
        Actions:
            - Try to live migrate while VM is powering up
        Expected Results:
            - Migration should fail
        """
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_POWERING_UP)
        with pytest.raises(exceptions.DiskException):
            testflow.step("Try to migrate VM %s disks", self.vm_name)
            ll_vms.migrate_vm_disks(
                vm_name=self.vm_name, timeout=TASK_TIMEOUT, wait=True,
                ensure_on=False, same_type=config.MIGRATE_SAME_TYPE
            )


class TestCase5994_powering_off(BaseTestCase5994):

    @polarion("RHEVM3-5994")
    @tier2
    def test_lsm_during_powering_off_state(self):
        """
        Actions:
            - Try to live migrate while VM is powering off
        Expected Results:
            - Migration should fail
        """
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        ll_vms.shutdownVm(True, self.vm_name)
        testflow.step("Stop VM %s", self.vm_name)
        ll_vms.waitForVMState(self.vm_name, config.VM_POWER_DOWN)
        with pytest.raises(exceptions.DiskException):
            testflow.step("Try to migrate VM %s disks", self.vm_name)
            ll_vms.migrate_vm_disks(
                vm_name=self.vm_name, timeout=TASK_TIMEOUT, wait=True,
                ensure_on=False, same_type=config.MIGRATE_SAME_TYPE
            )
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)


@pytest.mark.usefixtures(
    remove_templates.__name__,
    remove_vms.__name__,
    initialize_vm_and_template_names.__name__,
    create_templates.__name__,
    create_vms_from_templates.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5993(BaseTestCase):
    """
    Live migration with thin provision copy
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5993'
    vms_to_wait = list()

    @polarion("RHEVM3-5993")
    @tier2
    def test_thin_provision_copy_template_on_both_domains(self):
        """
        Template is copied to both domains:
        - Create a VM from template and run the VM
        - Move VM to target domain
        template is copied on only one domain:
        - Create VM from template and run the VM
        - Move the VM to second domain
        """
        testflow.step("Migrate VM %s", self.vm_names[1])
        ll_vms.migrate_vm_disks(
            self.vm_names[1], LIVE_MIGRATION_TIMEOUT,
            ensure_on=config.LIVE_MOVE, target_domain=self.second_domain
        )
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_names[1]], live_operation=config.LIVE_MOVE
        )

        testflow.step("Migrate VM %s", self.vm_names[0])
        with pytest.raises(exceptions.DiskException):
            ll_vms.migrate_vm_disks(
                self.vm_names[0], LIVE_MIGRATION_TIMEOUT,
                ensure_on=config.LIVE_MOVE, same_type=config.MIGRATE_SAME_TYPE
            )


@pytest.mark.usefixtures(
    create_snapshot.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5992(BaseTestCase):
    """
    Snapshots and move VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5992'

    @polarion("RHEVM3-5992")
    @tier3
    def test_snapshot(self):
        """
        Tests live migrating VM containing snapshot
        - VM with snapshots
        - Run the VM
        - Migrate the VM to second domain
        """
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, ensure_on=config.LIVE_MOVE, wait=config.LIVE_MOVE,
            same_type=config.MIGRATE_SAME_TYPE
        )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_second_vm.__name__,
    add_disk.__name__,
    attach_disk_to_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5991(BaseTestCase):
    """
    Live migration with shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # Gluster doesn't support shareable disks
    __test__ = (
        config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    polarion_test_case = '5991'
    shareable = True

    @polarion("RHEVM3-5991")
    @tier2
    def test_lsm_with_shared_disk(self):
        """
        Create and run several VM's with the same shared disk
        - Try to move one of the VM's images
        """
        self.check_if_live_move([self.vm_name, self.vm_name_2])
        target_sd = ll_disks.get_other_storage_domain(
            self.new_disk_name, self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE,
            ignore_type=[config.STORAGE_TYPE_GLUSTER]
        )
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.new_disk_name, target_sd
        )
        if config.LIVE_MOVE:
            with pytest.raises(exceptions.DiskException):
                ll_vms.migrate_vm_disk(
                    self.vm_name, self.new_disk_name, target_sd
                )
        else:
            ll_vms.migrate_vm_disk(
                self.vm_name, self.new_disk_name, target_sd
            )


@pytest.mark.usefixtures(
    start_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5989(BaseTestCase):
    """
    Suspended VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5989'

    def _suspended_vm_and_wait_for_state(self, state):
        """
        Suspending VM and perform LSM after VM is in desired state
        """
        testflow.step("Suspend VM %s", self.vm_name)
        assert ll_vms.suspendVm(True, self.vm_name, wait=False), (
            "Failed to suspend VM %s" % self.vm_name
        )
        assert ll_vms.waitForVMState(self.vm_name, state), (
            "VM %s failed to reach state %s" % (self.vm_name, state)
        )
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, LIVE_MIGRATION_TIMEOUT, wait=config.LIVE_MOVE,
            ensure_on=False, same_type=config.MIGRATE_SAME_TYPE
        )

    @polarion("RHEVM3-5989")
    @tier3
    def test_lsm_while_suspended_state(self):
        """
        2) Suspended state
            - create and run a VM
            - suspend the VM
            - Try to migrate the VM's images once the VM is suspended
        * We should not be able to migrate images
        """
        with pytest.raises(exceptions.DiskException):
            self._suspended_vm_and_wait_for_state(config.VM_SUSPENDED)
        assert ll_vms.waitForVMState(self.vm_name, config.VM_SUSPENDED), (
            "VM %s not is %s state" % (self.vm_name, config.VM_SUSPENDED)
        )


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5988(AllPermutationsDisks):
    """
    Create live snapshot during live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5988'
    snap_created = None

    def _prepare_snapshots(self, vm_name, expected_status=True):
        """
        Creates one snapshot on the VM vm_name
        """
        snapshot_description = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
        )

        testflow.step("Creating new snapshot for VM %s", vm_name)
        status = ll_vms.addSnapshot(
            expected_status, vm_name, snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
        return status


class TestCase5988_before_snapshot(BaseTestCase5988):

    @polarion("RHEVM3-5988")
    @tier3
    def test_lsm_before_snapshot(self):
        """
        1) Move -> create snapshot
            - Create and run a VM
            - Move VM's
            - Try to create a live snapshot
        * We should succeed to create a live snapshot
        """
        testflow.step("Migrate VM %s disks", self.vm_name)
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_names[0], self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.migrate_vm_disks(
            self.vm_name, LIVE_MIGRATION_TIMEOUT, wait=config.LIVE_MOVE,
            ensure_on=config.LIVE_MOVE, same_type=config.MIGRATE_SAME_TYPE,
            target_domain=target_sd
        )
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        self.verify_lsm(source_sd=self.storage_domain, target_sd=target_sd)
        assert self._prepare_snapshots(self.vm_name)


class TestCase5988_after_snapshot(BaseTestCase5988):

    @polarion("RHEVM3-5988")
    @tier3
    def test_lsm_after_snapshot(self):
        """
        2) Create snapshot -> move
            - Create and run a VM
            - Create a live snapshot
            - Move the VM's images
        * We should succeed to move the VM
        """
        assert self._prepare_snapshots(self.vm_name)
        testflow.step("Migrate VM %s disks", self.vm_name)
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_names[0], self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.migrate_vm_disks(
            self.vm_name, LIVE_MIGRATION_TIMEOUT,
            ensure_on=config.LIVE_MOVE, same_type=config.MIGRATE_SAME_TYPE,
            target_domain=target_sd
        )
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        self.verify_lsm(source_sd=self.storage_domain, target_sd=target_sd)


class TestCase5988_while_snapshot(BaseTestCase5988):

    @polarion("RHEVM3-5988")
    @tier3
    def test_lsm_while_snapshot(self):
        """
        3) Move + create snapshots
            - Create and run a VM
            - Try to create a live snapshot + move
        * We should block move+create live snapshot in backend.
        """
        self.check_if_live_move([self.vm_name])
        for disk in config.DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            testflow.step(
                "Migrate VM %s disk %s to storage domain %s",
                self.vm_name, disk, target_sd
            )
            ll_vms.migrate_vm_disk(
                self.vm_name, disk, target_sd, timeout=LIVE_MIGRATION_TIMEOUT,
                wait=False
            )
            ll_disks.wait_for_disks_status([disk], status=config.DISK_LOCKED)
            assert self._prepare_snapshots(self.vm_name, expected_status=False)
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            storage_helpers.wait_for_disks_and_snapshots(
                [self.vm_name], live_operation=config.LIVE_MOVE
            )
            assert ll_vms.verify_vm_disk_moved(
                vm_name=self.vm_name, disk_name=disk,
                source_sd=self.storage_domain, target_sd=target_sd
            ), "Failed to migrate VM %s disk %s" % (self.vm_name, disk)


@pytest.mark.usefixtures(
    delete_disks.__name__,
    add_disk.__name__,
    attach_disk_to_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5986(BaseTestCase):
    """
    Time out
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """

    __test__ = False
    polarion_test_case = '5986'
    large_disk = True
    wipe_after_delete = True

    @polarion("RHEVM3-5986")
    @tier2
    def test_vms_live_migration(self):
        """
        Actions:
            - Create a VM with large preallocated+wipe after
              delete disk
            - Run VM
            - Move VM's images to second domain
        Expected Results:
            - Move should failed, rollback should occur
        """
        self.check_if_live_move([self.vm_name])
        target_sd = ll_disks.get_other_storage_domain(
            self.new_disk_name, self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.new_disk_name, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.new_disk_name, target_sd,
            LIVE_MIGRATE_LARGE_SIZE, wait=True
        )


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
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
        testflow.step(
            "Move VM %s disk %s to storage domain %s",
            self.vm_name, self.disk_to_move, target_sd
        )
        ll_vms.move_vm_disk(vm_name, self.disk_to_move, target_sd)
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_to_move, vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        self.check_if_live_move([self.vm_name])
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.disk_to_move, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.disk_to_move, target_sd, LIVE_MIGRATION_TIMEOUT
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        if config.LIVE_MOVE:
            testflow.step("Stop VM %s", self.vm_name)
            ll_vms.stop_vms_safely([self.vm_name])

    @polarion("RHEVM3-5995")
    @tier2
    def test_lsm_with_image_on_target(self):
        """
        Move disk images to a domain that already has one of the images on it
        """
        for disk in config.DISK_NAMES[self.storage]:
            self._perform_action(self.vm_name, disk)


@pytest.mark.usefixtures(
    delete_disks.__name__,
    add_disk.__name__,
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5996(BaseTestCase):
    """
    Hot plug disk
    1) Inactive disk
    - Create and run a VM
    - Hot plug a floating disk and keep it inactive
    - Move the disk images to a different domain
    2) Active disk
    - Create and run a VM
    - Hot plug a disk and activate it
    - Move the images to a different domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5996'

    def _test_plugged_disk(self, vm_name, activate=True):
        """
        Performs migration with hotplugged disk
        """
        self.check_if_live_move([self.vm_name])
        testflow.step(
            "Attaching disk %s to VM %s", self.new_disk_name, vm_name
        )
        assert ll_disks.attachDisk(
            True, self.new_disk_name, vm_name, active=activate
        ), "Failed to attach disk %s to VM %s" % (self.new_disk_name, vm_name)

        inactive_disk = ll_vms.is_active_disk(
            vm_name, self.new_disk_name, 'alias'
        )
        if activate and not inactive_disk:
            logger.warning(
                "Disk %s in vm %s is not active after attaching",
                self.new_disk_name, vm_name
            )
            testflow.step("Activate disk %s", self.new_disk_name)
            assert ll_vms.activateVmDisk(True, vm_name, self.new_disk_name)

        elif not activate and inactive_disk:
            logger.warning(
                "Disk %s in vm %s is active after attaching",
                self.new_disk_name, vm_name
            )
            testflow.step("Deactivate disk %s", self.new_disk_name)
            assert ll_vms.deactivateVmDisk(True, vm_name, self.new_disk_name)
        logger.info(
            "%s disks active: %s %s", self.new_disk_name,
            inactive_disk, type(inactive_disk)
        )
        ll_vms.waitForVmsDisks(vm_name)
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            vm_name, LIVE_MIGRATION_TIMEOUT, wait=config.LIVE_MOVE,
            ensure_on=config.LIVE_MOVE, same_type=config.MIGRATE_SAME_TYPE
        )


class TestCase5996_inactive_disk(BaseTestCase5996):

    @polarion("RHEVM3-5996")
    @tier3
    def test_inactive_disk(self):
        """
        Tests storage live migration with one disk in inactive status
        """
        self._test_plugged_disk(self.vm_name, False)


class TestCase5996_active_disk(BaseTestCase5996):

    @polarion("RHEVM3-5996")
    @tier3
    def test_active_disk(self):
        """
        Tests storage live migration with floating disk in active status
        """
        self._test_plugged_disk(self.vm_name)


@pytest.mark.usefixtures(
    delete_disks.__name__,
    add_disk.__name__,
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase6003(BaseTestCase):
    """
    Attach disk during migration

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6003'

    def migrate_and_attach_disk(self, active=True):
        """
        Attach disk to a VM during live storage migration

        Args:
            active (bool): Specifies whether disk should be activated after
            being attached to VM
        """
        self.check_if_live_move([self.vm_name])
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, timeout=LIVE_MIGRATION_TIMEOUT, wait=False,
            ensure_on=config.LIVE_MOVE, same_type=config.MIGRATE_SAME_TYPE
        )
        if config.LIVE_MOVE:
            logger.info(
                "Wait until the migration start creating '%s'",
                config.LIVE_SNAPSHOT_DESCRIPTION
            )
            assert ll_vms.wait_for_snapshot_creation(
                vm_name=self.vm_name,
                snapshot_description=config.LIVE_SNAPSHOT_DESCRIPTION
            ), "Snapshot %s was not found" % config.LIVE_SNAPSHOT_DESCRIPTION
        else:
            disk_objecs = ll_vms.getObjDisks(self.vm_name, get_href=False)
            vm_disks_names = [disk.get_name() for disk in disk_objecs]
            ll_disks.wait_for_disks_status(
                vm_disks_names, status=config.DISK_LOCKED
            )
        testflow.step(
            "Attach disk %s to VM %s", self.new_disk_name, self.vm_name
        )
        should_succeed = not config.LIVE_MOVE
        assert ll_disks.attachDisk(
            positive=should_succeed, alias=self.new_disk_name,
            vm_name=self.vm_name, active=active
        ), "Succeeded to attach disk during migration"


class TestCase6003_active_disk(BaseTestCase6003):

    @polarion("RHEVM3-6003")
    @tier3
    def test_attach_active_disk_during_lsm(self):
        """
        Migrate VM's images -> try to attach a disk during migration
        * we should fail to attach disk
        """
        self.migrate_and_attach_disk()


class TestCase6003_inactive_disk(BaseTestCase6003):

    @polarion("RHEVM3-5980")
    @tier3
    def test_attach_inactive_disk_during_lsm(self):
        """
        Actions:
            - Create a VM with 1 disk
            - Run the VM
            - Live migrate the disk
            - Try to attach a floating disk (attach as deactivated)
        Expected Results:
            - We should not be able to attach the disk to a VM which is in
            the middle of a LSM
        """
        self.migrate_and_attach_disk(active=False)


@pytest.mark.usefixtures(
    initialize_domain_to_deactivate.__name__,
    deactivate_domain.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase6001(BaseTestCase):
    """
    LSM to domain in maintenance
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '6001'

    @polarion("RHEVM3-6001")
    @tier2
    def test_lsm_to_maintenance_domain(self):
        """
        Try to migrate to a domain in maintenance
        * we should fail to attach disk
        """
        self.check_if_live_move([self.vm_name])
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.vm_disk.get_alias(), self.target_sd
        )
        with pytest.raises(exceptions.DiskException):
            ll_vms.migrate_vm_disk(
                self.vm_name, self.vm_disk.get_alias(), self.target_sd,
                LIVE_MIGRATION_TIMEOUT, True
            )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_disks_for_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5972(BaseTestCase):
    """
    Live migrate VM with multiple disks on multiple domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5972'
    disk_count = 3

    @polarion("RHEVM3-5972")
    @tier2
    def test_live_migration_with_multiple_disks(self):
        """
        Actions:
            - 1 VM with disks on 3 of the 3 domains
            - Live migrate the VM to the 3rd domain
        Expected Results:
            - Move should succeed
        """
        self.check_if_live_move([self.vm_name])
        for disk in self.disk_names[:-1]:
            testflow.step(
                "Migrate VM %s disk %s to storage domain %s",
                self.vm_name, disk, self.storage_domains[2]
            )
            ll_vms.migrate_vm_disk(
                self.vm_name, disk, self.storage_domains[2]
            )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    add_disk.__name__,
    attach_disk_to_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5970(BaseTestCase):
    """
    Wipe after delete
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([config.STORAGE_TYPE_ISCSI])
    polarion_test_case = '5970'
    regex = config.REGEX_DD_WIPE_AFTER_DELETE
    wipe_after_delete = True

    @polarion("RHEVM3-5970")
    @tier3
    def test_live_migration_wipe_after_delete(self):
        """
        Actions:
            - Create a VM with wipe after delete disk
            - Run the VM
            - Migrate the disk
        Expected Results:
            - Move should succeed
            - Make sure that we actually post zero when removing the source
              disk and snapshot
        """
        target_sd = ll_disks.get_other_storage_domain(
            self.new_disk_name, self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        self.check_if_live_move([self.vm_name])

        if config.LIVE_MOVE:
            host = ll_hosts.get_spm_host(config.HOSTS)
            self.host_ip = ll_hosts.get_host_ip(host)
            disk_obj = ll_disks.getVmDisk(self.vm_name, self.new_disk_name)
            self.regex = self.regex % disk_obj.get_image_id()

            def f(q):
                q.put(
                    watch_logs(
                        files_to_watch=config.VDSM_LOG, regex=self.regex,
                        time_out=LIVE_MIGRATION_TIMEOUT,
                        ip_for_files=self.host_ip, username=config.HOSTS_USER,
                        password=config.HOSTS_PW
                    )
                )

            q = Queue()
            p = Process(target=f, args=(q,))
            p.start()
            sleep(5)
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.new_disk_name, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.new_disk_name, target_sd, wait=False
        )
        if config.LIVE_MOVE:
            p.join()
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        assert ll_vms.verify_vm_disk_moved(
            self.vm_name, self.new_disk_name, self.storage_domain, target_sd
        ),  "Succeded to move disk %s" % self.new_disk_name
        if config.LIVE_MOVE:
            exception_code, output = q.get()
            assert exception_code, "Couldn't find regex %s, output: %s" % (
                self.regex, output
            )


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class TestCase5968(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5968'

    @polarion("RHEVM3-5968")
    @tier2
    def test_live_migration_auto_shrink(self):
        """
        Actions:
            - 2 data storage domains
            - Create -> run the VM -> move the VM
            - Shut down the VM once the move is finished
            - Delete the Live migration snapshot

        Expected Results:
            - The image actual size should not exceed the disks
              virtual size once we delete the snapshot
        """
        for disk in config.DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            self.check_if_live_move([self.vm_name])

            testflow.step(
                "Migrate VM %s disk %s to storage domain %s",
                self.vm_name, disk, target_sd
            )
            ll_vms.migrate_vm_disk(self.vm_name, disk, target_sd)
            if config.LIVE_MOVE:
                testflow.step("Stop VM %s", self.vm_name)
                assert ll_vms.stop_vms_safely([self.vm_name])
            testflow.step("Remove VM %s snapshots", self.vm_name)
            ll_vms.remove_all_vm_lsm_snapshots(self.vm_name)
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
            disk_obj = ll_disks.getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            logger.info(
                "Actual size after migrate disk %s is: %s",
                disk, actual_size
            )
            logger.info(
                "Virtual size after migrate disk %s is: %s",
                disk, virtual_size
            )
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            assert actual_size <= virtual_size, (
                "Actual size exceeded to virtual size"
            )


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class TestCase5967(AllPermutationsDisks):
    """
    Auto-Shrink - Live Migration failure
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5967'

    @polarion("RHEVM3-5967")
    @tier3
    def test_live_migration_auto_shrink(self):
        """
        Actions:
            - 2 data storage domains
            - Create -> run the VM -> move the VM
            - Stop the VM while the Live migration is in progress, causing
              a failure
            - Delete the Live migration snapshot

        Expected Results:
            - The image actual size should not exceed the disks
              virtual size once we delete the snapshot
            - Make sure that we can delete the snapshot and run the VM
        """
        for disk in config.DISK_NAMES[self.storage]:
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            self.check_if_live_move([self.vm_name])
            testflow.step(
                "Migrate VM %s disk %s to storage domain %s",
                self.vm_name, disk, target_sd
            )
            ll_vms.migrate_vm_disk(
                self.vm_name, disk, target_sd, wait=False
            )
            ll_disks.wait_for_disks_status([disk], status=config.DISK_LOCKED)
            if config.LIVE_MOVE:
                testflow.step("Stop VM %s", self.vm_name)
                assert ll_vms.stop_vms_safely([self.vm_name]), (
                    "Failed to stop VM %s" % self.vm_name
                )
            storage_helpers.wait_for_disks_and_snapshots(
                [self.vm_name], live_operation=config.LIVE_MOVE
            )
            disk_obj = ll_disks.getVmDisk(self.vm_name, disk)
            actual_size = disk_obj.get_actual_size()
            virtual_size = disk_obj.get_provisioned_size()
            testflow.step(
                "Verify disk %s actual size < Virtual size after migrate",
                disk
            )
            logger.info(
                "Actual size after migrate disk %s is: %s",
                disk, actual_size
            )
            logger.info(
                "Virtual size after migrate disk %s is: %s",
                disk, virtual_size
            )
            if self.storage in config.BLOCK_TYPES:
                actual_size -= EXTENT_METADATA_SIZE
            assert actual_size <= virtual_size, (
                "Actual size exceeded virtual size"
            )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    start_vm.__name__,
    add_disk.__name__,
    attach_disk_to_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5979(BaseTestCase):
    """
    Offline migration for disk attached to running VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5979'
    expected_lsm_snap_count = 0
    active = False

    @polarion("RHEVM3-5979")
    @tier3
    def test_offline_migration(self):
        """
        Actions:
            - Create a VM with 1 disk and start the VM
            - Attach a disk but remove the "active" tag so that the disk
              will be inactive
            - Move the inactive disk
        Expected Results:
            - We should succeed to migrate the disk offline
              (as in not with LSM command)
        """
        target_sd = ll_disks.get_other_storage_domain(
            self.new_disk_name, self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.new_disk_name, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.new_disk_name, target_sd
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

        snapshots = ll_vms.get_vm_snapshots(self.vm_name)
        LSM_snapshots = [
            s for s in snapshots if (
                s.get_description() == config.LIVE_SNAPSHOT_DESCRIPTION
            )
            ]
        testflow.step("Verify that the migration was not live migration")
        assert len(LSM_snapshots) == self.expected_lsm_snap_count


@pytest.mark.usefixtures(
    delete_disks.__name__,
    add_disk.__name__,
    attach_disk_to_vm.__name__,
    start_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5976(BaseTestCase):
    """
    Deactivate VM disk during live migrate
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5976'

    @polarion("RHEVM3-5976")
    @tier3
    def test_deactivate_disk_during_lsm(self):
        """
        Actions:
            - Create a VM with two disks and run it
            - Start a LSM on the VM disk
            - Deactivate the non-boot disk.
        Expected Results:
            - We should block with canDoAction
        """
        disk_id = ll_disks.get_disk_obj(self.new_disk_name).get_id()

        target_sd = ll_disks.get_other_storage_domain(
            disk_id, self.vm_name, force_type=config.MIGRATE_SAME_TYPE,
            key='id'
        )
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, self.new_disk_name, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.new_disk_name, target_sd=target_sd, wait=False
        )
        ll_disks.wait_for_disks_status(
            disk_id, key='id', status=config.DISK_LOCKED
        )
        testflow.step(
            "Try to deactivate disk %s while preforming migration",
            self.new_disk_name
        )
        assert ll_vms.deactivateVmDisk(
            False, self.vm_name, self.new_disk_name
        ), "Succeeded to deactivate disk %s during migration" % (
            self.new_disk_name
        )


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5977(BaseTestCase):
    """
    Migrate a VM between hosts + LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5977'

    def _migrate_vm_during_lsm_ops(self, wait):
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=wait, same_type=config.MIGRATE_SAME_TYPE
        )
        if wait:
            storage_helpers.wait_for_disks_and_snapshots(
                [self.vm_name], live_operation=config.LIVE_MOVE
            )
        testflow.step("Try to migrate VM %s to another host", self.vm_name)
        status = ll_vms.migrateVm(True, self.vm_name, wait=False)
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_jobs.wait_for_jobs([config.JOB_MIGRATE_VM])
        return status


class TestCase5977_vm_migration(BaseTestCase5977):
    """
    LSM during VM migration
    """
    @polarion("RHEVM3-5977")
    @tier3
    def test_LSM_during_vm_migration(self):
        """
        Actions:
            - Create and run a VM
            - Migrate the VM between the hosts
            - Try to LSM the VM disk during the VM migration
        Expected Results:
            - We should be stopped by CanDoAction
        """
        disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        target_sd = ll_disks.get_other_storage_domain(
            disk_name, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        hsm_host = ll_hosts.get_hsm_host(config.HOSTS)
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=hsm_host
        )
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        testflow.step(
            "Migrate VM %s to another host and try to migrate VM disk",
            self.vm_name
        )
        ll_vms.migrateVm(
            positive=True, vm=self.vm_name, host=spm_host, wait=False
        )
        with pytest.raises(exceptions.DiskException):
            ll_vms.migrate_vm_disk(
                self.vm_name, disk_name, target_sd, wait=False
            )
        ll_jobs.wait_for_jobs([config.JOB_MIGRATE_VM])


class TestCase5977_snapshot_creation(BaseTestCase5977):
    """
    Create snapshot during VM migration
    """

    @polarion("RHEVM3-5977")
    @tier3
    def test_migrate_vm_during_snap_creation_of_LSM(self):
        """
        Actions:
            - Create and run a VM
            - Start a LSM for the VM disk
            - Try to migrate the VM between hosts during the create snapshot
              step
        Expected Results:
            - We should be stopped by CanDoAction
        """
        self.vms_to_wait.append(self.vm_name)
        status = self._migrate_vm_during_lsm_ops(wait=False)
        assert not status, (
            "Succeeded to migrate vm during migration snapshot creation"
        )


class TestCase5977_after_lsm(BaseTestCase5977):
    """
    VM migration after LSM finishes
    """

    @polarion("RHEVM3-5977")
    @tier3
    def test_migrate_vm_after_LSM(self):
        """
        Actions:
            - Create a VM and run it
            - Start a LSM
            - When the LSM is finishes
            - Try to migrate the VM
        Expected Results:
            - We should succeed
        """
        self.vms_to_wait.append(self.vm_name)
        status = self._migrate_vm_during_lsm_ops(wait=True)
        assert status, "Succeeded to migrate vm after storage migration"


@pytest.mark.usefixtures(
    delete_disks.__name__,
    initialize_storage_domains.__name__,
    add_two_storage_domains.__name__,
    initialize_params.__name__,
    create_vm.__name__,
    add_disk.__name__,
    wait_for_disks_and_snapshots.__name__,
    poweroff_vm.__name__,
)
class BaseTestCase5975(StorageTest):
    """
    Extend storage domain while LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5975'
    installation = False

    def generate_sd_dict(self, index):
        return {
            'storage_type': BaseTestCase.storage,
            'host': config.HOSTS[0],
            'lun': config.ISCSI_DOMAINS_KWARGS[index]['lun'],
            'lun_address': config.ISCSI_DOMAINS_KWARGS[index]['lun_address'],
            'lun_target': config.ISCSI_DOMAINS_KWARGS[index]['lun_target'],
            'lun_port': config.LUN_PORT,
            'override_luns': True
        }

    def basic_flow(self):
        disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        if config.LIVE_MOVE:
            testflow.step("Start VM %s", self.vm_name)
            assert ll_vms.startVm(
                positive=True, vm=self.vm_name, wait_for_status=config.VM_UP
            )
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, disk_name, self.sd_target
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, disk_name, self.sd_target, wait=False
        )


class TestCase5975_src_domain(BaseTestCase5975):
    """
    Extend source domain during LSM
    """

    @polarion("RHEVM3-5975")
    @tier2
    def test_extend_src_domain_during_LSM(self):
        """
        Actions:
            - Create and run a VM
            - Live migrate the VM disk to the second iSCSI domain
            - While LSM is running, try to extend the SRC storage domain

        Expected Results:
            - LSM should succeed
            - Extend storage domain should succeed
        """
        self.basic_flow()
        testflow.step("Extend storage domain %s", self.sd_src)
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        assert ll_sd.extendStorageDomain(
            positive=True, storagedomain=self.sd_src,
            **self.generate_sd_dict(2)
        ), "Failed to extend source storage domain '%s'" % self.sd_src
        assert ll_vms.wait_for_snapshot_gone(
            vm_name=self.vm_name, snapshot=config.LIVE_SNAPSHOT_DESCRIPTION
        ), "Failed to remove snapshot %s" % config.LIVE_SNAPSHOT_DESCRIPTION


class TestCase5975_dest_domain(BaseTestCase5975):
    """
    Extend target domain during LSM
    """

    @polarion("RHEVM3-5975")
    @tier2
    def test_extend_dest_domain_during_LSM(self):
        """
        Actions:
            - create and run a VM
            - Live migrate the VM disk to the second iSCSI domain
            - While LSM is running, try to extend the DST storage domain

        Expected Results:
            - LSM should succeed
            - Extend storage domain should succeed
        """
        self.basic_flow()
        testflow.step("Extend storage domain %s", self.sd_target)
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        assert ll_sd.extendStorageDomain(
            positive=True, storagedomain=self.sd_target,
            **self.generate_sd_dict(2)
        ), "Failed to extend target storage domain '%s'" % self.sd_target
        assert ll_vms.wait_for_snapshot_gone(
            vm_name=self.vm_name, snapshot=config.LIVE_SNAPSHOT_DESCRIPTION
        ), "Failed to remove snapshot %s" % config.LIVE_SNAPSHOT_DESCRIPTION


@pytest.mark.usefixtures(
    initialize_variables_block_domain.__name__,
    unblock_connectivity_storage_domain_teardown.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase6000(BaseTestCase):
    """
    Live migrate - storage connectivity issues
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    # Bugzilla history:
    # 1106593: Failed recovering from crash or initializing after blocking
    # connection from host to target storage domain during LSM (marked as
    # Won't Fix)

    polarion_test_case = '6000'
    storage_domain_ip = None

    def _migrate_vm_disk_and_block_connection(
        self, disk, source, username, password, target, target_ip
    ):
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, disk, target
        )
        ll_vms.migrate_vm_disk(self.vm_name, disk, target, wait=False)
        testflow.step("Block connection between %s to %s", source, target_ip)
        status = storage_helpers.blockOutgoingConnection(
            source, username, password, target_ip
        )
        assert status, "Failed to block connection"

    @polarion("RHEVM3-6000")
    @tier4
    def test_LSM_block_from_host_to_target(self):
        """
        Actions:
            - Live migrate a VM
            - Block connectivity to target domain from host using iptables
        Expected Results:
            - We should fail migrate and roll back
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        status, target_sd_ip = ll_sd.getDomainAddress(True, self.target_sd)
        assert status
        self.storage_domain_ip = target_sd_ip['address']
        self._migrate_vm_disk_and_block_connection(
            vm_disk, self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.target_sd, self.storage_domain_ip
        )
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd, self.target_sd
        ),  "Succeded to move disk %s" % vm_disk


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
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
    @tier4
    def test_restart_spm_during_lsm(self):
        """
        Actions:
            - Run VM's on host
            - Start a live migrate of VM
            - Restart vdsm
        Expected Results:
            - Live migrate should fail
        """
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        spm_host_ip = ll_hosts.get_host_ip(ll_hosts.get_spm_host(config.HOSTS))
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        if config.LIVE_MOVE:
            testflow.step("Start VM %s", self.vm_name)
            assert ll_vms.startVm(
                positive=True, vm=self.vm_name, placement_host=spm_host,
                wait_for_status=config.VM_UP
            )
        testflow.step("Migrate VM %s", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE,
            ensure_on=config.LIVE_MOVE, target_domain=self.target_sd
        )
        testflow.step("Restart vdsmd on host %s", spm_host)
        assert restartVdsmd(spm_host_ip, config.HOSTS_PW), (
            "Failed to restart VDSM on host %s" % spm_host
        )
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), (
            'SPM was not elected on data-center %s' % config.DATA_CENTER_NAME
        )
        ll_hosts.wait_for_hosts_states(positive=True, names=spm_host)
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, self.storage_domain, self.target_sd
        ),  "Succeeded to move disk %s" % vm_disk


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5999(BaseTestCase):
    """
    Live migrate during host restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    # Bugzilla history:
    # 1210771: After rebooting the spm job "Handling non responsive Host" is
    # stuck in STARTED (even if the host is back up)
    polarion_test_case = '5999'

    def reboot_host_during_lsm(self, spm=True):
        """
        Actions:
            - Run HA VM on host
            - Start a live migrate of VM
            - Reboot the host (spm/hsm)
        Expected Results:
            - We should fail migration
        """
        host = ll_hosts.get_spm_host(config.HOSTS) if spm else (
            ll_hosts.get_hsm_host(config.HOSTS)
        )
        host_ip = ll_hosts.get_host_ip(host)
        testflow.step("Update VM %s to be HA", self.vm_name)
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true',
            placement_host=host
        )
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        testflow.step("Migrate VM %s", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, ensure_on=config.LIVE_MOVE,
            same_type=config.MIGRATE_SAME_TYPE
        )
        testflow.step("Rebooting Host %s", host)
        executor = rhevm_helpers.get_host_executor(host_ip, config.HOSTS_PW)
        rc, out, error = executor.run_cmd(cmd=shlex.split(config.REBOOT_CMD))

        assert rc, "Failed to reboot Host %s, error: %s, out: %s" % (
            host, error, out
        )
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), (
            'SPM was not elected on data-center %s' % config.DATA_CENTER_NAME
        )
        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)
        logger.info("Waiting for host %s to come back up", host)
        ll_hosts.wait_for_hosts_states(
            True, host, timeout=config.HOST_STATE_TIMEOUT
        )
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, source_sd
        ), (
            "Succeeded to migrate VM %s disk %s during %s host reboot" % (
                self.vm_name, vm_disk, "SPM" if spm else "HSM"
            )
        )


class TestCase5999_spm(BaseTestCase5999):
    """
    Reboot SPM duting LSM
    """

    @polarion("RHEVM3-5999")
    @tier4
    def test_reboot_spm_during_lsm(self):
        """
        Actions:
            - Run HA VM on spm host
            - Start a live migrate of VM
            - Reboot the host (spm)
        Expected Results:
            - We should fail migration
        """
        self.reboot_host_during_lsm()


class TestCase5999_hsm(BaseTestCase5999):
    """
    Reboot HSM duting LSM
    """

    @polarion("RHEVM3-5999")
    @tier4
    def test_reboot_hsm_during_lsm(self):
        """
        Actions:
            - Run HA VM on hsm host
            - Start a live migrate of VM
            - Reboot the host (hsm)
        Expected Results:
            - We should fail migration
        """
        self.reboot_host_during_lsm(spm=False)


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5997(BaseTestCase):
    """
    Kill VM's pid during live migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5997'

    def perform_action(self):
        testflow.step("Start VM %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        testflow.step("Migrate VM %s disks", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        testflow.step("Killing VM's %s pid", self.vm_name)
        vm_host = ll_vms.get_vm_host(vm_name=self.vm_name)
        assert vm_host, "Failed to get VM: %s hoster" % self.vm_name
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=vm_host
        )
        assert ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=self.vm_name
        )

        ll_disks.wait_for_disks_status(vm_disk, timeout=DISK_TIMEOUT)

        status = ll_vms.verify_vm_disk_moved(self.vm_name, vm_disk, source_sd)
        assert not status, "Succeeded to migrate vm disk %s" % vm_disk


class TestCase5997_ha_vm(BaseTestCase5997):
    """
    Kill HA VM PID during LSM
    """

    @polarion("RHEVM3-5997")
    @tier4
    def test_kill_ha_vm_pid_during_lsm(self):
        """
        Actions:
            - Run HA VM on host
            - Start a live migrate of VM
            - Kill -9 VM's pid
        Expected Results:
            - We should fail migration
        """
        testflow.step("Update VM %s to be HA", self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, highly_available='true')
        self.perform_action()


class TestCase5997_regular_vm(BaseTestCase5997):
    """
    Kill VM PID during LSM
    """

    @polarion("RHEVM3-5997")
    @tier4
    def test_kill_regular_vm_pid_during_lsm(self):
        """
        Actions:
            - Run VM on host
            - Start a live migrate of VM
            - Kill -9 VM's pid
        Expected Results:
            - We should fail migration
        """
        self.perform_action()


@pytest.mark.usefixtures(
    wait_for_disks_and_snapshots.__name__
)
class TestCase5985(BaseTestCase):
    """
    No space left
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
    @tier2
    def test_no_space_disk_during_lsm(self):
        """
        Actions:
            - Start a live migration
            - While migration is running, create a large preallocated disk
        Expected Results:
            - Migration or create disk should fail nicely.
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        self.check_if_live_move([self.vm_name])
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, self.vm_name
        )
        target_sd = ll_disks.get_other_storage_domain(
            vm_disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        sd_size = ll_sd.get_free_space(target_sd)
        testflow.step(
            "Migrate VM %s disk %s to storage domain %s",
            self.vm_name, vm_disk, target_sd
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, vm_disk, target_sd, wait=False
        )
        testflow.step("Add disk %s", self.disk_name)
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
        ), "Succeeded to migrate vm disk %s" % vm_disk


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_disks_for_vm.__name__,
    deactivate_domain.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5971(BaseTestCase):
    """
    Multiple domains - only one domain unreachable
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5971'
    disk_count = 3
    inactive_disk_index = 2
    sd_to_deactivate_index = 2

    @polarion("RHEVM3-5971")
    @tier2
    def test_lsm_with_multiple_disks_one_sd_in_maintenance(self):
        """
        Actions:
            - 1 VM with disks on 3 of the 3 domains
            - Put the domain with the inactive disk in maintenance
            - Start live migrate
        Expected Results:
            - We should fail migrate
        """
        self.check_if_live_move([self.vm_name])
        for index, disk in enumerate(self.disk_names):
            src_sd = ll_disks.get_disk_storage_domain_name(disk, self.vm_name)
            target_sd = ll_disks.get_other_storage_domain(
                disk, self.vm_name, force_type=config.MIGRATE_SAME_TYPE
            )
            testflow.step(
                "%sMigrate VM %s disk %s to storage domain %s",
                "Try to " if index == 2 else "",
                self.vm_name, disk, self.storage_domains[2]
            )
            if index == 2:
                with pytest.raises(exceptions.DiskException):
                    ll_vms.migrate_vm_disk(self.vm_name, disk, target_sd)

                assert not ll_vms.verify_vm_disk_moved(
                    self.vm_name, disk, src_sd
                ), "Succeeded to migrate disk %s" % disk
            else:
                ll_vms.migrate_vm_disk(
                    self.vm_name, disk, target_sd=target_sd
                )
                assert ll_vms.verify_vm_disk_moved(
                    self.vm_name, disk, src_sd
                ), "Failed to migrate disk %s" % disk


@pytest.mark.usefixtures(
    restart_vdsmd.__name__,
    wait_for_disks_and_snapshots.__name__,
)
class BaseTestCase5966(BaseTestCase):
    """
    Kill VDSM during LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5966'
    restart_vdsmd_host_ip = None
    host_resource = None
    source_sd = None
    vm_disk = None

    def basic_flow(self, wait=False):
        self.vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        self.source_sd = ll_disks.get_disk_storage_domain_name(
            self.vm_disk, self.vm_name
        )
        self.restart_vdsm_host = ll_hosts.get_spm_host(config.HOSTS)
        testflow.step("Start VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP,
            placement_host=self.restart_vdsm_host
        ), "Failed to start VM %s" % self.vm_name
        self.host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=self.restart_vdsm_host
        )
        testflow.step("Migrate VM %s", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=wait, same_type=config.MIGRATE_SAME_TYPE
        )


class TestCase5966_during_lsm(BaseTestCase5966):

    @polarion("RHEVM3-5966")
    @tier4
    def test_kill_vdsm_during_lsm(self):
        """
        Actions:
            - Run VM's on host
            - Start a live migrate of VM
            - Kill VDSM
        Expected Results:
            - LSM should fail nicely
        """
        self.basic_flow()
        testflow.step("Kill vdsmd on host %s", self.restart_vdsm_host)
        assert ll_hosts.kill_vdsmd(self.host_resource), (
            "Failed to kill vdsmd on host %s" % self.restart_vdsm_host
        )
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, self.vm_disk, self.source_sd
        ), "Failed to migrate disk %s" % self.vm_disk


class TestCase5966_during_second_lsm(BaseTestCase5966):

    @polarion("RHEVM3-5966")
    @tier4
    def test_kill_vdsm_during_second_lsm(self):
        """
        Actions:
            - Run VM's on host
            - Start a live migrate of VM
            - Once the move is finished repeat step2
            - Kill vdsm
        Expected Results:
            - LSM should fail nicely
        """
        self.basic_flow(wait=True)
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        self.source_sd = ll_disks.get_disk_storage_domain_name(
            self.vm_disk, self.vm_name
        )
        testflow.step("Migrate VM %s", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE
        )
        testflow.step("Kill vdsmd on host %s", self.restart_vdsm_host)
        assert ll_hosts.kill_vdsmd(self.host_resource), (
            "Failed to restart vdsmd"
        )
        assert not ll_vms.verify_vm_disk_moved(
            self.vm_name, self.vm_disk, self.source_sd
        ), "Failed to migrate disk %s" % self.vm_disk


@pytest.mark.usefixtures(
    initialize_variables_block_domain.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5981(AllPermutationsDisks):
    """
    Merge after a failure in LSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    # TODO: Fix this case
    __test__ = False
    polarion_test_case = '5981'

    @polarion("RHEVM3-5981")
    @tier4
    def test_merge_snapshot_live_migration_failure(self):
        """
        Actions:
            - Create a VM with OS installed
            - Run the VM on hsm
            - Start LSM and write to the VM -> fail LSM (block connection
            between the VM's host to the storage doamin)
            - Power off the VM
            - Delete the snapshot
            - Run the VM
        Expected Results:
            - LSM should fail nicely
            - We should be able to merge the snapshot
            - We should be able to run the VM
        """
        for index, disk in enumerate(config.DISK_NAMES[self.storage]):
            hsm_host = ll_hosts.get_hsm_host(config.HOSTS)
            testflow.step(
                "Update VM %s to run on host %s", self.vm_name, hsm_host
            )
            ll_vms.updateVm(True, self.vm_name, placement_host=hsm_host)
            testflow.step("Start VM %s", self.vm_name)
            ll_vms.startVm(True, self.vm_name, config.VM_UP, True)
            disk_id = ll_disks.get_disk_obj(disk).get_id()
            target_sd = ll_disks.get_other_storage_domain(
                disk=disk_id, vm_name=self.vm_name,
                force_type=config.MIGRATE_SAME_TYPE, key='id'
            )
            logger.info("Ensure disk is accessible")
            assert ll_vms.get_vm_disk_logical_name(
                self.vm_name, disk_id, key='id'
            )

            def f(q):
                q.put(
                    watch_logs(
                        files_to_watch=config.VDSM_LOG,
                        regex='syncImageData',
                        time_out=LIVE_MIGRATION_TIMEOUT,
                        ip_for_files=self.host_ip, username=config.HOSTS_USER,
                        password=config.HOSTS_PW
                    )
                )

            q = Queue()
            p = Process(target=f, args=(q,))
            p.start()
            sleep(5)
            testflow.step(
                "Live migrate VM %s disk %s to storage domain %s",
                self.vm_name, disk, target_sd
            )
            ll_vms.migrate_vm_disk(
                self.vm_name, disk, target_sd, wait=False
            )
            p.join()

            def f():
                status, _ = storage_helpers.perform_dd_to_disk(
                    self.vm_name, disk, size=int(config.DISK_SIZE * 0.9),
                    write_to_file=True
                )

            testflow.step("Start Writing to disk")
            p = Process(target=f, args=())
            p.start()
            status = storage_helpers.wait_for_dd_to_start(
                self.vm_name, timeout=DD_TIMEOUT
            )
            assert status, "dd didn't start writing to disk"
            logger.info(
                "Stop the VM while the storage migration is running",
            )
            vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
            source_sd = ll_disks.get_disk_storage_domain_name(
                vm_disk, self.vm_name
            )
            testflow.step(
                "Block connection between %s to %s",
                self.host_ip, self.storage_domain_ip
            )
            assert storage_helpers.blockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
                self.storage_domain_ip
            )

            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            testflow.step("Remove all VM %s snapshots", self.vm_name)
            ll_vms.remove_all_vm_lsm_snapshots(self.vm_name)
            testflow.step(
                "Unblock connection between %s to %s",
                self.host_ip, self.storage_domain_ip
            )
            assert storage_helpers.unblockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
                self.storage_domain_ip
            )
            assert ll_hosts.wait_for_spm(
                config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
                config.WAIT_FOR_SPM_INTERVAL
            ), "A new SPM host was not elected"
            assert not ll_vms.verify_vm_disk_moved(
                self.vm_name, disk, source_sd, target_sd
            ), "Succeeded to migrate vm disk %s" % disk
            testflow.step("Stop VM %s", self.vm_name)
            ll_vms.stop_vms_safely([self.vm_name])


@pytest.mark.usefixtures(
    create_second_vm.__name__,
    wait_for_disks_and_snapshots.__name__
)
class BaseTestCase5983(BaseTestCase):
    """
    Migrate multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = False
    polarion_test_case = '5983'
    vm_names = list()

    def _perform_action(self, host):
        """
        Place VMs on requested, power them on and then run live migration
        """
        self.vm_names = [self.vm_name, self.vm_name_2]

        for vm in self.vm_names:
            testflow.step("Run VM %s on host %s", vm, host)
            ll_vms.updateVm(True, vm, placement_host=host)
        ll_vms.start_vms(self.vm_names, 1, config.VM_UP, False)
        testflow.step("Migrate VM %s disks", self.vm_name)
        for vm in self.vm_names:
            ll_vms.migrate_vm_disks(vm, same_type=config.MIGRATE_SAME_TYPE)


class TestCase5983_spm(BaseTestCase5983):

    @polarion("RHEVM3-5983")
    @tier2
    def test_migrate_multiple_vms_on_spm(self):
        """
        Actions:
            - Create 2 VMs and run them on SPM host only
            - LSM the disks
        Expected Results:
            - We should succeed in migrating all disks
        """
        spm = ll_hosts.get_spm_host(config.HOSTS)
        self._perform_action(spm)


class TestCase5983_hsm(BaseTestCase5983):

    @polarion("RHEVM3-5983")
    @tier2
    def test_migrate_multiple_vms_on_hsm(self):
        """
        Actions:
            - Create 2 VMs and run them on HSM host only
            - LSM the disks
        Expected Results:
            - We should succeed in migrating all disks
        """
        hsm = ll_hosts.get_hsm_host(config.HOSTS)
        self._perform_action(hsm)


@pytest.mark.usefixtures(
    initialize_variables_block_domain.__name__,
    unblock_connectivity_storage_domain_teardown.__name__,
    wait_for_disks_and_snapshots.__name__
)
class TestCase5974(BaseTestCase):
    """
    LSM during pause due to EIO
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Storage_Migration
    """
    __test__ = config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([config.STORAGE_TYPE_ISCSI])
    polarion_test_case = '5974'
    block_spm_host = False

    @classmethod
    @polarion("RHEVM3-5974")
    @tier4
    def test_LSM_block_from_host_to_target(cls):
        """
        Actions:
            - Block connectivity to the storage from the HSM host
            - Start LSM
        Expected Results:
            - We should not be able to LSM a VM which is paused on EIO
        """
        testflow.step("Start VM %s on host %s", cls.vm_name, cls.host)
        assert ll_vms.startVm(
            True, cls.vm_name, config.VM_UP, placement_host=cls.host
        )
        vm_disk = ll_vms.getVmDisks(cls.vm_name)[0].get_alias()
        source_sd = ll_disks.get_disk_storage_domain_name(
            vm_disk, cls.vm_name
        )
        cls.target_sd = ll_disks.get_other_storage_domain(
            vm_disk, cls.vm_name, force_type=config.MIGRATE_SAME_TYPE
        )
        status, target_sd_ip = ll_sd.getDomainAddress(True, cls.target_sd)
        cls.storage_domain_ip = target_sd_ip.get('address')
        assert status
        testflow.step(
            "Block connection between %s to %s", cls.host_ip,
            cls.storage_domain_ip
        )
        assert storage_helpers.blockOutgoingConnection(
            cls.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            cls.storage_domain_ip
        ), "Failed to block connection from host %s to storage domain %s" % (
            cls.host_ip, cls.storage_domain_ip
        )
        testflow.step("Migrate VM %s", cls.vm_name)
        ll_vms.migrate_vm_disks(
            cls.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE,
            target_domain=cls.target_sd
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        assert not ll_vms.verify_vm_disk_moved(
            cls.vm_name, vm_disk, source_sd, target_sd=cls.target_sd
        ), "Succeeded to migrate VM disk %s" % vm_disk
