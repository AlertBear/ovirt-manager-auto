#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MGMT network role networking feature config
"""
from rhevmtests.networking.config import *  # NOQA

EXT_DC_0 = EXTRA_DC[0]
EXT_DC_1 = EXTRA_DC[1]
EXTRA_CLUSTER_0 = EXTRA_CL[0]
EXTRA_CLUSTER_1 = EXTRA_CL[1]
EXTRA_CLUSTER_2 = EXTRA_CL[2]
EXTRA_CLUSTER_3 = EXTRA_CL[3]
MGMT = "management"
NET_1 = NETWORKS[0]
NET_2 = NETWORKS[1]
NET_3 = NETWORKS[2]
NET_4 = NETWORKS[3]
VIRSH_USER = "virsh"
VIRSH_PASS = "qum5net"
NET_DICT = {
    NET_1: {
        "required": "true"
    }
}
