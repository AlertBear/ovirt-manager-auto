"""
Base for setup the environment
This creates builds the environment in the systems plus VM for disks tests
"""
import logging
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import addSnapshot, stopVm

from rhevmtests.storage.storage_clone_vm_from_snapshot import config
from common import _create_vm

logger = logging.getLogger(__name__)


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    logger.info("SETTING UP environment")
    build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DC_TYPE, basename=config.TESTNAME)

    logger.info("Creating VM for the tests environment")
    assert _create_vm(config.VM_NAME[0], config.VIRTIO_BLK)
    assert stopVm(True, vm=config.VM_NAME[0])
    assert addSnapshot(True, config.VM_NAME[0], config.SNAPSHOT_NAME)


def teardown_module():
    """
    removes created datacenter, storages etc.
    """
    logger.info("TEARING DOWN - cleanDataCenter")
    cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)
