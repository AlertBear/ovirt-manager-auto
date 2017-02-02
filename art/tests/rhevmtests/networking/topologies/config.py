#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for topologies test
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

NETMASK = "255.255.255.240"
SRC_ADDRESS = "10.35.147.50"
DST_HOST_IP = "10.35.147.62"
NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="topo"
)

NON_VM_BOND_IP = {
    "1": {
        "address": SRC_ADDRESS,
        "netmask": NETMASK,
        "boot_protocol": "static"
    }
}

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID.pop(0) if not conf.PPC_ARCH else "1000"
    },
    NETS[1][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_ID.pop(0) if not conf.PPC_ARCH else "1001"
    },
    NETS[1][2]: {
        "required": "false",
    },
    NETS[1][3]: {
        "required": "false",
    },
    NETS[1][4]: {
        "required": "false",
        "usages": ""
    },
    NETS[1][5]: {
        "required": "false",
        "usages": ""
    },
    NETS[1][6]: {
        "usages": ""
    },
    NETS[1][7]: {
        "required": "false",
        "usages": ""
    },
}
