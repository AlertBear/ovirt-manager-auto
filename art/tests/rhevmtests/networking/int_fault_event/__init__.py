#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Display of NIC Slave/Bond fault on RHEV-M Event Log feature test
"""

import logging
import config as config
import rhevmtests.networking as networking

logger = logging.getLogger("Int_Fault_Event_Init")


def setup_package():
    """
    Running cleanup
    """
    config.HOST_NICS = config.VDS_HOSTS_0.nics
    networking.network_cleanup()
