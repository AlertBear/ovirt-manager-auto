#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for cumulative_rx_tx_statistics
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.networking.helper as net_helper

HOST_NET = NETWORKS[0]
VM_NET = NETWORKS[1]
EXTRA_NET = NETWORKS[2]
NIC_1 = NIC_NAME[1]
DC_0 = DC_NAME[0]
DC_3_5 = "DC_3_5"
CL_0 = CLUSTER_NAME[0]
CL_1 = CLUSTER_NAME[1]
CL_3_5 = "Stats_Cl_3_5"
HOST_0_NAME = None  # Filled in setup_package
VM_0 = VM_NAME[0]
VM_1 = VM_NAME[1]
VM_IPS = net_helper.create_random_ips()
HOST_IPS = net_helper.create_random_ips()
STAT_KEYS = ["data.total.rx", "data.total.tx"]
ETH0 = VM_NICS[0]
HOST_0_NIC_1 = None  # Filled in setup_package
BASIC_IP_DICT_NETMASK = {
    "ip_prefix": {
        "address": "",
        "netmask": "255.255.0.0",
        "boot_protocol": "static"
    }
}
