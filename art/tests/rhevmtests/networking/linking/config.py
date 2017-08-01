#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Network Linking feature tests
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=10, prefix="linking_vnic_profile"
)
VNICS = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=10, prefix="linking_vnic"
)
NETS = global_helper.generate_object_names(
    num_of_cases=6, num_of_objects=10, prefix="linking_net"
)


# vNICS
CASE_01_VNIC_1 = VNICS[1][0]
CASE_02_VNIC_1 = VNICS[2][0]
CASE_02_VNIC_2 = VNICS[2][1]
CASE_03_VNIC_1 = VNICS[3][0]
CASE_04_VNIC_1 = VNICS[4][0]
CASE_04_VNIC_2 = VNICS[4][1]
CASE_04_VNIC_1_REN = "%s_rename" % VNICS[4][0]
CASE_04_VNIC_2_REN = "%s_rename" % VNICS[4][1]
CASE_04_VNIC_3 = VNICS[4][2]
CASE_05_VNIC_1 = VNICS[5][0]

# vNIC profiles
CASE_04_VNIC_PROFILE_1 = VNIC_PROFILES[4][0]
CASE_05_VNIC_PROFILE_1 = VNIC_PROFILES[5][0]
CASE_05_VNIC_PROFILE_2 = VNIC_PROFILES[5][1]

# Networks
CASE_01_NET_1 = NETS[1][0]
CASE_02_NET_1 = NETS[2][0]
CASE_02_NET_2 = NETS[2][1]
CASE_03_NET_1 = NETS[3][0]
CASE_04_NET_1 = NETS[4][0]
CASE_05_NET_1 = NETS[5][0]
CASE_05_NET_2 = NETS[5][1]

NET_DICT = {
    CASE_01_NET_1: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    },
    CASE_02_NET_1: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    },
    CASE_02_NET_2: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    },
    CASE_03_NET_1: {
        "required": "false"
    },
    CASE_04_NET_1: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    },
    CASE_05_NET_1: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    },
    CASE_05_NET_2: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "nic": 1
    }
}
