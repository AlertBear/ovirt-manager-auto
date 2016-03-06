#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
RequiredNetwork init
"""

import helper
import logging
import config as conf
from rhevmtests import networking
import rhevmtests.networking.helper as networking_helper

logger = logging.getLogger("Required_Network_Init")


def setup_package():
    """
    Prepare the environment
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    networking.network_cleanup()
    logger.info("Deactivating all hosts besides %s", conf.HOSTS[0])
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )
    helper.deactivate_hosts()


def teardown_package():
    """
    Activate all hosts
    """
    logger.info("Activating all hosts besides %s", conf.HOSTS[0])
    helper.activate_hosts()
