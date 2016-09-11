#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for network custom properties
"""
from collections import OrderedDict

import rhevmtests.helpers as global_helper

BRIDGE_OPTS = OrderedDict({
    "priority": ["32768", "1"],
    "multicast_querier": ["0", "1"]
})
KEY1 = BRIDGE_OPTS.keys()[0]
KEY2 = BRIDGE_OPTS.keys()[1]
PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][1]])
DEFAULT_PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][0]])
MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][1]])
DEFAULT_MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][0]])
TX_CHECKSUM = "-K {nic} tx {state}"
RX_CHECKSUM = "-K {nic} rx {state}"
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
