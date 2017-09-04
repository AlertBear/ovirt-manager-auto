#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Jumbo frame test
"""

import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper

CASE_3_IPS = None
CASE_4_IPS = None
CASE_5_IPS = None
CASE_7_IPS = None
CASE_IPS = None
VMS_RESOURCES = dict()

VNICS = global_helper.generate_object_names(
    num_of_cases=10, num_of_objects=5, prefix="jumbo_frame_vnic"
)
NETS = global_helper.generate_object_names(
    num_of_cases=10, num_of_objects=10, prefix="jumbo_net"
)

NETS_RESTORE_MTU = ["net_restore_%s" % i for i in range(3)]

CASE_1_NETS = {
    NETS[1][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
    }
}

CASE_2_NETS = {
    NETS[2][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "usages": "",
    },
    NETS[2][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "usages": "",
    },
}

CASE_3_NETS = {
    NETS[3][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
    },
}

CASE_4_NETS = {
    NETS[4][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "vlan_id": conf.REAL_VLANS[2] if conf.REAL_VLANS else None,
        "mtu": conf.MTU[0]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "mtu": conf.MTU[2]
    },
    NETS[4][3]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "mtu": conf.MTU[3]
    },
}

CASE_5_NETS = {
    NETS[5][0]: {
        "required": "false",
        "vlan_id": conf.REAL_VLANS[3] if conf.REAL_VLANS else None,
        "mtu": conf.MTU[1],
    },
}

CASE_6_NETS = {
    NETS[6][0]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
    NETS[6][1]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "usages": "",
    },
}

CASE_7_NETS = {
    NETS[7][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.REAL_VLANS[0] if conf.REAL_VLANS else None,
    },
    NETS[7][1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "vlan_id": conf.REAL_VLANS[1] if conf.REAL_VLANS else None,
    },
}

CASE_8_NETS = {
    NETS[8][0]: {
        "required": "false",
        "mtu": conf.MTU[1],
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
    NETS[8][1]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
}

CASE_9_NETS = {
    NETS[9][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
}

NETS_DICT = {
    NETS_RESTORE_MTU[0]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
    NETS_RESTORE_MTU[1]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
    NETS_RESTORE_MTU[2]: {
        "required": "false",
        "mtu": conf.MTU[3],
    },
}
