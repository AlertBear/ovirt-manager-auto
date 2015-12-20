#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for bridgeless test
"""
from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper


HOST_0_NAME = None  # Filled in setup_package
HOST0_NICS = None  # filled in setup_package
NUM_DUMMYS = 4
DUMMYS = ["dummy_%s" % i for i in xrange(NUM_DUMMYS)]
VLAN_IDS = [str(i) for i in xrange(2, 4)]
NETS = global_helper.generate_object_names(num_of_cases=4, num_of_objects=3)

NET_DICT = {
    NETS[1][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][0]: {
        "vlan_id": VLAN_IDS[0],
        "required": "false",
        "usages": ""
    },
    NETS[3][0]: {
        "vlan_id": VLAN_IDS[1],
        "required": "false",
        "usages": ""
    },
    NETS[4][0]: {
        "required": "false",
        "usages": ""
    }
}
