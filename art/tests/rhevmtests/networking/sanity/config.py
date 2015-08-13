#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for sanity test
"""

import helper
from rhevmtests.networking.config import *  # NOQA
import art.unittest_lib.network as network_lib

HOST_NICS = None  # Filled in setup_package
HOST_NAME_0 = None  # Filled in setup_package
VDS_HOSTS_0 = VDS_HOSTS[0]
HOST_0_IP = HOSTS_IP[0]
NET0 = NETWORKS[0]
VNET0 = VLAN_NETWORKS[0]
HOST_0 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER = CLUSTER_NAME[0]
EXTRA_DC = EXTRA_DC[0]
DC_NAMES = [DC_NAME, EXTRA_DC]
NIC_1 = NIC_NAME[1]
VPROFILE_0 = VNIC_PROFILE[0]
VM_0 = VM_NAME[0]
NETS = network_lib.generate_networks_names(cases=25)
NET_2 = NETS[2][0]
NET_3 = NETS[3][0]
NET_3_1 = NETS[3][1]
NET_4 = NETS[4][0]
NET_5 = NETS[5][0]

DUMMYS = ["dummy_%s" % i for i in xrange(15)]
VDSMD_SERVICE = "vdsmd"
VLAN_ID = 1

NETS_DICT = {
    NET_2: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NET_3: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NET_3_1: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false",
        "usages": ""
    },
    NET_4: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "false"
    },
    NET_5: {
        "vlan_id": helper.generate_vlan_id(),
        "required": "true"
    },
}
