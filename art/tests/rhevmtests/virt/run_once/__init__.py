"""
Virt - Run Once Test
Check all the menu options in run vm once.
"""

import logging
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
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
            "Failed to deatch and deactivate storage domain %s",
            config.SHARED_ISO_DOMAIN_NAME
        )
