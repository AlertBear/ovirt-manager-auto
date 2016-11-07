#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network test cases that do not fit to any feature plan
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import remove_all_networks
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@attr(tier=2)
@pytest.mark.usefixtures(remove_all_networks.__name__)
class TestMisc01(NetworkTest):
    """
    1. Create new network called 'net-155'
    2. Create new network called 'net-1-5-5-b----'
    3. Create new network called 'm-b_1-2_3_4-3_5'
    """

    __test__ = True

    @polarion("RHEVM3-11877")
    def test_create_net_with_dash(self):
        """
        1. Create new network called 'net-155'
        2. Create new network called 'net-1-5-5-b----'
        3. Create new network called 'm-b_1-2_3_4-3_5'
        """
        networks = ["net-155", "net-1-5-5-b----", "m-b_1-2_3_4-3_5"]
        for net in networks:
            testflow.step("Create %s on %s", net, conf.DC_0)
            assert ll_networks.add_network(
                positive=True, name=net, data_center=conf.DC_0
            )


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestActiveBondSlaveNic(NetworkTest):
    """
    1. Create bond with mode 1 - active-backup.
    2. Check that the engine report the correct active slave of the BOND.
    3. Create bond with mode 5 -balance-tlb.
    4. Check that the engine report the correct active slave of the BOND.
    5. Create bond with mode 6 - balance-alb.
    6. Check that the engine report the correct active slave of the BOND.
    """

    __test__ = True
    bond_1 = "bond01"
    bond_2 = "bond02"
    bond_3 = "bond03"
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [2, 3],
                "mode": 1
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [-1, -2],
                "mode": 5
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [-3, -4],
                "mode": 6
            },
        }
    }
    step_log = (
        "Check that the active slave name bond %s that reported via "
        "engine match to the active slave name on the host"
    )
    assert_log = (
        "Active slave name bond %s that reported via engine isn't "
        "match to the active slave name on the host"
    )

    @polarion("RHEVM-17189")
    def test_01_report_active_slave_in_bond_mode_1(self):
        """
        Verify that RHV is report primary/active interface of the bond
        mode 1.
        """
        testflow.step(self.step_log, self.bond_1)
        assert helper.compare_active_slave_from_host_to_engine(
            bond=self.bond_1
        ), self.assert_log % self.bond_1

    @polarion("RHEVM-17190")
    def test_02_report_active_slave_in_bond_mode_5(self):
        """
        Verify that RHV is report primary/active interface of the bond
        mode 5.
        """
        testflow.step(self.step_log, self.bond_2)
        assert helper.compare_active_slave_from_host_to_engine(
            bond=self.bond_2
        ), self.assert_log % self.bond_2

    @polarion("RHEVM-17192")
    def test_03_report_active_slave_in_bond_mode_6(self):
        """
        Verify that RHV is report primary/active interface of the bond
        mode 6.
        """
        testflow.step(self.step_log, self.bond_3)
        assert helper.compare_active_slave_from_host_to_engine(
            bond=self.bond_3
        ), self.assert_log % self.bond_3
