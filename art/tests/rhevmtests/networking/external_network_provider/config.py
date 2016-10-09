#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider config file
"""

import rhevmtests.networking.config as conf

# Packstack params
DELETE_IPTABLE_RULE = (
    "iptables -D FORWARD -m physdev ! --physdev-is-bridged -j REJECT "
    "--reject-with icmp-host-prohibited"
)
OSNP_VDSM_HOOK = "vdsm-hook-openstacknet"
ANSWER_FILE = "/root/packstack-answer-file"
RHOS_CMD = "rhos-release 9"
RHOS_LATEST = (
    "http://rhos-release.virt.bos.redhat.com/repos/rhos-release/"
    "rhos-release-latest.noarch.rpm"
)
PACKSTACK_CMD = "packstack --answer-file=%s" % ANSWER_FILE
COMPUTE_HOSTS = "CONFIG_COMPUTE_HOSTS=.*"
NETWORK_HOSTS = "CONFIG_NETWORK_HOSTS=.*"
ANSWER_FILE_HOSTS_PARAMS = [COMPUTE_HOSTS, NETWORK_HOSTS]
OVS_BRIDGE_IFACES = "CONFIG_NEUTRON_OVS_BRIDGE_IFACES=.*"
OVS_TUNNEL_IF = "CONFIG_NEUTRON_OVS_TUNNEL_IF=.*"
ANSWER_FILE_HOSTS_IFACES = [OVS_BRIDGE_IFACES, OVS_TUNNEL_IF]
PBDU_FORWARD = "ovs-vsctl set bridge {bridge} other-config:forward-bpdu=true"
OVS_SHOW_CMD = "ovs-vsctl list-br"
OVS_TUNNEL_IPS = ["172.16.0.200", "172.16.0.201"]

# Provider params
PROVIDER_NAME = "neutron_network_provider"
PROVIDER_IP = "10.35.128.98"
PROVIDER_URL = "http://{ip}".format(ip=PROVIDER_IP)
PROVIDER_URL_PORT = "{url}:9696".format(url=PROVIDER_URL)
PROVIDER_PLUGIN_TYPE = "open_vswitch"
BR_EXT = "br-ext"
NETWORK_MAPPING = "{interface}:{br_ext}"
PROVIDER_BROKER_TYPE = "rabbit_mq"
AGENT_PORT = 5672
AGENT_ADDRESS = PROVIDER_IP
PROVIDER_USERNAME = "neutron"
PROVIDER_PASSWORD = None
AGENT_USERNAME = "guest"
AGENT_PASSWORD = "guest"
TENENT_NAME = "services"
AUTHENTICATION_URL = "{url}:35357/v2.0/".format(url=PROVIDER_URL)
ROOT_PASSWORD = conf.HOSTS_PW

NEUTRON_PARAMS = {
    "name": PROVIDER_NAME,
    "url": PROVIDER_URL_PORT,
    "plugin_type": PROVIDER_PLUGIN_TYPE,
    "network_mapping": None,
    "broker_type": PROVIDER_BROKER_TYPE,
    "agent_address": AGENT_ADDRESS,
    "username": PROVIDER_USERNAME,
    "password": PROVIDER_PASSWORD,
    "tenant_name": TENENT_NAME,
    "requires_authentication": True,
    "authentication_url": AUTHENTICATION_URL,
    "agent_user": AGENT_USERNAME,
    "agent_password": AGENT_PASSWORD,
    "agent_port": AGENT_PORT
}

PROVIDER_NETWORKS = None
OVS_TUNNEL_BRIDGE = "ovs-tunnel"
VM_NIC = "neutron_vnic"
PROVIDER_NETWORKS_NAME = ["onp1", "onp2", "onp3", "onp4", "onp5"]

# OVN provider parameters
OVN_PROVIDER_NAME = "ovn-network-provider"
OVN_PROVIDER_PROTOCOL = "http"
OVN_PROVIDER_PORT = 9696
OVN_PROVIDER_API_URL_SUFFIX = "/v2.0"
OVN_PROVIDER_TENENT_NAME = "oVirt"

# OVN class parameters
OVN_EXTERNAL_PROVIDER_PARAMS = {
    "name": OVN_PROVIDER_NAME,
    "url": "{http}://{hostname}:{port}".format(
        http=OVN_PROVIDER_PROTOCOL, hostname=conf.VDC_HOST,
        port=OVN_PROVIDER_PORT
    ),
    "api_url": "{http}://{hostname}:{port}{api_url}".format(
        http=OVN_PROVIDER_PROTOCOL, hostname=conf.VDC_HOST,
        port=OVN_PROVIDER_PORT, api_url=OVN_PROVIDER_API_URL_SUFFIX,
    ),
    "provider_api_element_name": "openstack_network_provider",
    "requires_authentication": False,
    "tenant_name": OVN_PROVIDER_TENENT_NAME,
    "read_only": False
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

# Ping configuration for all test cases
OVN_PING_SIZE = 1300
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

# OVN Bridge interface file
OVN_BRIDGE_INTERFACE_FILE = "/var/run/openvswitch/br-int.mgmt"

# RPM packages to install on servers
OVN_COMMON_RPMS = [
    "openvswitch",
    "openvswitch-ovn-common",
    "python-openvswitch"
]

# Specific RPM packages to install
OVN_PROVIDER_RPMS = [
    "openvswitch-ovn-central",
    "ovirt-provider-ovn"
]
OVN_DRIVER_RPMS = [
    "openvswitch-ovn-host",
    "ovirt-provider-ovn-driver"
]

# RPM packages to remove
OVN_PROVIDER_REMOVE_RPMS = [
    "ovirt-provider-ovn",
    "openvswitch-ovn-common",
    "python-openvswitch"
]
OVN_DRIVER_REMOVE_RPMS = [
    "ovirt-provider-ovn-driver",
    "openvswitch-ovn-common",
    "python-openvswitch"
]

# Services that can make OVN malfunction
OVN_FW_SERVICES = [
    "firewalld",
    "iptables"
]
OVN_VSWITCHD_SERVICE = "ovs-vswitchd"

# Services to stop pre removing RPM packages
OVN_PROVIDER_SERVICE = "ovirt-provider-ovn"
OVN_DRIVER_SERVICE = "ovn-controller"

# Services to stop and restore their state
OVN_SERVICES_TO_STOP_AND_START = [
    "openvswitch",
    "ovsdb-service"
]
OVN_SERVICES_RUNNING = dict()

# Commands and constants to be used with SSH terminal
OVN_CMD_PING = "ping -c {count} -s {size} -I {eth} {ip}"
OVN_CMD_SET_IP = "ip addr flush dev {eth} && ip addr add {net} dev {eth} && " \
                 "ip link set dev {eth} up"
OVN_CMD_RESOLV_CONFIG = "/etc/resolv.conf"
OVN_CMD_NET_SCRIPT = "/etc/sysconfig/network-scripts/ifcfg-{eth}"
OVN_CMD_DHCLIENT = "dhclient -r {eth} && dhclient {eth}"
OVN_CMD_VDSM_TOOL = "vdsm-tool ovn-config {provider_ip} {host_ip}"
OVN_CMD_SYSD_RELOAD = "systemctl daemon-reload"
OVN_CMD_KILL_PROCESS = "pkill -f {process_name}"
OVN_CMD_DEL_OVN_BRIDGE = "ovs-vsctl del-br br-int"
OVN_CMD_SERVICE_STATUS = "systemctl is-active {name}.service"
