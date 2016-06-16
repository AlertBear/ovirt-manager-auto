#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Linking tests
"""

VLAN_IDS = [str(i) for i in xrange(30, 34)]
NET_1 = "linking_net_1"
NET_2 = "linking_net_2"
NET_3 = "linking_net_3"
NET_4 = "linking_net_4"
NET_5 = "linking_net_5"
NET_LIST = [NET_1, NET_2, NET_3, NET_4]

VLAN_NET_DICT = {
    NET_1: {
        "vlan_id": VLAN_IDS[0],
        "required": "false",
        "nic": 1
    },
    NET_2: {
        "vlan_id": VLAN_IDS[1],
        "required": "false",
        "nic": 1
    },
    NET_3: {
        "vlan_id": VLAN_IDS[2],
        "required": "false",
        "nic": 1
    },
    NET_4: {
        "vlan_id": VLAN_IDS[3],
        "required": "false",
        "nic": 1
    },
}
