#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for arbitrary_vlan_device_name
"""

import rhevmtests.helpers as global_helper
import random

ARBITRARY_NETS = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=3, prefix="avdn_net"
)
VLAN_NAMES = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=6, prefix="avdn_vlan_"
)
BRIDGE_NAMES = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=6, prefix="avdn_br_"
)
ARBITRARY_VLAN_IDS_CASE_1 = [str(i) for i in random.sample(xrange(2, 20), 2)]
ARBITRARY_VLAN_IDS_CASE_2 = [str(i) for i in random.sample(xrange(30, 50), 6)]
ARBITRARY_VLAN_IDS_CASE_3 = [str(i) for i in random.sample(xrange(60, 90), 4)]
ARBITRARY_NET_DICT = {
    ARBITRARY_NETS[3][0]: {
        "vlan_id": ARBITRARY_VLAN_IDS_CASE_3[2],
        "required": "false",
    },
    ARBITRARY_NETS[3][1]: {
        "vlan_id": ARBITRARY_VLAN_IDS_CASE_3[3],
        "required": "false",
        "usages": ""
    }
}
