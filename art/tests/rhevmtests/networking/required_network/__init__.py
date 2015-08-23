#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
RequiredNetwork Test
"""

import logging
import rhevmtests.networking.config as config
import rhevmtests.networking as networking
import helper

logger = logging.getLogger("Required_Network_Init")


def setup_package():
    """
    Prepare the environment
    """
    networking.network_cleanup()
    logger.info("Deactivating all hosts besides %s", config.HOSTS[0])
    helper.deactivate_hosts()


def teardown_package():
    """
    Activate all hosts
    """
    logger.info("Activating all hosts besides %s", config.HOSTS[0])
    helper.activate_hosts()
