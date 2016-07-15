#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for topologies test
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="topo"
)

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID[0] if not conf.PPC_ARCH else "1000"
    },
    NETS[2][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID[1] if not conf.PPC_ARCH else "1001"
    },
    NETS[3][0]: {
        "required": "false",
    },
    NETS[4][0]: {
        "required": "false",
    },
    NETS[5][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[7][0]: {
        "usages": ""
    },
    NETS[8][0]: {
        "required": "false",
        "usages": ""
    },
}
