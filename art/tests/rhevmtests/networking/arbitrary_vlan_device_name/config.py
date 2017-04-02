#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for arbitrary_vlan_device_name
"""

import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper

ARBITRARY_NETS = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=3, prefix="avdn_net"
)
VLAN_NAMES = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=11, prefix="avdn_vlan_"
)

VLAN_IDS_LIST = [conf.VLAN_IDS.pop(i) for i in range(15)]

ARBITRARY_NET_DICT = {
    ARBITRARY_NETS[1][0]: {
        "vlan_id": VLAN_IDS_LIST[11],
        "required": "false",
    },
    ARBITRARY_NETS[1][1]: {
        "vlan_id": VLAN_IDS_LIST[12],
        "required": "false",
        "usages": ""
    }
}
