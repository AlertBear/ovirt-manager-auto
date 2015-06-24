#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Display of NIC Slave/Bond fault on RHEV-M Event Log feature test
"""

import logging
import config as c
from rhevmtests.networking import network_cleanup
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Int_Fault_Event_Init")


def setup_package():
    """
    Prepare environment
    """
    c.HOST_NICS = c.VDS_HOSTS_0.nics
    if c.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        network_cleanup()

    else:
        logger.info("Create setup with datacenter, cluster and host")
        if not hl_networks.create_basic_setup(
            datacenter=c.DC_NAME[0], storage_type=c.STORAGE_TYPE,
            version=c.COMP_VERSION, cluster=c.CLUSTER_NAME[0],
            cpu=c.CPU_NAME, host=c.HOSTS[0],
            host_password=c.HOSTS_PW
        ):
            raise exceptions.NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if c.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")

    else:
        if not hl_networks.remove_basic_setup(
            datacenter=c.DC_NAME[0], cluster=c.CLUSTER_NAME[0],
            hosts=c.HOSTS[0]
        ):
                logger.error("Failed to remove setup")
