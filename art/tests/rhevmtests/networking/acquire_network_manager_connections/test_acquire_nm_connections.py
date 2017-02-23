#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Acquire connections created by NetworkManager
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as ll_host_network
import config as nm_conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import NetworkTest, attr
from fixtures import nmcli_create_networks
from rhevmtests.networking import (
    config as conf,
    fixtures,
    helper as network_helper
)
from rhevmtests.networking.fixtures import (
    clean_host_interfaces_fixture_function
)


@pytest.fixture(scope="module", autouse=True)
def nm_networks_prepare_setup(request):
    """
    Prepare networks setup for tests
    """
    nm_networks = fixtures.NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        assert network_helper.remove_networks_from_setup(
                    hosts=nm_networks.host_0_name
                )

    network_helper.prepare_networks_on_setup(
        networks_dict=nm_conf.NETS_DICT, dc=nm_networks.dc_0,
        cluster=nm_networks.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces_fixture_function.__name__,
    nmcli_create_networks.__name__,
)
class TestAcquireNmConnections(NetworkTest):
    """
    1. Create flat connection via NetworkManager and use it via VDSM
    2. Create BOND connection via NetworkManager and use it via VDSM
    3. Create VLAN connection via NetworkManager and use it via VDSM
    """
    # params = [
    #   NM network, host NIC, RHV network, VLAN id, clean host interface
    # ]

    # clean_host_interfaces_fixture_function params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # NetworkManager flat network params
    flat_connection = "flat_nm_net"
    flat_type = "nic"
    flat_rhv_network = nm_conf.NETS[1][0]
    flat_param = [
        flat_connection, flat_type, flat_rhv_network, None, hosts_nets_nic_dict
    ]

    # NetworkManager BOND network params
    bond_connection = "bond_nm_net"
    bond_type = "bond"
    bond_rhv_network = nm_conf.NETS[1][1]
    bond_param = [
        bond_connection, bond_type, bond_rhv_network, None, hosts_nets_nic_dict
    ]

    # NetworkManager VLAN network params
    vlan_connection = "vlan_nm_net"
    vlan_type = "nic"
    vlan_rhv_network = nm_conf.NETS[1][2]
    vlan_vlan_id = nm_conf.VLAN_IDS.pop(0)
    vlan_param = [
        vlan_connection, vlan_type, vlan_rhv_network, vlan_vlan_id,
        hosts_nets_nic_dict
    ]

    @pytest.mark.parametrize(
        ("connection", "type_", "network", "vlan_id", "hosts_nets_nic_dict"),
        [
            polarion("RHEVM-19392")(flat_param),
            polarion("RHEVM-19393")(bond_param),
            polarion("RHEVM-19394")(vlan_param),
        ],
        ids=[
            "Acquire flat connection from NetworkManager",
            "Acquire BOND connection from NetworkManager",
            "Acquire VLAN connection from NetworkManager",
        ]
    )
    @bz({"1426225": {}})
    def test_acquire_nm_connetion(
        self, connection, type_, network, vlan_id, hosts_nets_nic_dict
    ):
        """
        Use network that was created via NetworkManager in VDSM
        """
        slaves = list()
        if type_ == "bond" or network == nm_conf.NETS[1][4]:
            nic = "bond1"
            slaves = conf.HOST_0_NICS[1:3]
        else:
            nic = conf.HOST_0_NICS[1]

        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": nic,
                    "slaves": slaves
                }
            }
        }
        assert ll_host_network.setup_networks(
            host_name=conf.HOST_0_NAME, **sn_dict
        )
