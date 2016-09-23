#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for MAC pool range per DC
"""

import rhevmtests.networking.config as network_conf

# Deprecated commands for test case 1
MAC_POOL_RANGE_CMD = "MacPoolRanges"
MAX_COUNT_POOL_CMD = "MaxMacCountPool"

# Filled in setup_package
DEFAULT_MAC_POOL_VALUES = None

MAC_POOL_NAME = ["_".join(["mac_pool_name", str(i)]) for i in range(3)]
EXT_CL_NAME = ["_".join(["mac_pool_cluster", str(i)]) for i in range(4)]
NICS_NAME = ["_".join(["mac_pool_vnic", str(i)]) for i in range(7)]

# Prepare setup fixture
MAC_POOL_CL = "mac_pool_cluster_setup"
MP_STORAGE = "mac_pool_storage_setup"
MP_TEMPLATE = "mac_pool_template_setup"

# Common use for all tests
MAC_POOL_RANGE_LIST = [
    ("00:00:00:10:10:10", "00:00:00:10:10:11"),
    ("00:00:00:20:10:10", "00:00:00:20:10:12"),
    ("00:00:00:30:10:10", "00:00:00:30:10:12")
]

DEFAULT_MAC_POOL = "Default"

MAC_POOL_NAME_0 = MAC_POOL_NAME[0]
MAC_POOL_NAME_1 = MAC_POOL_NAME[1]
MAC_POOL_NAME_2 = MAC_POOL_NAME[2]

EXT_CL_1 = EXT_CL_NAME[1]
EXT_CL_2 = EXT_CL_NAME[2]
EXT_CL_3 = EXT_CL_NAME[3]

MP_VM_0 = "mac_pool_vm_0"
MP_VM_1 = "mac_pool_vm_1"

NIC_NAME_0 = network_conf.NIC_NAME[0]
NIC_NAME_1 = NICS_NAME[1]
NIC_NAME_2 = NICS_NAME[2]
NIC_NAME_3 = NICS_NAME[3]
NIC_NAME_4 = NICS_NAME[4]
NIC_NAME_5 = NICS_NAME[5]
NIC_NAME_6 = NICS_NAME[6]
