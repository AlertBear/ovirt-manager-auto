#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for io networks test
"""
from rhevmtests.networking.config import *  # NOQA
import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(num_of_cases=11, num_of_objects=6)
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
    }
}
