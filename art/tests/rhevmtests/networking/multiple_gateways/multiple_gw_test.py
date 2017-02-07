#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import config as multiple_gw_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest
from art.unittest_lib import attr, testflow
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import (
    NetworkFixtures,
    setup_networks_fixture,
    clean_host_interfaces  # flake8: noqa
)


@pytest.fixture(scope="module", autouse=True)
def multiple_gw_prepare_setup(request):
    """
    Create networks on engine
    """
    multiple_gw = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
            hosts=multiple_gw.host_0_name
        )
    request.addfinalizer(fin)

    network_helper.prepare_networks_on_setup(
        networks_dict=multiple_gw_conf.NETS_DICT, dc=multiple_gw.dc_0,
        cluster=multiple_gw.cluster_0
    )


@attr(tier=2)
class TestGatewaysCase01(NetworkTest):
    """
    1. Verify you can configure additional VLAN network with static IP and
        gateway
    2. Verify you can configure additional bridgeless network with static IP.
    3. Verify you can configure additional display network with static ip
        config.
    4. Verify you can add additional NIC to the already created bond.
    5. Verify you can remove slave from already created bond
    """
    # Test params = [network, host NIC, IP, IP gateway]
    # VLAN network params
    vlan_net = multiple_gw_conf.NETS[1][0]
    vlan_net_ip = multiple_gw_conf.IPS.pop(0)
    vlan_net_params = [vlan_net, 1, vlan_net_ip, None]

    # Bridgeless network params
    brless_net = multiple_gw_conf.NETS[1][1]
    brless_net_ip = multiple_gw_conf.IPS.pop(0)
    brless_net_params = [brless_net, 1, brless_net_ip, None]

    # Display network params
    display_net = multiple_gw_conf.NETS[1][2]
    display_net_ip = multiple_gw_conf.IPS.pop(0)
    display_net_params = [display_net, 1, display_net_ip, None]

    # Zero gateway params
    zero_net = multiple_gw_conf.NETS[1][2]
    zero_net_ip = multiple_gw_conf.IPS.pop(0)
    zero_net_gw = "0.0.0.0"
    zero_net_params = [zero_net, 1, zero_net_ip, zero_net_gw]

    @pytest.mark.parametrize(
        ("network", "nic", "ip", "gateway"),
        [
            polarion("RHEVM3-3953")(vlan_net_params),
            polarion("RHEVM3-3954")(brless_net_params),
            polarion("RHEVM3-3956")(display_net_params),
            polarion("RHEVM3-3966")(zero_net_params),
        ],
        ids=[
            "VLAN network with gateway",
            "Bridgeless network with gateway",
            "Display network with gateway",
            "VM network with gateway 0.0.0.0",
        ]
    )
    def test_check_ip_rule(self, network, nic, ip, gateway):
        """
        Check correct configuration with ip rule function
        """
        host = conf.HOST_0_NAME
        ip_gateway = multiple_gw_conf.GATEWAY if not gateway else gateway
        sn_dict = {
            "add": {
                network: {
                    "nic": conf.HOST_0_NICS[nic],
                    "network": network,
                    "ip": {
                        "1": {
                            "address": ip,
                            "gateway": ip_gateway,
                            "netmask": 24,
                            "boot_protocol": "static"
                        }
                    }
                }
            }
        }
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)
        testflow.step(
            "Check correct configuration with ip rule command on %s network",
            network
        )
        if not gateway:
            assert ll_networks.check_ip_rule(
                vds_resource=conf.VDS_0_HOST, subnet=multiple_gw_conf.SUBNET
            )

        assert hl_host_network.clean_host_interfaces(host_name=host)


@attr(tier=2)
@pytest.mark.usefixtures(setup_networks_fixture.__name__)
class TestGatewaysCase02(NetworkTest):
    """
    1. Verify you can add additional NIC to the already created bond
    2. Verify you can remove slave from already created bond
    """
    # Test params = [BOND, BOND slave to Add/Remove]
    # Add slave params
    bond_1 = "bond20"
    net_bond_1 = multiple_gw_conf.NETS[2][0]
    add_slave_params = [bond_1, 3]

    # Remove slave params
    net_bond_2 = multiple_gw_conf.NETS[2][1]
    bond_2 = "bond21"
    remove_slave_params = [bond_2, 6]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            net_bond_1: {
                "nic": bond_1,
                "network": net_bond_1,
                "slaves": [1, 2],
                "ip": {
                    "1": {
                        "address": multiple_gw_conf.IPS.pop(0),
                        "gateway": multiple_gw_conf.GATEWAY
                    }
                }
            },
            net_bond_2: {
                "nic": bond_2,
                "network": net_bond_2,
                "slaves": [4, 5, 6],
                "ip": {
                    "1": {
                        "address": multiple_gw_conf.IPS.pop(0),
                        "gateway": multiple_gw_conf.GATEWAY
                    }
                }
            }
        }
    }

    @pytest.mark.parametrize(
        ("bond", "slave"),
        [
            polarion("RHEVM3-3963")(add_slave_params),
            polarion("RHEVM3-3964")(remove_slave_params),
        ],
        ids=[
            "Add slave to BOND",
            "Remove slave from BOND"
        ]
    )
    def test_update_bond_slaves(self, bond, slave):
        """
        Check correct configuration with ip rule function
        """
        log = "Add" if bond == self.bond_1 else "Remove"
        slave = conf.VDS_0_HOST.nics[slave]
        sn_dict = {
            "update": {
                "1": {
                    "nic": bond,
                    "slaves": [slave]
                }
            }
        }
        testflow.step("%s slave %s from bond %s", log, slave, bond)
        assert hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
        testflow.step("Checking IP rule after %s slave %s", log.lower(), slave)
        assert ll_networks.check_ip_rule(
            vds_resource=conf.VDS_0_HOST, subnet=multiple_gw_conf.SUBNET,
            matches=4
        )
