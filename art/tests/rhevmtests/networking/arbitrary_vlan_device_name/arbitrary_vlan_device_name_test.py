#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
This job required password less ssh between the machine that run the job
and the host
"""

import logging

import pytest

import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    case_01_fixture, case_02_fixture, case_03_fixture, case_04_fixture,
    case_05_fixture, case_06_fixture
)

logger = logging.getLogger("ArbitraryVlanDeviceName_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(case_01_fixture.__name__)
class TestArbitraryVlanDeviceName01(NetworkTest):
    """
    1. Create VLAN entity with name on the host
    2. Check that the VLAN network exists on host via engine
    3. Attach the vlan to bridge
    4. Add the bridge with VLAN to virsh
    5. Remove the VLAN using setupNetwork
    """
    __test__ = True
    vlan = conf.VLAN_NAMES[0]
    bridge = conf.BRIDGE_NAMES[0]

    @polarion("RHEVM3-4170")
    def test_vlan_on_nic(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step("Check if %s in %s NICs", self.vlan, conf.HOST_0_NAME)
        self.assertTrue(
            helper.check_if_nic_in_host_nics(
                nic=self.vlan, host=conf.HOST_0_NAME
            )
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge, conf.HOST_0_NAME
        )
        self.assertTrue(
            network_helper.is_network_in_vds_caps(
                host_resource=conf.VDS_0_HOST, network=self.bridge
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_02_fixture.__name__)
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
    vlan = conf.VLAN_NAMES[0]
    bridge = conf.BRIDGE_NAMES[0]

    @polarion("RHEVM3-4171")
    def test_vlan_on_bond(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step("Check if %s in %s NICs", self.vlan, conf.HOST_0_NAME)
        self.assertTrue(
            helper.check_if_nic_in_host_nics(
                nic=self.vlan, host=conf.HOST_0_NAME
            )
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge, conf.HOST_0_NAME
        )
        self.assertTrue(
            network_helper.is_network_in_vds_caps(
                host_resource=conf.VDS_0_HOST, network=self.bridge
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_03_fixture.__name__)
class TestArbitraryVlanDeviceName03(NetworkTest):
    """
    1. Create 3 VLANs with name on the host
    2. For each VLAN check that the VLAN network exists on host via engine
    3. For each VLAN attach the vlan to bridge
    4. For each VLAN add the bridge with VLAN to virsh
    5. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    @polarion("RHEVM3-4172")
    def test_multiple_vlans_on_nic(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridge_names is in getVdsCaps
        """
        for i in range(3):
            testflow.step(
                "Check if %s in %s NICs", conf.VLAN_NAMES[i], conf.HOST_0_NAME
            )
            self.assertTrue(
                helper.check_if_nic_in_host_nics(
                    nic=conf.VLAN_NAMES[i], host=conf.HOST_0_NAME
                )
            )
            testflow.step(
                "Check if %s in %s GetVdsCaps",
                conf.BRIDGE_NAMES[i], conf.HOST_0_NAME
            )
            self.assertTrue(
                network_helper.is_network_in_vds_caps(
                    host_resource=conf.VDS_0_HOST, network=conf.BRIDGE_NAMES[i]
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(case_04_fixture.__name__)
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

    @polarion("RHEVM3-4173")
    def test_multiple_vlans_on_bond(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridge_names is in getVdsCaps
        """
        for i in range(3):
            testflow.step(
                "Check if %s in %s NICs", conf.VLAN_NAMES[i], conf.HOST_0_NAME
            )
            self.assertTrue(
                helper.check_if_nic_in_host_nics(
                    nic=conf.VLAN_NAMES[i], host=conf.HOST_0_NAME
                )
            )
            testflow.step(
                "Check if %s in %s GetVdsCaps",
                conf.BRIDGE_NAMES[i], conf.HOST_0_NAME
            )
            self.assertTrue(
                network_helper.is_network_in_vds_caps(
                    host_resource=conf.VDS_0_HOST, network=conf.BRIDGE_NAMES[i]
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(case_05_fixture.__name__)
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
    vlan = conf.VLAN_NAMES[0]
    bridge = conf.BRIDGE_NAMES[0]

    @polarion("RHEVM3-4174")
    def test_mixed_vlan_types(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step("Check if %s in %s NICs", self.vlan, conf.HOST_0_NAME)
        self.assertTrue(
            helper.check_if_nic_in_host_nics(
                nic=conf.VLAN_NAMES[0], host=conf.HOST_0_NAME
            )
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge, conf.HOST_0_NAME
        )
        self.assertTrue(
            network_helper.is_network_in_vds_caps(
                host_resource=conf.VDS_0_HOST, network=conf.BRIDGE_NAMES[0]
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_06_fixture.__name__)
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
    vlan = conf.VLAN_NAMES[0]
    bridge = conf.BRIDGE_NAMES[0]

    @polarion("RHEVM3-4175")
    def test_vlan_with_non_vm(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        testflow.step("Check if %s in %s NICs", self.vlan, conf.HOST_0_NAME)
        self.assertTrue(
            helper.check_if_nic_in_host_nics(
                nic=conf.VLAN_NAMES[0], host=conf.HOST_0_NAME
            )
        )
        testflow.step(
            "Check if %s in %s GetVdsCaps", self.bridge, conf.HOST_0_NAME
        )
        self.assertTrue(
            network_helper.is_network_in_vds_caps(
                host_resource=conf.VDS_0_HOST, network=conf.BRIDGE_NAMES[0]
            )
        )
