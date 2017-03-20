#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network QoS job
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

MB_CONVERTER = 1000000
QOS_NAME = global_helper.generate_object_names(
    num_of_cases=7, num_of_objects=6, prefix="host_net_qos_name"
)
NETS = global_helper.generate_object_names(
    num_of_cases=7, num_of_objects=6, prefix="ho_net_qos"
)

QOS_SHARE = "MaxHostNetworkQosShares"
DEFAULT_SHARE = 100
UPDATED_SHARE = "200"
RATE_LIMIT = "MaxAverageNetworkQoSValue"
DEFAULT_RATE = 1024
UPDATED_RATE = "2048"
HOST_NET_QOS_TYPE = "hostnetwork"
TEST_VALUE = 10
SHARE_OVERLIMIT_C3 = DEFAULT_SHARE + 5
SHARE_OVERLIMIT_C4 = DEFAULT_SHARE + 1
RATE_OVERLIMIT = DEFAULT_RATE + 1


QOS_1 = {
    "type_": HOST_NET_QOS_TYPE,
    "outbound_average_linkshare": TEST_VALUE,
    "outbound_average_realtime": TEST_VALUE,
    "outbound_average_upperlimit": TEST_VALUE
}
QOS_2 = {
    "type_": HOST_NET_QOS_TYPE,
    "outbound_average_linkshare": TEST_VALUE,
    "outbound_average_realtime": TEST_VALUE - 1,
    "outbound_average_upperlimit": TEST_VALUE + 1
}

NETS_DICT = {
    NETS[1][0]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[1][1]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[1][2]: {
        "required": "false"
    },
    NETS[2][0]: {
        "usages": "",
        "required": "false"
    },
    NETS[3][0]: {
        "usages": "",
        "required": "false"
    },
    NETS[4][0]: {
        "required": "false"
    },
    NETS[5][1]: {
        "required": "false"
    },
    NETS[5][2]: {
        "required": "false"
    },
    NETS[6][0]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[6][1]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[7][0]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[7][1]: {
        "vlan_id": conf.VLAN_IDS.pop(0),
        "required": "false"
    },
}
