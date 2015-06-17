"""
Base for setup the environment
This creates builds the environment in the systems plus 2 VMs for disks tests
"""
import logging
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains, vms

from rhevmtests.storage.storage_full_disk_sanity import config

logger = logging.getLogger(__name__)

from common import create_vm

VM_NAMES = []


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        logger.info("Setting up environment")
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE)

    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]

        for vm_prefix in [config.VM1_NAME, config.VM2_NAME]:
            vm_name = vm_prefix % storage_type
            assert create_vm(
                vm_name=vm_name, disk_interface=config.VIRTIO_BLK,
                storage_domain=storage_domain
            )
            VM_NAMES.append(vm_name)

    logger.info("Stopping vms %s", VM_NAMES)
    vms.stop_vms_safely(VM_NAMES)


def teardown_module():
    """
    removes created datacenter, storages etc.
    """
    external = ["external-%s" % vm for vm in VM_NAMES]
    vm_names = filter(vms.does_vm_exist, VM_NAMES + external)
    vms.stop_vms_safely(vm_names)
    vms.removeVms(True, vm_names)

    if not config.GOLDEN_ENV:
        logger.info("Tear down - cleanDataCenter")
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
