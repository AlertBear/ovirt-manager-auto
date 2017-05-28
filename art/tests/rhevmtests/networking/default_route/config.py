#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Config for default route tests
"""

import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper

EXTRA_CL_NAME = "Default-route-extra-cluster"
NETS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=4, prefix="dr_"
)

NET_DICT_CASE_01 = {
    NETS[1][0]: {
        "required": "false"
    }
}

NET_DICT_CASE_02 = {
    NETS[2][0]: {
        "required": "false"
    },
    NETS[2][1]: {
        "required": "false"
    }
}

NET_DICT_CASE_03 = {
    NETS[3][0]: {
        "vlan_id": conf.VLAN_ID[1],
        "required": "false"
    },
    NETS[3][1]: {
        "vlan_id": conf.VLAN_ID[2],
        "required": "false"
    }
}

NET_DICT_CASE_04 = {
    NETS[4][0]: {
        "vlan_id": conf.VLAN_ID[3],
        "required": "false"
    }
}

IP_DHCP = {
    "1": {
        "boot_protocol": "dhcp"
    }
}
