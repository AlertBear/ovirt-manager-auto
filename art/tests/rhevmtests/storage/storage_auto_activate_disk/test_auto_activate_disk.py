"""
Adding Disk to a VM which is not down adds a Disk that is activated tests
Author: Meital Bourvine
"""
import config
import logging
import helpers

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.low_level import vms, disks
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType)

import art.test_handler.exceptions as exceptions
from art.test_handler.tools import tcms  # pylint: disable=E0611

from art.unittest_lib import StorageTest as TestCase, attr

logger = logging.getLogger(__name__)

TCMS_PLAN_ID = '12632'
DISK_PERMUTATIONS = helpers.get_all_disk_permutation()
TIMEOUT_RESUME_VM = 500


class VmWithOs(TestCase):
    """
    Prepare a VM with OS installed
    """

    __test__ = False

    vm_name = None

    tcms_test_case = ''

    @classmethod
    def setup_class(cls):
        """
        Create a vm with a disk and OS
        """
        logger.info("setup class %s", cls.__name__)

        cls.vm_name = "vm_%s" % (cls.tcms_test_case)

        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        helpers.create_and_start_vm(cls.vm_name, storage_domain)

    @classmethod
    def teardown_class(cls):
        """
        Shuts down the vm and removes it
        """
        if not vms.removeVm(True, cls.vm_name, stopVM='true'):
            raise exceptions.VMException("Failed to remove vm %s!" %
                                         cls.vm_name)


@attr(tier=1)
class TestCase334691(VmWithOs):
    """
    Add disks while vm is running
    """

    __test__ = True

    tcms_test_case = '334691'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_attach_new_disk_while_running(self):
        """
        Attach different types of disks while the vm is running
        """
        for permutation in DISK_PERMUTATIONS:
            logger.info("Adding disk %s %s %s",
                        permutation['interface'],
                        permutation['sparse'],
                        permutation['disk_format'])
            helpers.attach_new_disk(self.vm_name, **permutation)


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
            **permutation)


@attr(tier=1)
class TestCase334692(VmWithAnotherDiskWhileStatus):
    """
    Add disks while VM is in a certain state
    """

    __test__ = True

    tcms_test_case = '334692'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
            assert vms.startVm(True, self.vm_name,
                               wait_for_status=config.VM_UP,
                               timeout=TIMEOUT_RESUME_VM)
            test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                      config.DATA_CENTER_NAME)

    def tearDown(self):
        """
        Remove the disks from the VM
        """
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
