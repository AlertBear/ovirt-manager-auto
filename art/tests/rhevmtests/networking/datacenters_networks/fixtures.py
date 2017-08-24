#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for datacenter networks
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def create_networks_on_dc(request):
    """
    Create networks on Data-Center
    """
    create_nets = request.node.cls.create_networks_on_dc_params
    dcs_to_remove_nets = getattr(
        request.cls, "remove_network_from_dcs_params", create_nets.keys()
    )

    def fin():
        """
        Remove networks from Data-Center
        """
        results = []
        for dc_name in dcs_to_remove_nets:
            testflow.teardown(
                "Removing networks from Data-Center: %s" % dc_name
            )
            results.append(
                (
                    ll_networks.delete_networks_in_datacenter(
                        datacenter=dc_name, mgmt_net=conf.MGMT_BRIDGE
                    ),
                    "Failed to delete networks from DC: %s" % dc_name
                )
            )
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin)

    for dc_name, networks in create_nets.items():
        for network, network_properties in networks.items():
            testflow.setup(
                "Creating network: %s on Data-Center: %s" % (network, dc_name)
            )
            assert ll_networks.create_network_in_datacenter(
                positive=True, datacenter=dc_name, name=network,
                **network_properties
            )
