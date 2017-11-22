#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for sanity test
"""

import rhevmtests.helpers as global_helper
from rhevmtests.networking import config as conf, helper as network_helper


# Host network QoS
QOS_NAME = global_helper.generate_object_names(
    num_of_cases=3, num_of_objects=1, prefix="sanity_qos"
)

# Networks
NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="sanity_net"
)

# vNIC profiles
VNIC_PROFILES = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=1, prefix="sanity_vnic_profile"
)

VNICS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=10, prefix="sanity_vnic"
)
# Register_domain
EXTRA_SD_NAME = "sanity_register_domain_network_SD"
REGISTER_VM_NAME = "sanity_register_domain_network_vm"
MAC_NOT_IN_POOL = "00:00:00:00:00:01"
REGISTER_VM_NIC = "sanity_register_domain_vnic"

IPV6_IPS = network_helper.create_random_ips(mask=24, ip_version=6)

HOST_NAME = None  # Filled in test
HOST_VDS = None  # Filled in test

BASIC_IP_DICT_NETMASK = {
    "ip_netmask": {
        "address": "1.1.1.1",
        "netmask": "255.255.255.0",
        "boot_protocol": "static"
    }
}

BASIC_IP_DICT_PREFIX = {
    "ip_prefix": {
        "address": "2.2.2.2",
        "netmask": "24",
        "boot_protocol": "static"
    }
}

CASE_1_NETS = {
    NETS[1][0]: {
        "required": "false",
    }
}

CASE_2_NETS = {
    NETS[2][0]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][1]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[2][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[2][3]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][4]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[2][5]: {
        "required": "false",
        "usages": ""
    }
}

CASE_3_NETS = {
    NETS[3][0]: {
        "required": "false",
    }
}

CASE_4_NETS = {
    NETS[4][0]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NETS[4][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "mtu": conf.MTU[1]
    },
    NETS[4][3]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    NETS[4][4]: {
        "required": "false",
        "usages": ""
    },
    NETS[4][5]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "usages": "",
    },
    NETS[4][6]: {
        "required": "false",
        "usages": ""
    },
    NETS[4][7]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
        "usages": ""
    }
}

CASE_5_NETS = {
    NETS[5][0]: {
        "required": "false",
    },
    NETS[5][1]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
    NETS[5][2]: {
        "required": "false",
    },
    NETS[5][3]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    }
}

CASE_6_NETS = {
    NETS[6][0]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[6][1]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    },
    NETS[6][2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0)
    },
    NETS[6][3]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    }
}

CASE_8_NETS = {
    NETS[8][0]: {
        "required": "true",
    }
}

CASE_9_NETS = {
    NETS[9][0]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    NETS[9][1]: {
        "required": "false",
    },
    NETS[9][2]: {
        "required": "false",
    }
}

CASE_10_NETS = {
    NETS[10][0]: {
        "required": "false",
    }
}

CASE_12_NETS = {
    NETS[12][0]: {
        "required": "false",
    }
}

CASE_14_NETS = {
    NETS[14][0]: {
        "required": "false",
    }
}

CASE_16_NETS = {
    NETS[16][0]: {
        "required": "false",
    },
    NETS[16][1]: {
        "required": "false",
    }
}

CASE_17_NETS = {
    NETS[17][0]: {
        "required": "false",
    }
}

CASE_18_NETS = {
    NETS[18][0]: {
        "required": "false"
    }
}

# OVN tests
OVN_PROVIDER = None
OVN_NET_1 = NETS[19][0]

OVN_NETS = {
    OVN_NET_1: None
}

OVN_SUBNETS = ["sanity_ovn_subnet_%s" % i for i in range(1, 3)]

OVN_SUBNET_1 = {
    "name": OVN_SUBNETS[0],
    "cidr": "10.0.0.0/24",
    "enable_dhcp": True,
    "ip_version": 4,
    "network_id": None
}

# OVN extra vNIC name
OVN_VNIC = "sanity_ovn_vnic"
