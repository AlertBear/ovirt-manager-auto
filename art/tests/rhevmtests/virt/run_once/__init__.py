"""
Virt - Run Once Test
Check all the menu options in run vm once.
"""

import logging
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors

logger = logging.getLogger("RUN ONCE")
#################################################


def setup_package():
    """
    Prepare environment for Run Once test
    """
    logger.info(
        "attach and activate %s storage domain", config.SHARED_ISO_DOMAIN_NAME
    )
    if not hl_storagedomains.attach_and_activate_domain(
            config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME
    ):
        raise errors.StorageDomainException(
            "Failed to attach and deactivate storage domain %s"
            % config.SHARED_ISO_DOMAIN_NAME
        )
    logger.info("Create VM %s without disk", config.VM_RUN_ONCE)
    if not ll_vms.createVm(
            positive=True,
            vmName=config.VM_RUN_ONCE,
            vmDescription="run once vm",
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            size=2 * config.GB, nic=config.NIC_NAME[0],
            memory=config.GB,
            network=config.MGMT_BRIDGE,
            os_type=config.VM_OS_TYPE,
            display_type=config.VM_DISPLAY_TYPE,
            type=config.VM_TYPE
    ):
        raise errors.VMException("Failed to create vm")


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Teardown...")
    logger.info("detach and deactivate %s", config.SHARED_ISO_DOMAIN_NAME)
    if not hl_storagedomains.detach_and_deactivate_domain(
            config.DC_NAME[0], config.SHARED_ISO_DOMAIN_NAME
    ):
        logger.error(
            "Failed to detach and deactivate storage domain %s",
            config.SHARED_ISO_DOMAIN_NAME
        )
    logger.info("remove vm %s", config.VM_RUN_ONCE)
    if not ll_vms.removeVm(True, config.VM_RUN_ONCE):
        logger.error("Failed to remove vm %s", config.VM_RUN_ONCE)
