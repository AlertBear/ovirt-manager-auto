#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for MultiHost
"""

import rhevmtests.helpers as global_helper

VNICS = global_helper.generate_object_names(
    num_of_cases=7, num_of_objects=3, prefix="multi_host_vnic"
)

NETS = global_helper.generate_object_names(
    num_of_cases=11, prefix="MultiHost"
)

VLAN_IDS = [str(i) for i in xrange(2, 60)]
UPDATE_CHANGES_ENGINE = "Check that the host nic was updated via engine"
UPDATE_CHANGES_HOST = "Check that the host nic was updated on the host"
SLEEP = 10

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",  # case01 use VLAN_IDS[0] and VLAN_IDS[1]
    },
    NETS[2][0]: {
        "required": "false"
    },
    NETS[3][0]: {
        "required": "false"  # case03 use VLAN_IDS[2]
    },
    NETS[4][0]: {
        "required": "false"  # case04 use VLAN_IDS[3]
    },
    NETS[5][0]: {
        "required": "false"  # case05 use VLAN_IDS[4]
    },
    NETS[6][0]: {
        "required": "false"  # case06 use VLAN_IDS[5]
    },
    NETS[7][0]: {
        "required": "false"  # case07 use VLAN_IDS[6] and VLAN_IDS[7]
    },
}
