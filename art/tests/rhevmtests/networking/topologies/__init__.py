#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Topologies Test
"""

import logging
import rhevmtests.networking as networking

logger = logging.getLogger("Topologies_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
