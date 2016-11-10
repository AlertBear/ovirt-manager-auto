#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for register domain test
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

EXTRA_SD_NAME = "Register_domain_network_SD"
EXTRA_SD_PATH = conf.UNUSED_DATA_DOMAIN_PATHS[0]
EXTRA_SD_ADDRESS = conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]

NETS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=2, prefix="reg_dom"
)
VM_NAMES = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=1, prefix="register_domain_network_vm"
)
VM_NICS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=1, prefix="register_domain_vnic"
)
VMS_LIST = [i[0] for i in VM_NAMES.values()]
NETS_LIST = [i[0] for i in NETS.values()]
VMS_NICS_LIST = [i[0] for i in VM_NICS.values()]
MAC_NOT_IN_POOL_1 = "00:00:00:00:00:01"
MAC_NOT_IN_POOL_2 = "00:00:00:00:00:02"
DUPLICATE_MAC_1 = "00:00:00:00:00:03"
DUPLICATE_MAC_2 = "00:00:00:00:00:04"
DUPLICATE_MAC_3 = "00:00:00:00:00:05"
MAC_LIST = [
    None, MAC_NOT_IN_POOL_1, MAC_NOT_IN_POOL_2, DUPLICATE_MAC_1,
    DUPLICATE_MAC_2, DUPLICATE_MAC_3, None, None, None, None
]

VMS_DICT = dict()

for vm, net, mac, nic, in zip(VMS_LIST, NETS_LIST, MAC_LIST, VMS_NICS_LIST):
    VMS_DICT[vm] = dict()
    VMS_DICT[vm]["network"] = net
    VMS_DICT[vm]["mac"] = mac
    VMS_DICT[vm]["nic"] = nic

NETS_DICT = {
    NETS[1][0]: {
        "required": "false",
    },
    NETS[2][0]: {
        "required": "false",
    },
    NETS[2][1]: {
        "required": "false",
    },
    NETS[3][0]: {
        "required": "false",
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
    NETS[7][0]: {
        "required": "false",
    },
    NETS[8][0]: {
        "required": "false",
    },
}
