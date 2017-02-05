#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for multiple gateways feature
"""
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper

VLAN_IDS = [str(i) for i in xrange(2, 60)]
NETS = global_helper.generate_object_names(
    num_of_cases=11, prefix="multi_gw"
)
IPS = network_helper.create_random_ips(num_of_ips=10, mask=24)
SUBNET = "5.5.5.0"
GATEWAY = "5.5.5.254"

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0)
    },
    NETS[1][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[1][2]: {
        "required": "false",
        "cluster_usages": "display"
    },
    NETS[2][0]: {
        "required": "false",
    },
    NETS[2][1]: {
        "required": "false",
    },
}
