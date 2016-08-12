"""
-----------------
test_vms
-----------------

@author: Nelly Credi
"""

import logging

from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import vms as ll_vm

from rhevmtests import config

logger = logging.getLogger(__name__)


class TestCaseVM(TestCase):
    """
    vm tests
    """
    __test__ = True

    vm_name = config.VM_NAME[0]
    storage_name = config.STORAGE_NAME[0]

    @attr(tier=2)
    def test_add_disk_to_vm_wrong_format(self):
        """
        Negative - verify vm functionality
        add disk to vm with wrong format & verify failure
        """
        logger.info('Add disk to vm - wrong format')
        status = ll_vm.addDisk(
            positive=False, vm=self.vm_name, provisioned_size=2147483648,
            storagedomain=self.storage_name,
            type=config.ENUMS['disk_type_system'],
            format='bad_config', interface=config.ENUMS['interface_virtio']
        )
        assert status, 'Add disk to vm - wrong format'

    @attr(tier=2)
    def test_add_disk_to_vm_wrong_interface(self):
        """
        Negative - verify vm functionality
        add disk to vm with wrong interface & verify failure
        """
        logger.info('Add disk to vm - wrong interface')
        status = ll_vm.addDisk(
            positive=False, vm=self.vm_name, provisioned_size=2147483648,
            interface='bad_config', storagedomain=self.storage_name,
            type=config.ENUMS['disk_type_system'],
            format=config.ENUMS['format_cow']
        )
        assert status, 'Add disk to vm - wrong interface'

    @attr(tier=1)
    def test_add_remove_disk(self):
        """
        Positive - verify vm functionality
        add disk to vm & remove it
        """
        logger.info('Add disk to vm')
        status = ll_vm.addDisk(
            positive=True, vm=self.vm_name, provisioned_size=2147483648,
            alias='test_disk', interface=config.ENUMS['interface_virtio'],
            storagedomain=self.storage_name,
            type=config.ENUMS['disk_type_system'],
            format=config.ENUMS['format_cow']
        )
        assert status, 'Add disk to vm'
        logger.info('Remove disk from vm')
        status = ll_vm.removeDisk(
            positive=True, vm=self.vm_name, disk='test_disk'
        )
        assert status, 'Failed to remove disk from vm'
