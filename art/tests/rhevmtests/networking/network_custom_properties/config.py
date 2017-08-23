#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for network custom properties
"""
from collections import OrderedDict

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

BRIDGE_OPTS = OrderedDict(
    {
        "priority": ["32768", "1"],
        "multicast_querier": ["0", "1"]
    }
)
KEY1 = BRIDGE_OPTS.keys()[0]
KEY2 = BRIDGE_OPTS.keys()[1]
PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][1]])
DEFAULT_PRIORITY = "=".join([KEY1, BRIDGE_OPTS[KEY1][0]])
MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][1]])
DEFAULT_MULT_QUERIER = "=".join([KEY2, BRIDGE_OPTS[KEY2][0]])
TX_CHECKSUM = "-K {nic} tx {state}"
RX_CHECKSUM = "-K {nic} rx {state}"
NETS = global_helper.generate_object_names(num_of_cases=15, prefix="cus_pr")

CASE_01_NETS_DICT = {
    NETS[1][0]: {
        "required": "false"
    },
    NETS[1][1]: {
        "required": "false",
        "usages": ""
    },
    NETS[1][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[1][3]: {
        "required": "false",
        "usages": "",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    }
}

CASE_02_NETS_DICT = {
    NETS[2][0]: {
        "required": "false"
    }
}

CASE_03_NETS_DICT = {
    NETS[3][0]: {
        "required": "false"
    },
    NETS[3][1]: {
        "required": "false"
    }
}

CASE_04_NETS_DICT = {
    NETS[4][0]: {
        "required": "false",
    },
    NETS[4][1]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    }
}

CASE_05_NETS_DICT = {
    NETS[5][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[5][1]: {
        "required": "false",
        "usages": ""
    }
}

CASE_06_NETS_DICT = {
    NETS[6][0]: {
        "required": "false"
    }
}

CASE_07_NETS_DICT = {
    NETS[7][0]: {
        "required": "false"
    }
}

CASE_08_NETS_DICT = {
    NETS[8][0]: {
        "required": "false"
    }
}

CASE_09_NETS_DICT = {
    NETS[9][0]: {
        "required": "false"
    }
}

CASE_10_NETS_DICT = {
    NETS[10][0]: {
        "required": "false"
    },
    NETS[11][0]: {
        "required": "false"
    }
}

CASE_11_NETS_DICT = {
    NETS[11][0]: {
        "required": "false"
    }
}

CASE_12_NETS_DICT = {
    NETS[12][0]: {
        "required": "false"
    }
}
