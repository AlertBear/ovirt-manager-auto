#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

from rhevmtests.networking.config import *  # NOQA
import art.unittest_lib.network as network_lib

HOST_NICS = None  # Filled in setup_package
VDS_HOSTS_0 = VDS_HOSTS[0]
HOST_0_IP = HOSTS_IP[0]
NET0 = NETWORKS[0]
VNET0 = VLAN_NETWORKS[0]
HOST_0 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER = CLUSTER_NAME[0]
NIC_NETS = network_lib.generate_networks_names(cases=20, prefix="nic")
HOST_NETS = network_lib.generate_networks_names(cases=20, prefix="host")
SN_NETS = network_lib.generate_networks_names(cases=20, prefix="sn")
VDSMD_SERVICE = "vdsmd"
BASIC_IP_DICT = {
    "1": {
        "address": "1.1.1.1",
        "netmask": "255.255.255.0",
        "boot_protocol": "static"
    }
}
NIC_DICT = {
    NIC_NETS[1][0]: {
        "required": "false"
    },
    NIC_NETS[2][0]: {
        "vlan_id": "21",
        "required": "false"
    },
    NIC_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    NIC_NETS[4][0]: {
        "required": "false"
    },
    NIC_NETS[5][0]: {
        "vlan_id": "51",
        "required": "false"
    },
    NIC_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[7][0]: {
        "required": "false"
    },
    NIC_NETS[8][0]: {
        "required": "false",
        "usages": "",
        "mtu": MTU[1]
    },
    NIC_NETS[8][1]: {
        "required": "false",
        "vlan_id": "811",
        "mtu": MTU[0]
    },
    NIC_NETS[9][0]: {
        "required": "false"
    },
    NIC_NETS[10][0]: {
        "required": "false"
    },
    NIC_NETS[11][0]: {
        "required": "false"
    },
    NIC_NETS[12][0]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[12][1]: {
        "required": "false",
        "vlan_id": "121"
    },
    NIC_NETS[12][2]: {
        "required": "false",
        "vlan_id": "122"
    },
    NIC_NETS[13][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": "131"
    },
    NIC_NETS[14][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": "141"
    }
}

SN_DICT = {
    SN_NETS[1][0]: {
        "required": "false"
    },
    SN_NETS[2][0]: {
        "vlan_id": "22",
        "required": "false"
    },
    SN_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    SN_NETS[4][0]: {
        "required": "false"
    },
    SN_NETS[5][0]: {
        "vlan_id": "52",
        "required": "false"
    },
    SN_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[7][0]: {
        "required": "false"
    },
    SN_NETS[8][0]: {
        "required": "false",
        "usages": "",
        "mtu": MTU[1]
    },
    SN_NETS[8][1]: {
        "required": "false",
        "vlan_id": "822",
        "mtu": MTU[0]
    },
    SN_NETS[9][0]: {
        "required": "false"
    },
    SN_NETS[10][0]: {
        "required": "false"
    },
    SN_NETS[11][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[11][1]: {
        "required": "false",
        "vlan_id": "112"
    },
    SN_NETS[11][2]: {
        "required": "false",
        "vlan_id": "1122"
    },
    SN_NETS[12][0]: {
        "required": "false"
    },
    SN_NETS[15][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[15][1]: {
        "required": "false",
        "vlan_id": "152"
    },
    SN_NETS[15][2]: {
        "required": "false",
        "vlan_id": "1522"
    }
}

HOST_DICT = {
    HOST_NETS[1][0]: {
        "required": "false"
    },
    HOST_NETS[2][0]: {
        "vlan_id": "23",
        "required": "false"
    },
    HOST_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    HOST_NETS[4][0]: {
        "required": "false"
    },
    HOST_NETS[5][0]: {
        "vlan_id": "53",
        "required": "false"
    },
    HOST_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[7][0]: {
        "required": "false"
    },
    HOST_NETS[8][0]: {
        "required": "false",
        "usages": "",
        "mtu": MTU[1]
    },
    HOST_NETS[8][1]: {
        "required": "false",
        "vlan_id": "83",
        "mtu": MTU[0]
    },
    HOST_NETS[9][0]: {
        "required": "false"
    },
    HOST_NETS[10][0]: {
        "required": "false"
    },
    HOST_NETS[11][0]: {
        "required": "false"
    },
    HOST_NETS[12][0]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[12][1]: {
        "required": "false",
        "vlan_id": "123"
    },
    HOST_NETS[12][2]: {
        "required": "false",
        "vlan_id": "1231"
    },
    HOST_NETS[13][0]: {
        "required": "false"
    },
    HOST_NETS[14][0]: {
        "required": "false",
        "vlan_id": "143"
    },
    HOST_NETS[15][0]: {
        "required": "false",
        "vlan_id": "153"
    }
}
