#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Data-Center networks
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

DCS = ["DataCenter_Test_%d" % i for i in range(5)]

NETS = global_helper.generate_object_names(
    num_of_cases=4, num_of_objects=5, prefix="DCNet"
)

# DC setup settings
DC_CONFIG = {
    DCS[0]: {
        "name": DCS[0],
        "version": conf.COMP_VERSION,
    },
    DCS[1]: {
        "name": DCS[1],
        "version": conf.COMP_VERSION,
    },
    DCS[2]: {
        "name": DCS[2],
        "version": conf.COMP_VERSION,
    },
    DCS[3]: {
        "name": DCS[3],
        "version": conf.COMP_VERSION,
    },
    DCS[4]: {
        "name": DCS[4],
        "version": conf.COMP_VERSION,
    }
}

# Custom network properties for test_created_network_properties
CUSTOM_NET_PROPERTIES = {
    "description": "New network",
    "stp": False,
    "vlan_id": 500,
    "usages": [],
    "mtu": 5555
}

# Create networks for tests
CREATE_NETWORKS = {
    # Case 1
    DCS[0]: {
        NETS[1][0]: {},
        NETS[1][1]: {}
    },
    DCS[1]: {
        NETS[1][0]: {},
        NETS[1][1]: {}
    },
    # Case 2
    DCS[2]: {
        NETS[2][0]: {
            "usages": []
        },
        NETS[2][1]: {
            "stp": False
        },
        NETS[2][2]: {
            "description": "New network"
        },
        NETS[2][3]: {
            "vlan_id": 500
        },
        NETS[2][4]: {
            "mtu": 5555
        }
    },
    # Case 3
    DCS[3]: {
        NETS[3][0]: {},
        NETS[3][1]: {}
    },
    # Case 4
    DCS[4]: {
        NETS[4][0]: {}
    }
}

# Networks collections to be used in test cases
NETS_CASE_1 = NETS[1][:2]
NETS_CASE_2 = CREATE_NETWORKS.get(DCS[2]).keys()
NETS_CASE_4 = [NETS[4][0]]

# DC used in cases
DCS_CASE_1 = DCS[:2]
DCS_CASE_2 = DCS[2]
DCS_CASE_3 = DCS[3]
DCS_CASE_4 = DCS[4]
