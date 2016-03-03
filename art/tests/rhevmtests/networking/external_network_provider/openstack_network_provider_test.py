#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
OpenStack network provider tests
"""
import pytest

import rhevmtests.networking.config as conf
import config as osnp_conf
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    add_neutron_provider, ExternalNetworkProviderFixtures,
    get_provider_networks, import_openstack_network
)


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    add_neutron_provider.__name__,
    get_provider_networks.__name__
)
class TestOsnp01(NetworkTest):
    """
    Import network from OpenStack network provider
    Delete imported network
    """
    __test__ = True

    @polarion("RHEVM-14817")
    def test_01_add_openstack_provider(self):
        """
        Add OpenStack network provider.
        Add is done in add_neutron_provider fixture.
        """
        testflow.step("Add OpenStack network provider")
        pass

    @polarion("RHEVM-14831")
    def test_02_import_networks(self):
        """
        Import network from OpenStack network provider
        """
        neut = ExternalNetworkProviderFixtures()
        neut.init()
        testflow.step("Import networks from Neutron provider")
        assert neut.neut.import_network(
            network=osnp_conf.PROVIDER_NETWORKS[0], datacenter=conf.DC_0
        )

    @polarion("RHEVM-14895")
    def test_03_delete_networks(self):
        """
        Delete network from OpenStack network provider
        """
        testflow.step("Import networks imported from Neutron provider")
        assert hl_networks.remove_networks(
            positive=True, networks=[osnp_conf.PROVIDER_NETWORKS[0]]
        )


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    add_neutron_provider.__name__,
    import_openstack_network.__name__
)
class TestOsnp02(NetworkTest):
    """
    Run VM with neutron network
    """
    __test__ = True

    @polarion("RHEVM-14832")
    def test_01_run_vm_openstack_network(self):
        """
        Run VM with neutron network
        """
        pytest.skip("NotImplemented")
