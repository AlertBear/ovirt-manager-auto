#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for io networks test
"""
import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(num_of_cases=11, num_of_objects=6)
LABEL_NAME = global_helper.generate_object_names(
    num_of_cases=10, num_of_objects=12, prefix="label"
)
NET_DICT = {
    "invalid_ips": {
        "required": "false",
    },
    "invalid_netmask": {
        "required": "false",
    },
    NETS[4][0]: {
        "required": "false",
    },
    NETS[5][0]: {
        "required": "false",
    },
    NETS[10][0]: {
        "required": "false"
    },
    NETS[10][1]: {
        "required": "false"
    },
}
