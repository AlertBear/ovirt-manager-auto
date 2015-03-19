#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MGMT network role networking feature config
"""
from rhevmtests.networking.config import *  # NOQA

LAST_HOST = HOSTS[-1]
EXT_DC_0 = EXTRA_DC[0]
EXT_DC_1 = EXTRA_DC[1]
ORIG_DC = DC_NAME[0]
CLUSTER_0 = CLUSTER_NAME[0]
CLUSTER_1 = CLUSTER_NAME[1]
EXTRA_CLUSTER_0 = EXTRA_CL[0]
EXTRA_CLUSTER_1 = EXTRA_CL[1]
EXTRA_CLUSTER_2 = EXTRA_CL[2]
MGMT = "management"
net1 = NETWORKS[0]
net2 = NETWORKS[1]
net3 = NETWORKS[2]
