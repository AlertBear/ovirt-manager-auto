#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for QoS test
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper


M_K_CONVERTER = 1024
BITS_BYTES = 8
QOS_NAME = global_helper.generate_object_names(object_type="QoS", count=6)
QOS_TYPE = "network"
BW_PARAMS = (10, 10, 100)
UPDATED_BW_PARAMS = (5, 5, 50)
DC_NAME = DC_NAME[0]
VM_NAME_0 = VM_NAME[0]
VM_NAME_1 = VM_NAME[1]
NIC_NAME_1 = NIC_NAME[1]
NIC_NAME_2 = NIC_NAME[2]
VDS_HOST = VDS_HOSTS[0]
HOST = HOSTS[0]
