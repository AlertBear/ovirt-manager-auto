#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Management network as a role feature init
"""

import config as conf
from rhevmtests import networking


def setup_package():
    """
    Network cleanup
    """
    conf.HOST_1_NAME = conf.HOSTS[1]
    conf.VDS_1_HOST = conf.VDS_HOSTS[1]
    networking.network_cleanup()
