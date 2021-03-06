#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for port mirroring
"""

from rhevmtests.networking import config as conf, helper as network_helper

VMS_NETWORKS_PARAMS = dict()
NUM_VMS = 5
NET1_IPS = network_helper.create_random_ips(num_of_ips=6)
NET2_IPS = network_helper.create_random_ips(num_of_ips=6, base_ip_prefix="6")
PM_NETWORK = ["pm_net_1", "pm_net_2", "pm_net_3"]
PM_NIC_NAME = [
    "Port-mirroring-vnic-net-5.5.5", "Port-mirroring-vnic-net-6.6.6"
]
PM_VNIC_PROFILE = [
    '%s_vNIC_PORT_MIRRORING' % net for net in [conf.MGMT_BRIDGE] + PM_NETWORK
]
MGMT_IPS = []  # Gets filled up during the test
VLAN_0 = conf.REAL_VLANS[0] if conf.REAL_VLANS else None
VLAN_1 = conf.REAL_VLANS[1] if conf.REAL_VLANS else None

NETS_DICT = {
    PM_NETWORK[0]: {
        "vlan_id": VLAN_0,
        "required": "false"
    },
    PM_NETWORK[1]: {
        "vlan_id": VLAN_1,
        "required": "false"
    }
}
