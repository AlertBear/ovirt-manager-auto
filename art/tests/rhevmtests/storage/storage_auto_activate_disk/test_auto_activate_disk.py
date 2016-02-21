"""
Adding Disk to a VM which is not down adds a Disk that is activated tests
"""
import logging

import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)

DISK_PERMUTATIONS = ll_disks.get_all_disk_permutation(
    interfaces=storage_helpers.INTERFACES
)


class VmWithOs(TestCase):
    """
    Prepare a VM with an OS installed
    """
    __test__ = False
    polarion_test_case = None
    vm_name = None
    vm_initial_disks = list()

    @classmethod
    def setup_class(cls):
        """
        Select a VM from the inventory for use, ensure VirtIO-SCSI Enabled
        option is selected
        """
        logger.info("setup class %s", cls.__name__)
        if not ll_vms.does_vm_exist(config.VM_NAME[0]):
            raise exceptions.VMException(
                "VM '%s' doesn't exist" % config.VM_NAME[0]
            )
        logger.info("Pick VM '%s' from inventory for use", config.VM_NAME[0])
        cls.vm_name = config.VM_NAME[0]

        cls.vm_initial_disks = [d.get_id() for d in ll_vms.getVmDisks(
            cls.vm_name)]

        cls.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage
        )[0]

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the VM used for tests, restore the VirtIO-SCSI Enabled
        option if it was updated
        """
        logger.info("teardown_class %s", cls.__name__)
        if cls.vm_name:
            ll_vms.stop_vms_safely([cls.vm_name])
            logger.info(
                "Restore configuration to any VM that had its VirtIO-SCSI "
                "Enabled set to False before the start of the test run"
            )

    def setUp(self):
        """ Start VM for test """
        if not ll_vms.startVm(True, self.vm_name, config.VM_UP):
            raise exceptions.VMException(
                "Could not power on VM '%s'" % self.vm_name
            )

    def tearDown(self):
        """ Stop VM for test, remove created disks """
        ll_vms.stop_vms_safely([self.vm_name])
        for disk in ll_vms.getVmDisks(self.vm_name):
            if disk.get_id() not in self.vm_initial_disks:
                if not ll_disks.deleteDisk(
                        True, alias="", disk_id=disk.get_id()
                ):
                    TestCase.test_failed = True
                    logger.error(
                        "Deleting disk with ID '%s' failed", disk.get_id()
                    )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        self.teardown_exception()


@attr(tier=2)
class TestCase4936(VmWithOs):
    """
    Add disks while vm is running
    """
    __test__ = True
    polarion_test_case = "4936"

    @polarion("RHEVM3-4936")
    def test_attach_new_disk_while_running(self):
        """
        Attach different types of disks while the vm is running
        """
        for permutation in DISK_PERMUTATIONS:
            logger.info(
                "Adding disk %s %s %s", permutation["interface"],
                permutation["sparse"], permutation["format"]
            )
            helpers.attach_new_disk(
                self.polarion_test_case, self.vm_name, True,
                self.storage_domain, **permutation
            )


class VmWithAnotherDiskWhileStatus(VmWithOs):
    """
    Add another disk to the VM while the VM is in a specific state
    """
    __test__ = False

    def attach_new_disk_while_status(
            self, action, status, activate_expected_status=True, **permutation
    ):
        """
        Try to add a new disk while OS is in requested state
        """
        if action == config.VM_SUSPEND:
            if ll_vms.get_vm_state(self.vm_name) != config.VM_SUSPENDED:
                logger.info("Changing vm %s state to %s", self.vm_name, action)
                assert ll_vms.changeVMStatus(
                    True, self.vm_name, action, status, async="true"
                )
                assert ll_vms.waitForVMState(self.vm_name, config.VM_SUSPENDED)
        else:
            logger.info("Changing vm %s state to %s", self.vm_name, action)
            assert ll_vms.changeVMStatus(
                True, self.vm_name, action, status, async="false"
            )

        assert helpers.attach_new_disk(
            self.polarion_test_case, self.vm_name, activate_expected_status,
            self.storage_domain, **permutation
        )


@attr(tier=2)
class TestCase4937(VmWithAnotherDiskWhileStatus):
    """
    Add disks while VM is in a certain state
    """
    __test__ = True
    polarion_test_case = "4937"

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_powering_up(self):
        """
        Attach different types of disks while the vm is powering up
        """
        expected_status = " ".join([config.VM_POWER_UP, config.VM_UP])
        for permutation in DISK_PERMUTATIONS:
            logger.info("Stopping vm %s", self.vm_name)
            assert ll_vms.stopVm(True, self.vm_name)
            logger.info(
                "Adding disk %s %s %s", permutation["interface"],
                permutation["sparse"], permutation["format"]
            )
            self.attach_new_disk_while_status(
                config.VM_START, expected_status, False, **permutation
            )
            logger.info("Waiting for VM to power on")
            assert ll_vms.waitForVMState(self.vm_name)

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_powering_down(self):
        """
        Attach different types of disks while the vm is powering down
        """
        expected_status = " ".join([config.VM_POWER_DOWN, config.VM_DOWN])
        for permutation in DISK_PERMUTATIONS:
            logger.info(
                "Adding disk %s %s %s", permutation["interface"],
                permutation["sparse"], permutation["format"])
            self.attach_new_disk_while_status(
                config.VM_STOP, expected_status, False, **permutation
            )
            logger.info("Waiting for VM to shut down")
            ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
            logger.info("Waiting for VM to power on")
            assert ll_vms.startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_suspend(self):
        """
        Attach different types of disks while the vm is suspended
        """
        for permutation in DISK_PERMUTATIONS:
            logger.info(
                "Adding disk %s %s %s", permutation['interface'],
                permutation['sparse'], permutation['format'])
            self.attach_new_disk_while_status(
                config.VM_SUSPEND,
                config.VM_SUSPENDED,
                activate_expected_status=False,
                **permutation
            )
