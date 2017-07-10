#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Network/
4_2_Network_Duplicate_VLAN_ID
https://bugzilla.redhat.com/show_bug.cgi?id=1410490
"""

import pytest

import config as dup_vlan_conf
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import tier2, NetworkTest
from rhevmtests.networking.fixtures import (
    clean_host_interfaces_fixture_function,
    remove_all_networks
)
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    host_network as hl_host_network
)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    remove_all_networks.__name__
)
class TestDuplicateVlanId01(NetworkTest):
    """
    Test same VLAN ID on engine and on host
    """
    # clean_host_interfaces_fixture_function params
    hosts_nets_nic_dict = conf.CLEAN_HOSTS_DICT

    # remove_all_networks params
    remove_dcs_networks = [conf.DC_0]

    @tier2
    @polarion("RHEVM-21837")
    def test_01_create_networks_same_vlan_id(self):
        """
        Create 2 networks with the same VLAN ID
        """
        assert hl_networks.create_and_attach_networks(
            data_center=conf.DC_0, cluster=conf.CL_0,
            network_dict=dup_vlan_conf.ALLOW_DUPLICATE_VLAN_ID_CREATE_NETWORKS
        )

    @tier2
    @pytest.mark.parametrize(
        "positive",
        [
            pytest.param(True, marks=(polarion("RHEVM3-21841"))),
            pytest.param(False, marks=(polarion("RHEVM3-21962"))),
        ],
        ids=[
            "Same_vlan_different_host_nics",
            "Negative_same_vlan_same_host_nic",
        ]
    )
    @pytest.mark.usefixtures(
        clean_host_interfaces_fixture_function.__name__
    )
    def test_02_attach_networks(self, positive):
        """
        Attach 2 networks with the same VLAN ID to different host NICS
        """
        n1 = conf.HOST_0_NICS[1]
        n2 = conf.HOST_0_NICS[2] if positive else n1
        dup_vlan_conf.ALLOW_DUPLICATE_VLAN_ID_SN_DICT["add"]["1"]["nic"] = n1
        dup_vlan_conf.ALLOW_DUPLICATE_VLAN_ID_SN_DICT["add"]["2"]["nic"] = n2
        res = hl_host_network.setup_networks(
            host_name=conf.HOST_0_NAME,
            **dup_vlan_conf.ALLOW_DUPLICATE_VLAN_ID_SN_DICT
        )
        assert res == positive
