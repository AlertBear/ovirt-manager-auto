#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Jumbo frame test
"""

import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper

CASE_3_IPS = None
CASE_4_IPS = None
CASE_5_IPS = None
CASE_7_IPS = None
CASE_IPS = None
VMS_RESOURCES = dict()

VNICS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=5, prefix="jumbo_frame_vnic"
)
NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="jumbo_net"
)

NETS_DICT = {
    NETS[35][0]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
    NETS[35][0]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
    NETS[35][1]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
    NETS[1][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
    },
    NETS[2][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.VLAN_IDS.pop(0),
        "usages": "",
    },
    NETS[2][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.VLAN_IDS.pop(0),
        "usages": "",
    },
    NETS[3][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
    },
    NETS[4][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID[2] if conf.VLAN_ID else None,
        "mtu": conf.MTU[0]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "mtu": conf.MTU[2]
    },
    NETS[4][3]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "mtu": conf.MTU[3]
    },
    NETS[5][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID[3] if conf.VLAN_ID else None,
        "mtu": conf.MTU[1],
    },
    NETS[6][0]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[6][1]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "usages": "",
    },
    NETS[7][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.VLAN_ID[0] if conf.VLAN_ID else None,
    },
    NETS[7][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.VLAN_ID[1] if conf.VLAN_ID else None,
    },
    NETS[8][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[8][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[9][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
}
