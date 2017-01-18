#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).

This test will use the following elements on the engine:

Host (VDS_HOST0), networks (vm & non-vm), BONDS, VLANS, Bridge
"""

import pytest

import config as vlan_name_conf
import helper
import rhevmtests.networking.config as network_conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow, NetworkTest
from fixtures import (
    create_vlans_and_bridges_on_host, create_networks_on_engine
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa


@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__
)
class TestArbitraryVlanDeviceName01(NetworkTest):
    """
    1) Create empty BOND.
    2) Create VLAN(s) entity with name on the host.
    3) Check that the VLAN(s) networks exists on host via engine.
    4) Attach the VLAN to bridge.
    5) Add the bridge with VLAN to virsh.
    """

    # create_vlans_and_bridges_on_host
    vlan_ids = vlan_name_conf.ARBITRARY_VLAN_IDS_CASE_1
    vlan_names = vlan_name_conf.VLAN_NAMES[1]
    bridge_names = vlan_name_conf.BRIDGE_NAMES[1]
    bond = "bond01"

    # param_list include: NIC/bond, vlan_ids, vlan_nams, bridge_names
    param_list = [
        (1, [vlan_ids[0]], [vlan_names[0]], [bridge_names[0]]),
        (bond, [vlan_ids[1]], [vlan_names[1]], [bridge_names[1]])
    ]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [2, 3]
            }
        }
    }

    @attr(tier=2)
    @pytest.mark.parametrize(
        ("nic", "vlan_name", "bridge_name"),
        [
            polarion("RHEVM3-4170")([1, vlan_names[0], bridge_names[0]]),
            polarion("RHEVM3-4171")([bond, vlan_names[1], bridge_names[1]])
        ]
    )
    def test_vlan_on_nic_and_on_bond(self, nic, vlan_name, bridge_name):
        """
        1) Check that the VLAN network exists on host via engine.
        2) Check that the bridge is in getVdsCaps.
        """
        nic = (
            network_conf.HOST_0_NICS[nic] if isinstance(nic, int)
            else self.bond
        )
        testflow.step(
            "Check if VLAN name %s exists on host NIC %s", vlan_name, nic
        )
        assert helper.check_if_nic_in_host_nics(
            nic=vlan_name, host=network_conf.HOST_0_NAME
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", bridge_name,
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=bridge_name
        )


@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__
)
class TestArbitraryVlanDeviceName02(NetworkTest):
    """
    1) Create empty BOND.
    2) Create 6 VLAN(s) entity with name on the host.
    3) For each VLAN check that the VLAN network exists on host via engine.
    4) For each VLAN attach the vlan to bridge.
    5) For each VLAN add the bridge with VLAN to virsh.
    """

    # create_vlans_and_bridges_on_host
    vlan_ids = vlan_name_conf.ARBITRARY_VLAN_IDS_CASE_2
    vlan_names = vlan_name_conf.VLAN_NAMES[2]
    bridge_names = vlan_name_conf.BRIDGE_NAMES[2]
    bond = "bond02"

    # param_list include: NIC/bond, vlan_ids, vlan_nams, bridge_names
    param_list = [
        (1, vlan_ids[:3], vlan_names[:3], bridge_names[:3]),
        (bond, vlan_ids[3:], vlan_names[3:], bridge_names[3:])
    ]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            bond: {
                "nic": bond,
                "slaves": [2, 3]
            }
        }
    }

    @attr(tier=2)
    @pytest.mark.parametrize(
        ("nic", "vlan_names", "bridge_names"),
        [
            polarion("RHEVM3-4172")([1, vlan_names[:3], bridge_names[:3]]),
            polarion("RHEVM3-4173")([bond, vlan_names[3:], bridge_names[3:]])
        ]
    )
    def test_multiple_vlan_on_nic_and_on_bond(
        self, nic, vlan_names, bridge_names
    ):
        """
        1) Check that the VLANs network exists on host via engine.
        2) Check that the bridge is in getVdsCaps.
        """
        nic = (
            network_conf.HOST_0_NICS[nic] if isinstance(nic, int)
            else "%s" % self.bond
        )
        for vlan_name, bridge_name in zip(vlan_names, bridge_names):
            testflow.step(
                "Check if VLAN name %s exists on host NIC %s", vlan_name, nic
            )
            assert helper.check_if_nic_in_host_nics(
                nic=vlan_name, host=network_conf.HOST_0_NAME
            )

            testflow.step(
                "Check if %s in %s GetVdsCaps", bridge_name,
                network_conf.HOST_0_NAME
            )
            assert network_helper.is_network_in_vds_caps(
                host_resource=network_conf.VDS_0_HOST, network=bridge_name
            )


@pytest.mark.usefixtures(
    create_networks_on_engine.__name__,
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__
)
class TestArbitraryVlanDeviceName03(NetworkTest):
    """
    1) Create VLAN network and Non-VM network on NIC via SetupNetworks.
    2) Create VLAN(s) entity with name on the host.
    3) Check that the VLAN network and Non-VM network exists on host via engin.
    4) For each VLAN attach the vlan to bridge.
    5) For each VLAN add the bridge with VLAN to virsh.
    """

    # create_vlans_and_bridges_on_host
    vlan_ids = vlan_name_conf.ARBITRARY_VLAN_IDS_CASE_3
    vlan_names = vlan_name_conf.VLAN_NAMES[3]
    bridge_names = vlan_name_conf.BRIDGE_NAMES[3]

    # param_list include: NIC/bond, vlan_ids, vlan_nams, bridge_names
    param_list = [
        (1, [vlan_ids[0]], [vlan_names[0]], [bridge_names[0]]),
        (2, [vlan_ids[1]], [vlan_names[1]], [bridge_names[1]])
    ]

    # create_networks_on_engine
    net_1 = vlan_name_conf.ARBITRARY_NETS[3][0]
    net_2 = vlan_name_conf.ARBITRARY_NETS[3][1]

    # setup_networks_fixture
    hosts_nets_nic_dict = {
        0: {
            net_1: {
                "nic": 1,
                "network": net_1
            },
            net_2: {
                "nic": 2,
                "network": net_2
            },
        }
    }

    @attr(tier=2)
    @pytest.mark.parametrize(
        ("vlan_name", "bridge_name"),
        [
            polarion("RHEVM3-4174")([vlan_names[0], bridge_names[0]]),
            polarion("RHEVM3-4175")([vlan_names[1], bridge_names[1]])
        ]
    )
    def test_vlans_types_and_vlan_with_non_vm(self, vlan_name, bridge_name):
        """
        1) Check that the VLAN network exists on host via engine.
        2) Check that the bridge is in getVdsCaps.
        """
        nic = (
            "%s" % network_conf.HOST_0_NICS[1]
            if vlan_name == self.vlan_names[0] else
            "%s" % network_conf.HOST_0_NICS[2]
        )
        testflow.step(
            "Check if VLAN name %s exist on host NIC %s", vlan_name, nic
        )
        assert helper.check_if_nic_in_host_nics(
            nic=vlan_name, host=network_conf.HOST_0_NAME
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", bridge_name,
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=bridge_name
        )
