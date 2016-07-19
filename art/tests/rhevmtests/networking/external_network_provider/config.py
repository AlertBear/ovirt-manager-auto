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
ANSWER_FILE = "/root/neutron_answer5"
RHOS_CMD = "rhos-release 8"
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
PROVIDER_MOCK_GIT = "https://github.com/mmirecki/ovirt-provider-mock.git"
PROVIDER_NAME = "neutron_network_provider"
PROVIDER_IP = "10.35.128.196"
PROVIDER_URL = "http://{ip}".format(ip=PROVIDER_IP)
PROVIDER_URL_PORT = "{url}:9696".format(url=PROVIDER_URL)
PROVIDER_PLUGIN_TYPE = "open_vswitch"
NETWORK_MAPPING = "{interface}:br-ext"
PROVIDER_BROKER_TYPE = "rabbit_mq"
PROVIDER_PORT = 9999
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
BR_EXT = "br-ext"
VM_NIC = "neutron_vnic"
PROVIDER_NETWORKS_NAME = ["onp1", "onp2", "onp3", "onp4", "onp5"]
