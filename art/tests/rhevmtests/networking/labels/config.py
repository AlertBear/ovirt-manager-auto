#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for labels test
"""
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf


LABEL_NAME = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=12, prefix="label"
)
NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="label_net"
)
CASE_1_NETS = {
    NETS[1][0]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[1][1]: {
        "required": "false"
    },
    NETS[1][2]: {
        "usages": "",
        "required": "false"
    },
    NETS[1][3]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    }
}

CASE_2_NETS = {
    NETS[2][0]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[2][1]: {
        "required": "false"
    }
}

CASE_3_NETS = {
    NETS[3][0]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "usages": ""
    }
}

CASE_4_NETS = {
    NETS[4][0]: {
        "required": "false"
    }
}

CASE_5_NETS = {
    NETS[5][0]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[5][1]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[5][2]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[5][3]: {
        "usages": "",
        "required": "false"
    },
    NETS[5][4]: {
        "required": "false",
    },
    NETS[5][5]: {
        "required": "false",
        "usages": ""
    },
    NETS[5][6]: {
        "required": "false"
    },
    NETS[5][7]: {
        "required": "false"
    }
}

CASE_6_NETS = {
    NETS[6][0]: {
        "required": "false"
    }
}

CASE_7_NETS = {
    NETS[7][0]: {
        "required": "false"
    },
    NETS[7][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[7][2]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false"
    },
    NETS[7][3]: {
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "required": "false",
        "usages": ""
    }
}

CASE_8_NETS = {
    NETS[8][0]: {
        "required": "false"
    },
    NETS[8][1]: {
        "required": "false"
    },
    NETS[8][2]: {
        "usages": "",
        "required": "false"
    },
    NETS[8][3]: {
        "usages": "",
        "required": "false"
    },
    NETS[8][4]: {
        "required": "false"
    },
    NETS[8][5]: {
        "usages": "",
        "required": "false"
    }
}

CASE_9_NETS = {
    NETS[9][0]: {
        "required": "false"
    },
    NETS[9][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[9][2]: {
        "required": "false"
    },
    NETS[9][3]: {
        "required": "false",
        "usages": ""
    }
}
