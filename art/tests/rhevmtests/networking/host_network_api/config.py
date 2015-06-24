#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

import helper
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
SN_NETS = network_lib.generate_networks_names(cases=25, prefix="sn")
VDSMD_SERVICE = "vdsmd"
VLAN_ID = 2

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

NIC_DICT = {
    NIC_NETS[1][0]: {
        "required": "false"
    },
    NIC_NETS[2][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NIC_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    NIC_NETS[4][0]: {
        "required": "false"
    },
    NIC_NETS[4][1]: {
        "required": "false"
    },
    NIC_NETS[5][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NIC_NETS[5][1]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NIC_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[6][1]: {
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
        "vlan_id": helper.generate_vlan_id(),
        "mtu": MTU[0]
    },
    NIC_NETS[9][0]: {
        "required": "false"
    },
    NIC_NETS[10][0]: {
        "required": "false"
    },
    NIC_NETS[10][1]: {
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
        "vlan_id": helper.generate_vlan_id()
    },
    NIC_NETS[12][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    NIC_NETS[13][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    NIC_NETS[14][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    NIC_NETS[14][1]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    NIC_NETS[15][0]: {
        "required": "false"
    }
}

SN_DICT = {
    SN_NETS[1][0]: {
        "required": "false"
    },
    SN_NETS[2][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    SN_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    SN_NETS[4][0]: {
        "required": "false"
    },
    SN_NETS[4][1]: {
        "required": "false"
    },
    SN_NETS[5][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    SN_NETS[5][1]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    SN_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[6][1]: {
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
        "vlan_id": helper.generate_vlan_id(),
        "mtu": MTU[0]
    },
    SN_NETS[9][0]: {
        "required": "false"
    },
    SN_NETS[10][0]: {
        "required": "false"
    },
    SN_NETS[10][1]: {
        "required": "false"
    },
    SN_NETS[11][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[11][1]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[11][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
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
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[15][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[18][0]: {
        "required": "false"
    },
    SN_NETS[19][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[19][1]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[20][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[21][0]: {
        "required": "false"
    },
    SN_NETS[22][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[22][1]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[22][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[23][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[23][1]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    SN_NETS[23][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    }
}

HOST_DICT = {
    HOST_NETS[1][0]: {
        "required": "false"
    },
    HOST_NETS[2][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    HOST_NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    HOST_NETS[4][0]: {
        "required": "false"
    },
    HOST_NETS[4][1]: {
        "required": "false"
    },
    HOST_NETS[5][0]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    HOST_NETS[5][1]: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    HOST_NETS[6][0]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[6][1]: {
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
        "vlan_id": helper.generate_vlan_id(),
        "mtu": MTU[0]
    },
    HOST_NETS[9][0]: {
        "required": "false"
    },
    HOST_NETS[10][0]: {
        "required": "false"
    },
    HOST_NETS[10][1]: {
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
        "vlan_id": helper.generate_vlan_id()
    },
    HOST_NETS[12][2]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    HOST_NETS[13][0]: {
        "required": "false"
    },
    HOST_NETS[14][0]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    HOST_NETS[15][0]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    HOST_NETS[15][1]: {
        "required": "false",
        "vlan_id": helper.generate_vlan_id()
    },
    HOST_NETS[17][0]: {
        "required": "false"
    }
}
