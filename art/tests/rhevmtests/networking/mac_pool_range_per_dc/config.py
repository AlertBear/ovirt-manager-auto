#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature config
"""

from rhevmtests.networking.config import *  # NOQA

MAC_POOL_NAME = ["_".join(["MAC_POOL", str(i)]) for i in range(6)]
MAC_POOL_CL = "MAC_POOL_CL"
MP_VM_NAMES = ["_".join(["MAC_POOL_VM", str(i)]) for i in range(6)]

DEFAULT_MAC_POOL_VALUES = None  # Filled in setup_package
EXT_DC_0 = EXTRA_DC[0]
MP_VM = MP_VM_NAMES[0]
MP_TEMPLATE = "MP_Template"
MAC_POOL_NAME_0 = MAC_POOL_NAME[0]
MAC_POOL_NAME_1 = MAC_POOL_NAME[1]
MAC_POOL_NAME_2 = MAC_POOL_NAME[2]
NIC_NAME_0 = NIC_NAME[0]
NIC_NAME_1 = NIC_NAME[1]
NIC_NAME_2 = NIC_NAME[2]
NIC_NAME_3 = NIC_NAME[3]
NIC_NAME_4 = NIC_NAME[4]
NIC_NAME_5 = NIC_NAME[5]
MP_STORAGE = "MAC_P_Storage"
