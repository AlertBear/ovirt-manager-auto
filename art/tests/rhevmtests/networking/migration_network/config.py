#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Migration Network config
"""

import rhevmtests.helpers as global_helper
from rhevmtests.networking import (
    config as network_conf,
    helper as network_helper
)
import rhevmtests.networking.config as config

# Host migration participants index list
MIGRATION_HOSTS = [0, 1]

# VM settings
VM_NAME = network_conf.VM_0
VM_ADDITIONAL_VNIC = "migration_network_vnic"
VM_ORIGIN_HOSTER_INDEX = 1

# TCPDump number of migration PCAPs to capture
TCPDUMP_PACKETS_COUNT = 500

# TCPDump Running timeout (in minutes)
TCPDUMP_TIMEOUT = 4

# Total timeout (in minutes) for all migration tests
DEFAULT_MIGRATION_TIMEOUT = 4

# Total timeout (in minutes) for required NIC down PCAP test
REQUIRED_NIC_MIGRATION_TIMEOUT = 3

# Total ICMP packets to send when testing destination migration IP connection
ICMP_DST_IP_COUNT = 1

# VLAN ID's that are configured on the switch (not arbitrary)
VLAN_CASE_2 = network_conf.REAL_VLANS[0] if network_conf.REAL_VLANS else None
VLAN_CASE_8 = network_conf.REAL_VLANS[1] if network_conf.REAL_VLANS else None

# BONDs names
BOND_CASE_6 = "bond6"
BOND_CASE_7 = "bond7"
BOND_CASE_8 = "bond8"

# BOND mode
BOND_MODE = 4

# Host setup Network settings
NETWORK_NAMES = ["mig_net_%s" % (i + 1) for i in range(2)]

# Two random IP addresses
IPS = network_helper.create_random_ips(mask=24)
IPSV6 = network_helper.create_random_ips(mask=24, ip_version=6)

NETS = global_helper.generate_object_names(
    num_of_cases=11, num_of_objects=2, prefix="mig"
)

# clean_host_interfaces_fixture_function cleanup dict
CLEANUP_HOSTS_SETUP_DICT = {
    0: {},
    1: {}
}

# Networks used in tests
SETUP_NETWORKS_DICT = {
    NETS[1][0]: {
        "required": "true",
    },
    NETS[1][1]: {
        "required": "true",
    },
    NETS[2][0]: {
        "required": "true",
        "vlan_id": VLAN_CASE_2
    },
    NETS[3][0]: {
        "required": "true",
        "usages": "",
    },
    NETS[4][0]: {
        "required": "true",
    },
    NETS[5][0]: {
        "required": "true",
    },
    NETS[6][0]: {
        "required": "true",
    },
    NETS[7][0]: {
        "required": "true",
        "usages": "",
    },
    NETS[8][0]: {
        "required": "true",
        "vlan_id": VLAN_CASE_8
    },
    NETS[9][0]: {
        "required": "true",
    },
    NETS[10][0]: {
        "required": "true",
    },
    NETS[11][0]: {
        "required": "true",
    }
}

# Host network setup template for two hosts with two NICs
HOSTS_NETS_TWO_NIC_DICT = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": config.NETMASK
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
                    "netmask": config.NETMASK
                },
            }
        },
        NETWORK_NAMES[1]: {
            "nic": 2,
            "network": None
        }
    }
}


# Host network setup template for two hosts with one NIC
HOSTS_NETS_ONE_NIC_DICT = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": config.NETMASK
                },
            }
        }
    },
    1: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[1],
                    "netmask": config.NETMASK
                },
            }
        }
    }
}

# Host network setup template for two hosts with BONDs
HOSTS_NETS_NIC_DICT_WITH_BONDS = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": None,
            "slaves": [2, 3],
            "network": None,
            "mode": BOND_MODE,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": config.NETMASK
                }
            }
        }
    },
    1: {
        NETWORK_NAMES[0]: {
            "nic": None,
            "slaves": [2, 3],
            "network": None,
            "mode": BOND_MODE,
            "ip": {
                "1": {
                    "address": IPS[1],
                    "netmask": config.NETMASK
                }
            }
        }
    }
}

# Host network setup template for single host
HOST_NET_NIC_DICT = {
    0: {
        NETWORK_NAMES[0]: {
            "nic": 1,
            "network": None,
            "ip": {
                "1": {
                    "address": IPS[0],
                    "netmask": config.NETMASK
                },
            }
        }
    }
}
