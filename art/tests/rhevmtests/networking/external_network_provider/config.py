#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider config file
"""

import rhevmtests.networking.config as conf

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
