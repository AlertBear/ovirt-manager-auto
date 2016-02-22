#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature config
"""
from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

HOST_0_NICS = None  # Filled in setup_package
HOST_1_NICS = None  # Filled in setup_package
HOST_0_NAME = None  # Filled in setup_package
HOST_1_NAME = None  # Filled in setup_package
VDS_0_HOST = None  # Filled in setup_package
VDS_1_HOST = None  # Filled in setup_package
HOST_O_SRIOV_NICS_OBJ = None  # Filled in setup_package
HOST_0_PF_LIST = list()  # Filled in setup_package
HOST_0_PF_NAMES = list()  # Filled in setup_package
NUM_VF_PATH = "/sys/class/net/%s/device/sriov_numvfs"
MAC_ADDR_FILE = "/sys/class/net/%s/address"
BW_VALUE = 10
BURST_VALUE = 100
VLAN_IDS = [str(i) for i in xrange(2, 60)]
NETWORK_QOS = "network_qos"
LABELS = global_helper.generate_object_names(
    num_of_cases=5, num_of_objects=2, prefix="label"
)
GENERAL_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="gen"
)
VM_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="vm"
)
GENERAL_DICT = {
    GENERAL_NETS[5][0]: {
        "required": "false"
    },
    GENERAL_NETS[6][0]: {
        "required": "false"
    }
}

VM_DICT = {
    VM_NETS[1][0]: {
        "required": "false"
    },
    VM_NETS[1][1]: {
        "required": "false"
    },
    VM_NETS[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[2]
    },
    VM_NETS[3][0]: {
        "required": "false"
    },
    VM_NETS[3][1]: {
        "required": "false"
    },
    VM_NETS[3][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3]
    },
    VM_NETS[3][3]: {
        "required": "false"
    },
    VM_NETS[4][0]: {
        "required": "false",
    },
    VM_NETS[4][1]: {
        "required": "false",
    },
    VM_NETS[4][2]: {
        "required": "false",
    },
    VM_NETS[4][3]: {
        "required": "false",
    },
}