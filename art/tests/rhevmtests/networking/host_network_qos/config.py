#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network QoS job
"""

from rhevmtests.networking.config import *  # NOQA
import art.unittest_lib.network as network_lib

HOST_1_NICS = None  # Filled in setup_package
VDS_HOSTS_1 = VDS_HOSTS[0]
HOST_1_IP = HOSTS_IP[0]
HOST_1 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER_1 = CLUSTER_NAME[0]
CLUSTER_2 = CLUSTER_NAME[1]

NETS = network_lib.generate_networks_names(cases=10, num_of_networks=2)
VLAN_IDS = [str(i) for i in xrange(2, 50)]


QOS_SHARE = "MaxHostNetworkQosShares"
DEFAULT_SHARE = 100
UPDATED_SHARE = "200"
RATE_LIMIT = "MaxAverageNetworkQoSValue"
DEFAULT_RATE = 1024
UPDATED_RATE = "2048"
HOST_NET_QOS_TYPE = "hostnetwork"
QOS_NAME = ("HostQoSProfile1", "HostQoSProfile2")
TEST_VALUE = 10

NETS_DICT = {
    NETS[2][0]: {
        "required": "false"
    },
    NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    NETS[4][0]: {
        "required": "false"
    },
    NETS[5][0]: {
        "vlan_id": VLAN_IDS[10],
        "required": "false"
    },
    NETS[5][1]: {
        "vlan_id": VLAN_IDS[11],
        "required": "false"
    },
}
