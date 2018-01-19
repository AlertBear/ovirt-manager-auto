import logging
import os
import shlex
import pytest

from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage import config
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    vms as ll_vms,
)

from rhevmtests.storage.fixtures import (
    create_vm, initialize_storage_domains, undo_snapshot, add_disk,
    create_template, attach_disk, poweroff_vm, remove_vms,
    create_fs_on_disk, create_several_snapshots,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    initialize_prepare_environment, add_disks_different_sd,
    add_two_vms_from_template,
)
logger = logging.getLogger(__name__)

LIVE_SNAPSHOT_DESC = 'test_live_snapshot'
MAX_DESC_LENGTH = 4000
SPECIAL_CHAR_DESC = '!@#$\% ^&*/\\'


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_prepare_environment.__name__,
    undo_snapshot.__name__,
)
class BasicEnvironmentSetUp(TestCase):
    """
    This class implements setup, teardowns and common functions
    """
    __test__ = False
    file_name = 'test_file'
    mount_path = '/root'
    cmd_create = 'echo "test_txt" > test_file'
    live_snapshot = None

    def _perform_snapshot_operation(self, vm_name, disks=None, wait=True):
        if not self.live_snapshot:
            if not ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
                vm_executor = storage_helpers.get_vm_executor(vm_name)
                assert storage_helpers._run_cmd_on_remote_machine(
                    vm_name, config.SYNC_CMD, vm_executor
                )
                assert ll_vms.stop_vms_safely([vm_name]), (
                    "Failed to power off vm %s" % vm_name
                )
                ll_vms.waitForVMState(vm_name, config.VM_DOWN)
        if disks:
            is_disks = "disks: %s" % disks
        else:
            is_disks = "all disks"
        testflow.step(
            "Adding new snapshot to VM %s with %s", self.vm_name, is_disks
        )
        status = ll_vms.addSnapshot(
            True, vm_name, self.snapshot_description, disks_lst=disks,
            wait=wait
        )
        assert status, (
            "Failed to create snapshot %s" % self.snapshot_description
        )
        if wait:
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
            ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    def check_file_existence_operation(self, vm_name, should_exist=True):

        ll_vms.start_vms([vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(vm_name)
        full_path = os.path.join(self.mount_path, self.file_name)
        logger.info("Checking full path %s", full_path)
        result = storage_helpers.does_file_exist(self.vm_name, full_path)
        logger.info("File %s", "exists" if result else "does not exist")

        if should_exist != result:
            return False
        return True


class TestCase18863(BasicEnvironmentSetUp):
    """
    Full flow snapshot operation:
    Create snapshot
    Add file to the VM
    Stop VM
    Preview and commit snapshot

    Expected Results:
    Snapshot should be successfully created
    Verify that a new data is written on new volumes
    Verify that the file no longer exists both after preview and after commit
    """
    __test__ = False
    polarion_test_case = '18863'

    def _test_snapshot_operation(self, vm_name):
        """
        Tests snapshot on given vm
        """
        if self.live_snapshot:
            ll_vms.start_vms([vm_name])
            ll_vms.waitForVMState(vm_name)
        live_message = "live" if self.live_snapshot else ""
        testflow.step("Creating %s snapshot on a VM %s", live_message, vm_name)
        self._perform_snapshot_operation(vm_name)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        ll_vms.start_vms([vm_name])
        ll_vms.waitForVMState(vm_name)
        testflow.step("Writing files to VM's %s disk", vm_name)
        cmd = self.cmd_create
        executor = storage_helpers.get_vm_executor(self.vm_name)
        status, out, _ = executor.run_cmd(shlex.split(cmd))
        assert not status, "Unable to write to VM %s: %s" % (vm_name, out)
        assert self.check_file_existence_operation(vm_name, True), (
            "Writing operation failed"
        )
        ll_vms.shutdownVm(True, vm_name, 'false')
        testflow.step(
            "Previewing snapshot %s on VM %s", self.snapshot_description,
            vm_name
        )
        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_description,
            ensure_vm_down=True
        )
        assert self.previewed, "Failed to preview snapshot %s" % (
            self.snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_ip=True
        )
        testflow.step("Checking that files no longer exist after preview")
        assert self.check_file_existence_operation(vm_name, False), (
            "Snapshot operation failed"
        )

        testflow.step(
            "Committing snapshot %s on VM %s", self.snapshot_description,
            vm_name
        )
        assert ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True
        ), "Failed to commit snapshot %s" % self.snapshot_description
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        testflow.step("Checking that files no longer exist after commit")
        assert self.check_file_existence_operation(vm_name, False), (
            "Snapshot operation failed"
        )

    @polarion("RHEVM-18863")
    @tier1
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running
        """
        self._test_snapshot_operation(self.vm_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_prepare_environment.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    create_fs_on_disk.__name__,
    poweroff_vm.__name__,
)
class TestCase11679(BasicEnvironmentSetUp):
    """
    Add a disk to the VMs
    Create snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = False
    full_path = None
    polarion_test_case = '11679'

    def check_file_existence_operation(
            self, should_exist=True, operation='snapshot'
    ):
        ll_vms.start_vms([self.vm_name], 1, config.VM_UP, wait_for_ip=True)
        logger.info("Checking full path %s", self.full_path)
        result = storage_helpers.does_file_exist(self.vm_name, self.full_path)
        logger.info("File %s", "exist" if result else "not exist")

        assert should_exist == result, "%s operation failed" % operation

    def _test_snapshot_operation(self, vm_name):
        """
        Tests snapshot operation on given vm
        """
        if self.live_snapshot:
            logger.info("Make sure VM %s is up", vm_name)
            if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
                ll_vms.start_vms([vm_name], config.VM_UP, wait_for_ip=True)
        testflow.step("Creating snapshot")
        self._perform_snapshot_operation(vm_name)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        if not self.live_snapshot:
            if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
                ll_vms.start_vms([vm_name], config.VM_UP, wait_for_ip=True)
        storage_helpers.create_file_on_vm(
            vm_name, self.file_name, self.mount_point
        )
        self.full_path = os.path.join(self.mount_point, self.file_name)
        self.check_file_existence_operation(True, 'writing')
        ll_vms.stop_vms_safely([vm_name])

        testflow.step(
            "Previewing snapshot %s on VM %s",
            self.snapshot_description, vm_name
        )

        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_description,
            ensure_vm_down=True)
        assert self.previewed, "Failed to preview snapshot %s" % (
            self.snapshot_description
        )
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        )

        testflow.step("Checking that files no longer exist after preview")
        self.check_file_existence_operation(False)

        testflow.step("Commit snapshot")
        self.check_file_existence_operation(False)
        assert ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True), (
                "Failed to commit snapshot %s" % self.snapshot_description
            )
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        testflow.step("Checking that files no longer exist after commit")
        self.check_file_existence_operation(False)

    @polarion("RHEVM3-11679")
    @tier2
    def test_snapshot_operation(self):
        """
        Create a snapshot while VM is running
        """
        self._test_snapshot_operation(self.vm_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase11676(TestCase):
    """
    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = False
    live_snapshot = None
    polarion_test_case = '11676'

    @polarion("RHEVM3-11676")
    @tier3
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        if self.live_snapshot:
            assert ll_vms.start_vms([self.vm_name]), (
                "Failed to start VM %s" % self.vm_name
            )
        description = MAX_DESC_LENGTH * 'a'
        testflow.step(
            "Trying to create snapshot on VM %s with description "
            "containing %d 'a' letters", self.vm_name, MAX_DESC_LENGTH
        )
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=description
        )

    @polarion("RHEVM3-11676")
    @tier3
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        if self.live_snapshot:
            assert ll_vms.start_vms([self.vm_name]), (
                "Failed to start VM %s" % self.vm_name
            )
        testflow.step(
            "Trying to create snapshot with description %s",
            SPECIAL_CHAR_DESC
        )
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=SPECIAL_CHAR_DESC
        ), "Failed to add snapshot %s to VM %s" % (
            SPECIAL_CHAR_DESC, self.vm_name
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_storage_domains.__name__,
    add_disks_different_sd.__name__,
)
class TestCase11665(TestCase):
    """
    Create 2 additional disks on a VM, each on a different storage domain
    Add snapshot

    Expected Results:
    You should be able to create a snapshot
    """
    __test__ = False
    disks_count = 2
    live_snapshot = None
    polarion_test_case = '11665'

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_CREATE_SNAPSHOT])
    @polarion("RHEVM3-11665")
    @tier3
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on VM that has disks on multiple
        storage domains
        """
        if self.live_snapshot:
            assert ll_vms.startVm(
                True, self.vm_name, config.VM_UP, True,
            ), "Failed to start VM %s" % self.vm_name
        testflow.step(
            "Create a snapshot on VM %s that contains multiple disks on "
            "different domains", self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase11680(TestCase):
    """
    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = False
    live_snapshot = None
    polarion_test_case = '11680'

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MIGRATE_VM])
    @polarion("RHEVM3-11680")
    @tier3
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        if self.live_snapshot:
            assert ll_vms.startVm(True, self.vm_name), (
                "Failed to start VM %s" % self.vm_name
            )
        testflow.step("Migrate VM %s", self.vm_name)
        assert ll_vms.migrateVm(True, self.vm_name, wait=False)
        testflow.step("Take snapshot while the VM is migrating")
        assert ll_vms.addSnapshot(
            False, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_storage_domains.__name__,
    add_disks_different_sd.__name__,
)
class TestCase11674(TestCase):
    """
    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = False
    disks_count = 1
    live_snapshot = None
    polarion_test_case = '11674'

    @polarion("RHEVM3-11674")
    @tier2
    def test_snapshot_with_multiple_disks(self):
        """
        Checks that created snapshot appears only once although VM has more
        disks
        """
        if self.live_snapshot:
            assert ll_vms.startVm(
                True, self.vm_name, config.VM_UP, True,
            ), "Failed to start VM %s" % self.vm_name
        snap_descs = set([config.ACTIVE_SNAPSHOT, LIVE_SNAPSHOT_DESC])
        testflow.step("Create snapshot on VM %s", self.vm_name)
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )
        testflow.step(
            "Ensure only one snapshot appears even if the VM has multiple "
            "disks attached"
        )
        snapshots = ll_vms._getVmSnapshots(self.vm_name, False)
        current_snap_descs = set([snap.description for snap in snapshots])
        assert snap_descs == current_snap_descs


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_template.__name__,
    add_two_vms_from_template.__name__,
    remove_vms.__name__,
)
class TestCase11684(TestCase):
    """
    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add snapshot for both thin and cloned VMs

    Expected Results:

    Snapshots should be created for both cases
    """
    __test__ = False
    live_snapshot = None
    polarion_test_case = '11684'
    vm_names = list()

    @polarion("RHEVM3-11684")
    @tier3
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        testflow.step("Create a snapshot on a thinly provisioned vm")
        assert ll_vms.addSnapshot(
            True, vm=self.vm_thin, description=LIVE_SNAPSHOT_DESC
        )

    @polarion("RHEVM3-11684")
    @tier3
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        testflow.step("Create a snapshot on a cloned vm")
        assert ll_vms.addSnapshot(
            True, vm=self.vm_clone, description=LIVE_SNAPSHOT_DESC
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_several_snapshots.__name__,
)
class TestCase18886(TestCase):
    """
    - Create VM with disks
    - Create snapshot A
    - Create snapshot B
    - Preview snapshot A and commit

    Expected result:
        Snapshot B should removed after commits to snapshot A
    """
    __test__ = False
    live_snapshot = None
    snap_count = 2
    polarion_test_case = '18886'

    @polarion("RHEVM-18886")
    @tier3
    def test_commit_snapshot(self):

        testflow.step(
            "Preview snapshot %s of VM %s", self.snapshot_list[0],
            self.vm_name
        )

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_list[0]), (
            "Failed to preview snapshot %s" % self.snapshot_list[0]
        )
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        testflow.step(
            "Commit snapshot %s of VM %s", self.snapshot_list[0],
            self.vm_name
        )
        assert ll_vms.commit_snapshot(True, self.vm_name), (
            "Failed to commit snapshot %s" % self.snapshot_list[0]
        )

        assert not ll_vms._getVmSnapshot(
            self.vm_name, self.snapshot_list[1]
        ), "Snapshot %s exists after commit to an earlier snapshot %s" % (
            self.snapshot_list[1], self.snapshot_list[0]
        )
