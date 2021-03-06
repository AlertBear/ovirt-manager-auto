#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Consolidated network config module
"""

import art.test_handler.exceptions as exceptions
from rhevmtests.config import *  # flake8: noqa
from rhevmtests.networking.config_handler import DEFAULT_CONFIG_SECTION_NAME

# Global parameters
VIRSH_USER = "virsh"
VIRSH_PASS = "qum5net"
MANAGEMENT_NET_USAGE = "management"
MIGRATION_NET_USAGE = "migration"
DISPLAY_NET_USAGE = "display"
DEFAULT_ROUTE_USAGE = "default_route"
ALL_NETWORK_USAGES = "display,vm,migration,management,default_route"
STORAGE_TYPE = "nfs"
MTU = [9000, 5000, 2000, 1500]
NETMASK = '255.255.255.0'
REAL_VLANS = GE.get('extra_configuration_options').get('vlan_id')
REAL_VLANS = [i.strip() for i in REAL_VLANS.split(',')] if REAL_VLANS else []
VLANS = [str(i) for i in xrange(2, 4096)]
DUMMY_VLANS = filter(lambda vlan_id: vlan_id not in REAL_VLANS, VLANS)

BOND = ["bond%s" % str(i) for i in xrange(10)]
TIMEOUT = 60
NET_EXCEPTION = exceptions.NetworkException
VM_NICS = ['eth0', 'eth1', 'eth2', 'eth3']
FIREWALL_SRV = "iptables"
LABEL_LIST = ["_".join(["label", str(elm)]) for elm in range(10)]
DUMMY_0 = "dummy_0"
DUMP_TIMEOUT = TIMEOUT * 4
DC_0 = DC_NAME[0]
CL_0 = CLUSTER_NAME[0]
CL_1 = CLUSTER_NAME[1]
PASSTHROUGH_INTERFACE = "pci_passthrough"
VM_0 = VM_NAME[0]
VM_1 = VM_NAME[1]
VM_NIC_0 = NIC_NAME[0]
VM_NIC_1 = NIC_NAME[1]
VM_NIC_2 = NIC_NAME[2]
HOST_0_NICS = None  # Filled in test
VDS_0_HOST = None  # Filled in test
HOST_0_NAME = None  # Filled in test
HOST_0_IP = None  # Filled in test
HOST_1_NICS = None  # Filled in test
VDS_1_HOST = None  # Filled in test
HOST_1_NAME = None  # Filled in test
HOST_1_IP = None  # Filled in test
HOSTS_LIST = None  # Filled in setup_package
VDS_2_HOST = None  # Filled in test
HOST_2_NAME = None  # Filled in test
HOST_2_NICS = None  # Filled in test
VDS_HOSTS_LIST = None  # Filled in setup_package
VM_DISK_SIZE = 1024
DEFAULT_MGMT_QOS = "Default-Mgmt-Net-QoS"
LAST_VM = VM_NAME[-1]
CLEAN_HOSTS_DICT = {
    0: {}
}
VMS_TO_STORE = dict()

# MultiHost and multiple_gw parameters
SUBNET = "5.5.5.0"
MG_GATEWAY = "5.5.5.254"
MG_IP_ADDR = "5.5.5.1"

# Jumbo frame parameters
INTER_SUBNET = '3.3.3.'
IPS = ['3.3.3.1', '3.3.3.2']
SEND_MTU = [4500, 8500, 1500, 1000]
SOURCE_IP = '100.1.1.1'
DEST_IP = '100.1.1.2'
GATEWAY = '3.3.3.254'
TRAFFIC_TIMEOUT = 120
VM_IP_LIST = []

# PPC
VM_DISPLAY_TYPE = ENUMS[
    "display_type_vnc"
] if PPC_ARCH else ENUMS["display_type_spice"]

# QoS parameters
QOS_TEST_VALUE = 10
HOST_NET_QOS_TYPE = "hostnetwork"
NET_QOS_TYPE = "network"

# libvirt
LIBVIRTD_CONF = "/etc/libvirt/libvirtd.conf"
SASL_OFF = "none"
SASL_ON = "sasl"

# Network Filter
VDSM_NO_MAC_SPOOFING = "vdsm-no-mac-spoofing"

# Host network api
BASIC_IPV6_DICT = {
    "ip": {
        "address": None,
        "netmask": "24",
        "boot_protocol": "static",
        "version": "v6"
    }
}

# Misc
SSH_TYPE = "ssh"

# LDAP parameters for OVN provider tests
AAA_PROFILES_DIR = "/etc/ovirt-engine/aaa"
AAA_ART_ANSWER_FILES_RELATIVE_PATH = "../coresystem/aaa/ldap/answerfiles"
AAA_AD_PROFILE = "%s/ad-w2k12r2.properties" % AAA_PROFILES_DIR
AAA_AD_PROPERTIES = {
    DEFAULT_CONFIG_SECTION_NAME : {
        "pool.default.serverset.srvrecord.domain-conversion.type": "regex",
        "pool.default.serverset.srvrecord.domain-conversion."
        "regex.pattern": "^(?<domain>.*)$",
        "pool.default.serverset.srvrecord.domain-conversion."
        "regex.replacement": "BRQ._sites.${domain}"
    }
}

# ovirt-engine-extension-aaa-ldap-setup answer files
AAA_LDAP_ANSWER_FILES = {
    "ad": "adw2k12r2.conf",
    "ipa": "ipa.conf",
    "openldap": "openldap.conf",
    "rhds": "rhds.conf"
}

# Long network name
LONG_NETWORK_NAME = "long_network_name_" + "@_!" * 79
