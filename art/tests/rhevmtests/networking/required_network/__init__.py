"""
RequiredNetwork Test
"""

import logging
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import (
    create_basic_setup, remove_basic_setup
)
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("RequiredNetwork")


def setup_package():
    """
    Prepare the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        return

    logger.info("Create setup with datacenter, cluster and host")
    if not create_basic_setup(datacenter=config.DC_NAME[0],
                              storage_type=config.STORAGE_TYPE,
                              version=config.COMP_VERSION,
                              cluster=config.CLUSTER_NAME[0],
                              cpu=config.CPU_NAME, host=config.HOSTS[0],
                              host_password=config.HOSTS_PW):
        raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")
        return

    if not remove_basic_setup(datacenter=config.DC_NAME[0],
                              cluster=config.CLUSTER_NAME[0],
                              hosts=config.HOSTS[0]):
        raise NetworkException("Failed to remove setup")
