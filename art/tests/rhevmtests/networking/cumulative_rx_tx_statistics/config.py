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
BASIC_IP_DICT_NETMASK = {
    'host_1': {
        "ip_prefix": {
            "address": HOST_IPS[0],
            "netmask": "255.255.0.0",
        }
    },
    'host_2': {
        "ip_prefix": {
            "address": HOST_IPS[1],
            "netmask": "255.255.0.0",
        }
    }
}

CASE_1_NETS = {
    NETWORK_0: {
        "required": "false",
    },
}
CASE_2_NETS = {
    NETWORK_1: {
        "required": "false"
    },
    NETWORK_2: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    }
}

# vm_stats_test: test_update_nic
UPDATE_NIC = {
    'case_vm_1': {
        "network": NETWORK_2,
        "logger": "Change NIC name %s to %s" % (VM_NIC_NAME, NETWORK_2)
    },
    'case_vm_2': {
        "network": None,
        "logger": "Change NIC name %s to empty profile" % VM_NIC_NAME
    },
    'case_vm_3': {
        "plugged": False,
        "logger": "Unplug vNIC %s from VM %s" % (VM_NIC_NAME, conf.VM_1)
    },
    'case_vm_4': {
        "plugged": True,
        "logger": "Plug vNIC %s to VM %s" % (VM_NIC_NAME, conf.VM_1)
    },
}
