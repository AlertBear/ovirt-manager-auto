#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Int fault events
"""

from rhevmtests.networking.config import *  # NOQA

HOST_NICS = None  # Filled in setup_package
VDS_HOSTS_0 = VDS_HOSTS[0]
HOST_0 = HOSTS[0]
HOST_INTERFACE_STATE_UP = 609
HOST_INTERFACE_STATE_DOWN = 610
HOST_BOND_SLAVE_STATE_UP = 611
HOST_BOND_SLAVE_STATE_DOWN = 612
STATE_UP = "up"
STATE_DOWN = "down"
SAMPLER_TIMEOUT = 60
INT_SLEEP = 15
LABEL_0 = LABEL_LIST[0]
NETWORK_0 = NETWORKS[0]
DC_0 = DC_NAME[0]
CL_0 = CLUSTER_NAME[0]
BOND_0 = BOND[0]
HOST_0_IP = HOSTS_IP[0]
