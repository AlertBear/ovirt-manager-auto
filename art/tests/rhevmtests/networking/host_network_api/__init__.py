#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Init for new host network API
"""

import helper
import logging
import config as conf
from rhevmtests import networking
from art.rhevm_api.utils import test_utils
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Host_Network_API_Init")


def setup_package():
    """
    Prepare environment
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    logger.info("Running network cleanup")
    networking.network_cleanup()
    logger.info(
        "Creating %s dummy interfaces on %s",
        conf.NUM_DUMMYS, conf.VDS_0_HOST
    )
    if not hl_networks.create_dummy_interfaces(
        host=conf.VDS_0_HOST, num_dummy=conf.NUM_DUMMYS
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create dummy interfaces on %s" % conf.HOST_0_NAME
        )
    helper.check_dummy_on_host(host=conf.HOST_0_NAME)

    logger.info(
        "Configuring engine to support ethtool opts for %s version",
        conf.COMP_VERSION
    )
    cmd = [
        "UserDefinedNetworkCustomProperties=ethtool_opts=.*",
        "--cver=%s" % conf.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        raise conf.NET_EXCEPTION("Failed to set ethtool via engine-config")


def teardown_package():
    """
    Cleans environment
    """
    logger.info("Delete all dummy interfaces on %s", conf.VDS_0_HOST)
    if not hl_networks.delete_dummy_interfaces(host=conf.VDS_0_HOST):
        logger.error(
            "Failed to delete dummy interfaces on %s", conf.VDS_0_HOST
        )
    helper.check_dummy_on_host(host=conf.HOST_0_NAME, positive=False)
    logger.info("Activating %s", conf.HOST_0_NAME)
    if not hl_hosts.activate_host_if_not_up(conf.HOST_0_NAME):
        logger.error("Failed to activate %s", conf.HOST_0_NAME)
