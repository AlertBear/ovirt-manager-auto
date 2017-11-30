#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Bad bond feature tests

The following elements will be used for the testing:
2 Hosts, 2 bonds
"""

import pytest

import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)
from fixtures import get_linux_ad_partner_mac_value, refresh_hosts_capabilities
from rhevmtests.networking.fixtures import (
    setup_networks_fixture,
    clean_host_interfaces  # flake8: noqa
)


@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    get_linux_ad_partner_mac_value.__name__,
    refresh_hosts_capabilities.__name__
)
@pytest.mark.skipif(
    conf.NO_EXTRA_BOND_MODE_SUPPORT,
    reason=conf.NO_EXTRA_BOND_MODE_SUPPORT_SKIP_MSG
)
class TestLACPBond(NetworkTest):
    """
    1. Check if bond of slaves connected to LACP switch ports, report
       switch 'ad_partner_mac' value
    2. Check if bond of slaves connected to non-LACP switch ports, report a
       zero 'ad_partner_mac' value
    """

    # [Host index, bond_name, True for valid bond check or False for invalid]
    # Valid bond case parameters
    valid_bond = "bond0"
    valid = [0, valid_bond, True]

    # Invalid bond case parameters
    invalid_bond = "bond1"
    invalid = [0, invalid_bond, False]

    # setup_networks_fixture parameters
    hosts_nets_nic_dict = {
        0: {
            valid_bond: {
                "nic": valid_bond,
                "slaves": [2, 3],
                "mode": 4
            },
            invalid_bond: {
                "nic": invalid_bond,
                "slaves": [4, 5],
                "mode": 4
            }
        }
    }

    # refresh_hosts_capabilities fixture parameters
    hosts_to_refresh = [0, 1]

    @tier2
    @pytest.mark.parametrize(
        ("host_index", "bond_name", "check_valid"),
        [
            pytest.param(*valid, marks=(polarion("RHEVM3-19180"))),
            pytest.param(*invalid, marks=(polarion("RHEVM3-19181"))),
        ],
        ids=[
            "valid_LACP_bond",
            "invalid_LACP_bond"
        ]
    )
    def test_bond_mode_4(self, host_index, bond_name, check_valid):
        """
        Check if host setup of bond mode 4 is valid or invalid
        """
        outcome = "valid (non-zero)" if check_valid else "invalid (zero)"
        host_name = conf.HOSTS[host_index]

        testflow.step(
            "Verifying that bond: %s on host: %s reported a %s MAC address "
            "by vdsClient", bond_name, host_name, outcome
        )
        vds_mac = helper.check_bond_ad_partner_mac_in_vds_client(
            host_name=host_name, bond_name=bond_name
        )
        assert helper.check_mac_address(
            mac_address=vds_mac, positive=check_valid
        ), "vdsClient MAC address is not: %s " % outcome

        testflow.step(
            "Verifying that bond: %s on host: %s reported a %s MAC address "
            "by REST", bond_name, host_name, outcome
        )
        rest_mac = helper.check_bond_ad_partner_mac_in_rest(
            host_name=host_name, bond_name=bond_name
        )
        assert helper.check_mac_address(
            mac_address=rest_mac, positive=check_valid
        ), "REST MAC address is not: %s " % outcome

        testflow.step(
            "Verifying that REST reported MAC address is equal to vdsClient "
            "MAC address"
        )
        assert vds_mac == rest_mac, (
            "MAC addresses are not equal: "
            "REST reported: %s vdsClient reported: %s", rest_mac, vds_mac
        )
