#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for labels test
"""
from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

HOST0_NICS = None  # filled in setup_package
HOST1_NICS = None  # filled in setup_package
NUM_DUMMYS = 4
DUMMYS = ["dummy_%s" % i for i in xrange(NUM_DUMMYS)]
VLAN_IDS = [str(i) for i in xrange(2, 20)]

LABEL_NAME = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="label"
)

NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10
)

NET_DICT = {
    NETS[1][0]: {
        "required": "false"
    },
    NETS[2][0]: {
        "vlan_id": VLAN_IDS[1],
        "required": "false"
    },
    NETS[3][0]: {
        "required": "false"
    },
    NETS[4][0]: {
        "usages": "",
        "required": "false"
    },
    NETS[4][1]: {
        "vlan_id": VLAN_IDS[2],
        "required": "false"
    },
    NETS[5][0]: {
        "vlan_id": VLAN_IDS[3],
        "required": "false"
    },
    NETS[6][0]: {
        "required": "false"
    },
    NETS[7][0]: {
        "vlan_id": VLAN_IDS[4],
        "required": "false",
        "usages": ""
    },
    NETS[9][0]: {
        "vlan_id": VLAN_IDS[6],
        "required": "false"
    },
    NETS[9][1]: {
        "vlan_id": VLAN_IDS[7],
        "required": "false"
    },
    NETS[10][0]: {
        "required": "false"
    },
    NETS[10][1]: {
        "required": "false"
    },
    NETS[11][0]: {
        "required": "false"
    },
    NETS[11][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[12][0]: {
        "usages": "",
        "required": "false"
    },
    NETS[12][1]: {
        "vlan_id": VLAN_IDS[8],
        "required": "false"
    },
    NETS[13][0]: {
        "required": "false"
    },
    NETS[16][0]: {
        "required": "false"
    },
    NETS[17][0]: {
        "required": "false"
    },
    NETS[17][1]: {
        "required": "false"
    },
    NETS[17][2]: {
        "usages": "",
        "required": "false"
    },
    NETS[17][3]: {
        "usages": "",
        "required": "false"
    },
    NETS[17][4]: {
        "required": "false"
    },
    NETS[17][5]: {
        "usages": "",
        "required": "false"
    },
    NETS[18][0]: {
        "required": "false"
    },
    NETS[18][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[18][2]: {
        "required": "false"
    },
    NETS[18][3]: {
        "required": "false",
        "usages": ""
    },
    NETS[19][0]: {
        "required": "false"
    },
    NETS[20][0]: {
        "required": "false"
    },
    NETS[20][1]: {
        "vlan_id": VLAN_IDS[9],
        "required": "false"
    },
    NETS[20][2]: {
        "required": "false"
    },
    NETS[20][3]: {
        "vlan_id": VLAN_IDS[10],
        "required": "false"
    },
}
