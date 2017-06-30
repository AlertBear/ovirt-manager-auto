#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for report the active slave in BOND interface
"""

import pytest

import helper
from art.test_handler.tools import polarion
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture,
    clean_host_interfaces  # flake8: noqa
)


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
    # Tests IDS
    id_ = "on BOND %s (mode %s)"

    # setup_networks_fixture params
    bond_1 = "bond01"
    bond_2 = "bond02"
    bond_3 = "bond03"
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [3, 4],
                "mode": 1
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [5, 6],
                "mode": 5
            },
            bond_3: {
                "nic": bond_3,
                "slaves": [7, 8],
                "mode": 6
            },
        }
    }

    @tier2
    @pytest.mark.parametrize(
        "bond",
        [
            pytest.param(bond_1, marks=(polarion("RHEVM3-17189"))),
            pytest.param(bond_2, marks=(polarion("RHEVM3-17190"))),
            pytest.param(bond_3, marks=(polarion("RHEVM3-17192"))),
        ],
        ids=[
            "Create_bond_with_mode_1_active-backup",
            "Create_bond_with_mode_5_balance-tlb",
            "Create_bond_with_mode_6_balance-alb",
        ]
    )
    def test_report_active_slave(self, bond):
        """
        Verify that RHV is report primary/active interface of the bond
        mode 1, 5 and 6.
        """
        mode = self.hosts_nets_nic_dict.get(0).get(bond).get("mode")
        testflow.step(
            "Check that the active slave name bond %s mode %s that reported "
            "via engine match to the active slave name on the host", bond, mode
        )
        assert helper.compare_active_slave_from_host_to_engine(
            bond=bond
        ), (
            "Active slave name bond %s  mode %s that reported via engine "
            "isn't match to the active slave name on the host" % (bond, mode)
        )
