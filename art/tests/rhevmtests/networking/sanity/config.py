#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for sanity test
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf


# Host network QoS
QOS_NAME = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=1, prefix="sanity_qos"
)

# Networks
NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="sanity_net"
)

# vNIC profiles
VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=1, prefix="sanity_vnic_profile"
)

VNICS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="sanity_vnic"
)
HOST_NAME = None  # Filled in test
HOST_VDS = None  # Filled in test

BASIC_IP_DICT_NETMASK = {
    "ip_netmask": {
        "address": "1.1.1.1",
        "netmask": "255.255.255.0",
        "boot_protocol": "static"
    }
}

BASIC_IP_DICT_PREFIX = {
    "ip_prefix": {
        "address": "2.2.2.2",
        "netmask": "24",
        "boot_protocol": "static"
    }
}

SN_DICT = {
    NETS[1][0]: {
        "required": "false",
    },
    NETS[2][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0)
    },
    NETS[2][2]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0)
    },
    NETS[2][3]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][4]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0)
    },
    NETS[2][5]: {
        "required": "false",
        "usages": ""
    },
    NETS[3][0]: {
        "required": "false",
    },
    NETS[4][0]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "mtu": conf.MTU[1]
    },
    NETS[4][3]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    NETS[4][4]: {
        "required": "false",
        "usages": ""
    },
    NETS[4][5]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "usages": "",
    },
    NETS[4][6]: {
        "required": "false",
        "usages": ""
    },
    NETS[4][7]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
        "usages": ""
    },
    NETS[5][0]: {
        "required": "false",
    },
    NETS[5][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[5][2]: {
        "required": "false",
    },
    NETS[5][3]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[6][0]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0)
    },
    NETS[6][1]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[6][2]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0)
    },
    NETS[6][3]: {
        "required": "false",
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
    NETS[8][0]: {
        "required": "true",
    },
    NETS[9][0]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    NETS[9][1]: {
        "required": "false",
    },
    NETS[9][2]: {
        "required": "false",
    },
    NETS[10][0]: {
        "required": "false",
    },
    NETS[12][0]: {
        "required": "false",
    },
    NETS[15][0]: {
        "required": "true",
    },
}
