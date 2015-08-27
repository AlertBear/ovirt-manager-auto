#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Multiple gateways feature Init
"""

import logging
import rhevmtests.networking as networking


logger = logging.getLogger("Multiple_Gateway_Init")

#################################################


def setup_package():
    """
    running cleanup
    """
    networking.network_cleanup()
