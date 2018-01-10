"""
mac_addr tests
"""

import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import tier2, NetworkTest, testflow
import rhevmtests.networking.config as network_config
import rhevmtests.helpers as global_helper
import helper
import rhevmtests.networking.mac_addr.config as macaddr_config
from fixtures import reset_host_nics
from rhevmtests.networking.fixtures import (  # noqa: F401
    clean_host_interfaces_fixture_function,
    remove_all_networks,
    create_and_attach_networks,
    create_bond
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    reset_host_nics.__name__,
    clean_host_interfaces_fixture_function.__name__,
    create_bond.__name__,
)
class TestMacAddrNm(NetworkTest):
    """
    1. Create BOND with MACADDR via NM and check that VDSM set MACADDR value in
        IFCFG
    2. Create VLAN over BOND with MACADDR via NM and check that VDSM set
        MACADDR value in IFCFG
    3. Create BOND without MACADDR via NM and check that VDSM set MACADDR value
        in IFCFG
    4. Create VLAN over BOND without MACADDR via NM and check that VDSM set
        MACADDR value in IFCFG
    """
    dc = network_config.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [network_config.CL_0],
            "networks": macaddr_config.ALL_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # clean_host_interfaces_fixture_function params
    hosts_nets_nic_dict = network_config.CLEAN_HOSTS_DICT

    # create_bond params
    host_resource = 0
    host_nics = [2, 3]
    # params = [macaddr, engine_network_name]

    via_nm = "nm"
    via_ifcfg = "ifcfg"

    # Via NetworkManager
    # With MACADDR BOND params
    nm_with_macaddr_mac = "00:00:00:00:00:01"
    nm_with_macaddr_network = macaddr_config.NETS[1][0]
    nm_bond_param_with_macaddr = [
        nm_with_macaddr_mac,
        nm_with_macaddr_network,
        via_nm
    ]

    # With MACADDR BOND_VLAN params
    nm_vlan_with_macaddr_mac = "00:00:00:00:00:02"
    nm_vlan_with_macaddr_network = macaddr_config.NETS[1][1]
    nm_vlan_bond_param_with_macaddr = [
        nm_vlan_with_macaddr_mac,
        nm_vlan_with_macaddr_network,
        via_nm
    ]

    # Without MACADDR BOND params
    nm_without_macaddr_network = macaddr_config.NETS[1][2]
    nm_bond_param_without_macaddr = [
        None,
        nm_without_macaddr_network,
        via_nm
    ]

    # Without MACADDR BOND_VLAN params
    nm_vlan_without_macaddr_network = macaddr_config.NETS[1][1]
    nm_vlan_bond_param_without_macaddr = [
        None,
        nm_vlan_without_macaddr_network,
        via_nm
    ]

    # Via IFCFG files
    # With MACADDR BOND params
    ifcfg_with_macaddr_mac = "00:00:00:00:00:03"
    ifcfg_with_macaddr_network = macaddr_config.NETS[2][0]
    ifcfg_bond_param_with_macaddr = [
        ifcfg_with_macaddr_mac,
        ifcfg_with_macaddr_network,
        via_ifcfg
    ]

    # With MACADDR BOND_VLAN params
    ifcfg_vlan_with_macaddr_mac = "00:00:00:00:00:04"
    ifcfg_vlan_with_macaddr_network = macaddr_config.NETS[2][1]
    ifcfg_vlan_bond_param_with_macaddr = [
        ifcfg_vlan_with_macaddr_mac,
        ifcfg_vlan_with_macaddr_network,
        via_ifcfg
    ]

    # Without MACADDR BOND params
    ifcfg_without_macaddr_network = macaddr_config.NETS[2][2]
    ifcfg_bond_param_without_macaddr = [
        None,
        ifcfg_without_macaddr_network,
        via_ifcfg
    ]

    # Without MACADDR BOND_VLAN params
    ifcfg_vlan_without_macaddr_network = macaddr_config.NETS[2][3]
    ifcfg_vlan_bond_param_without_macaddr = [
        None,
        ifcfg_vlan_without_macaddr_network,
        via_ifcfg
    ]

    @tier2
    @pytest.mark.parametrize(
        ("macaddr", "network", "via"),
        [
            pytest.param(
                *nm_bond_param_with_macaddr, marks=(
                        polarion("RHEVM-23914")
                )
            ),
            pytest.param(
                *nm_vlan_bond_param_with_macaddr, marks=(
                        polarion("RHEVM-25022")
                )
            ),
            pytest.param(
                *nm_bond_param_without_macaddr, marks=(
                        polarion("RHEVM-25014")
                )
            ),
            pytest.param(
                *nm_vlan_bond_param_without_macaddr, marks=(
                        polarion("RHEVM-25024")
                )
            ),
            pytest.param(
                *ifcfg_bond_param_with_macaddr, marks=(
                        polarion("RHEVM-23229")
                )
            ),
            pytest.param(
                *ifcfg_vlan_bond_param_with_macaddr, marks=(
                        polarion("RHEVM-25023")
                )
            ),
            pytest.param(
                *ifcfg_bond_param_without_macaddr, marks=(
                        polarion("RHEVM-25013")
                )
            ),
            pytest.param(
                *ifcfg_vlan_bond_param_without_macaddr, marks=(
                        polarion("RHEVM-25025")
                )
            ),
        ],
        ids=[
            # Via NetworkManager
            "BOND_with_MACADDR_via_NM",
            "BOND_VLAN_with_MACADDR_via_NM",
            "BOND_without_MACADDR_via_NM",
            "BOND_VLAN_without_MACADDR_via_NM",

            # Via IFCFG
            "BOND_with_MACADDR_via_IFCFG",
            "BOND_VLAN_with_MACADDR_via_IFCFG",
            "BOND_without_MACADDR_via_IFCFG",
            "BOND_VLAN_without_MACADDR_via_IFCFG",
        ]
    )
    def test_mac_addr(self, macaddr, network, via):
        """
        Test BOND/VLAN over BOND with/without MACADDR value
        """
        _id = global_helper.get_test_parametrize_ids(
            item=self.test_mac_addr.parametrize,
            params=[macaddr, network, via]
        )
        testflow.step(_id)
        assert helper.run_macaddr_test(network=network)
