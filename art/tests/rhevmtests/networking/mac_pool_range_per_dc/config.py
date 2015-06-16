#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature config
"""
from rhevmtests.networking.config import *  # NOQA

MAC_POOL_NAME = ["_".join(["MAC_POOL", str(i)]) for i in range(6)]
MAC_POOL_RANGE_LIST = [
    ("00:00:00:10:10:10", "00:00:00:10:10:11"),
    ("00:00:00:20:10:10", "00:00:00:20:10:12"),
    ("00:00:00:30:10:10", "00:00:00:30:10:12")
]
MAC_POOL_CL = "MAC_POOL_CL"
MP_VM_NAMES = ["_".join(["MAC_POOL_VM", str(i)]) for i in range(6)]

LAST_HOST = HOSTS[-1]
EXT_DC_0 = EXTRA_DC[0]
MP_VM = MP_VM_NAMES[0]
EXT_DC_1 = EXTRA_DC[1]
ORIG_DC = DC_NAME[0]
MAC_POOL_NAME_0 = MAC_POOL_NAME[0]
MAC_POOL_NAME_1 = MAC_POOL_NAME[1]
NIC_NAME_1 = NIC_NAME[1]
