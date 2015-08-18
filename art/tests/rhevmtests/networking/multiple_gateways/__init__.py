#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Multiple gateways feature Init
"""

import logging

import rhevmtests.networking.config as config
import rhevmtests.networking as networking
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.high_level.networks as hl_networks


logger = logging.getLogger("Multiple_Gateway_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if not config.GOLDEN_ENV:
        logger.info(
            "Create setup 1 with datacenter %s, cluster %s and host %s",
            config.DC_NAME[0], config.CLUSTER_NAME[0], config.HOSTS[0]
        )
        if not hl_networks.create_basic_setup(
            datacenter=config.DC_NAME[0], storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION, cluster=config.CLUSTER_NAME[0],
            cpu=config.CPU_NAME, host=config.HOSTS[0],
            host_password=config.HOSTS_PW
        ):
            raise exceptions.NetworkException("Failed to create setup")

    else:
        logger.info("Running on golden env, no setup")
        networking.network_cleanup()


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env")

    else:
        logger.info("Removing DC/Cluster and host")
        if not hl_networks.remove_basic_setup(
            datacenter=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            hosts=config.HOSTS[0]
        ):
            logger.error("Failed to remove setup")
