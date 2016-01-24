"""
Base for setup the environment
This creates builds the environment in the systems plus VM for disks tests
"""
import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, stopVm, safely_remove_vms,
)
from art.test_handler import exceptions
import config
import rhevmtests.storage.helpers as helpers

logger = logging.getLogger(__name__)

VM_NAMES = []

vm_args = {
    'positive': True,
    'vmDescription': config.VM_NAME % "description",
    'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK,
    'cluster': config.CLUSTER_NAME,
    'storageDomainName': None,
    'installation': False,
    'size': config.VM_DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'useAgent': True,
    'os_type': config.OS_TYPE,
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
    'image': config.COBBLER_PROFILE,
}


def setup_package():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = config.VM_NAME % storage_type

        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['vmDescription'] = vm_name

        if not helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        VM_NAMES.append(vm_name)
        assert stopVm(True, vm=vm_name)
        assert addSnapshot(True, vm_name, config.SNAPSHOT_NAME)


def teardown_package():
    """
    removes created datacenter, storages etc.
    """
    safely_remove_vms(VM_NAMES)
