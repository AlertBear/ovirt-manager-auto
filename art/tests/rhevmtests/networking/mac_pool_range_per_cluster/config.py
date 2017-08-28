#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for MAC pool range per DC
"""
import rhevmtests.helpers as global_helper

NICS_NAME = global_helper.generate_object_names(
    num_of_cases=9, num_of_objects=8, prefix="mac_pool"
)
MAC_POOL_NAME = ["_".join(["mac_pool_name", str(i)]) for i in range(3)]
EXT_CL_NAME = ["_".join(["mac_pool_cluster", str(i)]) for i in range(4)]
MP_VMS_NAMES = ["mac_pool_vm_%d" % i for i in range(7)]

# Common use for all tests
MAC_POOL_RANGE_LIST = [
    ("00:00:00:10:10:10", "00:00:00:10:10:11"),
    ("00:00:00:20:10:10", "00:00:00:20:10:12"),
    ("00:00:00:30:10:10", "00:00:00:30:10:12")
]
DEFAULT_MAC_POOL = "Default"

# Deprecated commands for test case 1
MAC_POOL_RANGE_CMD = "MacPoolRanges"
MAX_COUNT_POOL_CMD = "MaxMacCountPool"

# Filled in setup_package
DEFAULT_MAC_POOL_VALUES = None

# Prepare setup fixture
MAC_POOL_CL = "mac_pool_cluster_setup"
MP_STORAGE = "mac_pool_storage_setup"
MP_TEMPLATE = "mac_pool_template_setup"

# Test cases VMs
MP_VM_0 = MP_VMS_NAMES[0]
MP_VM_1 = MP_VMS_NAMES[1]
MP_VM_CASE_6 = MP_VMS_NAMES[6]

# Test cases MAC pool names
MAC_POOL_NAME_0 = MAC_POOL_NAME[0]
MAC_POOL_NAME_1 = MAC_POOL_NAME[1]
MAC_POOL_NAME_2 = MAC_POOL_NAME[2]

# Test cases cluster names
EXT_CL_1 = EXT_CL_NAME[1]
EXT_CL_2 = EXT_CL_NAME[2]
EXT_CL_3 = EXT_CL_NAME[3]

# Test cases vNIC names
CASE_3_NIC_1 = NICS_NAME[3][0]
CASE_3_NIC_2 = NICS_NAME[3][1]
CASE_3_NIC_3 = NICS_NAME[3][2]
CASE_3_NIC_4 = NICS_NAME[3][3]
CASE_3_ALL_NICS = NICS_NAME[3][:4]

CASE_4_NIC_1 = NICS_NAME[4][0]
CASE_4_NIC_2 = NICS_NAME[4][1]
CASE_4_NIC_3 = NICS_NAME[4][2]
CASE_4_NIC_4 = NICS_NAME[4][3]
CASE_4_NIC_5 = NICS_NAME[4][4]
CASE_4_REMOVE_NICS = NICS_NAME[4][:4]

CASE_5_NIC_4 = NICS_NAME[5][3]
CASE_5_NIC_5 = NICS_NAME[5][4]
CASE_5_NIC_6 = NICS_NAME[5][5]
CASE_5_SETUP_NICS = NICS_NAME[5][:3]
CASE_5_ALL_NICS = NICS_NAME[5][:6]

CASE_6_NIC_1 = NICS_NAME[6][0]
CASE_6_NIC_2 = NICS_NAME[6][1]

CASE_8_NIC_1 = NICS_NAME[8][0]

CASE_9_NIC_1 = NICS_NAME[9][0]
CASE_9_NIC_2 = NICS_NAME[9][1]
