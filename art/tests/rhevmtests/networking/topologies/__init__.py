#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Topologies Test
"""

import logging
from rhevmtests import networking

logger = logging.getLogger("Topologies_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
