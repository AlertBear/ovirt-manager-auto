#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for arbitrary_vlan_device_name
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

ARBITRARY_NETS = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=3, prefix="avdn"
)
VLAN_NAMES = ["vlan10", "vlan20", "vlan30"]
ARBITRARY_VLAN_IDS = ["10", "20", "30"]
BRIDGE_NAMES = ["br_vlan10", "br_vlan20", "br_vlan30"]
ARBITRARY_NET_DICT = {
    ARBITRARY_NETS[5][0]: {
        "vlan_id": conf.VLAN_ID[0],
        "required": "false",
    },
    ARBITRARY_NETS[6][0]: {
        "vlan_id": conf.VLAN_ID[1],
        "required": "false",
        "usages": ""
    }

}
