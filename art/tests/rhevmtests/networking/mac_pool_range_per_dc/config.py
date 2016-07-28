#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature config
"""

import rhevmtests.networking.config as network_conf

MAC_POOL_NAME = ["_".join(["mac_pool", str(i)]) for i in range(6)]
MAC_POOL_CL = "mac_pool_cluster"
MP_VM_NAMES = ["_".join(["mac_pool_vm", str(i)]) for i in range(6)]
NICS_NAME = ["_".join(["mac_pool_vnic", str(i)]) for i in range(7)]
DEFAULT_MAC_POOL_VALUES = None  # Filled in setup_package
EXT_DC_0 = "mac_pool_range_ext_dc_0"
MP_VM = MP_VM_NAMES[0]
MP_TEMPLATE = "mac_pool_template"
MAC_POOL_NAME_0 = MAC_POOL_NAME[0]
MAC_POOL_NAME_1 = MAC_POOL_NAME[1]
MAC_POOL_NAME_2 = MAC_POOL_NAME[2]
NIC_NAME_0 = network_conf.NIC_NAME[0]
NIC_NAME_1 = NICS_NAME[1]
NIC_NAME_2 = NICS_NAME[2]
NIC_NAME_3 = NICS_NAME[3]
NIC_NAME_4 = NICS_NAME[4]
NIC_NAME_5 = NICS_NAME[5]
NIC_NAME_6 = NICS_NAME[6]
MP_STORAGE = "mac_pool_storage"
MAC_POOL_RANGE_LIST = [
    ("00:00:00:10:10:10", "00:00:00:10:10:11"),
    ("00:00:00:20:10:10", "00:00:00:20:10:12"),
    ("00:00:00:30:10:10", "00:00:00:30:10:12")
]
EXT_DC_1 = "mac_pool_range_ext_dc_1"
