"""
Tests for unmanaged external provider

The following elements will be used for the testing:
unmanaged provider and unmanaged network
"""

import pytest

import config as ovn_conf
import rhevmtests.networking.config as net_config
from art.rhevm_api.tests_lib.low_level import (
    external_providers,
    networks as ll_networks
)
from art.test_handler.tools import bz, polarion
from art.unittest_lib import NetworkTest, tier2, testflow
from fixtures import remove_unmanaged_provider


@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_unmanaged_provider.__name__
)
class TestUnmanagedProvider(NetworkTest):
    """
    1. Create unmanaged provider
    2. Create unmanaged network
    3. Update unmanaged network
    4. Delete unmanaged network
    5. Delete unmanaged provider
    """
    # Common parameters
    unmanaged_provider_name = "unmanaged_provider_test"
    unmanaged_network_name = "unmanaged_provider_network"

    # remove_unmanaged_provider fixture parameters
    remove_provider_name = unmanaged_provider_name

    @tier2
    @polarion("RHEVM-24983")
    def test_create_unmanaged_provider(self):
        """
        Create unmanaged provider
        """
        testflow.step("Create unmanaged external network provider")
        ovn_conf.UNMANAGED_PROVIDER = (
            external_providers.ExternalNetworkProvider(
                name=self.unmanaged_provider_name, read_only=False,
                unmanaged=True,
                provider_api_element_name="openstack_network_provider"
            )
        )
        assert ovn_conf.UNMANAGED_PROVIDER.add()

    @tier2
    @bz({"1535573": {}})
    @polarion("RHEVM-24976")
    def test_create_unmanaged_network(self):
        """
        Create unmanaged network
        """
        assert ll_networks.add_network(
            positive=True, name=self.unmanaged_network_name,
            data_center=net_config.DC_0,
            external_network_provider_name=self.unmanaged_provider_name
        )

    @tier2
    @polarion("RHEVM-24978")
    def test_update_unmanaged_network(self):
        """
        Update unmanaged network
        """
        new_name = "".join([self.unmanaged_network_name, "_new"])
        assert ll_networks.update_network(
            positive=True, network=self.unmanaged_network_name,
            data_center=net_config.DC_0, name=new_name
        )
        self.unmanaged_provider_name = new_name

    @tier2
    @polarion("RHEVM-25041")
    def test_remove_unmanaged_network(self):
        """
        Remove unmanaged network
        """
        assert ll_networks.remove_network(
            positive=True, network=self.unmanaged_network_name,
            data_center=net_config.DC_0
        )

    @tier2
    @polarion("RHEVM-25052")
    def test_remove_unmanaged_provider(self):
        """
        Remove unmanaged provider
        """
        assert ovn_conf.UNMANAGED_PROVIDER.remove(
            openstack_ep=self.unmanaged_provider_name
        )
        self.remove_provider_name = ""
