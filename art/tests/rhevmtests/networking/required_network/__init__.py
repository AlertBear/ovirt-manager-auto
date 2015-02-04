#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
RequiredNetwork Test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import (
    create_basic_setup, remove_basic_setup
)
from rhevmtests.networking.required_network.helper import(
    deactivate_hosts, activate_hosts
)

logger = logging.getLogger("Required_Network_Init")


def setup_package():
    """
    Prepare the environment
    """
    if config.GOLDEN_ENV:
        network_cleanup()
        logger.info("Running on golden env")
        logger.info("Deactivating all hosts besides %s", config.HOSTS[0])
        deactivate_hosts()

    else:
        logger.info("Create setup with datacenter, cluster and host")
        if not create_basic_setup(
            datacenter=config.DC_NAME[0], storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION, cluster=config.CLUSTER_NAME[0],
            cpu=config.CPU_NAME, host=config.HOSTS[0],
            host_password=config.HOSTS_PW
        ):
            raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")
        logger.info("Activating all hosts besides %s", config.HOSTS[0])
        activate_hosts()

    else:
        if not remove_basic_setup(
            datacenter=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            hosts=config.HOSTS[0]
        ):
            logger.error("Failed to remove setup")
