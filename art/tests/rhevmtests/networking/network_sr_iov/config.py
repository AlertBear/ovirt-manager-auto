#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature config
"""
from rhevmtests.networking.config import *  # NOQA

HOST_0_NICS = None  # Filled in setup_package
HOST_0_NAME = None  # Filled in setup_package
VDS_0_HOST = None  # Filled in setup_package
HOST_O_SRIOV_NICS_OBJ = None  # Filled in setup_package
HOST_0_PF_LIST = list()  # Filled in setup_package
HOST_0_PF_NAMES = list()  # Filled in setup_package
NUM_VF_PATH = "/sys/class/net/%s/device/sriov_numvfs"
BW_VALUE = 10
BURST_VALUE = 100
