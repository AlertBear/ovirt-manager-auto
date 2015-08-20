#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for cumulative_rx_tx_statistics
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.networking.helper as net_helper

NET_0 = NETWORKS[0]
NET_1 = NETWORKS[1]
NIC_1 = NIC_NAME[1]
DC_0 = DC_NAME[0]
DC_3_5 = "DC_3_5"
CL_0 = CLUSTER_NAME[0]
CL_1 = CLUSTER_NAME[1]
CL_3_5 = "Stats_Cl_3_5"
LAST_HOST = HOSTS[-1]
VM_ON_CL1 = VM_NAME[-2]
VM_ON_CL2 = VM_NAME[-1]
VM_IPS = net_helper.create_random_ips()
HOST_IPS = net_helper.create_random_ips()
STAT_KEYS = ["data.total.rx", "data.total.tx"]
ETH0 = VM_NICS[0]
HOST_4_NIC_1 = VDS_HOSTS[-1].nics[1]

BASIC_IP_DICT_PREFIX = {
    "ip_prefix": {
        "address": "",
        "netmask": "16",
        "boot_protocol": "static"
    }
}
