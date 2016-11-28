#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for sanity test
"""

from rhevmtests.networking.config import *  # flake8: noqa
import rhevmtests.helpers as global_helper

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

VLAN_IDS = [str(i) for i in xrange(2, 20)]
DUMMIES = ["dummy_%s" % i for i in xrange(12)]

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
        "vlan_id": VLAN_IDS[1]
    },
    NETS[2][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[2]
    },
    NETS[2][3]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3]
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
        "mtu": MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "usages": "",
        "mtu": MTU[1]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[4],
        "mtu": MTU[1]
    },
    NETS[4][3]: {
        "required": "false",
        "mtu": MTU[1]
    },
    NETS[5][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[5][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[5],
        "usages": "",
    },
    NETS[5][2]: {
        "required": "false",
        "usages": ""
    },
    NETS[5][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[6],
        "usages": ""
    },
    NETS[6][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[7]
    },
    NETS[6][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[8],
    },
    NETS[6][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[9]
    },
    NETS[6][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[10],
    },
    NETS[8][0]: {
        "required": "true",
    },
    NETS[9][0]: {
        "required": "false",
        "mtu": MTU[0]
    },
    NETS[10][0]: {
        "required": "false",
    },
    NETS[12][0]: {
        "required": "false",
    },
    NETS[14][0]: {
        "required": "false",
    },
    NETS[14][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[12],
    },
    NETS[14][2]: {
        "required": "false",
    },
    NETS[14][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[13],
    },
    NETS[15][0]: {
        "required": "true",
    },
}
