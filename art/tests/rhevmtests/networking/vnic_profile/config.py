#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for vNIC profile test
"""

import rhevmtests.helpers as global_helper

VLAN_IDS = [str(i) for i in xrange(2, 20)]

NETS = global_helper.generate_object_names(num_of_cases=4, num_of_objects=20)

VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=20, prefix="vnic-profile_vnic_profile"
)

VNICS = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=20, prefix="vnic-profile_vnics"
)

NETS_DICT = {
    NETS[2][0]: {
        "required": "false",
    },
    NETS[2][1]: {
        "required": "false",
    },
    NETS[2][2]: {
        "required": "false",
    },
    NETS[2][3]: {
        "required": "false",
    },
    NETS[2][4]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][5]: {
        "required": "false",
    },
    NETS[2][6]: {
        "required": "false",
        "profile_required": "false"
    },
    NETS[2][7]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][8]: {
        "required": "false",
    },
    NETS[2][9]: {
        "required": "false",
        "vlan_id": VLAN_IDS[0]
    },
    NETS[2][10]: {
        "required": "false",
        "vlan_id": VLAN_IDS[1]
    },
    NETS[2][11]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3]
    },
    NETS[2][12]: {
        "required": "false",
        "vlan_id": VLAN_IDS[4]
    },
    NETS[2][13]: {
        "required": "false",
    },
    NETS[2][14]: {
        "required": "false",
    },
    NETS[2][16]: {
        "required": "false",
        "vlan_id": VLAN_IDS[5]
    },
    NETS[2][17]: {
        "required": "false",
        "vlan_id": VLAN_IDS[6]
    },
    NETS[3][0]: {
        "required": "false",
    },
}
