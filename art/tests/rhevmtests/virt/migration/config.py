#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration config file
"""

from rhevmtests.virt.config import *  # flake8: noqa
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper

CANCEL_VM_MIGRATE = False
MIGRATION_VM = VM_NAME[0]
MIGRATION_VM_LOAD = "virt_migration_vm"
CONNECTIVITY_CHECK = False if PPC_ARCH else True
MIGRATION_IMAGE_VM = "vm_with_loadTool"
OS_RHEL_7 = ENUMS['rhel7x64']
HOST_INDEX_MAX_MEMORY = -1
# for network migration check
NUM_PACKETS = 500

REAL_VLANS = [str(i) for i in xrange(162, 169)]
NETS = global_helper.generate_object_names(
    num_of_cases=13, num_of_objects=5, prefix="mig"
)
# network for all migration cases
NETS_DICT = {
    NETS[1][0]: {
        "required": "true",
    },
    NETS[1][1]: {
        "required": "true",
    },
    NETS[2][0]: {
        "required": "true",
        "vlan_id": REAL_VLANS[0]
    },
    NETS[2][1]: {
        "required": "true",
    },
    NETS[3][0]: {
        "required": "true",
        "usages": "",
    },
    NETS[3][1]: {
        "required": "true",
    },
    NETS[4][0]: {
        "required": "true",
    },
    NETS[4][1]: {
        "required": "true",
    },
    NETS[5][0]: {
        "required": "true",
    },
    NETS[5][1]: {
        "required": "true",
    },
    NETS[6][0]: {
        "required": "true",
    },
    NETS[7][0]: {
        "required": "true",
    },
    NETS[7][1]: {
        "required": "true",
    },
    NETS[8][0]: {
        "required": "true",
        "usages": "",
    },
    NETS[8][1]: {
        "required": "true",
    },
    NETS[9][0]: {
        "required": "true",
        "vlan_id": REAL_VLANS[1]
    },
    NETS[9][1]: {
        "required": "true",
    },
    NETS[10][0]: {
        "required": "true",
    },
    NETS[10][1]: {
        "required": "true",
    },
    NETS[11][0]: {
        "required": "true",
    },
}
# Network setup parameters
NETMASK = "255.255.0.0"
NET_1 = None
NET_2 = None
NETWORK_NAMES = ['net_1', 'net_2']
IPS = network_helper.create_random_ips()
# 2 Hosts without bonds
HOSTS_NETS_NIC_DICT = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": NETMASK
                },
            }
        },
        NETWORK_NAMES[1]: {
            "nic": 2,
            "network": None
        }
    },
    1: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[1],
                    "netmask": NETMASK
                },
            }
        },
        NETWORK_NAMES[1]: {
            "nic": 2,
            "network": None
        }
    }
}
# 2 Hosts with bonds
HOSTS_NETS_NIC_DICT_WITH_BONDS = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": None,
            "slaves": [2, 3],
            "network": None,
            "mode": 4,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": NETMASK
                }
            }
        },
        NETWORK_NAMES[1]: {
            "nic": 1,
            "network": None
        }
    },
    1: {
        NETWORK_NAMES[0]: {
            "nic": None,
            "slaves": [2, 3],
            "network": None,
            "mode": 4,
            "ip": {
                "1": {
                    "address": IPS[1],
                    "netmask": NETMASK
                }
            }
        },
        NETWORK_NAMES[1]: {
            "nic": 1,
            "network": None
        }
    }
}
# With one HOST
HOST_NET_NIC_DICT = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": NETMASK
                },
                "2": {
                    "address": IPS[1],
                    "netmask": NETMASK
                }
            }
        }
    }
}
