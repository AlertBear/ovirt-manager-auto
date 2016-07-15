#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for network custom properties
"""

import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(
    num_of_cases=15, prefix="cus_pr"
)
VLAN_IDS = [str(i) for i in xrange(2, 60)]

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
    },
    NETS[1][1]: {
        "required": "false",
        "usages": "",
    },
    NETS[1][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[0]
    },
    NETS[1][3]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[1]
    },
    NETS[2][0]: {
        "required": "false",
    },
    NETS[3][0]: {
        "required": "false",
    },
    NETS[3][1]: {
        "required": "false",
    },
    NETS[4][0]: {
        "required": "false",
    },
    NETS[4][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[2]
    },
    NETS[5][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3]
    },
    NETS[5][1]: {
        "required": "false",
        "usages": "",
    },
    NETS[6][0]: {
        "required": "false",
    },
    NETS[7][0]: {
        "required": "false",
    },
    NETS[8][0]: {
        "required": "false",
    },
    NETS[9][0]: {
        "required": "false",
    },
    NETS[10][0]: {
        "required": "false",
    },
    NETS[11][0]: {
        "required": "false",
    },
}
