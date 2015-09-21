#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

from rhevmtests.networking.config import *  # NOQA
import art.unittest_lib.network as network_lib

HOST_4_NICS = None  # Filled in setup_package
VDS_HOSTS_4 = VDS_HOSTS[3]
NET0 = NETWORKS[0]
HOST_4 = HOSTS[3]
DC_NAME = DC_NAME[0]
CLUSTER_2 = CLUSTER_NAME[1]
SYNC_DC = "Sync_DC"
SYNC_CL = "Sync_cluster"
NIC_NETS = network_lib.generate_networks_names(cases=20, prefix="nic")
HOST_NETS = network_lib.generate_networks_names(cases=20, prefix="host")
SYNC_NETS_DC_1 = network_lib.generate_networks_names(cases=20, prefix="sync1_")
SYNC_NETS_DC_2 = network_lib.generate_networks_names(cases=20, prefix="sync2_")
SN_NETS = network_lib.generate_networks_names(
    cases=35, num_of_networks=10, prefix="sn"
)
VDSMD_SERVICE = "vdsmd"
VLAN_ID = 2
NUM_DUMMYS = 15
DUMMYS = ["dummy_%s" % i for i in xrange(NUM_DUMMYS)]
NETWORKS_DICT = {}
VLAN_STR = "vlan"
MTU_STR = "mtu"
BRIDGE_STR = "bridged"
VLAN_IDS = [str(i) for i in xrange(2, 60)]

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
        "vlan_id": VLAN_IDS[0],
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
        "vlan_id": VLAN_IDS[1],
        "required": "false"
    },
    NIC_NETS[5][1]: {
        "vlan_id": VLAN_IDS[2],
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
        "vlan_id": VLAN_IDS[3],
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
        "vlan_id": VLAN_IDS[4]
    },
    NIC_NETS[12][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[5]
    },
    NIC_NETS[13][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[6]
    },
    NIC_NETS[14][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[7]
    },
    NIC_NETS[14][1]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[8]
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
        "vlan_id": VLAN_IDS[9],
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
        "vlan_id": VLAN_IDS[10],
        "required": "false"
    },
    SN_NETS[5][1]: {
        "vlan_id": VLAN_IDS[11],
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
        "vlan_id": VLAN_IDS[12],
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
        "vlan_id": VLAN_IDS[13]
    },
    SN_NETS[11][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[14]
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
        "vlan_id": VLAN_IDS[15]
    },
    SN_NETS[15][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[16]
    },
    SN_NETS[18][0]: {
        "required": "false"
    },
    SN_NETS[19][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[17]
    },
    SN_NETS[19][1]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[18]
    },
    SN_NETS[20][0]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[19]
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
        "vlan_id": VLAN_IDS[20]
    },
    SN_NETS[22][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[21]
    },
    SN_NETS[23][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[23][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[22]
    },
    SN_NETS[23][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[23]
    },
    SN_NETS[24][0]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[24][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[24]
    },
    SN_NETS[24][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[25]
    },
    SN_NETS[24][3]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[24][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS[26]
    },
    SN_NETS[24][5]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[25][0]: {
        "required": "false",
    },
    SN_NETS[25][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[48]
    },
    SN_NETS[25][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[49]
    },
    SN_NETS[25][3]: {
        "required": "false",
    },
    SN_NETS[25][4]: {
        "required": "false",
    },
    SN_NETS[25][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[50]
    },
    SN_NETS[26][0]: {
        "required": "false",
    },
    SN_NETS[26][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[51]
    },
    SN_NETS[26][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[52]
    },
    SN_NETS[26][3]: {
        "required": "false",
    },
    SN_NETS[26][4]: {
        "required": "false",
    },
    SN_NETS[26][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[53]
    }
}

HOST_DICT = {
    HOST_NETS[1][0]: {
        "required": "false"
    },
    HOST_NETS[2][0]: {
        "vlan_id": VLAN_IDS[27],
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
        "vlan_id": VLAN_IDS[28],
        "required": "false"
    },
    HOST_NETS[5][1]: {
        "vlan_id": VLAN_IDS[29],
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
        "vlan_id": VLAN_IDS[30],
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
        "vlan_id": VLAN_IDS[31]
    },
    HOST_NETS[12][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[32]
    },
    HOST_NETS[13][0]: {
        "required": "false"
    },
    HOST_NETS[14][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[33]
    },
    HOST_NETS[15][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[34]
    },
    HOST_NETS[15][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[35]
    },
    HOST_NETS[17][0]: {
        "required": "false"
    },
    HOST_NETS[18][0]: {
        "required": "false"
    },
    HOST_NETS[18][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[46]
    },
    HOST_NETS[18][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[47]
    },
    HOST_NETS[18][3]: {
        "required": "false"
    },
}

SYNC_DICT_1 = {
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[36]
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[37]
    },
    SYNC_NETS_DC_1[1][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[42]
    },
    SYNC_NETS_DC_1[2][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[43]
    },
    SYNC_NETS_DC_1[2][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[3][0]: {
        "required": "false",
        "mtu": MTU[0]
    },
    SYNC_NETS_DC_1[3][1]: {
        "required": "false",
        "mtu": MTU[1]
    },
    SYNC_NETS_DC_1[3][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[4][0]: {
        "required": "false",
        "mtu": MTU[0]
    },
    SYNC_NETS_DC_1[4][1]: {
        "required": "false",
        "mtu": MTU[1]
    },
    SYNC_NETS_DC_1[4][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[5][0]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[5][1]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[6][0]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[6][1]: {
        "required": "false",
        "usages": ""
    },
}

SYNC_DICT_2 = {
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[40]
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[41]
    },
    SYNC_NETS_DC_1[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[44]
    },
    SYNC_NETS_DC_1[2][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[45]
    },
    SYNC_NETS_DC_1[3][0]: {
        "required": "false",
        "mtu": MTU[1]
    },
    SYNC_NETS_DC_1[3][1]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[3][2]: {
        "required": "false",
        "mtu": MTU[0]
    },
    SYNC_NETS_DC_1[4][0]: {
        "required": "false",
        "mtu": MTU[1]
    },
    SYNC_NETS_DC_1[4][1]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[4][2]: {
        "required": "false",
        "mtu": MTU[0]
    },
    SYNC_NETS_DC_1[5][0]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[5][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[6][0]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[6][1]: {
        "required": "false"
    },
}
