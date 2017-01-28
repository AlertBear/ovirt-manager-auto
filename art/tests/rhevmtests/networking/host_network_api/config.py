#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper


VLAN_IDS = [str(i) for i in xrange(2, 70)]
NETS = global_helper.generate_object_names(
    num_of_cases=7, num_of_objects=40, prefix="HostNetApi"
)

NETS_CLASS_01_DICT = {
    # host_network_api_test: test_attach_network_to_nic networks
    # via HostNic
    NETS[1][0]: {
        "required": "false"
    },
    NETS[1][1]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[1][2]: {
        "usages": "",
        "required": "false"
    },
    NETS[1][3]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # via Host
    NETS[1][4]: {
        "required": "false"
    },
    NETS[1][5]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[1][6]: {
        "usages": "",
        "required": "false"
    },
    NETS[1][7]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # via SetupNetwork
    NETS[1][8]: {
        "required": "false"
    },
    NETS[1][9]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[1][10]: {
        "usages": "",
        "required": "false"
    },
    NETS[1][11]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
}

NETS_CLASS_02_DICT = {
    # host_network_api: test_attach_network_with_ip_to_nic params
    # via HostNic
    NETS[2][0]: {
        "required": "false"
    },
    NETS[2][1]: {
        "required": "false"
    },
    NETS[2][2]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][3]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][4]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][5]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][6]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[2][7]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # via Host
    NETS[2][8]: {
        "required": "false"
    },
    NETS[2][9]: {
        "required": "false"
    },
    NETS[2][10]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][11]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][12]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][13]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][14]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[2][15]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # via SetupNetworks
    NETS[2][16]: {
        "required": "false"
    },
    NETS[2][17]: {
        "required": "false"
    },
    NETS[2][18]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][19]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false"
    },
    NETS[2][20]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][21]: {
        "required": "false",
        "usages": ""
    },
    NETS[2][22]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[2][23]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
}


NETS_CLASS_03_DICT = {
    # host_network_api: test_attach_network_with_ip_to_nic params
    # via HostNic
    NETS[3][0]: {
        "required": "false"
    },
    # via Host
    NETS[3][1]: {
        "required": "false"
    },
    # via SetupNetworks
    NETS[3][2]: {
        "required": "false"
    }
}

NETS_CLASS_04_DICT = {
    # host_network_api: test_mtu_negative params
    NETS[4][0]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NETS[4][1]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NETS[4][2]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NETS[4][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
        "mtu": conf.MTU[0]
    },
}

NETS_CLASS_05_DICT = {
    # host_network_api: test_update_network_with_ip_nic params
    NETS[5][0]: {
        "required": "false",
    },
    NETS[5][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[5][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[5][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[5][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[5][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[5][6]: {
        "required": "false",
    },
}

NETS_CLASS_06_DICT = {
    # host_network_api: test_remove_un_managed_network
    NETS[6][0]: {
        "required": "false",
    },
    NETS[6][1]: {
        "required": "false",
    },
    NETS[6][2]: {
        "required": "false",
    },
    NETS[6][3]: {
        "required": "false",
    }
}

NETS_CLASS_07_DICT = {
    # host_network_api: test_attach_network_to_nic_mixeds etup_network_fixture
    NETS[7][0]: {
        "required": "false",
    },
    NETS[7][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][2]: {
        "required": "false"
    },
    NETS[7][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][4]: {
        "required": "false",
    },
    NETS[7][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][6]: {
        "required": "false",
    },
    NETS[7][7]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # host_network_api: test_attach_network_to_nic_mixed test
    NETS[7][8]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][9]: {
        "required": "false",
    },
    NETS[7][10]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][11]: {
        "required": "false",
    },
    NETS[7][12]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][13]: {
        "required": "false",
    },
    NETS[7][14]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    NETS[7][15]: {
        "required": "false",
    },
}

QOS_NAME = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=6, prefix="host_net_qos"
)
SYNC_NETS_DC_1 = global_helper.generate_object_names(
    num_of_cases=25, num_of_objects=50, prefix="sync1_"
)
SN_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=20, prefix="sn"
)
IPV6_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=30, prefix="ipv6_"
)
PERSIST_NETS = global_helper.generate_object_names(
    num_of_cases=1, num_of_objects=2, prefix="persist_"
)

SYNC_DC = "Sync_DC"
SYNC_CL = "Sync_cluster"
NUM_DUMMYS = 15
DUMMYS = ["dummy_%s" % i for i in xrange(NUM_DUMMYS)]
VLAN_STR = "vlan"
MTU_STR = "mtu"
BRIDGE_STR = "bridged"
BOOTPROTO_STR = "ipv4_boot_protocol"
NETMASK_STR = "ipv4_netmask"
IPADDR_STR = "ipv4_address"
AVERAGE_SHARE_STR = "outAverageLinkShare"
AVERAGE_LIMIT_STR = "outAverageUpperLimit"
AVERAGE_REAL_STR = "outAverageRealTime"
QOS_VALUES = [AVERAGE_SHARE_STR, AVERAGE_LIMIT_STR, AVERAGE_REAL_STR]
VLAN_IDS = [str(i) for i in xrange(2, 200)]
IPS = network_helper.create_random_ips(num_of_ips=50, mask=24)
IPV6_IPS = network_helper.create_random_ips(
    num_of_ips=50, mask=24, ip_version=6
)
IPV4_IPS = network_helper.create_random_ips(num_of_ips=50, mask=24)
BASIC_IP_DICT_NETMASK = {
    "ip": {
        "address": None,
        "netmask": "255.255.255.0",
        "boot_protocol": "static"
    }
}

BASIC_IP_DICT_PREFIX = {
    "ip": {
        "address": None,
        "netmask": "24",
        "boot_protocol": "static"
    }
}

BASIC_IPV6_DICT = {
    "ip": {
        "address": None,
        "netmask": "24",
        "boot_protocol": "static",
        "version": "v6"
    }
}

BASIC_IPV4_AND_IPV6_DICT = {
    "ipv6": {
        "address": None,
        "netmask": "24",
        "boot_protocol": "static",
        "version": "v6"
    },
    "ipv4": {
        "address": None,
        "netmask": "24",
        "boot_protocol": "static"
    }
}

IP_DICT_NETMASK = BASIC_IP_DICT_NETMASK["ip"]
IP_DICT_PREFIX = BASIC_IP_DICT_PREFIX["ip"]
IPV6_IP_DICT = BASIC_IPV6_DICT["ip"]

SN_DICT = {
    # test_multiple_vlans_networks_on_nic params
    SN_NETS[1][0]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false",
    },
    SN_NETS[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[1][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[1][3]: {
        "vlan_id": VLAN_IDS.pop(0),
        "required": "false",
    },
    SN_NETS[1][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[1][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[2][0]: {
        "required": "false"
    },
    SN_NETS[3][0]: {
        "required": "false"
    },
    SN_NETS[3][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[3][2]: {
        "required": "false",
    },
    SN_NETS[3][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[3][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[3][5]: {
        "required": "false",
    },
    SN_NETS[3][6]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[4][0]: {
        "required": "false"
    },
    SN_NETS[4][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SN_NETS[4][2]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[4][3]: {
        "required": "false"
    },
}


SYNC_DICT_1_CASE_1 = {
    # On NIC
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][3]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    SYNC_NETS_DC_1[1][4]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[1][5]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][6]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][7]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[1][8]: {
        "required": "false",
        "usages": ""
    },
    # On BOND
    SYNC_NETS_DC_1[1][9]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][10]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][11]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][12]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    SYNC_NETS_DC_1[1][13]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[1][14]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][15]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][16]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[1][17]: {
        "required": "false",
        "usages": ""
    },
}

SYNC_DICT_2_CASE_1 = {
    # On NIC
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][3]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[1][4]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][5]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    SYNC_NETS_DC_1[1][6]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[1][7]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][8]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
        "mtu": conf.MTU[1]
    },
    # On BOND
    SYNC_NETS_DC_1[1][9]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][10]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][11]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    SYNC_NETS_DC_1[1][12]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[1][13]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[1][14]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    SYNC_NETS_DC_1[1][15]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[1][16]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][17]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
        "mtu": conf.MTU[1]
    },
}

IP_DICT_CASE_2 = {
    # NIC
    SYNC_NETS_DC_1[2][0]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][2]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][3]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][4]: {
        "required": "false"
    },
    # BOND
    SYNC_NETS_DC_1[2][5]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][6]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][7]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][8]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][9]: {
        "required": "false"
    },
}

SYNC_DICT_1_CASE_3 = {
    # NIC
    SYNC_NETS_DC_1[3][0]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[3][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[3][1]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[3][2]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[3][1],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    # BOND
    SYNC_NETS_DC_1[3][3]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[3][2],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[3][4]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[3][5]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[3][3],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
}

SYNC_DICT_2_CASE_3 = {
    # NIC
    SYNC_NETS_DC_1[3][0]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[3][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 20,
            "outbound_average_upperlimit": 20,
            "outbound_average_realtime": 20
        }
    },
    SYNC_NETS_DC_1[3][1]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[3][1],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[3][2]: {
        "required": "false",
    },
    # BOND
    SYNC_NETS_DC_1[3][3]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[3][2],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 20,
            "outbound_average_upperlimit": 20,
            "outbound_average_realtime": 20
        }
    },
    SYNC_NETS_DC_1[3][4]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[3][3],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[3][5]: {
        "required": "false",
    }
}

IPV6_NETS_CLASS_1 = {
    # Static
    IPV6_NETS[1][0]: {
        "required": "false"
    },
    IPV6_NETS[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][2]: {
        "required": "false"
    },
    IPV6_NETS[1][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][4]: {
        "required": "false",
        "usages": ""
    },
    IPV6_NETS[1][5]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # autoconf
    IPV6_NETS[1][6]: {
        "required": "false"
    },
    IPV6_NETS[1][7]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][8]: {
        "required": "false"
    },
    IPV6_NETS[1][9]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][10]: {
        "required": "false",
        "usages": ""
    },
    IPV6_NETS[1][11]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
    # DHCP
    IPV6_NETS[1][12]: {
        "required": "false"
    },
    IPV6_NETS[1][13]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][14]: {
        "required": "false"
    },
    IPV6_NETS[1][15]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
    },
    IPV6_NETS[1][16]: {
        "required": "false",
        "usages": ""
    },
    IPV6_NETS[1][17]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS.pop(0),
    },
}

IPV6_NETS_CLASS_2 = {
    # Static
    IPV6_NETS[2][0]: {
        "required": "false"
    },
    IPV6_NETS[2][1]: {
        "required": "false",
    },
    IPV6_NETS[2][2]: {
        "required": "false"
    },
    IPV6_NETS[2][3]: {
        "required": "false",
    },
    IPV6_NETS[2][4]: {
        "required": "false",
    },
}

PERSIST_NETS_DICT = {
    PERSIST_NETS[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
        "mtu": conf.MTU[0]

    },
    PERSIST_NETS[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS.pop(0),
        "mtu": conf.MTU[0]
    }
}

QOS_VAL = 10
QOS = {
    "type_": "hostnetwork",
    "outbound_average_linkshare": QOS_VAL,
    "outbound_average_realtime": QOS_VAL,
    "outbound_average_upperlimit": QOS_VAL
}
