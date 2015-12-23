"""
DataCenter Networks feature test
"""
import logging
import config as conf
import rhevmtests.networking as networking
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("DC_Networks_Init")


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    logger.info("Create basic setup")
    if not hl_networks.create_basic_setup(
        datacenter=conf.DC_NAMES[1], storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create %s on setup" % conf.DC_NAMES[1]
        )


def teardown_package():
    """
    Cleans environment
    """
    logger.info("Remove basic setup")
    if not hl_networks.remove_basic_setup(datacenter=conf.DC_NAMES[1]):
        logger.error("Cannot remove %s", conf.DC_NAMES[1])
