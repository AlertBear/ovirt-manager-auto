#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Management network as a role feature init
"""
import config as conf
from rhevmtests.networking import network_cleanup


def setup_package():
    """
    Clean environment
    """
    conf.LAST_HOST = conf.HOSTS[-1]
    network_cleanup()
