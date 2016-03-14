#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Sanity init
"""

import helper
import logging
import rhevmtests.networking as network
from rhevmtests.networking.sanity import config as conf
import rhevmtests.networking.helper as networking_helper

logger = logging.getLogger("Network_Sanity_Init")


def setup_package():
    """
    Network cleanup
    Create dummy interfaces on host
    Enable ethtool and queues on engine
    Create networks in DC
    """
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_0_IP = conf.VDS_0_HOST.ip
    network.network_cleanup()
    networking_helper.prepare_dummies(
        host_resource=conf.VDS_0_HOST, num_dummy=20
    )
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    helper.engine_config_set_ethtool_and_queues()
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.SN_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )


def teardown_package():
    """
    Remove networks from DC
    Delete dummy interfaces from host
    """
    networking_helper.remove_networks_from_setup()
    networking_helper.delete_dummies(host_resource=conf.VDS_0_HOST)
