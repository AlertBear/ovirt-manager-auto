"""
3.6 Feature: Freeze/Thaw a vm
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_VM_Freeze_Thaw
"""
import logging
import os
import re
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase
from rhevmtests.storage import config
from rhevmtests.storage import helpers as storage_helpers

from art.rhevm_api.utils.resource_utils import runMachineCommand

logger = logging.getLogger(__name__)


DD_CMD = "dd if=/dev/urandom of=%s & echo $!"
CHECK_PID_CMD = "file /proc/%s"
DD_FILE_SIZE_CMD = "du %s"
WRITE_TO_FILE_CMD = "echo 'test write freeze/thaw' > %s"
OVIRT_GUEST_AGENT_STOP_CMD = "service ovirt-guest-agent stop"
QEMU_GUEST_AGENT_STOP_CMD = "service qemu-ga stop"


class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    file_path = "/tmp/test_file"
    dd_path = "/tmp/dd_output"

    def setUp(self):
        """
        Create and start a vm
        """
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )

        ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
        self.vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        logger.info("Running tests on vm %s", self.vm_name)

    def assert_fail_write_to_filesystem_with_timeout(self):
        """
        Ensure writing a file while the vm's filesystems are frozen fails
        with a timeout
        """
        self.assertTrue(
            "timeout" in self.run_cmd(
                WRITE_TO_FILE_CMD % self.file_path, positive=False,
                timeout=5
            ),
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

        self.assertTrue(
            ll_vms.freeze_vm(True, self.vm_name),
            "Failed to freeze vm %s filesystems" % self.vm_name
        )

        self.run_cmd(CHECK_PID_CMD % dd_pid)

        dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        second_dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        self.assertEqual(
            dd_file_size, second_dd_file_size,
            "File %s size isn't suppose to be increased when the filesystems "
            "are frozen" % self.dd_path
        )

        self.assert_fail_write_to_filesystem_with_timeout()
        self.func_to_exec_on_freeze()

        self.assertTrue(
            ll_vms.thaw_vm(True, self.vm_name),
            "Failed to thaw vm %s filesystems" % self.vm_name
        )
        self.run_cmd(CHECK_PID_CMD % dd_pid)
        new_dd_file_size = self.run_cmd(
            DD_FILE_SIZE_CMD % self.dd_path, out_as_int=True
        )
        self.assertTrue(
            new_dd_file_size > dd_file_size,
            "File %s size after thaw is not bigger than when the filesystem "
            "was frozen. Did the write operation restart?"
        )

        self.run_cmd(WRITE_TO_FILE_CMD % self.file_path)

    def tearDown(self):
        """
        Remove the vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to stop and remove vm %s", self.vm_name)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=1)
class TestCase14677(BaseTestCase):
    """
    RHEVM3-14677 - Basic freeze and thaw flow
    """
    __test__ = True

    @polarion("RHEVM3-14677")
    def test_basic_freeze_thaw_flow(self):
        """
        Test the basic flow
        """
        self.freeze_thaw_basic_flow()


@attr(tier=2)
class TestCase14717(BaseTestCase):
    """
    RHEVM3-14717 - Multiple freeze/thaw calls
    """
    __test__ = True
    NUMBER_OF_TIMES = 5

    @polarion("RHEVM3-14717")
    def test_multiple_freeze_thaw_flow(self):
        """
        Execute the basic flow multiple times
        """
        for _ in range(self.NUMBER_OF_TIMES):
            self.freeze_thaw_basic_flow()


@attr(tier=2)
class TestCase14713(BaseTestCase):
    """
    RHEVM3-14713 - Freeze and thaw a vm with multiple disks
    """
    __test__ = True

    def setUp(self):
        """
        Attach a disk and create a filesystem on it
        """
        super(TestCase14713, self).setUp()
        self.disk_alias = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        if not ll_disks.addDisk(
            True, alias=self.disk_alias,
            provisioned_size=10 * config.GB, interface=config.VIRTIO,
            sparse=True, format=config.COW_DISK,
            storagedomain=self.storage_domain
        ):
            raise exceptions.DiskException(
                "Unable to add disk %s on storage domain %s" %
                (self.disk_alias, self.storage_domain)
            )

        ll_disks.wait_for_disks_status([self.disk_alias])
        ll_disks.attachDisk(True, self.disk_alias, self.vm_name)
        out, mount_point = storage_helpers.create_fs_on_disk(
            self.vm_name, self.disk_alias
        )
        if not out:
            raise Exception(
                "Unable to create filesystem on disk %s with vm %s" %
                (self.disk_alias, self.vm_name)
            )
        self.dd_path = os.path.join(mount_point, "dd_file")
        self.file_path = os.path.join(mount_point, "test_file")

    @polarion("RHEVM3-14713")
    def test_freeze_thaw_multiple_disks(self):
        """
        Execute the basic flow on an attached disk
        """
        self.freeze_thaw_basic_flow()


@attr(tier=2)
class TestCase14716(BaseTestCase):
    """
    RHEVM3-14716 - Freeze a vm and create a memory snapshot
    """
    __test__ = True
    snapshot_description = "before_freeze_call"

    @polarion("RHEVM3-14716")
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
        self.assertTrue(
            ll_vms.addSnapshot(True, self.vm_name, self.snapshot_description),
            "Taking a snapshot while the vm's filesystems are frozen failed"
        )


@attr(tier=2)
class TestCase14715(BaseTestCase):
    """
    RHEVM3-14715 - Negative cases
    """
    __test__ = True

    @polarion("RHEVM3-14715")
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
        self.assertTrue(
            ll_vms.freeze_vm(False, self.vm_name),
            "Succeeded to freeze suspended vm %s" % self.vm_name
        )
        self.assertTrue(
            ll_vms.thaw_vm(False, self.vm_name),
            "Succeeded to thaw suspended vm %s" % self.vm_name
        )
        ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )
        self.assertTrue(
            ll_vms.freeze_vm(True, self.vm_name),
            "Failed to freeze vm filesystems %s" % self.vm_name
        )
        self.assertTrue(
            ll_vms.freeze_vm(False, self.vm_name),
            "Succeeded to freeze the already frozen vm %s" % self.vm_name
        )
        self.assert_fail_write_to_filesystem_with_timeout()

        self.assertTrue(
            ll_vms.thaw_vm(True, self.vm_name),
            "Failed to thaw vm %s filesystems" % self.vm_name
        )
        self.assertTrue(
            ll_vms.thaw_vm(True, self.vm_name),
            "Failed to thaw vm %s with filesystems that are not frozen" %
            self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        self.run_cmd(OVIRT_GUEST_AGENT_STOP_CMD)
        self.assertTrue(
            ll_vms.freeze_vm(True, self.vm_name),
            "Failed to freeze a vm %s when ovirt guest agent "
            "is stopped" % self.vm_name
        )
        self.assert_fail_write_to_filesystem_with_timeout()
        self.assertTrue(
            ll_vms.thaw_vm(True, self.vm_name),
            "Failed to thaw vm %s filesystems when ovirt guest agent "
            " is stopped" % self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        self.run_cmd(QEMU_GUEST_AGENT_STOP_CMD)
        self.assertTrue(
            ll_vms.freeze_vm(False, self.vm_name),
            "Succeeded to freeze vm %s when qemu-guest-agent is not running" %
            self.vm_name
        )
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )
        self.assertTrue(
            ll_vms.thaw_vm(False, self.vm_name),
            "Succeeded to thaw vm %s when qemu-guest-agent is not running" %
            self.vm_name
        )

        ll_vms.reboot_vm(True, self.vm_name)
        ll_vms.waitForVMState(self.vm_name, config.VM_REBOOT)
        self.assertTrue(
            ll_vms.freeze_vm(False, self.vm_name),
            "Succeeded to freeze vm %s that is in reboot status" % self.vm_name
        )
        self.assertTrue(
            ll_vms.thaw_vm(False, self.vm_name),
            "Succeeded to thaw vm %s that is in reboot status" % self.vm_name
        )
        ll_vms.waitForVMState(self.vm_name, config.VM_UP)
        ll_vms.waitForIP(self.vm_name, timeout=60)
        self.run_cmd(
            WRITE_TO_FILE_CMD % self.file_path, positive=True,
            timeout=5
        )

        ll_vms.stopVm(True, self.vm_name, async='false')
        self.assertTrue(
            ll_vms.waitForVMState(self.vm_name, config.VM_DOWN),
            "VM %s is not in status down" % self.vm_name
        )

        self.assertTrue(
            ll_vms.freeze_vm(False, self.vm_name),
            "Succeeded to freeze when vm %s is down" % self.vm_name
        )
        self.assertTrue(
            ll_vms.thaw_vm(False, self.vm_name),
            "Succeeded to thaw when vm %s is down" % self.vm_name
        )
