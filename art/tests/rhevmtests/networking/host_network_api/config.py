#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config for Host Network API job
"""

import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper

QOS_NAME = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=6, prefix="QoS"
)
NIC_NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=15, prefix="nic"
)
HOST_NETS = global_helper.generate_object_names(
    num_of_cases=20, num_of_objects=15, prefix="host"
)
SYNC_NETS_DC_1 = global_helper.generate_object_names(
    num_of_cases=25, num_of_objects=15, prefix="sync1_"
)
SN_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=20, prefix="sn"
)
IPV6_NETS = global_helper.generate_object_names(
    num_of_cases=35, num_of_objects=10, prefix="ipv6_"
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
VLAN_IDS = [str(i) for i in xrange(2, 70)]
IPS = network_helper.create_random_ips(num_of_ips=50, mask=24)
IPV6_IPS = network_helper.create_random_ips(
    num_of_ips=50, mask=24, ip_version=6
)
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

IP_DICT_NETMASK = BASIC_IP_DICT_NETMASK["ip"]
IP_DICT_PREFIX = BASIC_IP_DICT_PREFIX["ip"]
IPV6_IP_DICT = BASIC_IPV6_DICT["ip"]


NIC_DICT = {
    NIC_NETS[1][0]: {
        "required": "false"
    },
    NIC_NETS[1][1]: {
        "vlan_id": VLAN_IDS[0],
        "required": "false"
    },
    NIC_NETS[1][2]: {
        "usages": "",
        "required": "false"
    },
    NIC_NETS[1][3]: {
        "required": "false"
    },
    NIC_NETS[1][4]: {
        "required": "false"
    },
    NIC_NETS[1][5]: {
        "vlan_id": VLAN_IDS[1],
        "required": "false"
    },
    NIC_NETS[1][6]: {
        "vlan_id": VLAN_IDS[2],
        "required": "false"
    },
    NIC_NETS[1][7]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[1][8]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[1][9]: {
        "required": "false"
    },
    NIC_NETS[1][10]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[6]
    },
    NIC_NETS[1][11]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[7]
    },
    NIC_NETS[1][12]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[8]
    },
    NIC_NETS[2][0]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    NIC_NETS[2][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[3],
        "mtu": conf.MTU[0]
    },
    NIC_NETS[2][2]: {
        "required": "false"
    },
    NIC_NETS[3][0]: {
        "required": "false"
    },
    NIC_NETS[3][1]: {
        "required": "false"
    },
    NIC_NETS[3][2]: {
        "required": "false"
    },
    NIC_NETS[3][3]: {
        "required": "false",
        "usages": ""
    },
    NIC_NETS[3][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS[4]
    },
    NIC_NETS[3][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[5]
    },
    NIC_NETS[3][6]: {
        "required": "false"
    }
}

SN_DICT = {
    SN_NETS[1][0]: {
        "required": "false"
    },
    SN_NETS[1][1]: {
        "vlan_id": VLAN_IDS[9],
        "required": "false"
    },
    SN_NETS[1][2]: {
        "usages": "",
        "required": "false"
    },
    SN_NETS[1][3]: {
        "required": "false"
    },
    SN_NETS[1][4]: {
        "required": "false"
    },
    SN_NETS[1][5]: {
        "vlan_id": VLAN_IDS[10],
        "required": "false"
    },
    SN_NETS[1][6]: {
        "vlan_id": VLAN_IDS[11],
        "required": "false"
    },
    SN_NETS[1][7]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[1][8]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[1][9]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    SN_NETS[1][10]: {
        "required": "false",
        "vlan_id": VLAN_IDS[12],
        "mtu": conf.MTU[0]
    },
    SN_NETS[1][11]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[17]
    },
    SN_NETS[1][12]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[18]
    },
    SN_NETS[1][13]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[19]
    },
    SN_NETS[1][14]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[1][15]: {
        "required": "false",
        "vlan_id": VLAN_IDS[20]
    },
    SN_NETS[1][16]: {
        "required": "false",
        "vlan_id": VLAN_IDS[21]
    },
    SN_NETS[2][0]: {
        "required": "false"
    },
    SN_NETS[2][1]: {
        "required": "false"
    },
    SN_NETS[2][2]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[2][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[13]
    },
    SN_NETS[2][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS[14]
    },
    SN_NETS[3][0]: {
        "required": "false"
    },
    SN_NETS[3][1]: {
        "required": "false",
        "usages": ""
    },
    SN_NETS[3][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[22]
    },
    SN_NETS[3][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[23]
    },
    SN_NETS[6][0]: {
        "required": "false",
    },
    SN_NETS[6][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[48]
    },
    SN_NETS[6][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[49]
    },
    SN_NETS[6][3]: {
        "required": "false",
    },
    SN_NETS[6][4]: {
        "required": "false",
    },
    SN_NETS[6][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[50]
    },
    SN_NETS[7][0]: {
        "required": "false",
    },
    SN_NETS[7][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[51]
    },
    SN_NETS[7][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[52]
    },
    SN_NETS[7][3]: {
        "required": "false",
    },
    SN_NETS[7][4]: {
        "required": "false",
    },
    SN_NETS[7][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[53]
    },
}

HOST_DICT = {
    HOST_NETS[1][0]: {
        "required": "false"
    },
    HOST_NETS[1][1]: {
        "vlan_id": VLAN_IDS[27],
        "required": "false"
    },
    HOST_NETS[1][2]: {
        "usages": "",
        "required": "false"
    },
    HOST_NETS[1][3]: {
        "required": "false"
    },
    HOST_NETS[1][4]: {
        "required": "false"
    },
    HOST_NETS[1][5]: {
        "vlan_id": VLAN_IDS[28],
        "required": "false"
    },
    HOST_NETS[1][6]: {
        "vlan_id": VLAN_IDS[29],
        "required": "false"
    },
    HOST_NETS[1][7]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[1][8]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[1][9]: {
        "required": "false"
    },
    HOST_NETS[1][10]: {
        "required": "false",
        "vlan_id": VLAN_IDS[33]
    },
    HOST_NETS[1][11]: {
        "required": "false",
        "vlan_id": VLAN_IDS[34]
    },
    HOST_NETS[1][12]: {
        "required": "false",
        "vlan_id": VLAN_IDS[35]
    },
    HOST_NETS[2][0]: {
        "required": "false",
        "usages": "",
        "mtu": conf.MTU[1]
    },
    HOST_NETS[2][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[30],
        "mtu": conf.MTU[0]
    },
    HOST_NETS[2][2]: {
        "required": "false"
    },
    HOST_NETS[3][0]: {
        "required": "false"
    },
    HOST_NETS[3][1]: {
        "required": "false"
    },
    HOST_NETS[3][2]: {
        "required": "false"
    },
    HOST_NETS[3][3]: {
        "required": "false",
        "usages": ""
    },
    HOST_NETS[3][4]: {
        "required": "false",
        "vlan_id": VLAN_IDS[31]
    },
    HOST_NETS[3][5]: {
        "required": "false",
        "vlan_id": VLAN_IDS[32]
    },
    HOST_NETS[3][6]: {
        "required": "false"
    },
    HOST_NETS[3][7]: {
        "required": "false"
    },
    HOST_NETS[3][8]: {
        "required": "false",
        "vlan_id": VLAN_IDS[46]
    },
    HOST_NETS[3][9]: {
        "required": "false",
        "vlan_id": VLAN_IDS[47]
    },
    HOST_NETS[3][10]: {
        "required": "false"
    },
}

SYNC_DICT_1 = {
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[36]
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[37]
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
    SYNC_NETS_DC_1[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[42]
    },
    SYNC_NETS_DC_1[2][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[43]
    },
    SYNC_NETS_DC_1[2][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[2][3]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },
    SYNC_NETS_DC_1[2][4]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[2][5]: {
        "required": "false",
    },

    SYNC_NETS_DC_1[2][6]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][7]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[2][8]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[3][0]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[3][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[3][2]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[3][3]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[3][4]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[4][0]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[4][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[4][2]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[4][3]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[4][4]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[5][0]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[5][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[5][1]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[5][2]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[5][2],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[5][3]: {
        "vlan_id": VLAN_IDS[13],
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[5][3],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": None,
            "outbound_average_realtime": None
        }
    },
    SYNC_NETS_DC_1[5][4]: {
        "vlan_id": VLAN_IDS[14],
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[5][4],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": None,
            "outbound_average_realtime": None
        }
    },
    SYNC_NETS_DC_1[6][0]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[6][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[6][1]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[6][2]: {
        "required": "false",
        "qos": {
            "datacenter": conf.DC_0,
            "qos_name": QOS_NAME[6][2],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
}

SYNC_DICT_2 = {
    SYNC_NETS_DC_1[1][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[40]
    },
    SYNC_NETS_DC_1[1][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[1][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[41]
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
        "vlan_id": VLAN_IDS[54],
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[2][0]: {
        "required": "false",
        "vlan_id": VLAN_IDS[44]
    },
    SYNC_NETS_DC_1[2][1]: {
        "required": "false"
    },
    SYNC_NETS_DC_1[2][2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[45]
    },
    SYNC_NETS_DC_1[2][3]: {
        "required": "false",
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[2][4]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[2][5]: {
        "required": "false",
        "mtu": conf.MTU[0]
    },

    SYNC_NETS_DC_1[2][6]: {
        "required": "false",
        "usages": ""
    },
    SYNC_NETS_DC_1[2][7]: {
        "required": "false"
    },

    SYNC_NETS_DC_1[2][8]: {
        "required": "false",
        "vlan_id": VLAN_IDS[55],
        "mtu": conf.MTU[1]
    },
    SYNC_NETS_DC_1[5][0]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[19][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 20,
            "outbound_average_upperlimit": 20,
            "outbound_average_realtime": 20
        }
    },
    SYNC_NETS_DC_1[5][1]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[19][1],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[5][2]: {
        "required": "false",
    },
    SYNC_NETS_DC_1[5][3]: {
        "vlan_id": VLAN_IDS[13],
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[5][3],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": None,
            "outbound_average_realtime": None
        }
    },
    SYNC_NETS_DC_1[5][4]: {
        "vlan_id": VLAN_IDS[14],
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[5][4],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": None,
            "outbound_average_realtime": None
        }
    },
    SYNC_NETS_DC_1[6][0]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[20][0],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 20,
            "outbound_average_upperlimit": 20,
            "outbound_average_realtime": 20
        }
    },
    SYNC_NETS_DC_1[6][1]: {
        "required": "false",
        "qos": {
            "datacenter": SYNC_DC,
            "qos_name": QOS_NAME[20][1],
            "qos_type": "hostnetwork",
            "outbound_average_linkshare": 10,
            "outbound_average_upperlimit": 10,
            "outbound_average_realtime": 10
        }
    },
    SYNC_NETS_DC_1[6][2]: {
        "required": "false",
    }
}

IPV6_NETS_DICT = {
    IPV6_NETS[1][0]: {
        "required": "false"
    },
    IPV6_NETS[1][1]: {
        "required": "false",
        "vlan_id": VLAN_IDS[56]
    },
    IPV6_NETS[1][2]: {
        "required": "false"
    },
    IPV6_NETS[1][3]: {
        "required": "false",
        "vlan_id": VLAN_IDS[57]
    },
    IPV6_NETS[1][4]: {
        "required": "false",
        "usages": ""
    },
    IPV6_NETS[1][5]: {
        "required": "false",
        "usages": "",
        "vlan_id": VLAN_IDS[58]
    },
}
