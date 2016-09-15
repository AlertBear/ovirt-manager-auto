#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
DOCS
"""

import rhevmtests.helpers as global_helper

BRIDGELESS_VLAN_IDS = [str(i) for i in xrange(2, 4)]
BRIDGELESS_NETS = global_helper.generate_object_names(
    num_of_cases=4, num_of_objects=3, prefix="br"
)

BRIDGELESS_NET_DICT = {
    BRIDGELESS_NETS[1][0]: {
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[2][0]: {
        "vlan_id": BRIDGELESS_VLAN_IDS[0],
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[3][0]: {
        "vlan_id": BRIDGELESS_VLAN_IDS[1],
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[4][0]: {
        "required": "false",
        "usages": ""
    }
}
