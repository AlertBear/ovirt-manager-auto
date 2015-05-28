#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

from rhevmtests.networking.config import *  # NOQA
import art.unittest_lib.network as network_lib

HOST_NICS = None  # Filled in setup_package
VDS_HOSTS_0 = VDS_HOSTS[0]
HOST_0_IP = HOSTS_IP[0]
NET0 = NETWORKS[0]
VNET0 = VLAN_NETWORKS[0]
HOST_0 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER = CLUSTER_NAME[0]
NETWORKS = network_lib.generate_networks_names(20)
VDSMD_SERVICE = "vdsmd"
BASIC_IP_DICT = {
    "1": {
        "address": "1.1.1.1",
        "netmask": "255.255.255.0",
        "boot_protocol": "static"
    }
}
