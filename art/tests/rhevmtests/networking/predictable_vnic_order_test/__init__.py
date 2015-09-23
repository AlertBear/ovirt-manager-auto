#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Predictable vNIC order feature test init
"""

import logging
import rhevmtests.networking as networking


logger = logging.getLogger("Predictable_vNIC_Order_Init")


def setup_package():
    """
    Running cleanup
    """
    networking.network_cleanup()
