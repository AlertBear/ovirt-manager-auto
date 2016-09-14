#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for cumulative_rx_tx_statistics
"""

import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

HOST_IPS = network_helper.create_random_ips(base_ip_prefix="6")
VM_IPS = network_helper.create_random_ips()
TOTAL_RX = None  # Filled in test
TOTAL_TX = None  # Filled in test
VM_NIC_NAME = "rx-tx-vnic"
VMS_IPS_PARAMS = dict()
STAT_KEYS = ["data.total.rx", "data.total.tx"]
NIC_STAT = {
    STAT_KEYS[0]: 0,
    STAT_KEYS[1]: 0
}
NETWORK_0 = "rx_tx_host_net"
NETWORK_1 = "rx_tx_vm_net_1"
NETWORK_2 = "rx_tx_vm_net_2"
ETH0 = conf.VM_NICS[0]
BASIC_IP_DICT_NETMASK = {
    "ip_prefix": {
        "address": "",
        "netmask": "255.255.0.0",
        "boot_protocol": "static"
    }
}

NET_DICT = {
    NETWORK_0: {
        "required": "false",
    },
    NETWORK_1: {
        "required": "false"
    },
    NETWORK_2: {
        "required": "false",
        "vlan_id": 2
    }
}
