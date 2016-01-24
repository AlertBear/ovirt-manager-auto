"""
Base for setting up the environment
This creates VMs for each of the storage types
"""
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions

logger = logging.getLogger(__name__)

VM_NAMES = []


def setup_package():
    """
    Creates VMs for each storage type and powers them off
    """
    import rhevmtests.storage.helpers as storage_helpers
    storage_helpers.storage_cleanup()
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]

        for vm_prefix in [config.VM1_NAME, config.VM2_NAME]:
            vm_name = vm_prefix % storage_type
            if not storage_helpers.create_vm(
                vm_name=vm_name, storage_domain=storage_domain,
                installation=False
            ):
                raise exceptions.VMException(
                    "Failed to create vm %s" % vm_name
                )
            VM_NAMES.append(vm_name)

    logger.info("Stopping vms %s", VM_NAMES)
    ll_vms.stop_vms_safely(VM_NAMES)


def teardown_package():
    """
    Powers off the VMs created (and any external instances that may have
    come up), then removed them
    """
    external = ["external-%s" % vm for vm in VM_NAMES]
    vm_names = filter(ll_vms.does_vm_exist, VM_NAMES + external)
    ll_vms.stop_vms_safely(vm_names)
    ll_vms.removeVms(True, vm_names)
    ll_jobs.wait_for_jobs([config.ENUMS['job_remove_vm']])
