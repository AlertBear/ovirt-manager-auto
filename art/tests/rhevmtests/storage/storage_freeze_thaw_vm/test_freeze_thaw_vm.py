"""
3.6 Feature: Freeze/Thaw a vm
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_VM_Freeze_Thaw
"""
import logging
import os
import pytest
import re
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms
)
from rhevmtests.storage import config
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.rhevm_api.utils.resource_utils import runMachineCommand

from rhevmtests.storage.fixtures import (
    add_disk, attach_disk, create_fs_on_disk, create_vm, start_vm,
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
    start_vm.__name__
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
        Ensure writing a file while the vm's filesystems are frozen fails
        with a timeout
        """
        assert "timeout" in self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=False,
            timeout=5
        ), (
            "Write operation when the filesystems are frozen should have "
            "failed with a timeout"
        )

    def func_to_exec_on_freeze(self):
        pass

    def run_cmd(self, cmd, out_as_int=False, positive=True, timeout=20):
        """
        Runs a command on the test vm, returning the output or an exception in
        case of a failure

        :param cmd: Command to be executed
        :type cmd: str
        :param out_as_int: Determines whether the output should be returned as
        an integer
        :type out_as_int: bool
        :param positive: True if the command is expected to succeed, False
        otherwise
        :type positive: bool
        :param timeout: Time to wait for the command (in seconds)
        :type timeout: int
        :raises: Exception
        :returns: The output of the command executed
        :rtype: int or str
        """
        rc, out = runMachineCommand(
            positive, ip=self.vm_ip, user=config.VM_USER,
            password=config.VM_PASSWORD, cmd=cmd, timeout=timeout
        )
        logger.debug("cmd: %s, rc: %s, out: %s:", cmd, rc, out)
        if not rc:
            raise Exception(
                "Command %s failed, output: %s" % (cmd, out)
            )
        if out_as_int:
            return int(re.search('\d+', out['out']).group())
        else:
            return out['out']

    def freeze_thaw_basic_flow(self):
        """
        * Starts writing process to the disk
        * Freeze the vm
        * Try to execute a simple write => it should timeout
        * Ensure the writing process before the freeze is still running but no
        data is being written
        * Thaw the vm
        * Ensure the writing process is still running and file size is
        increased
        * Try to execute a simple write => it should succeed
        """
        dd_pid = self.run_cmd(DD_CMD % self.dd_path, out_as_int=True)

        testflow.step("Freezing filesystem of vm %s", self.vm_name)
        assert ll_vms.freeze_vm(
            True, self.vm_name
        ), "Failed to freeze vm %s filesystems" % self.vm_name

        self.run_cmd(CHECK_PID_CMD % dd_pid)

        dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        second_dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        assert dd_file_size == second_dd_file_size, (
            "File %s size isn't suppose to be increased when the filesystems "
            "are frozen" % self.dd_path
        )

        testflow.step(
            "Ensures it is impossible to create a file on a freezed filesystem"
        )
        self.assert_fail_write_to_filesystem_with_timeout()
        self.func_to_exec_on_freeze()

        testflow.step("Thaw filesystem of vm %s", self.vm_name)
        assert ll_vms.thaw_vm(
            True, self.vm_name
        ), "Failed to thaw vm %s filesystems" % self.vm_name
        self.run_cmd(CHECK_PID_CMD % dd_pid)
        new_dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        assert new_dd_file_size > dd_file_size, (
            "File %s size after thaw is not bigger than when the filesystem "
            "was frozen. Did the write operation restart?"
        )

        testflow.step(
            "Ensures it is possible to create a file on a thawed filesystem"
        )
        self.run_cmd(WRITE_TO_FILE_CMD % self.file_path)


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
    RHEVM3-14713 - Freeze and thaw a vm with multiple disks
    """
    __test__ = True
    disk_size = 10 * config.GB
    dd_path = os.path.join(config.MOUNT_POINT, '/', "dd_file")
    file_path = os.path.join(config.MOUNT_POINT, '/', "test_file")

    @polarion("RHEVM3-14713")
    @attr(tier=3)
    def test_freeze_thaw_multiple_disks(self):
        """
        Execute the basic flow on an attached disk
        """
        self.freeze_thaw_basic_flow()


class TestCase14716(BaseTestCase):
    """
    RHEVM3-14716 - Freeze a vm and create a memory snapshot
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
        While the vm's fileystems are frozen, create a snapshot
        """
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        ), "Taking a snapshot while the vm's filesystems are frozen failed"


class TestCase14715(BaseTestCase):
    """
    RHEVM3-14715 - Negative cases
    """
    __test__ = True

    @polarion("RHEVM3-14715")
    @attr(tier=3)
    def test_negative_cases(self):
        """
        * Suspend a vm
        => freeze/thaw should fail
        * Freeze an already frozen vm
        => should fail
        * Thaw an unfrozen vm
        => should pass
        * Freeze/Thaw a vm with no ovirt-guest-agent running
        => should pass
        * Freeze/Thaw a vm with no qemu-guest-agent running
        => should fail
        * Reboot a vm
        => freeze/thaw should fail
        * Shutdown a vm
        => freeze/thaw should fail
         """
        ll_vms.suspendVm(True, self.vm_name)
        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze suspended vm %s" % self.vm_name
        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw suspended vm %s" % self.vm_name
        ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )
        assert ll_vms.freeze_vm(
            True, self.vm_name
        ), "Failed to freeze vm filesystems %s" % self.vm_name
        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze the already frozen vm %s" % self.vm_name
        self.assert_fail_write_to_filesystem_with_timeout()

        assert ll_vms.thaw_vm(
            True, self.vm_name
        ), "Failed to thaw vm %s filesystems" % self.vm_name
        assert ll_vms.thaw_vm(True, self.vm_name), (
            "Failed to thaw vm %s with filesystems that are not frozen" %
            self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        self.run_cmd(OVIRT_GUEST_AGENT_STOP_CMD)
        assert ll_vms.freeze_vm(True, self.vm_name), (
            "Failed to freeze a vm %s when ovirt guest agent is stopped" %
            self.vm_name
        )
        self.assert_fail_write_to_filesystem_with_timeout()
        assert ll_vms.thaw_vm(True, self.vm_name), (
            "Failed to thaw vm %s filesystems when ovirt guest agent is "
            "stopped" % self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        self.run_cmd(QEMU_GUEST_AGENT_STOP_CMD)
        assert ll_vms.freeze_vm(False, self.vm_name), (
            "Succeeded to freeze vm %s when qemu-guest-agent is not running" %
            self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )
        assert ll_vms.thaw_vm(False, self.vm_name), (
            "Succeeded to thaw vm %s when qemu-guest-agent is not running" %
            self.vm_name
        )

        ll_vms.reboot_vm(True, self.vm_name)
        ll_vms.waitForVMState(self.vm_name, config.VM_REBOOT)
        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze vm %s that is in reboot status" % self.vm_name
        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw vm %s that is in reboot status" % self.vm_name
        ll_vms.waitForVMState(self.vm_name, config.VM_UP)
        ll_vms.waitForIP(self.vm_name, timeout=60)
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        ll_vms.stopVm(True, self.vm_name, async='false')
        assert ll_vms.waitForVMState(
            self.vm_name, config.VM_DOWN
        ), "VM %s is not in status down" % self.vm_name

        assert ll_vms.freeze_vm(
            False, self.vm_name
        ), "Succeeded to freeze when vm %s is down" % self.vm_name
        assert ll_vms.thaw_vm(
            False, self.vm_name
        ), "Succeeded to thaw when vm %s is down" % self.vm_name
