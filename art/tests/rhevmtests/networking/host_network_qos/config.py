#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network QoS job
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

HOST_1_NICS = None  # Filled in setup_package
VDS_HOSTS_1 = VDS_HOSTS[0]
HOST_1_IP = HOSTS_IP[0]
HOST_1 = HOSTS[0]
DC_NAME = DC_NAME[0]
CLUSTER_1 = CLUSTER_NAME[0]
CLUSTER_2 = CLUSTER_NAME[1]
QOS_NAME = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=4, prefix="QoS"
)
NETS = global_helper.generate_object_names(num_of_cases=15, num_of_objects=2)
VLAN_IDS = [str(i) for i in xrange(2, 50)]


QOS_SHARE = "MaxHostNetworkQosShares"
DEFAULT_SHARE = 100
UPDATED_SHARE = "200"
RATE_LIMIT = "MaxAverageNetworkQoSValue"
DEFAULT_RATE = 1024
UPDATED_RATE = "2048"
HOST_NET_QOS_TYPE = "hostnetwork"
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
    NETS[6][0]: {
        "vlan_id": VLAN_IDS[10],
        "required": "false"
    },
    NETS[6][1]: {
        "vlan_id": VLAN_IDS[11],
        "required": "false"
    },
    NETS[7][0]: {
        "vlan_id": VLAN_IDS[12],
        "required": "false"
    },
    NETS[8][1]: {
        "required": "false"
    },
    NETS[9][0]: {
        "required": "false"
    },
    NETS[10][0]: {
        "required": "false"
    },
    NETS[11][0]: {
        "vlan_id": VLAN_IDS[13],
        "required": "false"
    },
    NETS[11][1]: {
        "vlan_id": VLAN_IDS[14],
        "required": "false"
    },
    NETS[12][0]: {
        "vlan_id": VLAN_IDS[15],
        "required": "false"
    },
    NETS[12][1]: {
        "vlan_id": VLAN_IDS[16],
        "required": "false"
    },
    NETS[13][0]: {
        "usages": "",
        "required": "false"
    },
}
