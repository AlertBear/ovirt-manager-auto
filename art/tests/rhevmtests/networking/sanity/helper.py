#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for Sanity job
"""
import logging
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.hosts import getHostNicsList

logger = logging.getLogger("Sanity_Helper")


def check_dummy_on_host_interfaces(dummy_name):
    """
    Check if dummy interface if on host via engine
    :param dummy_name: Dummy name
    :type dummy_name: str
    :return: True/False
    :rtype: bool
    """
    host_nics = getHostNicsList(config.HOSTS[0])
    for nic in host_nics:
        if dummy_name == nic.name:
            return True
    return False
