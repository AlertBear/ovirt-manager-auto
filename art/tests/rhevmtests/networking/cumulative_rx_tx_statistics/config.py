#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for cumulative_rx_tx_statistics
"""

import rhevmtests.networking.config as conf

HOST_IPS = None  # Filled in test
VM_IPS = None  # Filled in test
TOTAL_RX = None  # Filled in test
TOTAL_TX = None  # Filled in test
STAT_KEYS = ["data.total.rx", "data.total.tx"]
NIC_STAT = {
    STAT_KEYS[0]: 0,
    STAT_KEYS[1]: 0
}
NETWORK_0 = "rx_tx_net_0"
NETWORK_1 = "rx_tx_net_1"
NETWORK_2 = "rx_tx_net_2"
ETH0 = conf.VM_NICS[0]
BASIC_IP_DICT_NETMASK = {
    "ip_prefix": {
        "address": "",
        "netmask": "255.255.0.0",
        "boot_protocol": "static"
    }
}
