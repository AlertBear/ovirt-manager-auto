#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network labels feature test
"""
import logging
import rhevmtests.networking as networking


logger = logging.getLogger("Network_Labels_Init")

# ################################################


def setup_package():
    """
   Running cleanup
    """
    networking.network_cleanup()
