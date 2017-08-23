#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for network filter
"""

import rhevmtests.helpers as global_helper

VM_INFO = dict()
FAKE_IP_1 = "1.2.3.4"
FAKE_IP_2 = "6.7.8.9"
IP_NAME = "IP"

VNICS = global_helper.generate_object_names(
    num_of_cases=9, num_of_objects=5, prefix="network_filter_vnic"
)

NETS = global_helper.generate_object_names(
    num_of_cases=10, prefix="nf_net"
)
VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=10, prefix="network-filter-vnic-profile"
)

NETWORK_FILTER_STR = "network_filter"

ARP_FILTER = "allow-arp"

CASE_01_NETS_DICT = {
    NETS[1][0]: {
        "required": "false"
    }
}

CASE_03_NETS_DICT = {
    NETS[3][0]: {
        "required": "false"
    }
}

CASE_04_NETS_DICT = {
    NETS[4][0]: {
        "required": "false"
    }
}
