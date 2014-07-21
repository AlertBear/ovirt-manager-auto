"""
Base for setup the environment
This creates builds the environment in the systems plus 2 VMs for disks tests
"""
import logging
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains, vms

from rhevmtests.storage.storage_full_disk_sanity import config

logger = logging.getLogger(__name__)


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    # Important:config has to be loaded here because how unittests plugin works
    logger.info("SETTING UP environment")
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE)

    from common import _create_vm
    logger.info("Creating two VMs for the tests environment")
    # TBD Use ThreadPOol to create Vms
    assert _create_vm(config.VM1_NAME, config.VIRTIO_BLK)
    assert vms.stopVm(True, vm=config.VM1_NAME)
    assert _create_vm(config.VM2_NAME, config.VIRTIO_BLK)
    assert vms.stopVm(True, vm=config.VM2_NAME)


def teardown_module():
    """
    removes created datacenter, storages etc.
    """
    # Important:config has to be loaded here because how unittests plugin works
    logger.info("TEARING DOWN - cleanDataCenter")
    storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)
