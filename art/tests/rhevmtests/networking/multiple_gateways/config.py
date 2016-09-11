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

IP_DICT = {
    "ip": {
        "1": {
            "address": None,
            "netmask": "255.255.255.0",
            "gateway": "5.5.5.254",
            "boot_protocol": "static"
        }
    }
}

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[0]
    },
    NETS[2][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[3][0]: {
        "required": "false",
        "cluster_usages": "display"
    },
    NETS[4][0]: {
        "required": "false",
    },
    NETS[5][0]: {
        "required": "false",
    },
    NETS[6][0]: {
        "required": "false",
    },
}
