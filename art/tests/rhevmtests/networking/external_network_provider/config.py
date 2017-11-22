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
    "verify_ssl": False
}

# OVN authorization tests parameters
# JDBC settings
OVN_JDBC_GROUP = "OvnAdmins"
OVN_JDBC_USERNAME = "ovn_admin@internal"
OVN_JDBC_USERNAME_PASSWORD = "123456"
# LDAP settings
OVN_LDAP_GROUP = "ovn_admins"
OVN_LDAP_DOMAIN = "ad-w2k12r2.rhev.lab.eng.brq.redhat.com"
OVN_LDAP_AUTH_PROFILE = "ad-w2k12r2"
OVN_LDAP_USERNAME = "{user}@{domain}@{auth_profile}".format(
    user="ovn_admin", domain=OVN_LDAP_DOMAIN,
    auth_profile=OVN_LDAP_AUTH_PROFILE
)
# LDAP and LDAP SSL ports
OVN_LDAP_PORTS = [389, 636]

OVN_LDAP_USERNAME_PASSWORD = "Heslo123"
# Negative authorization test password
OVN_WRONG_PASSWORD = "1234567"

# OVN configuration file (values to be changed)
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
OVN_NET_NO_SUB_1 = "ovn_net_no_subnet_1"
OVN_NET_NO_SUB_2 = "ovn_net_no_subnet_2"
OVN_NET_SUB_TO_BE_ATTACHED = "ovn_net_subnet_attachment"
OVN_NET_SUB = "ovn_net_subnet"
OVN_NET_SUB_NO_GW = "ovn_net_subnet_no_gw"
OVN_NET_PERF = "ovn_net_performance"
# Long network names test
OVN_LONG_NET_SPECIAL_CHARS = "A*_-&$()@"
OVN_LONG_NET_15_CHARS_SPECIAL = "a" * 6 + OVN_LONG_NET_SPECIAL_CHARS
OVN_LONG_NET_20_CHARS = "a" * 20
OVN_LONG_NET_256_CHARS_SPECIAL = "A" * 247 + OVN_LONG_NET_SPECIAL_CHARS
OVN_LONG_NET_256_CHARS = "a" * 256

# OVN DHCP subnet settings
OVN_NETS_CIDR = "172.16.0.0/24"
OVN_NETS_DNS = ["8.8.8.8"]

# OVN networks for TestOVNComponent
OVN_NETS = {
    OVN_NET_NO_SUB_1: None,
    OVN_NET_NO_SUB_2: None,
    OVN_NET_SUB: {
        "name": "%s_subnet" % OVN_NET_SUB,
        "cidr": OVN_NETS_CIDR,
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": OVN_NETS_DNS,
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    },
    OVN_NET_SUB_NO_GW: {
        "name": "%s_subnet" % OVN_NET_SUB_NO_GW,
        "cidr": OVN_NETS_CIDR,
        "enable_dhcp": True,
        "ip_version": 4
    },
    OVN_NET_SUB_TO_BE_ATTACHED: {
        "name": "ovn_network_attachment_subnet_1",
        "cidr": "10.0.0.0/24",
        "enable_dhcp": True,
        "ip_version": 4,
        "network_id": None
    }
}

# OVN networks for TestOVNPerformance
OVN_NETS_PERF = {
    OVN_NET_PERF: None
}

OVN_LONG_NETS = {
    OVN_LONG_NET_15_CHARS_SPECIAL: {
        "name": "long_net_subnet_15_special",
        "cidr": "172.16.0.0/24",
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": ["8.8.8.8"],
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    },
    OVN_LONG_NET_20_CHARS: {
        "name": "long_net_subnet_15",
        "cidr": "172.16.0.0/24",
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": ["8.8.8.8"],
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    },
    OVN_LONG_NET_256_CHARS_SPECIAL: {
        "name": "long_net_subnet_256_special",
        "cidr": "172.16.0.0/24",
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": ["8.8.8.8"],
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    },
    OVN_LONG_NET_256_CHARS: {
        "name": "long_net_subnet_256",
        "cidr": "172.16.0.0/24",
        "enable_dhcp": True,
        "network_id": None,
        "dns_nameservers": ["8.8.8.8"],
        "ip_version": 4,
        "gateway_ip": "172.16.0.254"
    }
}

# OVN vNIC profile
OVN_VNIC_PROFILE = "ovn_vnic_profile"

# OVN extra vNIC name
OVN_VNIC = "ovn_vnic"

# OVN VM IP networks
OVN_VM_0_NET = "7.7.7.1/24"
OVN_VM_0_IP = OVN_VM_0_NET.split("/")[0]
OVN_VM_1_NET = "7.7.7.2/24"
OVN_VM_1_IP = OVN_VM_1_NET.split("/")[0]

# VM Host resources
OVN_VMS_RESOURCES = {
    conf.VM_0: None,
    conf.VM_1: None
}

# Hosts performance counters to be used as baseline for VM-to-VM benchmark
# List of three elements:
# avg CPU usage, avg memory usage and file transfer rate
OVN_HOST_PERF_COUNTERS = None

# get_performance_counters parameters:
# First element: collect CPU performance flag
# Second element: collect memory performance flag
COLLECT_PERFORMANCE_FLAGS = [True, True]

# Copy file test parameters
OVN_COPY_FILE_SIZE_MB = 250

# Ping configuration for all test cases
OVN_PING_SIZE = 1400
OVN_PING_COUNT = 10

# Ping output packets received extraction
OVN_PING_PACKETS_RECEIVED_REGEX = "\d*(?= received)"

# Ping and migration test parameters
OVN_MIGRATION_PING_COUNT = 30
# Maximum number of packets loss during VM migration
# (1 packet loss = 1 second loss of communication)
OVN_MIGRATION_PING_LOSS_COUNT = 3

# dd command output MB/s value
OVN_DD_MBS_REGEX = "\d+\.?\d+(?=\D*\Z)"

# Timeout for migration and ping test
OVN_MIGRATION_TIMEOUT = 300

# Timeout for SSH copy test
OVN_COPY_TIMEOUT = 600

# Arbitrary MAC address for change MAC test (not supposed to be used)
OVN_ARBITRARY_MAC_ADDRESS = "00:01:11:11:11:11"

# RPM packages to remove
OVN_DRIVER_REMOVE_RPMS = [
    "openvswitch-ovn-common",
    "python-openvswitch"
]

# List of OVN servers with firewalld service started state
OVN_FIREWALLD_STARTED_SERVERS = []

# OVN network service ports
OVN_NETWORK_SERVICE_PORTS = [
    ("northbound", 6641),
    ("southbound", 6642)
]

# OVN config file settings
OVN_CONFIG_FILE = "/etc/ovirt-provider-ovn/ovirt-provider-ovn.conf"
OVN_CONFIG_FILE_BCK = None

# Services to stop pre-removing RPM packages
OVN_CONTROLLER_SERVICE = "ovn-controller"

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
    "dd if=/dev/zero bs=1M count={count} | "
    "ssh root@{dst} ""dd of=/dev/null"""
)
OVN_CMD_GET_CPU_USAGE = (
    "top -bn 2 -d 0.01 | grep '^%Cpu' | tail -n 1 | gawk '{print $2+$4+$6}'"
)
OVN_CMD_GET_MEM_USAGE = "free | grep Mem | awk '{print $3/$2 * 100.0}'"
OVN_CMD_ADD_FW_PORT = "firewall-cmd --zone=public --add-port={port}/{proto}"
OVN_CMD_DEL_FW_PORT = "firewall-cmd --zone=public --remove-port={port}/{proto}"
OVN_CMD_TEST_HTTP_RESPONSE = "curl -k {url}"
