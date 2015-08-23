#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for required network job
"""

import logging
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

logger = logging.getLogger("Required_Network_Helper")


def deactivate_hosts():
    """
    Set config.HOSTS[0] as SPM
    Deactivating all hosts in setup besides [config.VDS_HOSTS[0]
    """
    if not ll_hosts.checkHostSpmStatus(True, config.HOSTS[0]):
        logger.info("Set %s as SPM", config.HOSTS[0])
        if not ll_hosts.select_host_as_spm(
            True, config.HOSTS[0], config.DC_NAME[0]
        ):
            raise exceptions.NetworkException(
                "Failed to set %s as SPM" % config.HOSTS[0]
            )
    for host in config.HOSTS[1:]:
        if not ll_hosts.deactivateHost(True, host):
            raise exceptions.NetworkException(
                "Couldn't put %s into maintenance" % host
            )


def activate_hosts():
    """
    Activating all hosts in setup besides [config.VDS_HOSTS[0]
    """
    for host in config.HOSTS[1:]:
        if not ll_hosts.activateHost(True, host):
            logger.error("Couldn't set %s up", host)
