#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for required network job
"""

import logging
from rhevmtests.networking import config
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.hosts import (
    deactivateHost, activateHost
)

logger = logging.getLogger("Required_Network_Helper")


def deactivate_hosts():
    """
    Deactivating all hosts in setup besides [config.VDS_HOSTS[0]
    """
    for host in config.HOSTS[1:]:
        if not deactivateHost(True, host):
            raise NetworkException(
                "Couldn't put %s into maintenance" % host
            )


def activate_hosts():
    """
    Activating all hosts in setup besides [config.VDS_HOSTS[0]
    """
    for host in config.HOSTS[1:]:
        if not activateHost(True, host):
            logger.error("Couldn't set %s up", host)
