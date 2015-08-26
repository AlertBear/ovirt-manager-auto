"""
DataCenter Networks feature test
"""
import logging
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.test_handler.exceptions as exceptions

logger = logging.getLogger("DC_Networks_Init")
#################################################
DC_NAMES = [config.DC_NAME[0], "DC_NET_DC2"]


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    logger.info("Create basic setup")
    if not hl_networks.create_basic_setup(
        datacenter=DC_NAMES[1],
        storage_type=config.STORAGE_TYPE,
        version=config.COMP_VERSION
    ):
        raise exceptions.NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans environment
    """
    logger.info("Remove basic setup")
    if not hl_networks.remove_basic_setup(datacenter=DC_NAMES[1]):
        logger.error("Cannot remove DC")
