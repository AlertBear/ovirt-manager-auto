#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Config for acquire connections created by NetworkManager
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf

TIMEOUT = 10
CON_DOWN_CMD = "nmcli connection down {connection}"
CON_UP_CMD = "nmcli connection up {connection}"
CONNECT_CMD = "nmcli device connect {nic}"
SED_CMD = "sed -i /NM_CONTROLLED=no/d {path_}/ifcfg-{nic}"
RELOAD_CMD = "nmcli connection reload"
BASE_CMD = (
    "nmcli connection add type {type_} con-name {connection} "
    "ifname {nic} ipv4.method disabled ipv6.method ignore"
)
VLAN_CMD = (
    "nmcli connection add type {type_} con-name {connection} "
    "ifname {nic}.{vlan_id_1} ipv4.method disabled ipv6.method ignore "
    "dev {dev} id {vlan_id_2}"
)
BOND_CMD = (
    "nmcli connection add type bond con-name bond1 ifname bond1 mode "
    "active-backup ipv4.method disabled ipv6.method ignore"
)
SLAVE_CMD = (
    "nmcli connection modify id {slave} connection.slave-type "
    "bond connection.master bond1 connection.autoconnect yes"
)
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
        "vlan_id": conf.VLAN_IDS.pop(0),
    },
}
