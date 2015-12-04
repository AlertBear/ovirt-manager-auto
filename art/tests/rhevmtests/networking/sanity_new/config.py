#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for sanity test
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper
import art.unittest_lib.network as network_lib

# Global
HOST_0_NICS = None  # Filled in setup_package
VDS_HOST_0 = None  # Filled in setup_package
HOST_NAME_0 = None  # Filled in setup_package
CLUSTER_0_NAME = CLUSTER_NAME[0]
VM_0 = VM_NAME[0]
DC_0_NAME = DC_NAME[0]

# host network QoS
QOS_NAME = global_helper.generate_object_names(object_type="QoS", count=10)
TEST_VALUE = 10

# Network
NETS = network_lib.generate_networks_names(cases=20, num_of_networks=10)
VLAN_IDS = [str(i) for i in xrange(2, 20)]
DUMMYS = ["dummy_%s" % i for i in xrange(20)]

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
}
