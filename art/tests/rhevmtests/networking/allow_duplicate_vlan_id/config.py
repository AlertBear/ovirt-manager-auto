#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Config for allow duplicate VLAN ID
"""

# test_allow_duplicate_vlan_id
ALLOW_DUPLICATE_VLAN_ID_NET_1 = "allow_vdup_net1"
ALLOW_DUPLICATE_VLAN_ID_NET_2 = "allow_vdup_net2"
ALLOW_DUPLICATE_VLAN_ID_VLAN = 4093
ALLOW_DUPLICATE_VLAN_ID_CREATE_NETWORKS = {
    ALLOW_DUPLICATE_VLAN_ID_NET_1: {
        "required": "false",
        "vlan_id": ALLOW_DUPLICATE_VLAN_ID_VLAN

    },
    ALLOW_DUPLICATE_VLAN_ID_NET_2: {
        "required": "false",
        "vlan_id": ALLOW_DUPLICATE_VLAN_ID_VLAN

    }
}
ALLOW_DUPLICATE_VLAN_ID_SN_DICT = {
    "add": {
        "1": {
            "network": ALLOW_DUPLICATE_VLAN_ID_NET_1,
            "nic": None

        },
        "2": {
            "network": ALLOW_DUPLICATE_VLAN_ID_NET_2,
            "nic": None

        }
    }
}
