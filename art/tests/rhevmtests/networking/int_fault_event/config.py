#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Int fault events
"""

from rhevmtests.networking.config import *  # flake8: noqa
import rhevmtests.helpers as global_helper

HOST_NICS = None  # Filled in setup_package
VDS_HOSTS_0 = None  # Filled in setup_package
HOST_0 = None  # Filled in setup_package
HOST_0_IP = None  # Filled in setup_package
NETS = global_helper.generate_object_names(num_of_cases=10)
LABEL_NAME = global_helper.generate_object_names(
    num_of_cases=10, num_of_objects=1, prefix="label"
)
HOST_INTERFACE_STATE_UP = 609
HOST_INTERFACE_STATE_DOWN = 610
HOST_BOND_SLAVE_STATE_UP = 611
HOST_BOND_SLAVE_STATE_DOWN = 612
STATE_UP = "up"
STATE_DOWN = "down"
SAMPLER_TIMEOUT = 60
DC_0 = DC_NAME[0]
CL_0 = CLUSTER_NAME[0]
BOND_0 = BOND[0]

NETS_DICT = {
    NETS[2][0]: {
        "required": "true"
    },
    NETS[4][0]: {
        "required": "true"
    },
    NETS[5][0]: {
        "required": "false"
    },
    NETS[6][0]: {
        "required": "false"
    },
    NETS[7][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[8][0]: {
        "required": "false",
        "usages": ""
    },
}
