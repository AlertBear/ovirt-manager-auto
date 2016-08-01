#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Management As A Role test cases configuration
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

DATA_CENTERS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=1, prefix="mgmt_role_dc"
)

CLUSTERS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=4, prefix="mgmt_role_cl"
)

NETS = global_helper.generate_object_names(
    num_of_cases=8, num_of_objects=4, prefix="mgmt_role_n"
)

NET_DICT_CASE_02 = {
    NETS[2][0]: {
        "required": "true"
    },
    NETS[2][1]: {
        "required": "false"
    }
}

NET_DICT_CASE_03 = {
    NETS[3][0]: {
        "required": "true"
    }
}

NET_DICT_CASE_04 = {
    NETS[4][0]: {
        "required": "true"
    },
    NETS[4][1]: {
        "required": "true",
        "cluster_usages": conf.MIGRATION_NET_USAGE
    },
    NETS[4][2]: {
        "required": "true",
        "cluster_usages": conf.DISPLAY_NET_USAGE
    }
}

NET_DICT_CASE_05 = {
    NETS[5][0]: {
        "required": "true"
    }
}

NET_DICT_CASE_06 = {
    NETS[6][0]: {
        "required": "true"
    },
    NETS[6][1]: {
        "required": "true"
    }
}

NET_DICT_CASE_07 = {
    NETS[7][0]: {
        "required": "true"
    }
}

NET_DICT_CASE_08_1 = {
    NETS[8][0]: {
        "required": "true"
    }
}

NET_DICT_CASE_08_2 = {
    NETS[8][1]: {
        "required": "true"
    }
}
