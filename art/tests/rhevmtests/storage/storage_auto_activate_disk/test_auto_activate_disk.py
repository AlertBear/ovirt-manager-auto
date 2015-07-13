"""
Adding Disk to a VM which is not down adds a Disk that is activated tests
Author: Meital Bourvine
"""
import config
import helpers
import logging

from art.rhevm_api.tests_lib.low_level import vms, disks
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
import art.test_handler.exceptions as exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr

logger = logging.getLogger(__name__)

DISK_PERMUTATIONS = helpers.get_all_disk_permutation()


class VmWithOs(TestCase):
    """
    Prepare a VM with OS installed
    """
    __test__ = False
    polarion_test_case = ''
    vm_name = None

    @classmethod
    def setup_class(cls):
        """
        Create a vm with a disk and OS
        """
        logger.info("setup class %s", cls.__name__)

        cls.vm_name = "vm_%s" % cls.polarion_test_case

        cls.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        helpers.create_and_start_vm(cls.vm_name, cls.storage_domain)

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the vm and removes it
        """
        if not vms.removeVm(True, cls.vm_name, stopVM='true'):
            raise exceptions.VMException("Failed to remove vm %s!" %
                                         cls.vm_name)
        wait_for_jobs([config.ENUMS['job_remove_vm']])


@attr(tier=1)
class TestCase4936(VmWithOs):
    """
    Add disks while vm is running
    """
    __test__ = True
    polarion_test_case = '4936'

    @polarion("RHEVM3-4936")
    def test_attach_new_disk_while_running(self):
        """
        Attach different types of disks while the vm is running
        """
        for permutation in DISK_PERMUTATIONS:
            logger.info("Adding disk %s %s %s",
                        permutation['interface'],
                        permutation['sparse'],
                        permutation['disk_format'])
            helpers.attach_new_disk(
                self.vm_name, storage_domain=self.storage_domain, **permutation
            )


class VmWithAnotherDiskWhileStatus(VmWithOs):
    """
    Add another disk to the VM while the VM is in a specific status
    """
    __test__ = False

    def attach_new_disk_while_status(self, action, status,
                                     activate_expected_status=True,
                                     **permutation):
        """
        Try to add a new disk while OS is in a certain state
        """
        logger.info("Changing vm %s state to %s", self.vm_name, action)
        assert vms.changeVMStatus(True, self.vm_name, action, status,
                                  async='false')

        assert helpers.attach_new_disk(
            self.vm_name, should_be_active=activate_expected_status,
            storage_domain=self.storage_domain, **permutation
        )


@attr(tier=1)
class TestCase4937(VmWithAnotherDiskWhileStatus):
    """
    Add disks while VM is in a certain state
    """
    __test__ = True
    polarion_test_case = '4937'

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_powering_up(self):
        """
        Attach different types of disks while the vm is powering up
        """
        expected_status = " ".join([config.VM_POWER_UP, config.VM_UP])
        for permutation in DISK_PERMUTATIONS:
            logger.info("Stopping vm %s", self.vm_name)
            assert vms.stopVm(True, self.vm_name)
            logger.info(
                "Adding disk %s %s %s", permutation['interface'],
                permutation['sparse'], permutation['disk_format'])
            self.attach_new_disk_while_status(
                config.VM_START,
                expected_status,
                activate_expected_status=False,
                **permutation)
            logger.info("Waiting for VM to shut down")
            vms.waitForVMState(self.vm_name)

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_powering_down(self):
        """
        Attach different types of disks while the vm is powering down
        """
        expected_status = " ".join([config.VM_POWER_DOWN, config.VM_DOWN])
        for permutation in DISK_PERMUTATIONS:
            logger.info(
                "Adding disk %s %s %s", permutation['interface'],
                permutation['sparse'], permutation['disk_format'])
            self.attach_new_disk_while_status(
                config.VM_STOP,
                expected_status,
                activate_expected_status=False,
                **permutation)
            logger.info("Waiting for VM to shut down")
            vms.wait_for_vm_states(self.vm_name, states=config.VM_DOWN)
            logger.info("Starting vm %s", self.vm_name)
            assert vms.startVm(True, self.vm_name,
                               wait_for_status=config.VM_UP)

    @polarion("RHEVM3-4937")
    def test_attach_new_disk_suspend(self):
        """
        Attach different types of disks while the vm is suspended
        """
        for permutation in DISK_PERMUTATIONS:
            logger.info(
                "Adding disk %s %s %s", permutation['interface'],
                permutation['sparse'], permutation['disk_format'])
            self.attach_new_disk_while_status(
                config.VM_SUSPEND,
                config.VM_SUSPENDED,
                activate_expected_status=False,
                **permutation)
            logger.info("Starting vm %s", self.vm_name)
            # Wait for vm's ip to make sure the vm is in full restored state
            # before adding a new disk
            assert vms.startVm(
                True, self.vm_name, wait_for_ip=True
            )

    def tearDown(self):
        """
        Remove the disks from the VM
        """
        vms.waitForDisksStat(self.vm_name)
        vms.stop_vms_safely([self.vm_name])
        disk_names = []
        for permutation in DISK_PERMUTATIONS:
            disk_name = "%s_%s_%s_%s_disk" % (self.vm_name,
                                              permutation['interface'],
                                              permutation['disk_format'],
                                              permutation['sparse'])
            disk_names.append(disk_name)
            logger.info("Removing disk %s", disk_name)
            vms.removeDisk(True, self.vm_name, disk_name, wait=False)
        assert disks.waitForDisksGone(True, ",".join(disk_names))
        assert vms.startVm(True, self.vm_name)
        vms.wait_for_vm_states(self.vm_name)
