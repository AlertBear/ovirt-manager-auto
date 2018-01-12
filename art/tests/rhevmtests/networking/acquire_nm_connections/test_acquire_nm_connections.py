# -*- coding: utf-8 -*-

"""
Acquire connections created by NetworkManager
"""

import pytest

import config as nm_conf
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    NetworkTest,
)
from fixtures import nmcli_create_networks
import rhevmtests.networking.config as network_config
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces_fixture_function,
    remove_all_networks,
    create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    clean_host_interfaces_fixture_function.__name__,
    nmcli_create_networks.__name__,
)
class TestAcquireNmConnections(NetworkTest):
    """
    1. Create flat connection via NetworkManager and use it via VDSM
    2. Create BOND connection via NetworkManager and use it via VDSM
    3. Create VLAN connection via NetworkManager and use it via VDSM
    """

    dc = network_config.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [network_config.CL_0],
            "networks": nm_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces_fixture_function params
    hosts_nets_nic_dict = network_config.CLEAN_HOSTS_DICT

    # params = [host NIC, RHV network, VLAN id, clean host interface]

    # NetworkManager flat network params
    flat_type = "nic"
    flat_rhv_network = nm_conf.NETS[1][0]
    flat_param = [flat_type, flat_rhv_network, None, hosts_nets_nic_dict]

    # NetworkManager BOND network params
    bond_type = "bond"
    bond_rhv_network = nm_conf.NETS[1][1]
    bond_param = [bond_type, bond_rhv_network, None, hosts_nets_nic_dict]

    # NetworkManager VLAN network params
    vlan_type = "nic"
    vlan_rhv_network = nm_conf.NETS[1][2]
    vlan_vlan_id = nm_conf.CASE_1_NETS.get(vlan_rhv_network).get("vlan_id")
    vlan_param = [
        vlan_type, vlan_rhv_network, vlan_vlan_id, hosts_nets_nic_dict
    ]

    @tier2
    @pytest.mark.parametrize(
        ("type_", "network", "vlan_id", "hosts_nets_nic_dict"),
        [
            pytest.param(*flat_param, marks=(polarion("RHEVM3-19392"))),
            pytest.param(*bond_param, marks=(polarion("RHEVM3-19393"))),
            pytest.param(*vlan_param, marks=(polarion("RHEVM3-19394"))),
        ],
        ids=[
            "Acquire_flat_connection_from_NetworkManager",
            "Acquire_BOND_connection_from_NetworkManager",
            "Acquire_VLAN_connection_from_NetworkManager",
        ]
    )
    def test_acquire_nm_connetion(
        self, type_, network, vlan_id, hosts_nets_nic_dict
    ):
        """
        Use network that was created via NetworkManager in VDSM
        """
        nic = "bond1" if type_ == "bond" else network_config.HOST_0_NICS[1]
        sn_dict = {
            "add": {
                "1": {
                    "network": network,
                    "nic": nic,
                }
            }
        }
        assert hl_host_network.setup_networks(
            host_name=network_config.HOST_0_NAME, **sn_dict
        )
