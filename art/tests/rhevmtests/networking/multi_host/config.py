#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for MultiHost
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf


VNICS = global_helper.generate_object_names(
    num_of_cases=7, num_of_objects=3, prefix="multi_host_vnic"
)

NETS = global_helper.generate_object_names(
    num_of_cases=2, num_of_objects=30, prefix="MultiHost"
)

BOND_NAMES = ["bond%s" % i for i in range(0, 10)]

NETWORK_RENAME_TEST = "MULTIHOST_TEST"
EXTRA_CLUSTER_NAME = "Multi_Host_Cluster"

MSG_UPDATED_PREFIX = "Checking if network: {net} property: {prop} updated on"
MSG_UPDATED_ENGINE = "%s engine" % MSG_UPDATED_PREFIX
MSG_UPDATED_HOST = "%s host: {host}" % MSG_UPDATED_PREFIX
MSG_NOT_UPDATED_HOST = (
    "Network: {net} property: {prop} not updated on host: {host}"
)

CREATE_NETWORKS_DICT = {
    # Test case: VM network attached to host
    NETS[1][0]: {
        "required": "false",
        "usages": "vm"
    },
    # Test case: non-VM network attached to host
    NETS[1][1]: {
        "required": "false",
        "usages": ""
    },
    # Test case: Network attached to host
    NETS[1][2]: {
        "required": "false"
    },
    # Test case: Network with VLAN attached to host
    NETS[1][3]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    # Test case: Network attached to running VM
    NETS[1][4]: {
        "required": "false"
    },
    # Test case: Network attached to non-running VM
    NETS[1][5]: {
        "required": "false"
    },
    # Test case: Network attached to template
    NETS[1][6]: {
        "required": "false"
    },
    # Test case: Network attached to two hosts
    NETS[1][7]: {
        "required": "false"
    },
    # Test case: Network attached to two hosts, different cluster
    NETS[1][8]: {
        "required": "false"
    },
    # Test case: VM network attached to bond
    NETS[1][9]: {
        "required": "false"
    },
    # Test case: non-VM network attached to bond
    NETS[1][10]: {
        "required": "false",
        "usages": ""
    },
    # Test case: network attached to bond
    NETS[1][11]: {
        "required": "false"
    },
    # Test case: network with VLAN attached to bond
    NETS[1][12]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    # Test case: network with MTU attached to bond
    NETS[1][13]: {
        "required": "false",
        "mtu": 9000
    }
}
