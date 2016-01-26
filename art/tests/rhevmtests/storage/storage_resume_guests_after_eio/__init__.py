"""
Resume guests after storage domain error package
"""
import logging

from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler import exceptions
from rhevmtests.storage.storage_resume_guests_after_eio import config
from rhevmtests.storage.helpers import create_vm_or_clone

LOGGER = logging.getLogger(__name__)


def setup_package():
    """
    Prepares environment
    """
    for storage_type in config.STORAGE_SELECTOR:
        vm_name = "%s_%s" % (config.VM_NAME, storage_type)
        LOGGER.info("Creating VM %s" % vm_name)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['start'] = 'true'
        assert create_vm_or_clone(**vm_args)
        vms.waitForVMState(vm_name)


def teardown_package():
    """
    Cleans the environment
    """
    test_failed = False
    for storage_type in config.STORAGE_SELECTOR:
        vm_name = "%s_%s" % (config.VM_NAME, storage_type)
        if not vms.safely_remove_vms([vm_name]):
            LOGGER.error("Failed to remove vm %s", vm_name)
            test_failed = True
    if test_failed:
        raise exceptions.TearDownException("Test failed during teardown")
