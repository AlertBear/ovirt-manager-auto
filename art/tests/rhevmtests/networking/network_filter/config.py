#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for network filter
"""

import rhevmtests.helpers as global_helper

VNICS = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=5, prefix="network_filter_vnic"
)

NETS = global_helper.generate_object_names(
    num_of_cases=10, prefix="nf_net"
)
VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=10, prefix="network-filter-vnic-profile"
)

NETWORK_FILTER_STR = "network_filter"

ARP_FILTER = "allow-arp"

NETS_DICT = {
    NETS[1][0]: {
        "required": "false"
    },
    NETS[3][0]: {
        "required": "false"
    },
    NETS[4][0]: {
        "required": "false"
    },
}
