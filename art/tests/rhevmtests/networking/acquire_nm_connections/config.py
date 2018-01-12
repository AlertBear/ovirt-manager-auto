# -*- coding: utf-8 -*-

"""
Config for acquire connections created by NetworkManager
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as network_config

NETS = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=5, prefix="nm_network"
)

CASE_1_NETS = {
    NETS[1][0]: {
        "required": "false"
    },
    NETS[1][1]: {
        "required": "false"
    },
    NETS[1][2]: {
        "required": "false",
        "vlan_id": network_config.DUMMY_VLANS.pop(0),
    },
}
