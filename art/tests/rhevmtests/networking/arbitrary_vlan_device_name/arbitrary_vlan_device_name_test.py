#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).

This test will use the following elements on the engine:

Host (VDS_HOST0), networks (vm & non-vm), BONDS, VLANS, Bridge
"""

import logging

import pytest

import config as vlan_name_conf
import helper
import rhevmtests.networking.config as network_conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    create_vlans_and_bridges_on_host, create_networks_on_engine
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture, clean_host_interfaces
)  # flake8: noqa

logger = logging.getLogger("ArbitraryVlanDeviceName_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(create_vlans_and_bridges_on_host.__name__)
class TestArbitraryVlanDeviceName01(NetworkTest):
    """
    1. Create VLAN entity with name on the host
    2. Check that the VLAN network exists on host via engine
    3. Attach the vlan to bridge
    4. Add the bridge with VLAN to virsh
    5. Remove the VLAN using setupNetwork
    """
    __test__ = True

    vlan_ids = [vlan_name_conf.ARBITRARY_VLAN_IDS[0]]
    vlan_names = [vlan_name_conf.VLAN_NAMES[0]]
    bridge_names = [vlan_name_conf.BRIDGE_NAMES[0]]
    nic = 1

    @polarion("RHEVM3-4170")
    def test_vlan_on_nic(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step(
            "Check if %s in %s NICs", self.vlan_names[0],
            network_conf.HOST_0_NAME
        )
        assert helper.check_if_nic_in_host_nics(
            nic=self.vlan_names[0], host=network_conf.HOST_0_NAME
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge_names[0],
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=self.bridge_names[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__
)
class TestArbitraryVlanDeviceName02(NetworkTest):
    """
    1. Create empty BOND
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    vlan_ids = [vlan_name_conf.ARBITRARY_VLAN_IDS[0]]
    vlan_names = [vlan_name_conf.VLAN_NAMES[0]]
    bridge_names = [vlan_name_conf.BRIDGE_NAMES[0]]
    nic = "bond01"
    hosts_nets_nic_dict = {
        0: {
            nic: {
                "nic": nic,
                "slaves": [2, 3]
            }
        }
    }

    @polarion("RHEVM3-4171")
    def test_vlan_on_bond(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step(
            "Check if %s in %s NICs", self.vlan_names[0],
            network_conf.HOST_0_NAME
        )
        assert helper.check_if_nic_in_host_nics(
            nic=self.vlan_names[0], host=network_conf.HOST_0_NAME
        )

        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge_names[0],
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=self.bridge_names[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(create_vlans_and_bridges_on_host.__name__)
class TestArbitraryVlanDeviceName03(NetworkTest):
    """
    1. Create 3 VLANs with name on the host
    2. For each VLAN check that the VLAN network exists on host via engine
    3. For each VLAN attach the vlan to bridge
    4. For each VLAN add the bridge with VLAN to virsh
    5. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    vlan_ids = vlan_name_conf.ARBITRARY_VLAN_IDS
    vlan_names = vlan_name_conf.VLAN_NAMES
    bridge_names = vlan_name_conf.BRIDGE_NAMES
    nic = 1

    @polarion("RHEVM3-4172")
    def test_multiple_vlans_on_nic(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridge_names is in getVdsCaps
        """
        for vlan_name, bridge_name in zip(self.vlan_names, self.bridge_names):
            testflow.step(
                "Check if %s in %s NICs", vlan_name, network_conf.HOST_0_NAME
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


@attr(tier=2)
@pytest.mark.usefixtures(
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__
)
class TestArbitraryVlanDeviceName04(NetworkTest):
    """
    1. Create empty BOND
    2. Create 3 VLANs with name on the host
    3. For each VLAN check that the VLAN network exists on host via engine
    4. For each VLAN attach the vlan to bridge
    5. For each VLAN add the bridge with VLAN to virsh
    6. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    nic = "bond02"
    vlan_ids = vlan_name_conf.ARBITRARY_VLAN_IDS
    vlan_names = vlan_name_conf.VLAN_NAMES
    bridge_names = vlan_name_conf.BRIDGE_NAMES
    hosts_nets_nic_dict = {
        0: {
            nic: {
                "nic": nic,
                "slaves": [2, 3]
            }
        }
    }

    @polarion("RHEVM3-4173")
    def test_multiple_vlans_on_bond(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridge_names is in getVdsCaps
        """
        for vlan_name, bridge_name in zip(self.vlan_names, self.bridge_names):
            testflow.step(
                "Check if %s in %s NICs", vlan_name, network_conf.HOST_0_NAME
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


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks_on_engine.__name__,
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__,
)
class TestArbitraryVlanDeviceName05(NetworkTest):
    """
    1. Create VLAN on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    nic = 1
    network = vlan_name_conf.ARBITRARY_NETS[5][0]
    vlan_ids = [vlan_name_conf.ARBITRARY_VLAN_IDS[0]]
    vlan_names = [vlan_name_conf.VLAN_NAMES[0]]
    bridge_names = [vlan_name_conf.BRIDGE_NAMES[0]]
    hosts_nets_nic_dict = {
        0: {
            network: {
                "nic": nic,
                "network": network
            }
        }
    }

    @polarion("RHEVM3-4174")
    def test_mixed_vlan_types(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step(
            "Check if %s in %s NICs", self.vlan_names[0],
            network_conf.HOST_0_NAME
        )
        assert helper.check_if_nic_in_host_nics(
            nic=self.vlan_names[0], host=network_conf.HOST_0_NAME
        )

        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge_names[0],
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=self.bridge_names[0]
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_networks_on_engine.__name__,
    setup_networks_fixture.__name__,
    create_vlans_and_bridges_on_host.__name__,
)
class TestArbitraryVlanDeviceName06(NetworkTest):
    """
    1. Create Non-VM network on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    nic = 1
    network = vlan_name_conf.ARBITRARY_NETS[6][0]
    vlan_ids = [vlan_name_conf.ARBITRARY_VLAN_IDS[0]]
    vlan_names = [vlan_name_conf.VLAN_NAMES[0]]
    bridge_names = [vlan_name_conf.BRIDGE_NAMES[0]]
    hosts_nets_nic_dict = {
        0: {
            network: {
                "nic": nic,
                "network": network
            }
        }
    }

    @polarion("RHEVM3-4175")
    def test_vlan_with_non_vm(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step(
            "Check if %s in %s NICs", self.vlan_names[0],
            network_conf.HOST_0_NAME
        )
        assert helper.check_if_nic_in_host_nics(
            nic=self.vlan_names[0], host=network_conf.HOST_0_NAME
        )

        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge_names[0],
            network_conf.HOST_0_NAME
        )
        assert network_helper.is_network_in_vds_caps(
            host_resource=network_conf.VDS_0_HOST, network=self.bridge_names[0]
        )
