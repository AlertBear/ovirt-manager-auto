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
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import case_01_fixture


@attr(tier=2)
@pytest.mark.usefixtures(case_01_fixture.__name__)
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

    @polarion("RHEVM-14837")
    def test_bridgeless_network(self):
        """
        Attach non-VM network to host NIC
        """
        testflow.step("Attach non-VM network to host NIC")
        local_dict = {
            "add": {
                "1": {
                    "network": conf.BRIDGELESS_NETS[1][0],
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
                    "network": conf.BRIDGELESS_NETS[2][0],
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
                    "network": conf.BRIDGELESS_NETS[3][0],
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
                    "network": conf.BRIDGELESS_NETS[4][0],
                    "nic": self.bond_2
                }
            }
        }

        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )
