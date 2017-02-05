#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for io networks test
"""
import rhevmtests.helpers as global_helper

NETS = global_helper.generate_object_names(
    num_of_cases=11, num_of_objects=6, prefix="io_net_"
)
LABEL_NAME = global_helper.generate_object_names(
    num_of_cases=10, num_of_objects=12, prefix="label"
)
NET_DICT = {
    NETS[2][0]: {
        "required": "false",
    },
    NETS[2][1]: {
        "required": "false",
    },
    NETS[2][2]: {
        "required": "false",
    },
    NETS[2][3]: {
        "required": "false",
    },
    NETS[2][4]: {
        "required": "false",
    },
    NETS[2][5]: {
        "required": "false",
    },
    NETS[3][0]: {
        "required": "false",
    },
    NETS[4][0]: {
        "required": "false"
    },
    NETS[4][1]: {
        "required": "false"
    },
    NETS[4][2]: {
        "required": "false"
    },
    NETS[4][3]: {
        "required": "false"
    },
}
