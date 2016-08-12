#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""

import logging

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as required_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    case_02_fixture, case_03_fixture, all_classes_teardown
)

logger = logging.getLogger("Required_Network_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(all_classes_teardown.__name__)
class TestRequiredNetwork01(NetworkTest):
    """
    Check that management network is required by default
    Try to set it to non required.
    """
    __test__ = True
    net = None
    cluster = conf.CL_0
    mgmt = conf.MGMT_BRIDGE

    @polarion("RHEVM3-3753")
    def test_mgmt(self):
        """
        Check that management network is required by default
        Try to set it to non required.
        """

        testflow.step("Check that management network is required by default")
        assert ll_networks.is_network_required(
            network=self.mgmt, cluster=self.cluster
        )

        testflow.step("Try to set management network to non required.")
        assert ll_networks.update_cluster_network(
            positive=False, cluster=self.cluster, network=self.mgmt,
            required="false"
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_02_fixture.__name__)
class TestRequiredNetwork02(NetworkTest):
    """
    Attach required non-VM network to host
    Set host NIC down
    Check that host is non-operational
    """
    __test__ = True
    net = required_conf.NETS[2][0]
    networks = [net]

    @polarion("RHEVM3-3744")
    def test_nonoperational(self):
        """
        Set host NIC down
        Check that host is non-operational
        """
        testflow.step(
            "Set host NIC down and check that host is non-operational"
        )
        assert helper.set_nics_and_wait_for_host_status(
            nics=[conf.HOST_0_NICS[1]],
            nic_status=required_conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_03_fixture.__name__)
class TestRequiredNetwork03(NetworkTest):
    """
    Attach required VLAN network over BOND.
    Set BOND slaves down
    Check that host is non-operational
    Set BOND slaves up
    Check that host is operational
    """
    __test__ = True
    net = required_conf.NETS[3][0]
    bond = "bond4"
    vlan = required_conf.VLAN_IDS[0]

    @polarion("RHEVM3-3752")
    def test_1_nonoperational_bond_down(self):
        """
        Set bond SLAVES DOWN
        Check that host is non-operational
        """
        testflow.step(
            "Set bond SLAVES DOWN and check that host is non-operational"
        )
        assert helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4],
            nic_status=required_conf.NIC_STATE_DOWN,
            host_status=conf.HOST_NONOPERATIONAL
        )

    @polarion("RHEVM3-3745")
    def test_2_nonoperational_bond_down(self):
        """
        Set BOND slaves up
        Check that host is operational
        """
        testflow.step("Set bond slaves up and check that host is operatinal")
        assert helper.set_nics_and_wait_for_host_status(
            nics=conf.HOST_0_NICS[2:4],
            nic_status=required_conf.NIC_STATE_UP
        )
