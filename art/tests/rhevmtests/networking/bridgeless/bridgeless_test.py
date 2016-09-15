#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from rhevmtests.networking import helper as network_helper
import rhevmtests.networking.config as conf
import config as bridgeless_conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from rhevmtests.networking.fixtures import (
    NetworkFixtures, setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@pytest.fixture(scope="module", autouse=True)
def prepare_setup(request):
    """
    Prepare setup
    """
    bridgeless = NetworkFixtures()

    def fin():
        """
        Finalizer for remove networks
        """
        assert network_helper.remove_networks_from_setup(
            hosts=bridgeless.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=bridgeless_conf.BRIDGELESS_NET_DICT, dc=bridgeless.dc_0,
        cluster=bridgeless.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestBridgelessCase1(NetworkTest):
    """
    1) Attach non-VM network to host NIC.
    2) Attach non-VM with VLAN network to host NIC.
    3) Attach non-VM network with VLAN over bond.
    4) Attach non-VM network over bond
    """
    __test__ = True
    bond_1 = "bond01"
    bond_2 = "bond02"
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [-1, -2],
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-3, -4],
            }
        }
    }

    @polarion("RHEVM-14837")
    def test_bridgeless_network(self):
        """
        Attach non-VM network to host NIC
        """
        testflow.step("Attach non-VM network to host NIC")
        local_dict = {
            "add": {
                "1": {
                    "network": bridgeless_conf.BRIDGELESS_NETS[1][0],
                    "nic": conf.HOST_0_NICS[1]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )

    @polarion("RHEVM-14838")
    def test_vlan_bridgeless_network(self):
        """
        Attach non-VM with VLAN network to host NIC
        """
        testflow.step("Attach non-VM network with VLAN to host NIC")
        local_dict = {
            "add": {
                "1": {
                    "network": bridgeless_conf.BRIDGELESS_NETS[2][0],
                    "nic": conf.HOST_0_NICS[2]
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )

    @polarion("RHEVM-14840")
    def test_vlan_bond_bridgeless_network(self):
        """
        Attach non-VM network with VLAN over BOND
        """
        testflow.step("Attach non-VM network with VLAN to BOND")
        local_dict = {
            "add": {
                "1": {
                    "network": bridgeless_conf.BRIDGELESS_NETS[3][0],
                    "nic": self.bond_1
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )

    @polarion("RHEVM-14839")
    def test_bond_bridgeless_network(self):
        """
        Attach non-VM network over BOND
        """
        testflow.step("Attach non-VM network to BOND")
        local_dict = {
            "add": {
                "1": {
                    "network": bridgeless_conf.BRIDGELESS_NETS[4][0],
                    "nic": self.bond_2
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )
