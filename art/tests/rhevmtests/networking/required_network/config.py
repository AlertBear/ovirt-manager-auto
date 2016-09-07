#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for required_network test
"""

import rhevmtests.helpers as global_helper

NIC_STATE_DOWN = "down"
NIC_STATE_UP = "up"
VLAN_ID = "999"
NETS = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=1, prefix="req_net"
)
