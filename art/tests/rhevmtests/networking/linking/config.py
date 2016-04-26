#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Linking tests
"""

import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(num_of_cases=1, num_of_objects=4)
VLAN_IDS = [str(i) for i in xrange(30, 34)]

VLAN_NET_DICT = {
    NETS[1][0]: {
        "vlan_id": VLAN_IDS[0],
        "required": "false",
        "nic": 1
    },
    NETS[1][1]: {
        "vlan_id": VLAN_IDS[1],
        "required": "false",
        "nic": 1
    },
    NETS[1][2]: {
        "vlan_id": VLAN_IDS[2],
        "required": "false",
        "nic": 1
    },
    NETS[1][3]: {
        "vlan_id": VLAN_IDS[3],
        "required": "false",
        "nic": 1
    },
}
