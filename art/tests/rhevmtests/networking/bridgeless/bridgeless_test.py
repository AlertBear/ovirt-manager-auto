#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

import pytest

import config as bridgeless_conf
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    NetworkTest,
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces,
    setup_networks_fixture,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__
)
class TestBridgelessCase(NetworkTest):
    """
    Bridgeless test on host NIC and bond.
    """
    bond_1 = bridgeless_conf.BOND_1
    bond_2 = bridgeless_conf.BOND_2
    dc = conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "datacenter": dc,
            "cluster": conf.CL_0,
            "networks": bridgeless_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

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

    @tier2
    @pytest.mark.parametrize(
        ("net", "nic"),
        [
            polarion("RHEVM3-14837")(bridgeless_conf.CASE_1),
            polarion("RHEVM3-14838")(bridgeless_conf.CASE_2),
            polarion("RHEVM3-14840")(bridgeless_conf.CASE_3),
            polarion("RHEVM3-14839")(bridgeless_conf.CASE_4),
        ]
    )
    def test_bridgeless_network(self, net, nic):
        """
        1) Attach non-VM network to host NIC.
        2) Attach non-VM with VLAN network to host NIC.
        3) Attach non-VM network with VLAN over bond.
        4) Attach non-VM network over bond
        """
        nic = conf.HOST_0_NICS[nic] if isinstance(nic, int) else nic
        local_dict = {
            "add": {
                "1": {
                    "network": net,
                    "nic": nic
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **local_dict
        )
