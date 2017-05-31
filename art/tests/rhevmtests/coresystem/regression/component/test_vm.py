"""
-----------------
test_vms
-----------------
"""
from art.unittest_lib import (
    attr, testflow,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import vms as ll_vm

from rhevmtests.config import (
    ENUMS as enums,
    STORAGE_NAME as storages_names,
    VM_NAME as vms_names
)


class TestCaseVM(TestCase):
    """
    vm tests
    """
    BAD_CONFIG = "bad_config"

    alias = "test_disk"
    disk_format = enums["format_cow"]
    disk_type = enums["disk_type_system"]
    interface = enums["interface_virtio"]
    vm_name = vms_names[0]
    storage_name = storages_names[0]
    provisioned_size = 2147483648

    @attr(tier=2)
    def test_add_disk_to_vm_wrong_format(self):
        """
        Negative - verify vm functionality
        add disk to vm with wrong format & verify failure
        """
        testflow.step('Add disk to vm - wrong format')
        assert ll_vm.addDisk(
            positive=False,
            vm=self.vm_name,
            provisioned_size=self.provisioned_size,
            storagedomain=self.storage_name,
            type=self.disk_type,
            format=self.BAD_CONFIG,
            interface=self.interface
        )

    @attr(tier=2)
    def test_add_disk_to_vm_wrong_interface(self):
        """
        Negative - verify vm functionality
        add disk to vm with wrong interface & verify failure
        """
        testflow.step('Add disk to vm - wrong interface')
        assert ll_vm.addDisk(
            positive=False,
            vm=self.vm_name,
            provisioned_size=self.provisioned_size,
            interface=self.BAD_CONFIG,
            storagedomain=self.storage_name,
            type=self.disk_type,
            format=self.disk_format
        )

    @attr(tier=1)
    def test_add_remove_disk(self):
        """
        Positive - verify vm functionality
        add disk to vm & remove it
        """
        testflow.step('Add disk to vm')
        assert ll_vm.addDisk(
            positive=True,
            vm=self.vm_name,
            provisioned_size=self.provisioned_size,
            alias=self.alias,
            interface=self.interface,
            storagedomain=self.storage_name,
            type=self.disk_type,
            format=self.disk_format
        )

        testflow.step('Remove disk from vm')
        assert ll_vm.removeDisk(
            positive=True,
            vm=self.vm_name,
            disk=self.alias
        )
