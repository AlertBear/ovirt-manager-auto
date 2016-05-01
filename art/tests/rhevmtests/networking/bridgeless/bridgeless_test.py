#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

import logging

import pytest

import helper as bridgeless_helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    all_classes_teardown, bridgeless_prepare_setup, case_03_fixture,
    case_04_fixture
)

logger = logging.getLogger("Bridgeless_Networks_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(
    all_classes_teardown.__name__, bridgeless_prepare_setup.__name__
)
class TestBridgelessCase1(NetworkTest):
    """
    Attach Non-VM network to host NIC
    """
    __test__ = True

    @polarion("RHEVM-14837")
    def test_bridgeless_network(self):
        """
        Attach Non-VM network to host NIC
        """
        testflow.step("Attach non-VM network to host NIC")
        bridgeless_helper.create_networks_on_host(
            nic=conf.HOST_0_NICS[1], net=conf.NETS[1][0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    all_classes_teardown.__name__, bridgeless_prepare_setup.__name__
)
class TestBridgelessCase2(NetworkTest):
    """
    Attach Non-VM with VLAN network to host NIC
    """
    __test__ = True

    @polarion("RHEVM-14838")
    def test_vlan_bridgeless_network(self):
        """
        Attach Non-VM with VLAN network to host NIC
        """
        testflow.step("Attach non-VM network with VLAN to host NIC")
        bridgeless_helper.create_networks_on_host(
            nic=conf.HOST_0_NICS[1], net=conf.NETS[2][0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_03_fixture.__name__)
class TestBridgelessCase3(NetworkTest):
    """
    Create BOND
    Attach Non-VM network with VLAN over BOND
    """
    __test__ = True
    bond = conf.BOND[0]

    @polarion("RHEVM-14840")
    def test_bond_bridgeless_network(self):
        """
        Attach Non-VM network with VLAN over BOND
        """
        testflow.step("Attach non-VM network with VLAN to BOND")
        bridgeless_helper.create_networks_on_host(
            net=conf.NETS[3][0], nic=self.bond
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_04_fixture.__name__)
class TestBridgelessCase4(NetworkTest):
    """
    Create BOND
    Attach Non-VM network over BOND
    """
    __test__ = True
    bond = conf.BOND[1]

    @polarion("RHEVM-14839")
    def test_bond_bridgeless_network(self):
        """
        Attach bridgeless network over BOND
        """
        testflow.step("Attach non-VM network to BOND")
        bridgeless_helper.create_networks_on_host(
            net=conf.NETS[4][0], nic=self.bond
        )
