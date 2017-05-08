#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External Network Provider config file
"""

import rhevmtests.config as global_conf
import rhevmtests.networking.config as conf

# OVN provider parameters
OVN_PROVIDER_NAME = "ovirt-provider-ovn"
OVN_PROVIDER_PROTOCOL = "https"
OVN_PROVIDER_PORT = 9696
OVN_PROVIDER_API_URL_SUFFIX = "v2.0"
OVN_PROVIDER_KEYSTONE_PORT = 35357

# OVN class parameters
OVN_EXTERNAL_PROVIDER_URL = "{http}://{hostname}:{port}/{api_url}"
OVN_EXTERNAL_PROVIDER_KEYSTONE_URL = OVN_EXTERNAL_PROVIDER_URL.format(
    http=OVN_PROVIDER_PROTOCOL, hostname=conf.VDC_HOST,
    port=OVN_PROVIDER_KEYSTONE_PORT, api_url=OVN_PROVIDER_API_URL_SUFFIX
)
OVN_EXTERNAL_PROVIDER_PARAMS = {
    "name": None,
    "url": "{http}://{hostname}:{port}".format(
        http=OVN_PROVIDER_PROTOCOL, hostname=conf.VDC_HOST,
        port=OVN_PROVIDER_PORT
    ),
    "api_url": OVN_EXTERNAL_PROVIDER_URL.format(
        http=OVN_PROVIDER_PROTOCOL, hostname=conf.VDC_HOST,
        port=OVN_PROVIDER_PORT, api_url=OVN_PROVIDER_API_URL_SUFFIX,
    ),
    "provider_api_element_name": "openstack_network_provider",
    "requires_authentication": True,
    "read_only": False,
    "authentication_url": OVN_EXTERNAL_PROVIDER_KEYSTONE_URL,
    "keystone_url": OVN_EXTERNAL_PROVIDER_KEYSTONE_URL,
    # Default provider user for authentication is admin@local
    "username": global_conf.VDC_ADMIN_JDBC_LOGIN,
    "password": global_conf.VDC_PASSWORD,
    "keystone_username": global_conf.VDC_ADMIN_JDBC_LOGIN,
    "keystone_password": global_conf.VDC_PASSWORD,
    "verify_ssl": False
}

# OVN authorization tests parameters

# JDBC internal settings
OVN_JDBC_GROUP_NAME = "OvnAdmins"
OVN_JDBC_GROUP_USERNAME = "ovn_admin@internal"
OVN_JDBC_USERNAME_PASSWORD = "123456"

# LDAP settings
OVN_LDAP_GROUP_NAME = "ovn_admins"
# TODO: need to fill the ldap domain once it will become available
OVN_LDAP_GROUP_USERNAME = "ovn_admin@ldap_domain"
OVN_LDAP_USERNAME_PASSWORD = "123456"

OVN_WRONG_PASSWORD = "1234567"

OVN_AUTHENTICATION_BY_GROUP_CONF = {
    "AUTH": {
        "auth-plugin": "auth.plugins.ovirt:AuthorizationByGroup"
    },
    "OVIRT": {
        "ovirt-admin-group-attribute-name": (
            "AAA_AUTHZ_GROUP_NAME;java.lang.String;"
            "0eebe54f-b429-44f3-aa80-4704cbb16835"
        ),
        "ovirt-admin-group-attribute-value": None,
    }
}

# OVN class instance
OVN_PROVIDER = None

# OVN networks
OVN_NET_NAMES = ["ovn_net_%s" % i for i in range(1, 4)]
OVN_NET_1 = OVN_NET_NAMES[0]
OVN_NET_2 = OVN_NET_NAMES[1]
OVN_NET_3 = OVN_NET_NAMES[2]
OVN_NETS_CIDR = "172.16.0.0/24"
OVN_NETS_DNS = ["8.8.8.8"]
OVN_NETS = {
    OVN_NET_1: None,
    OVN_NET_2: None,
    OVN_NET_3: {
        "name": "%s_subnet" % OVN_NET_3,
        "cidr": OVN_NETS_CIDR,
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": OVN_NETS_DNS,
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    }
}

# OVN vNIC profile
OVN_VNIC_PROFILE = "ovn_vnic_profile"

# OVN extra vNIC name
OVN_VNIC = "ovn_vnic"

# OVN VM IP networks
OVN_VM_0_NET = "192.168.10.1/24"
OVN_VM_0_IP = OVN_VM_0_NET.split("/")[0]
OVN_VM_1_NET = "192.168.10.2/24"
OVN_VM_1_IP = OVN_VM_1_NET.split("/")[0]

# VM Host resources
OVN_VMS_RESOURCES = {
    conf.VM_0: None,
    conf.VM_1: None
}

# Copy file configuration
OVN_COPY_FILE_SIZE_MB = 250

# Ping configuration for all test cases
OVN_PING_SIZE = 1400
OVN_PING_COUNT = 10

# Ping output packets received extraction
OVN_PING_PACKETS_RECEIVED_REGEX = "\d*(?= received)"

# Ping and migration test configuration
OVN_MIGRATION_PING_COUNT = 30
# Maximum number of packets loss during VM migration
# (1 packet loss = 1 second loss of communication)
OVN_MIGRATION_PING_LOSS_COUNT = 3

# Timeout for migration and ping test
OVN_MIGRATION_TIMEOUT = 300

# Arbitrary MAC address for change MAC test (not supposed to be used)
OVN_ARBITRARY_MAC_ADDRESS = "00:01:11:11:11:11"

# RPM packages to remove
# All OVN releated packages are depend on openvswitch-ovn-common except
# python-openvswitch
OVN_DRIVER_REMOVE_RPMS = [
    "openvswitch-ovn-common",
    "python-openvswitch"
]

# Services that can make OVN malfunction
OVN_FW_SERVICES = [
    "firewalld",
    "iptables"
]

# OVN config file settings
OVN_CONFIG_FILE = "/etc/ovirt-provider-ovn/ovirt-provider-ovn.conf"
OVN_CONFIG_FILE_BCK = None

# Services to stop pre-removing RPM packages
OVN_DRIVER_SERVICE = "ovn-controller"

# Commands and constants to be used with SSH terminal
OVN_CMD_PING = "ping -M do -c {count} -s {size} -I {eth} {ip}"
OVN_CMD_SET_IP = (
    "ip addr flush dev {eth} && ip addr add {net} dev {eth} && "
    "ip link set dev {eth} up"
)
OVN_CMD_CP_FILE = "cp -pf {src} {dst}"
OVN_CMD_RESOLV_CONFIG = "/etc/resolv.conf"
OVN_CMD_NET_SCRIPT = "/etc/sysconfig/network-scripts/ifcfg-{eth}"
OVN_CMD_DHCLIENT = "dhclient -r {eth} && dhclient {eth}"
OVN_CMD_VDSM_TOOL = "vdsm-tool ovn-config {provider_ip} {host_ip}"
OVN_CMD_SERVICE_STATUS = "systemctl is-active {name}.service"
OVN_CMD_SSH_TRANSFER_FILE = (
    "dd if=/dev/urandom bs=1M count={count} | "
    "ssh root@{dst} ""dd of=/dev/null"""
)
