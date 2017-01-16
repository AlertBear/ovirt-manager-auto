#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
DOCS
"""

import rhevmtests.helpers as global_helper

BRIDGELESS_VLAN_IDS = [str(i) for i in xrange(2, 4)]
BRIDGELESS_NETS = global_helper.generate_object_names(
    num_of_cases=4, num_of_objects=3, prefix="bridge_net"
)
BOND_1 = "bond01"
BOND_2 = "bond02"

# parameters for test parametrize, network and host NIC index or bond
CASE_1 = [BRIDGELESS_NETS[1][0], 1]
CASE_2 = [BRIDGELESS_NETS[2][0], 2]
CASE_3 = [BRIDGELESS_NETS[3][0], BOND_1]
CASE_4 = [BRIDGELESS_NETS[4][0], BOND_2]

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
