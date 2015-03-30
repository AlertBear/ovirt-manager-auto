"""
Base for setup the environment
This creates builds the environment in the systems plus VM for disks tests
"""
import logging
from art.rhevm_api.tests_lib.high_level.datacenters import (
    build_setup,
    clean_datacenter,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, stopVm, safely_remove_vms,
)

from rhevmtests.storage.storage_clone_vm_from_snapshot import config
from common import _create_vm

logger = logging.getLogger(__name__)

VM_NAMES = []


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        logger.info("Setting up environment")
        build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.DC_TYPE, basename=config.TESTNAME)

    logger.info("Creating VM for the tests environment")
    for storage_type in config.STORAGE_SELECTOR:
        vm_name = config.VM_NAME % storage_type
        logger.info("Creating VM %s" % vm_name)
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]
        assert _create_vm(vm_name, config.VIRTIO_BLK,
                          storage_domain_name=storage_domain)
        VM_NAMES.append(vm_name)
        assert stopVm(True, vm=vm_name)
        assert addSnapshot(True, vm_name, config.SNAPSHOT_NAME)


def teardown_module():
    """
    removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        logger.info("Tearing down - cleanDataCenter")
        clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
    else:
        safely_remove_vms(VM_NAMES)
