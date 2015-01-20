"""
DataCenter Networks feature test
"""
import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.high_level.networks import(
    create_basic_setup, remove_basic_setup
)
from art.test_handler.exceptions import NetworkException
logger = logging.getLogger("DC_Networks_Init")
#################################################
DC_NAMES = [config.DC_NAME[0], "DC_NET_DC2"]


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        network_cleanup()
        if not create_basic_setup(
                datacenter=DC_NAMES[1],
                storage_type=config.STORAGE_TYPE,
                version=config.COMP_VERSION
        ):
            raise NetworkException("Failed to create setup")

    else:
        for dc in DC_NAMES:
            logger.info("Create datacenter %s", dc)
            if not create_basic_setup(
                    datacenter=dc,
                    storage_type=config.STORAGE_TYPE,
                    version=config.COMP_VERSION
            ):
                raise NetworkException(
                    "Failed to create setup for DC %s" % dc
                )


def teardown_package():
    """
    Cleans environment
    """
    if config.GOLDEN_ENV:
        if not remove_basic_setup(datacenter=DC_NAMES[1]):
            logger.error("Cannot remove DC")

    else:
        for dc in DC_NAMES:
            if not remove_basic_setup(datacenter=dc):
                logger.error("Cannot remove DCs")
