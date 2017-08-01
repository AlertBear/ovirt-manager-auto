#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
DOCS
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

BRIDGELESS_NETS = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=5, prefix="bridge_net"
)
BOND_1 = "bond01"
BOND_2 = "bond02"

# parameters for test parametrize, network and host NIC index or bond
CASE_1 = [BRIDGELESS_NETS[1][0], 1]
CASE_2 = [BRIDGELESS_NETS[1][1], 2]
CASE_3 = [BRIDGELESS_NETS[1][2], BOND_1]
CASE_4 = [BRIDGELESS_NETS[1][3], BOND_2]

CASE_1_NETS = {
    BRIDGELESS_NETS[1][0]: {
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[1][1]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[1][2]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "usages": ""
    },
    BRIDGELESS_NETS[1][3]: {
        "required": "false",
        "usages": ""
    }
}
