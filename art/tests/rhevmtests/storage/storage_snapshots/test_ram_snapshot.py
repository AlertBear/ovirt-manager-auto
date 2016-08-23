"""
Storage full snapshot test - ram snapshot
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Ram_Snapshots
"""
from rhevmtests.storage import config
import logging
import pytest
from art.test_handler.tools import bz, polarion
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.unittest_lib import (
    tier1,
    tier2,
    tier4,
)
from art.unittest_lib import StorageTest as TestCase, testflow
from rhevmtests.storage import helpers as storage_helpers
from helpers import is_pid_running_on_vm, start_cat_process_on_vm

from rhevmtests.storage.fixtures import (
    create_vm, create_snapshot, undo_snapshot, poweroff_vm, start_vm,
    remove_vms, remove_vm_from_export_domain, poweroff_vm_setup,
)

from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    create_memory_snapsot_running_process,
    pids_list,
)

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    pids_list.__name__,
    create_vm.__name__,
    create_snapshot.__name__,
    start_vm.__name__,
    create_memory_snapsot_running_process.__name__,
)
class VMWithMemoryStateSnapshot(TestCase):
    """
    Class with VM with base RAM snapshot to be used as base for tests that
    do not need to create RAM snapshot
    """
    __test__ = False
    persist_network = False
    pids = []
    cmdlines = [config.DEV_ZERO, config.DEV_URANDOM]


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
)
class CreateSnapshotWithMemoryState(TestCase):
    """
    Create a snapshot with memory state on specified host according to
    run_test_on_spm
    """
    __test__ = False

    def create_snapshot(self):
        """
        Create a snapshot with memory state
        """
        self.snapshot = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.step("Starting process on VM %s", self.vm_name)
        start_cat_process_on_vm(self.vm_name, config.DEV_ZERO)

        testflow.step(
            "Creating snapshot %s on VM %s", self.snapshot, self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot, persist_memory=True), (
                "Unable to create RAM snapshot on VM %s" % self.vm_name
            )

        testflow.step("Ensuring snapshot %s has memory state", self.snapshot)
        assert ll_vms.is_snapshot_with_memory_state(
            self.vm_name, self.snapshot
        ), "Snapshot %s does not contain memory state" % self.snapshot


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    start_vm.__name__,
)
class TestCase5129(CreateSnapshotWithMemoryState):
    """
    Polarion Test Case 5129 - Create Snapshot with Memory State on SPM
    """
    __test__ = True
    vm_run_on_spm = True

    @polarion("RHEVM3-5129")
    @tier2
    def test_create_snapshot_spm(self):
        """
        Create ram snapshot on spm
        """
        self.create_snapshot()


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    start_vm.__name__,
)
class TestCase5140(CreateSnapshotWithMemoryState):
    """
    Polarion Test Case 5140 - Create Snapshot with Memory State on HSM
    """
    __test__ = True
    vm_run_on_spm = False

    @polarion("RHEVM3-5140")
    @tier2
    def test_create_snapshot_hsm(self):
        """
        Create ram snapshot on hsm
        """
        self.create_snapshot()


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_memory_snapsot_running_process.__name__,
    poweroff_vm_setup.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class ReturnToSnapshot(VMWithMemoryStateSnapshot):
    """
    Class that returns to snapshot (using preview or
    commit as specified)
    """
    __test__ = False
    action_to_call = None

    def return_to_ram_snapshot(self):
        """
        Commit RAM snapshot
        """
        testflow.step(
            "Checking RAM snapshot %s on VM %s using action %s",
            self.memory_snapshot, self.vm_name, self.action_to_call.__name__,
        )
        assert self.action_to_call(
            True, self.vm_name, self.memory_snapshot, restore_memory=True,
        ), "Could not restore RAM snapshot %s on VM %s" % (
            self.memory_snapshot, self.vm_name
        )
        logger.info("Wait for running jobs")
        ll_jobs.wait_for_jobs(
            [config.JOB_RESTORE_SNAPSHOT, config.JOB_PREVIEW_SNAPSHOT]
        )

        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, True
        ), "Error when resuming VM %s from memory snapshot %s" % (
            self.vm_name, self.memory_snapshot
        )

        testflow.step(
            "Checking if process is still running on VM %s", self.vm_name
        )
        assert is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        ), "Process %s not running on VM %s" % (self.pids[0], self.vm_name)


class TestCase5139(ReturnToSnapshot):
    """
    Polarion Test Case 5139 - Preview to RAM Snapshot
    """
    __test__ = True
    action_to_call = staticmethod(ll_vms.preview_snapshot)

    @polarion("RHEVM3-5139")
    def test_preview_snapshot(self):
        """
        preview snapshot
        """
        self.return_to_ram_snapshot()


@bz({'1461811': {}})
class TestCase5138(ReturnToSnapshot):
    """
    Polarion Test Case 5138 - Restore RAM Snapshot
    """
    __test__ = True
    action_to_call = staticmethod(ll_vms.restore_snapshot)

    @polarion("RHEVM3-5138")
    @tier1
    def test_restore_snasphot(self):
        """
        restore snapshot
        """
        self.return_to_ram_snapshot()


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_memory_snapsot_running_process.__name__,
)
class TestCase5137(VMWithMemoryStateSnapshot):
    """
    Polarion Test Case 5137 - VM with multiple RAM Snapshots
    """
    __test__ = True
    second_snapshot_name = "second_ram_snapshot"
    vm_wait_for_ip = True

    @polarion("RHEVM3-5137")
    @tier2
    def test_vm_with_multiple_ram_snapshots(self):
        """
        * Start another process on the VM and create a new memory snapshot.
        * Preview first snapshot and check that only first process is running
        * Preview second snapshot and check that both processes are running
        """
        pid = start_cat_process_on_vm(self.vm_name, self.cmdlines[1])
        self.pids.append(pid)
        testflow.step(
            "Creating snapshot %s on VM %s", self.second_snapshot_name,
            self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.second_snapshot_name, persist_memory=True
        ), (
            "Unable to create snapshot %s on VM %s"
            % (self.memory_snapshot, self.vm_name)
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        testflow.step("Shutting down VM %s", self.vm_name)
        assert ll_vms.stopVm(True, self.vm_name)
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)

        testflow.step(
            "Previewing first snapshot (%s) on VM %s",
            self.memory_snapshot, self.vm_name
        )
        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.memory_snapshot, restore_memory=True
        ), "Unable to preview snapshot %s on VM %s" % (
            self.memory_snapshot, self.vm_name
        )
        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_ip=True, wait_for_status=config.VM_UP
        )
        testflow.step(
            "Checking if first process is running on VM %s", self.vm_name
        )
        assert is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        ), (
            "First process is not running on VM - memory state not "
            "restored correctly"
        )
        testflow.step(
            "Checking that second process is not running on VM %s",
            self.vm_name
        )
        assert not is_pid_running_on_vm(
            self.vm_name, self.pids[1], self.cmdlines[1]
        ), (
            "Second process is running on VM - memory state not "
            "restored correctly"
        )
        testflow.step("Powering VM %s off", self.vm_name)
        assert ll_vms.stopVm(
            True, self.vm_name
        ), "Could not power VM %s off" % self.vm_name
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        testflow.step("Undoing snapshot preview")
        assert ll_vms.undo_snapshot_preview(True, self.vm_name)
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        testflow.step(
            "Previewing second snapshot (%s) on VM %s",
            self.second_snapshot_name, self.vm_name
        )
        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.second_snapshot_name, restore_memory=True
        ), "Unable to preview snapshot %s on VM %s" % (
            self.second_snapshot_name, self.vm_name
        )

        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_ip=True, wait_for_status=config.VM_UP
        )

        testflow.step(
            "Checking that both processes are running on VM %s",
            self.vm_name
        )
        first = is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        )
        second = is_pid_running_on_vm(
            self.vm_name, self.pids[1], self.cmdlines[1]
        )
        assert first and second, (
            "Processes not both running on VM. First process: %s "
            "second process: %s" % (first, second)
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_memory_snapsot_running_process.__name__,
    poweroff_vm_setup.__name__,
    remove_vms.__name__,
)
class TestCase5136(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5136 - Create VM from snapshot with memory
    """
    __test__ = True
    persist_network = True

    @polarion("RHEVM3-5136")
    @tier2
    def test_create_vm_from_memory_state_snapshot(self):
        """
        Create VM from memory snapshot and check process is **not** running
        on new VM
        """
        self.cloned_vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        testflow.step(
            "Creating new VM %s from snapshot %s of VM %s",
            self.cloned_vm_name, self.memory_snapshot, self.vm_name
        )

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_name, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=self.memory_snapshot,
        ), (
            "Could not create VM %s from snapshot %s" %
            (self.cloned_vm_name, self.memory_snapshot)
        )
        self.vm_names.append(self.cloned_vm_name)

        testflow.step("Starting VM %s", self.cloned_vm_name)
        assert ll_vms.startVms([self.cloned_vm_name], config.VM_UP), (
            "Unable to start VM %s" % self.cloned_vm_name
        )
        status, ip = ll_vms.wait_for_vm_ip(self.cloned_vm_name)
        assert status, (
            "Failed to get IP for VM %s" % self.cloned_vm_name
        )

        testflow.step("Ensuring process is not running on the new VM")
        assert not is_pid_running_on_vm(
            self.cloned_vm_name, self.pids[0], self.cmdlines[0]
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_memory_snapsot_running_process.__name__,
    poweroff_vm_setup.__name__,
    remove_vm_from_export_domain.__name__,
)
class TestCase5134(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5134 - Import a VM with memory snapshot
    """
    __test__ = True
    persist_network = True

    @polarion("RHEVM3-5134")
    @bz({'1496805': {}})
    @tier2
    def test_import_vm_with_memory_state_snapshot(self):
        """
        Import a VM that has memory state snapshot and ensure it resumes memory
        state from that snapshot successfully
        """
        testflow.step(
            "Exporting VM %s to domain %s", self.vm_name,
            config.EXPORT_DOMAIN_NAME
        )
        assert ll_vms.exportVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME
        ), (
            "Unable to export VM %s to domain %s" %
            (self.vm_name, config.EXPORT_DOMAIN_NAME)
        )
        testflow.step(
            "Removing original VM to allow import VM without collapse "
            "snapshots"
        )
        assert ll_vms.removeVm(True, self.vm_name), (
            "Unable to remove VM %s", self.vm_name
        )

        testflow.step(
            "Importing VM %s from export domain %s",
            self.vm_name, config.EXPORT_DOMAIN_NAME
        )
        assert ll_vms.importVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME, self.storage_domain,
            config.CLUSTER_NAME
        ), "Unable to import VM %s from export domain %s" % (
            self.vm_name, config.EXPORT_DOMAIN_NAME
        )

        testflow.step(
            "Restoring snapshot %s with memory state on VM %s",
            self.memory_snapshot, self.vm_name
        )
        assert ll_vms.restore_snapshot(
            True, self.vm_name, self.memory_snapshot, restore_memory=True
        ), "Unable to restore snapshot %s on VM %s" % (
            self.memory_snapshot, self.vm_name
        )

        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        ), "Unable to start VM %s" % self.vm_name
        assert is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        ), (
            "process is not running on VM %s, memory state not correctly "
            "restored" % self.vm_name
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    start_vm.__name__,
    create_memory_snapsot_running_process.__name__,
    poweroff_vm_setup.__name__,
)
class TestCase5133(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5133 - Remove a snapshot with memory state
    """
    __test__ = True

    @polarion("RHEVM3-5133")
    @tier2
    def test_remove_memory_state_snapshot(self):
        """
        Remove snapshot with memory state and check that VM starts
        successfully
        """
        testflow.step(
            "Removing snapshot %s with memory state from VM %s",
            self.memory_snapshot, self.vm_name
        )
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.memory_snapshot
        ), "Unable to remove snapshot %s from VM %s" % (
            self.memory_snapshot, self.vm_name
        )
        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_ip=True, wait_for_status=config.VM_UP
        ), "Unable to start VM %s" % self.vm_name
        testflow.step(
            "Ensuring VM %s started without memory state", self.vm_name
        )
        assert not is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    start_vm.__name__,
    create_memory_snapsot_running_process.__name__,
    poweroff_vm_setup.__name__,
)
class TestCase5131(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5131 - Stateless VM with memory snapshot
    """
    __test__ = True

    @polarion("RHEVM3-5131")
    @tier4
    def test_stateless_vm_with_memory_snapshot(self):
        """
        * Restore memory snapshot
        * Set VM to stateless
        * Start VM - ensure it resumes from memory state
        * kill process and stop vm
        * Start VM - ensure it resumes from memory state again
        """
        testflow.step(
            "Restoring memory snapshot %s on VM %s",
            self.memory_snapshot, self.vm_name
        )
        assert ll_vms.restore_snapshot(
            True, self.vm_name, self.memory_snapshot, restore_memory=True
        ), "Unable to restore snapshot %s on VM %s" % (
            self.memory_snapshot, self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        testflow.step("Setting VM %s to stateless", self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, stateless=True), (
            "Unable to set VM %s to be stateless" % self.vm_name
        )
        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(True, self.vm_name, wait_for_status=config.VM_UP)
        assert is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        )
        testflow.step("Killing process %s", self.pids[0])
        assert ll_vms.kill_process_by_pid_on_vm(
            self.vm_name, self.pids[0], config.VM_USER, config.VM_PASSWORD
        )
        testflow.step("Power VM %s off", self.vm_name)
        vm_executor = storage_helpers.get_vm_executor(self.vm_name)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, config.SYNC_CMD, vm_executor
        )
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off vm %s" % self.vm_name
        )
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        # This is need it for RestoreFromSnapshot tasks on the background
        # due to the statless vm
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
        testflow.step("Starting VM %s again", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        )
        testflow.step("Ensure process is running on the VM")
        assert is_pid_running_on_vm(
            self.vm_name, self.pids[0], self.cmdlines[0]
        )
        assert ll_vms.stopVm(True, self.vm_name)
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        # This is need it for RestoreFromSnapshot tasks on the background
        # due to the statless vm
        wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
