#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network labels feature test
"""
import logging
from rhevmtests.networking import config, network_cleanup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import(
    create_basic_setup, remove_basic_setup
)

logger = logging.getLogger("Network_Labels_Init")

# ################################################


def setup_package():
    """
    Prepare environment:
    create 1 Data Center
    create 1 Cluster
    add 2 Hosts
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        network_cleanup()

    else:
        logger.info("Create setup with datacenter, cluster and host")
        if not create_basic_setup(
            datacenter=config.DC_NAME[0], storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION, cluster=config.CLUSTER_NAME[0],
            cpu=config.CPU_NAME, host=config.HOSTS,
            host_password=config.HOSTS_PW
        ):
            raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans environment by removing Host, Cluster and DC from the setup
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")

    else:
        if not remove_basic_setup(
            datacenter=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            hosts=config.HOSTS
        ):
            logger.error("Couldn't remove setup ")
