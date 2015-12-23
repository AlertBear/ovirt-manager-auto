#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for datacenters networks test
"""
from rhevmtests.networking.config import *  # NOQA


CREATE_NET_DICT = {
    "description": "New network",
    "stp": True,
    "vlan_id": 500,
    "usages": [],
    "mtu": 5555
}
VERIFY_NET_LIST = ["description", "stp", "vlan_id", "usages", "mtu"]
DC_NAMES = [DC_NAME[0], "DataCenter_Network_DC2"]
