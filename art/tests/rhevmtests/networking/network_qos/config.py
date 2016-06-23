#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for QoS test
"""

import rhevmtests.helpers as global_helper

M_K_CONVERTER = 1024
BITS_BYTES = 8
QOS_NAME = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=4, prefix="QoS"
)
QOS_TYPE = "network"
BW_PARAMS = (10, 10, 100)
UPDATED_BW_PARAMS = (5, 5, 50)

INBOUND_DICT = {
    "average": BW_PARAMS[0],
    "peak": BW_PARAMS[1],
    "burst": BW_PARAMS[2]
}
OUTBOUND_DICT = {
    "average": BW_PARAMS[0],
    "peak": BW_PARAMS[1],
    "burst": BW_PARAMS[2]
}

INBOUND_DICT_UPDATE = {
    "average": UPDATED_BW_PARAMS[0],
    "peak": UPDATED_BW_PARAMS[1],
    "burst": UPDATED_BW_PARAMS[2]
}
OUTBOUND_DICT_UPDATE = {
    "average": UPDATED_BW_PARAMS[0],
    "peak": UPDATED_BW_PARAMS[1],
    "burst": UPDATED_BW_PARAMS[2]
}
