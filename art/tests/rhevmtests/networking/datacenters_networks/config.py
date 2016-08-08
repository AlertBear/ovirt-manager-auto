#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for datacenters networks
"""

import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=10, prefix="dcNetwork"
)
DATACENTER_NETWORKS_NET_DICT = {
    "description": "New network",
    "stp": True,
    "vlan_id": 500,
    "usages": [],
    "mtu": 5555
}
DATACENTER_NETWORKS_VERIFY_NET_LIST = [
    "description", "stp", "vlan_id", "usages", "mtu"
]

DATACENTER_NETWORKS_DC_NAMES = [
    "DataCenter_Network_DC1", "DataCenter_Network_DC2"
]
DC_0_NET_LIST = None  # Filled in test
DC_1_NET_LIST = None  # Filled in test
