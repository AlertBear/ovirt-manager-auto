#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration config file
"""

from rhevmtests.virt.config import *  # flake8: noqa
import rhevmtests.networking.config as network_conf
import rhevmtests.helpers as global_helper
import rhevmtests.networking.helper as network_helper

CANCEL_VM_MIGRATE = False
MIGRATION_VM = VM_NAME[0]
MIGRATION_VM_LOAD = "virt_migration_vm"
CONNECTIVITY_CHECK = False if PPC_ARCH else True
MIGRATION_IMAGE_VM = "vm_with_loadTool"
OS_RHEL_7 = ENUMS['rhel7x64']
HOST_INDEX_MAX_MEMORY = -1
DATA_CENTER_NAME = DC_NAME[0]
# for network migration check
NUM_PACKETS = 500

REAL_VLANS = network_conf.VLAN_ID
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
            }
        }
    }
}


# migration policy name
MIGRATION_POLICY_MINIMAL_DOWNTIME = 'minimal_downtime'
MIGRATION_POLICY_LEGACY = 'legacy'
MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED = 'suspend_workload_if_needed'
MIGRATION_POLICY_POST_COPY = 'post_copy_migration'
MIGRATION_POLICY_INHERIT = 'inherit'  # inherit from policy cluster
MIGRATION_POLICY_NAME = [
    MIGRATION_POLICY_MINIMAL_DOWNTIME, MIGRATION_POLICY_LEGACY,
    MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED
]
# migration policy map name to id
MIGRATION_POLICIES = {
    MIGRATION_POLICY_MINIMAL_DOWNTIME: '80554327-0569-496b-bdeb-fcbbf52b827b',
    MIGRATION_POLICY_LEGACY: '00000000-0000-0000-0000-000000000000',
    MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED:
        '80554327-0569-496b-bdeb-fcbbf52b827c',
    MIGRATION_POLICY_POST_COPY: 'a7aeedb2-8d66-4e51-bb22-32595027ce71',
    MIGRATION_POLICY_INHERIT: 'inherit'
}
MIGRATION_BANDWIDTH_AUTO = 'auto'
MIGRATION_BANDWIDTH_HYPERVISOR_DEFAULT = 'hypervisor_default'
MIGRATION_BANDWIDTH_CUSTOM = 'custom'

CUSTOM_BW_32_MBPS = 32
HYPERVISOR_DEFAULT_BANDWIDTH = 52

MIGRATION_TIMEOUT = 300
