"""
Adding Disk to a VM which is not down adds a Disk that is activated tests
"""
import logging
import pytest
import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.unittest_lib import attr, StorageTest as TestCase, testflow
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    create_vm, delete_disks, poweroff_vm,
)

logger = logging.getLogger(__name__)


class VmWithOs(TestCase):
    """
    Prepare a VM with an OS installed
    """
    __test__ = False
    polarion_test_case = None

    def attach_new_disk(
        self, polarion_case, vm_name, should_be_active=True,
        storage_domain=None, **permutation
    ):
        """
        Add a new disk, the disk status should match should_be_active input
        """
        disk_alias = "%s_%s_%s_%s_%s_disk" % (
            polarion_case,
            vm_name,
            permutation["interface"],
            permutation["format"],
            permutation["sparse"]
        )
        disk_args = {
            "interface": permutation["interface"],
            "sparse": permutation["sparse"],
            "alias": disk_alias,
            "format": permutation["format"],
            "active": should_be_active,
            "storagedomain": storage_domain
        }

        assert ll_vms.addDisk(True, vm_name, config.GB, **disk_args)
        ll_disks.wait_for_disks_status(disk_args["alias"])
        self.disks_to_remove.append(disk_args["alias"])

        disk_obj = ll_disks.getVmDisk(vm_name, disk_alias)
        active = ll_vms.is_active_disk(vm_name, disk_obj.get_id())
        logger.info("Disk '%s' has status of '%s'", disk_alias, active)
        logger.info(
            "Disk Status is %s, expected disk status is %s",
            active, should_be_active
        )
        # Compare the actual and expected disk status
        if active == should_be_active:
            logger.info("Actual disk status matches the expected disk status")
            return True

        logger.info(
            "Actual disk status does not match the expected disk status"
        )
        return False

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

        assert self.attach_new_disk(
            self.polarion_test_case, self.vm_name, activate_expected_status,
            self.storage_domain, **permutation
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    delete_disks.__name__,
)
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
        for permutation in ll_disks.get_all_disk_permutation(
            (self.storage in config.BLOCK_TYPES),
            interfaces=storage_helpers.INTERFACES
        ):
            testflow.step(
                "Adding disk %s %s %s", permutation["interface"],
                permutation["sparse"], permutation["format"],
            )
            self.attach_new_disk(
                self.polarion_test_case, self.vm_name, True,
                self.storage_domain, **permutation
            )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    delete_disks.__name__,
)
class TestCase4937(VmWithOs):
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
        for permutation in ll_disks.get_all_disk_permutation(
            (self.storage in config.BLOCK_TYPES),
            interfaces=storage_helpers.INTERFACES
        ):
            logger.info("Stopping vm %s", self.vm_name)
            assert ll_vms.stopVm(True, self.vm_name)
            testflow.step(
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
        for permutation in ll_disks.get_all_disk_permutation(
            (self.storage in config.BLOCK_TYPES),
            interfaces=storage_helpers.INTERFACES
        ):
            testflow.step(
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
    @pytest.mark.usefixtures(poweroff_vm.__name__)
    def test_attach_new_disk_suspend(self):
        """
        Attach different types of disks while the vm is suspended
        """
        for permutation in ll_disks.get_all_disk_permutation(
            (self.storage in config.BLOCK_TYPES),
            interfaces=storage_helpers.INTERFACES
        ):
            testflow.step(
                "Adding disk %s %s %s", permutation['interface'],
                permutation['sparse'], permutation['format'])
            self.attach_new_disk_while_status(
                config.VM_SUSPEND,
                config.VM_SUSPENDED,
                activate_expected_status=False,
                **permutation
            )
