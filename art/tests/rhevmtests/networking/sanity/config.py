#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for sanity test
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

HOST_NICS = None  # Filled in setup_package
HOST_NAME_0 = None  # Filled in setup_package
VDS_HOST_0 = VDS_HOSTS[0]
HOST_0_IP = HOSTS_IP[0]
HOST_0 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER = CLUSTER_NAME[0]
EXTRA_DC = EXTRA_DC[0]
DC_NAMES = [DC_NAME, EXTRA_DC]
NIC_1 = NIC_NAME[1]
VPROFILE_0 = VNIC_PROFILE[0]
VM_0 = VM_NAME[0]
VM_1 = VM_NAME[1]
NETS = global_helper.generate_object_names(num_of_cases=20)
VLAN_IDS = [str(i) for i in xrange(2, 20)]
NET_2 = NETS[2][0]
NET_3 = NETS[3][0]
NET_3_1 = NETS[3][1]
NET_4 = NETS[4][0]
NET_5 = NETS[5][0]
NET_6 = NETS[6][0]
NET_8 = NETS[8][0]
NET_8_1 = NETS[8][1]
NET_8_2 = NETS[8][2]
NET_8_3 = NETS[8][3]
NET_10 = NETS[10][0]
NET_11 = NETS[11][0]
NET_13 = NETS[13][0]
NET_14 = NETS[14][0]
NET_15 = NETS[15][0]

DUMMYS = ["dummy_%s" % i for i in xrange(15)]
VDSMD_SERVICE = "vdsmd"

NETS_DICT = {
    NET_2: {
        "vlan_id": VLAN_IDS[0],
        "required": "false"
    },
    NET_3: {
        "vlan_id": VLAN_IDS[1],
        "required": "false"
    },
    NET_3_1: {
        "vlan_id": VLAN_IDS[2],
        "required": "false",
        "usages": ""
    },
    NET_4: {
        "vlan_id": VLAN_IDS[3],
        "required": "false"
    },
    NET_5: {
        "required": "true"
    },
    NET_6: {
        "vlan_id": VLAN_IDS[4],
        "required": "false",
        "mtu": MTU[2]
    },
    NET_8: {
        "vlan_id": VLAN_IDS[5],
        "required": "false",
        "mtu": MTU[0]
    },
    NET_8_1: {
        "vlan_id": VLAN_IDS[6],
        "required": "false"
    },
    NET_8_2: {
        "vlan_id": VLAN_IDS[7],
        "required": "false",
    },
    NET_8_3: {
        "vlan_id": VLAN_IDS[8],
        "required": "false"
    },
    NET_10: {
        "required": "false"
    },
    NET_13: {
        "required": "false"
    },
    NET_14: {
        "required": "false"
    },
    NET_15: {
        "required": "false"
    }
}
