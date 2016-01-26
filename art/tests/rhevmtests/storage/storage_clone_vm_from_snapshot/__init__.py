"""
Base for setup the environment
This creates builds the environment in the systems plus VM for disks tests
"""
import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, safely_remove_vms,
)
from art.test_handler import exceptions
import config
import rhevmtests.storage.helpers as helpers

logger = logging.getLogger(__name__)

VM_NAMES = []


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
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['vmDescription'] = vm_name

        if not helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        VM_NAMES.append(vm_name)
        assert addSnapshot(True, vm_name, config.SNAPSHOT_NAME)


def teardown_package():
    """
    removes created datacenter, storages etc.
    """
    safely_remove_vms(VM_NAMES)
