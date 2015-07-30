#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Management network as a role feature init
"""
from rhevmtests.networking import network_cleanup


def setup_package():
    """
    Clean environment
    """
    network_cleanup()
