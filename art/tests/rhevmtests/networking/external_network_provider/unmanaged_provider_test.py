"""
Tests for unmanaged external provider
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Network/
4_2_Network_Unmanaged_External_Provider
"""

import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, tier2
from art.rhevm_api.tests_lib.low_level import (
    external_providers
)


@pytest.mark.incremental
class TestUnmanagedProfiver(NetworkTest):
    """
    1. Create unmanaged provider
    2. Create unmanaged network
    3. Update OVN network p
    4. Delete unmanaged network
    5. Delete OVN unmanaged provider
    """
    PROVIDER = None
    UNMANAGED_PROVIDER_NAME = "Unmanaged_provider"
    UNMANAGED_PROVIDER_PARAMS = {
        "name": UNMANAGED_PROVIDER_NAME,
        "provider_api_element_name": "openstack_network_provider",
        "read_only": False,
        "unmanaged": True
    }

    @tier2
    @polarion("RHEVM-24983")
    def test_create_unmanaged_provider(self):
        """
        Create unmanaged provider
        """
        testflow.step("Create unmanaged external network provider")
        self.PROVIDER = external_providers.ExternalNetworkProvider(
            **self.UNMANAGED_PROVIDER_PARAMS
        )
        assert self.PROVIDER.add()
