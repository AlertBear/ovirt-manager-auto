#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for MultiHost
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

VDS_HOST_0 = None  # Filled in setup_package
VDS_HOST_1 = None  # Filled in setup_package
HOST_NAME_0 = None  # Filled in setup_package
HOST_NAME_1 = None  # Filled in setup_package
HOST_0_NICS = None  # Filled in setup_package
HOST_1_NICS = None  # Filled in setup_package
HOSTS_LIST = None  # Filled in setup_package
VDS_HOSTS_LIST = None  # Filled in setup_package
NETS = global_helper.generate_object_names(num_of_cases=11)
VLAN_IDS = [str(i) for i in xrange(2, 60)]
UPDATE_CHANGES_ENGINE = "Check that the host nic was updated via engine"
UPDATE_CHANGES_HOST = "Check that the host nic was updated on the host"
DC_NAME_0 = DC_NAME[0]
CLUSTER_NAME_0 = CLUSTER_NAME[0]
VM_NAME_0 = VM_NAME[0]
VM_NAME_1 = VM_NAME[1]
TEMPLATE_NAME_0 = TEMPLATE_NAME[0]
SLEEP = 10

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",  # case01 use VLAN_IDS[0] and VLAN_IDS[1]
    },
    NETS[2][0]: {
        "required": "false"
    },
    NETS[3][0]: {
        "required": "false"
    },
    NETS[4][0]: {
        "required": "false"
    },
    NETS[5][0]: {
        "required": "false"  # case05 use VLAN_IDS[2]
    },
    NETS[6][0]: {
        "required": "false"  # case06 use VLAN_IDS[3]
    },
    NETS[7][0]: {
        "required": "false"  # case07 use VLAN_IDS[4]
    },
}
