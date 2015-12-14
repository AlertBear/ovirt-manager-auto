#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics Init
"""

import logging
import config as conf
from rhevmtests import networking

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Init")


def setup_package():
    """
    Run network cleanup
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_0_NIC_1 = conf.VDS_HOSTS[0].nics[1]
    networking.network_cleanup()
