# -*- coding: utf-8 -*-

"""
Config for default route tests
"""

import rhevmtests.helpers as global_helper

EXTRA_CL_NAME = "Default-route-extra-cluster"
NETS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=4, prefix="dr_"
)

NET_DICT_CASE_01 = {
    NETS[1][0]: {
        "required": "false"
    }
}

NET_DICT_CASE_02 = {
    NETS[2][0]: {
        "required": "false"
    },
    NETS[2][1]: {
        "required": "false"
    }
}
