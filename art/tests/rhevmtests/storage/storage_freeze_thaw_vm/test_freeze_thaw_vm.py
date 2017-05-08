"""
3.6 Feature: Freeze/Thaw a VM
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_VM_Freeze_Thaw
"""
import logging
import os
import shlex
import pytest
import re
import paramiko
import socket
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from rhevmtests.storage import config
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase, testflow

from rhevmtests.storage.fixtures import (
    add_disk, attach_disk, create_fs_on_disk, create_vm, start_vm,
    init_vm_executor
)

from rhevmtests.storage.fixtures import remove_vm # noqa


logger = logging.getLogger(__name__)
DD_CMD = "dd if=/dev/urandom of=%s & echo $!"
CHECK_PID_CMD = "file /proc/%s"
DD_FILE_SIZE_CMD = "du %s"
WRITE_TO_FILE_CMD = "echo 'test write freeze/thaw' > %s"
OVIRT_GUEST_AGENT_STOP_CMD = "service ovirt-guest-agent stop"
QEMU_GUEST_AGENT_STOP_CMD = "service qemu-guest-agent stop"


@pytest.mark.usefixtures(
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__
)
class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    file_path = "/tmp/test_file"
    dd_path = "/tmp/dd_output"
    get_vm_ip = True

    def assert_fail_write_to_filesystem_with_timeout(self):
        """
        Ensure writing a file while the VM's filesystems are frozen fails
        with a timeout
        """
        command = WRITE_TO_FILE_CMD % self.file_path
        try:
            self.vm_executor.run_cmd(shlex.split(command), io_timeout=5)
        except(socket.timeout, paramiko.SSHException):
            return True
        logging.error(
            "Write operation when the filesystems are frozen should have"
            " failed with a timeout"
        )
        return False

    def func_to_exec_on_freeze(self):
        pass

    def freeze_thaw_basic_flow(self):
        """
        * Starts writing process to the disk
        * Freeze the VM
        * Try to execute a simple write => it should timeout
        * Ensure the writing process before the freeze is still running but no
        data is being written
        * Thaw the VM
        * Ensure the writing process is still running and file size is
        increased
        * Try to execute a simple write => it should succeed
        """

        command = DD_CMD % self.dd_path
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get DD PID with error: %s" % error
        dd_pid = int(re.search('\d+', out).group())

        testflow.step("Freezing filesystem of VM %s", self.vm_name)
        assert ll_vms.freeze_vm(
            True, self.vm_name
        ), "Failed to freeze VM %s filesystems" % self.vm_name

        command = CHECK_PID_CMD % dd_pid
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get DD PID with error: %s" % error

        command = DD_FILE_SIZE_CMD % self.dd_path
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get file %s size with error: %s" % (
            self.dd_path, error
        )
        dd_file_size = int(re.search('\d+', out).group())

        command = DD_FILE_SIZE_CMD % self.dd_path
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get file %s size with error: %s" % (
            self.dd_path, error
        )
        second_dd_file_size = int(re.search('\d+', out).group())

        assert dd_file_size == second_dd_file_size, (
            "File %s size isn't suppose to be increased when the filesystems "
            "are frozen" % self.dd_path
        )

        testflow.step(
            "Ensures it is impossible to create a file on a freezed filesystem"
        )

        assert self.assert_fail_write_to_filesystem_with_timeout()
        self.func_to_exec_on_freeze()

        testflow.step("Thaw filesystem of VM %s", self.vm_name)
        assert ll_vms.thaw_vm(True, self.vm_name), (
            "Failed to thaw VM %s filesystems" % self.vm_name
        )

        command = CHECK_PID_CMD % dd_pid
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get DD PID with error: %s" % error

        command = DD_FILE_SIZE_CMD % self.dd_path
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to get file %s size with error: %s" % (
            self.dd_path, error
        )
        new_dd_file_size = int(re.search('\d+', out).group())

        assert new_dd_file_size > dd_file_size, (
            "File %s size after thaw is not bigger than when the filesystem "
            "was frozen. Did the write operation restart?"
        )

        testflow.step(
            "Ensures it is possible to create a file on a thawed filesystem"
        )

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, out, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )


class TestCase14677(BaseTestCase):
    """
    RHEVM3-14677 - Basic freeze and thaw flow
    """
    __test__ = True

    @polarion("RHEVM3-14677")
    @attr(tier=2)
    def test_basic_freeze_thaw_flow(self):
        """
        Test the basic flow
        """
        self.freeze_thaw_basic_flow()


class TestCase14717(BaseTestCase):
    """
    RHEVM3-14717 - Multiple freeze/thaw calls
    """
    __test__ = True
    NUMBER_OF_TIMES = 5

    @polarion("RHEVM3-14717")
    @attr(tier=3)
    def test_multiple_freeze_thaw_flow(self):
        """
        Execute the basic flow multiple times
        """
        for _ in range(self.NUMBER_OF_TIMES):
            self.freeze_thaw_basic_flow()


@pytest.mark.usefixtures(
    add_disk.__name__,
    attach_disk.__name__,
    create_fs_on_disk.__name__,
)
class TestCase14713(BaseTestCase):
    """
    RHEVM3-14713 - Freeze and thaw a VM with multiple disks
    """
    __test__ = True
    disk_size = 10 * config.GB

    @polarion("RHEVM3-14713")
    @attr(tier=3)
    def test_freeze_thaw_multiple_disks(self):
        """
        Execute the basic flow on an attached disk
        """
        self.dd_path = os.path.join(self.mount_point, '/', "dd_file")
        self.file_path = os.path.join(self.mount_point, '/', "test_file")
        self.freeze_thaw_basic_flow()


class TestCase14716(BaseTestCase):
    """
    RHEVM3-14716 - Freeze a VM and create a memory snapshot
    """
    __test__ = True
    snapshot_description = "before_freeze_call"

    @polarion("RHEVM3-14716")
    @attr(tier=3)
    def test_preview_snapshot(self):
        """
        * Test basic flow
        * During the freeze, take a memory snapshot
        => should pass
        """
        self.freeze_thaw_basic_flow()

    def func_to_exec_on_freeze(self):
        """
        While the VM's fileystems are frozen, create a snapshot
        """
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        ), "Taking a snapshot while the VM's filesystems are frozen failed"
        ll_vms.waitForVMState(self.vm_name)


class TestCase14715(BaseTestCase):
    """
    RHEVM3-14715 - Negative cases
    """
    __test__ = True

    @polarion("RHEVM3-14715")
    @attr(tier=3)
    def test_negative_cases(self):
        """
        * Suspend a VM
        => freeze/thaw should fail
        * Freeze an already frozen VM
        => should fail
        * Thaw an unfrozen VM
        => should pass
        * Freeze/Thaw a VM with no ovirt-guest-agent running
        => should pass
        * Freeze/Thaw a VM with no qemu-guest-agent running
        => should fail
        * Reboot a VM
        => freeze/thaw should fail
        * Shutdown a VM
        => freeze/thaw should fail
         """

        ll_vms.suspendVm(True, self.vm_name)
        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze suspended VM %s" % self.vm_name

        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw suspended VM %s" % self.vm_name

        ll_vms.startVm(True, self.vm_name, wait_for_ip=True)

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, out, error = self.vm_executor.run_cmd(
            shlex.split(command), io_timeout=10
        )
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )

        assert ll_vms.freeze_vm(
            True, self.vm_name
        ), "Failed to freeze VM filesystems %s" % self.vm_name

        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze the already frozen VM %s" % self.vm_name
        assert self.assert_fail_write_to_filesystem_with_timeout()

        assert ll_vms.thaw_vm(
            True, self.vm_name
        ), "Failed to thaw VM %s filesystems" % self.vm_name

        assert ll_vms.thaw_vm(True, self.vm_name), (
            "Failed to thaw VM %s with filesystems that are not frozen" %
            self.vm_name
        )

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, _, error = self.vm_executor.run_cmd(
            shlex.split(command), io_timeout=10
        )
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )

        command = OVIRT_GUEST_AGENT_STOP_CMD
        rc, _, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, (
            "Failed to stop ovirt-guest-agent service with error: %s" % error
        )

        assert ll_vms.freeze_vm(True, self.vm_name), (
            "Failed to freeze a VM %s when ovirt guest agent is stopped" %
            self.vm_name
        )

        assert self.assert_fail_write_to_filesystem_with_timeout()

        assert ll_vms.thaw_vm(True, self.vm_name), (
            "Failed to thaw VM %s filesystems when ovirt guest agent is "
            "stopped" % self.vm_name
        )

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, _, error = self.vm_executor.run_cmd(
            shlex.split(command), io_timeout=10
        )
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )

        command = QEMU_GUEST_AGENT_STOP_CMD
        rc, _, error = self.vm_executor.run_cmd(shlex.split(command))
        assert not rc, (
            "Failed to stop service qemu-guest-agent with error: %s" % error
        )

        assert ll_vms.freeze_vm(False, self.vm_name), (
            "Succeeded to freeze VM %s when qemu-guest-agent is not running" %
            self.vm_name
        )

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, _, error = self.vm_executor.run_cmd(
            shlex.split(command), io_timeout=10
        )
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )
        assert ll_vms.thaw_vm(False, self.vm_name), (
            "Succeeded to thaw VM %s when qemu-guest-agent is not running" %
            self.vm_name
        )

        ll_vms.reboot_vm(True, self.vm_name)

        ll_vms.waitForVMState(self.vm_name, config.VM_REBOOT)

        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze VM %s that is in reboot status" % self.vm_name

        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw VM %s that is in reboot status" % self.vm_name

        ll_vms.waitForVMState(self.vm_name, config.VM_UP)

        ll_vms.wait_for_vm_ip(self.vm_name, timeout=60)

        command = WRITE_TO_FILE_CMD % self.file_path
        rc, _, error = self.vm_executor.run_cmd(
            shlex.split(command), io_timeout=10
        )
        assert not rc, "Failed to write to file %s with error: %s" % (
            self.file_path, error
        )

        ll_vms.stopVm(True, self.vm_name, async='false')

        assert ll_vms.waitForVMState(
            self.vm_name, config.VM_DOWN
        ), "VM %s is not in status down" % self.vm_name

        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze when VM %s is down" % self.vm_name

        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw when VM %s is down" % self.vm_name
