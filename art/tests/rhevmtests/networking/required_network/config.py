#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for required_network test
"""

import rhevmtests.helpers as global_helper

NIC_STATE_DOWN = "down"
NIC_STATE_UP = "up"
VLAN_IDS = [str(i) for i in xrange(2, 20)]
NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10
)

NETS_DICT = {
    NETS[2][0]: {
        "required": "true",
        "usages": ""
    },
    NETS[3][0]: {
        "required": "true",
        "vlan_id": VLAN_IDS[0]
    },
}
