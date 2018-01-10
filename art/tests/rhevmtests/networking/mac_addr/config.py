"""
Config file for mac_addr tests
"""

import rhevmtests.helpers as global_helper
from rhevmtests.networking import config

NETS = global_helper.generate_object_names(
    num_of_cases=2, num_of_objects=8, prefix="macaddr_net"
)
RESET_NETS = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=3, prefix="macaddr_rst"
)

CASE_NM_NETS = {
    NETS[1][0]: {
        "required": "false"
    },
    NETS[1][1]: {
        "required": "false",
        "vlan_id": config.DUMMY_VLANS.pop(0),
    },
    NETS[1][2]: {
        "required": "false",
    },
    NETS[1][3]: {
        "required": "false",
        "vlan_id": config.DUMMY_VLANS.pop(0),
        },
}

CASE_IFCFG_NETS = {
    NETS[2][0]: {
        "required": "false"
    },
    NETS[2][1]: {
        "required": "false",
        "vlan_id": config.DUMMY_VLANS.pop(0),
    },
    NETS[2][2]: {
        "required": "false",
    },
    NETS[2][3]: {
        "required": "false",
        "vlan_id": config.DUMMY_VLANS.pop(0),
        },
}

FIXTURE_RESET_NETS = {
    RESET_NETS[1][0]: {
        "required": "false"
    },
    RESET_NETS[1][1]: {
        "required": "false"
    },
    RESET_NETS[1][2]: {
        "required": "false"
    },
}
ALL_NETS = {}
ALL_NETS.update(CASE_NM_NETS)
ALL_NETS.update(CASE_IFCFG_NETS)
ALL_NETS.update(FIXTURE_RESET_NETS)
