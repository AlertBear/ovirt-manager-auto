"""
DataCenter Networks feature test
"""
import logging
from rhevmtests import config
from art.rhevm_api.tests_lib.high_level.networks import create_basic_setup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.datacenters import removeDataCenter
logger = logging.getLogger("Datacenter_Networks")
#################################################


def setup_package():
    """
    Prepare environment
    """
    for i in range(2):
        logger.info("Create datacenters,")
        if not create_basic_setup(datacenter=config.DC_NAME[i],
                                  storage_type=config.STORAGE_TYPE,
                                  version=config.COMP_VERSION):
            raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans environment
    """
    if not (removeDataCenter(positive=True, datacenter=config.DC_NAME[0]) and
            removeDataCenter(positive=True, datacenter=config.DC_NAME[1])):
        raise NetworkException("Cannot remove DCs")
