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
VLAN_IDS = [str(i) for i in xrange(2, 60)]
REAL_VLANS = [str(i) for i in xrange(162, 169)]
NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="jumbo"
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
        "vlan_id": VLAN_IDS[0],
        "usages": "",
    },
    NETS[2][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": VLAN_IDS[1],
        "usages": "",
    },
    NETS[3][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
    },
    NETS[4][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[9],
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "vlan_id": REAL_VLANS[2],
        "mtu": conf.MTU[0]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[11],
        "mtu": conf.MTU[2]
    },
    NETS[4][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[12],
        "mtu": conf.MTU[3]
    },
    NETS[5][0]: {
        "required": "false",
        "vlan_id": REAL_VLANS[3],
        "mtu": conf.MTU[1],
    },
    NETS[6][0]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": VLAN_IDS[5],
    },
    NETS[6][1]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "usages": "",
    },
    NETS[7][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": REAL_VLANS[0],
    },
    NETS[7][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": REAL_VLANS[1],
    },
    NETS[8][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": VLAN_IDS[6],
    },
    NETS[8][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[7],
    },
    NETS[9][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[8],
    },
}
