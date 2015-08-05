#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Init for new host network API
"""

import helper
import logging
import config as conf
import rhevmtests.networking as networking
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Host_Network_API_Init")


def setup_package():
    """
    Prepare environment
    """
    conf.HOST_1_NICS = conf.VDS_HOSTS_1.nics
    conf.HOST_4_NICS = conf.VDS_HOSTS_4.nics
    logger.info("Running network cleanup")
    networking.network_cleanup()
    for host in (conf.VDS_HOSTS_1, conf.VDS_HOSTS_4):
        logger.info(
            "Creating %s dummy interfaces on %s", conf.NUM_DUMMYS, host
        )
        if not hl_networks.create_dummy_interfaces(
            host=host, num_dummy=conf.NUM_DUMMYS
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create dummy interfaces on %s" % host
            )
    for host in (conf.HOST_1, conf.HOST_4):
        helper.check_dummy_on_host(host=host)

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
    for host in (conf.VDS_HOSTS_1, conf.VDS_HOSTS_4):
        logger.info("Delete all dummy interfaces on %s", host)
        if not hl_networks.delete_dummy_interfaces(host=host):
            logger.error("Failed to delete dummy interfaces on %s", host)

    for host in (conf.HOST_1, conf.HOST_4):
        helper.check_dummy_on_host(host=host, positive=False)
