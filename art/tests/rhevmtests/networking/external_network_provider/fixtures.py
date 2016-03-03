#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider fixtures
"""

import re

import pytest

import config as osnp_conf
import rhevmtests.helpers as global_helper
from art.rhevm_api.tests_lib.low_level import external_providers
from rhevmtests.networking.fixtures import NetworkFixtures
import art.rhevm_api.tests_lib.high_level.networks as hl_networks


class ExternalNetworkProviderFixtures(NetworkFixtures):
    """
    External Network Provider class
    """
    def __init__(self):
        super(ExternalNetworkProviderFixtures, self).__init__()
        self.neutron_ip = osnp_conf.PROVIDER_IP
        self.neutron_answer_file = "/root/neutron_answer5"
        self.neutron_root_password = osnp_conf.ROOT_PASSWORD
        self.neutron_resource = global_helper.get_host_resource(
            ip=self.neutron_ip, password=self.neutron_root_password
        )
        self.neut = None
        self.neutron_password = None

    def get_neutron_password(self):
        """
        Get Neutron password from answer file
        """
        if not self.neutron_password:
            pattern = "CONFIG_NEUTRON_KS_PW="
            out = self.neutron_resource.fs.read_file(
                path=self.neutron_answer_file
            )
            assert out
            re_out = re.findall(r'{pat}.*'.format(pat=pattern), out)
            assert re_out
            self.neutron_password = re_out[0].strip(pattern)

    def set_neut_params(self):
        """
        Set neutron provider params
        """
        self.get_neutron_password()
        osnp_conf.NEUTRON_PARAMS["password"] = self.neutron_password
        osnp_conf.NEUTRON_PARAMS["network_mapping"] = (
            osnp_conf.NETWORK_MAPPING.format(interface=self.host_0_nics[-1])
        )
        self.neut = external_providers.OpenStackNetworkProvider(
            **osnp_conf.NEUTRON_PARAMS
        )

    def get_all_provider_networks(self):
        """
        Get all networks from provider
        """
        if not osnp_conf.PROVIDER_NETWORKS:
            self.init()
            networks = [net.name for net in self.neut.get_all_networks()]
            assert networks
            osnp_conf.PROVIDER_NETWORKS = networks

    def init(self):
        """
        Get provider class with existing provider object
        """
        self.set_neut_params()
        self.neut.set_osp_obj()


@pytest.fixture(scope="module")
def add_neutron_provider(request):
    """
    Add neutron network provider
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.set_neut_params()

    def fin():
        """
        Remove neutron provider
        """
        external_network_provider.neut.remove(
            openstack_ep=osnp_conf.PROVIDER_NAME
        )
    request.addfinalizer(fin)

    assert external_network_provider.neut.add()


@pytest.fixture(scope="class")
def get_provider_networks(request):
    """
    Get all provider networks
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.get_all_provider_networks()


@pytest.fixture(scope="class")
def import_openstack_network(request, get_provider_networks):
    """
    Import network from OpenStack provider
    """
    external_network_provider = ExternalNetworkProviderFixtures()
    external_network_provider.init()
    net = osnp_conf.PROVIDER_NETWORKS[1]

    def fin():
        """
        Remove imported network
        """
        hl_networks.remove_networks(positive=True, networks=[net])
    request.addfinalizer(fin)

    assert external_network_provider.neut.import_network(
        network=net, datacenter=external_network_provider.dc_0
    )
