#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature config
"""
from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

HOST_0_NICS = None  # Filled in setup_package
HOST_0_NAME = None  # Filled in setup_package
VDS_0_HOST = None  # Filled in setup_package
HOST_O_SRIOV_NICS_OBJ = None  # Filled in setup_package
HOST_0_PF_LIST = list()  # Filled in setup_package
HOST_0_PF_NAMES = list()  # Filled in setup_package
NUM_VF_PATH = "/sys/class/net/%s/device/sriov_numvfs"
BW_VALUE = 10
BURST_VALUE = 100
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
    }
}
