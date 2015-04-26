#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for cumulative_rx_tx_statistics
"""

from rhevmtests.networking.config import *  # NOQA
import rhevmtests.networking.helper as net_helper

NET_0 = NETWORKS[0]
NET_1 = NETWORKS[1]
NIC_1 = NIC_NAME[1]
DC_0 = DC_NAME[0]
IPS = net_helper.create_random_ips()
STAT_KEYS = ["data.total.rx", "data.total.tx"]
ETH0 = VM_NICS[0]
