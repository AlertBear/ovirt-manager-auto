#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Init for new host network API
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Network/3_6_Network_Host_Network_API
"""

import logging
import config as conf
from rhevmtests import networking
from art.rhevm_api.utils import test_utils
import rhevmtests.networking.helper as network_helper
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts


logger = logging.getLogger("Host_Network_API_Init")


def setup_package():
    """
    Run network cleanup
    Create dummy interfaces on host
    Set ethtool support in engine
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    networking.network_cleanup()
    network_helper.prepare_dummies(
        host_resource=conf.VDS_0_HOST, num_dummy=conf.NUM_DUMMYS
    )

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
    Delete dummy interfaces
    Activate host if needed
    """
    network_helper.delete_dummies(host_resource=conf.VDS_0_HOST)
    hl_hosts.activate_host_if_not_up(conf.HOST_0_NAME)
