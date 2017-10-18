#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).

This test will use the following elements on the engine:

Host (VDS_HOST0), networks (vm & non-vm), BONDS, VLANS, Bridge
"""

import config as vlan_name_conf

import pytest
from fixtures import create_vlans_on_host
from rhevmtests import helpers

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import rhevmtests.networking.config as network_conf
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, tier2
from rhevmtests.networking.fixtures import (  # noqa: F401
     clean_host_interfaces,
     setup_networks_fixture,
     remove_all_networks,
     create_and_attach_networks,
)


@pytest.mark.usefixtures(
    create_and_attach_networks.__name__,
    setup_networks_fixture.__name__,
    create_vlans_on_host.__name__
)
class TestArbitraryVlanDeviceName01(NetworkTest):
    """
    1) Create empty BOND.
    2) Create VLAN(s) entity with name on the host.
    3) Check that the VLAN(s) networks exists on host via engine.
    """

    dc = network_conf.DC_0

    # create_and_attach_network params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [network_conf.CL_0],
            "networks": vlan_name_conf.CASE_1_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # create_networks_on_engine
    net_1 = vlan_name_conf.ARBITRARY_NETS[1][0]
    net_2 = vlan_name_conf.ARBITRARY_NETS[1][1]

    # create_vlans_on_host
    vlan_ids = vlan_name_conf.VLAN_IDS_LIST
    vlan_names = vlan_name_conf.VLAN_NAMES[1]
    bond_1 = "bond01"
    bond_2 = "bond02"

    # param_list include: NIC index/bond, vlan_ids, vlan_names
    param_list = [
        (1, [vlan_ids[0]], [vlan_names[0]]),
        (bond_1, [vlan_ids[1]], [vlan_names[1]]),
        (4, vlan_ids[2:5], vlan_names[2:5]),
        (bond_2, vlan_ids[5:8], vlan_names[5:8]),
        (7, [vlan_ids[9]], [vlan_names[9]]),
        (8, [vlan_ids[10]], [vlan_names[10]])
    ]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            bond_1: {
                "nic": bond_1,
                "slaves": [2, 3]
            },
            bond_2: {
                "nic": bond_2,
                "slaves": [5, 6]
            },
            net_1: {
                "nic": 7,
                "network": net_1
            },
            net_2: {
                "nic": 8,
                "network": net_2
            },
        }
    }

    @tier2
    @pytest.mark.parametrize(
        "vlan_names",
        [
            pytest.param([vlan_names[0]], marks=(polarion("RHEVM3-4170"))),
            pytest.param([vlan_names[1]], marks=(polarion("RHEVM3-4171"))),
            pytest.param(vlan_names[2:5], marks=(polarion("RHEVM3-4172"))),
            pytest.param(vlan_names[5:8], marks=(polarion("RHEVM3-4173"))),
            pytest.param([vlan_names[9]], marks=(polarion("RHEVM3-4174"))),
            pytest.param([vlan_names[10]], marks=(polarion("RHEVM3-4175"))),
        ],
        ids=(
            "Check_VLAN_on_host_NIC",
            "Check_VLAN_on_host_BOND",
            "Check_multiple_VLANs_on_host_NIC",
            "Check_multiple_VLANs_on_host_BOND",
            "Check_mixed_VLANs_types",
            "Check_VLAN_on_non-VM_network"
        )
    )
    def test_vlan_on_nic_and_on_bond(self, vlan_names):
        """
        Check that the VLAN network exists on host via engine.
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_vlan_on_nic_and_on_bond.parametrize,
            params=vlan_names
        )
        host_obj = ll_hosts.get_host_object(host_name=network_conf.HOST_0_NAME)
        testflow.step(_id)
        for vlan in vlan_names:
            assert ll_hosts.get_host_nic(host=host_obj, nic=vlan)
