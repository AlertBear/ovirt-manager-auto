#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
This job required password less ssh between the machine that run the job
and the host
"""

import helper
import logging
from art.unittest_lib import attr
from rhevmtests.networking import config
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as net_helper
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("ArbitraryVlanDeviceName_Cases")

HOST_NAME = None  # Filled in setup_module
HOST_NICS = None  # Filled in setup_module


def setup_module():
    """
    setup_module
    """
    global HOST_NAME
    global HOST_NICS
    HOST_NICS = config.VDS_HOSTS[0].nics
    HOST_NAME = ll_hosts.get_host_name_from_engine(config.VDS_HOSTS[0].ip)


class TestArbitraryVlanDeviceNameTearDown(TestCase):
    """
    Tear down for ArbitraryVlanDeviceName
    This job create networks on host and we need to make sure that we clean
    the host from all VLANs and bridges
    """
    apis = set(["rest"])

    @classmethod
    def teardown_class(cls):
        helper.job_tear_down()


@attr(tier=2)
class TestArbitraryVlanDeviceName01(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create VLAN entity with name on the host
    2. Check that the VLAN network exists on host via engine
    3. Attach the vlan to bridge
    4. Add the bridge with VLAN to virsh
    5. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN entity with name on the host
        """
        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=[helper.VLAN_IDS[0]],
            vlan_name=[helper.VLAN_NAMES[0]]
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=[helper.BRIDGE_NAMES[0]],
            network=[helper.VLAN_NAMES[0]]
        )

    @polarion("RHEVM3-4170")
    def test_vlan_on_nic(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        helper.check_if_nic_in_host_nics(
            nic=helper.VLAN_NAMES[0], host=HOST_NAME
        )
        net_helper.is_network_in_vds_caps(
            host_resource=config.VDS_HOSTS[0], network=helper.BRIDGE_NAMES[0]
        )


@attr(tier=2)
class TestArbitraryVlanDeviceName02(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create empty BOND
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create empty BOND via SetupNetworks
        Create VLAN entity with name on the host
        """
        network_host_api_dict = {
            "add": {
                "1": {
                    "nic": config.BOND[0],
                    "slaves": config.VDS_HOSTS[0].nics[2:4]
                }
            }
        }
        if not hl_host_network.setup_networks(
            host_name=config.HOSTS[0], **network_host_api_dict
        ):
            raise config.NET_EXCEPTION("Cannot create and attach BOND")

        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=config.BOND[0],
            vlan_id=[helper.VLAN_IDS[0]], vlan_name=[helper.VLAN_NAMES[0]]
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=[helper.BRIDGE_NAMES[0]],
            network=[helper.VLAN_NAMES[0]]
        )

    @polarion("RHEVM3-4171")
    def test_vlan_on_bond(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        helper.check_if_nic_in_host_nics(
            nic=helper.VLAN_NAMES[0], host=HOST_NAME
        )
        net_helper.is_network_in_vds_caps(
            host_resource=config.VDS_HOSTS[0], network=helper.BRIDGE_NAMES[0]
        )


@attr(tier=2)
class TestArbitraryVlanDeviceName03(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create 3 VLANs with name on the host
    2. For each VLAN check that the VLAN network exists on host via engine
    3. For each VLAN attach the vlan to bridge
    4. For each VLAN add the bridge with VLAN to virsh
    5. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN entity with name on the host
        """
        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=1,
            vlan_id=helper.VLAN_IDS,
            vlan_name=helper.VLAN_NAMES
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=helper.BRIDGE_NAMES,
            network=helper.VLAN_NAMES
        )

    @polarion("RHEVM3-4172")
    def test_multiple_vlans_on_nic(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridges is in getVdsCaps
        """
        for i in range(3):
            helper.check_if_nic_in_host_nics(
                nic=helper.VLAN_NAMES[i], host=HOST_NAME
            )
            net_helper.is_network_in_vds_caps(
                host_resource=config.VDS_HOSTS[0],
                network=helper.BRIDGE_NAMES[i]
            )


@attr(tier=2)
class TestArbitraryVlanDeviceName04(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create empty BOND
    2. Create 3 VLANs with name on the host
    3. For each VLAN check that the VLAN network exists on host via engine
    4. For each VLAN attach the vlan to bridge
    5. For each VLAN add the bridge with VLAN to virsh
    6. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create empty BOND
        Create VLAN entity with name on the host
        """
        logger.info("Create empty BOND")
        local_dict = {
            "add": {
                "1": {
                    "nic": config.BOND[0],
                    "slaves": HOST_NICS[2:4]
                },
            }
        }
        if not hl_host_network.setup_networks(
            host_name=config.HOSTS[0], **local_dict
        ):
            raise config.NET_EXCEPTION("Cannot create and attach BOND")

        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=1,
            vlan_id=helper.VLAN_IDS,
            vlan_name=helper.VLAN_NAMES
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=helper.BRIDGE_NAMES,
            network=helper.VLAN_NAMES
        )

    @polarion("RHEVM3-4173")
    def test_multiple_vlans_on_bond(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridges is in getVdsCaps
        """
        for i in range(3):
            helper.check_if_nic_in_host_nics(
                nic=helper.VLAN_NAMES[i], host=HOST_NAME
            )
            net_helper.is_network_in_vds_caps(
                host_resource=config.VDS_HOSTS[0],
                network=helper.BRIDGE_NAMES[i]
            )


@attr(tier=2)
class TestArbitraryVlanDeviceName05(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create VLAN on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN on NIC via SetupNetworks
        Create VLAN entity with name on the host
        """
        logger.info(
            "Create and attach VLAN network on NIC to DC/Cluster"
        )
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "false",
            },
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise config.NET_EXCEPTION("Cannot create and attach network")

        sn_dict = {
            "add": {
                "1": {
                    "network": config.VLAN_NETWORKS[0],
                    "nic": HOST_NICS[1]
                }
            }
        }
        logger.info(
            "Attach %s to %s via setupnetworks",
            config.VLAN_NETWORKS[0], HOST_NAME
        )
        if not hl_host_network.setup_networks(host_name=HOST_NAME, **sn_dict):
            raise config.NET_EXCEPTION(
                "Failed to attach  %s to %s via setupnetworks" %
                (config.VLAN_NETWORKS[0], HOST_NAME)
            )
        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=[helper.VLAN_IDS[0]],
            vlan_name=[helper.VLAN_NAMES[0]]
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=[helper.BRIDGE_NAMES[0]],
            network=[helper.VLAN_NAMES[0]]
        )

    @polarion("RHEVM3-4174")
    def test_mixed_vlan_types(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        helper.check_if_nic_in_host_nics(
            nic=helper.VLAN_NAMES[0], host=HOST_NAME
        )
        net_helper.is_network_in_vds_caps(
            host_resource=config.VDS_HOSTS[0], network=helper.BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        logger.info("Removing all networks from %s", config.DC_NAME[0])
        if not hl_networks.remove_all_networks(
            datacenter=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove all networks from %s", config.DC_NAME[0])
        super(TestArbitraryVlanDeviceName05, cls).teardown_class()


@attr(tier=2)
class TestArbitraryVlanDeviceName06(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create Non-VM network on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create Non-VM network on NIC via SetupNetworks
        Create VLAN entity with name on the host
        """
        logger.info(
            "Create and attach VLAN network on NIC to DC/Cluster and Host"
        )
        local_dict = {
            config.NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "false",
                "usages": ""
            },
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1],
        ):
            raise config.NET_EXCEPTION("Cannot create and attach network")

        helper.add_vlans_to_host(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=[helper.VLAN_IDS[0]],
            vlan_name=[helper.VLAN_NAMES[0]]
        )
        helper.add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=[helper.BRIDGE_NAMES[0]],
            network=[helper.VLAN_NAMES[0]]
        )

    @polarion("RHEVM3-4175")
    def test_vlan_with_non_vm(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        helper.check_if_nic_in_host_nics(
            nic=helper.VLAN_NAMES[0], host=HOST_NAME
        )
        net_helper.is_network_in_vds_caps(
            host_resource=config.VDS_HOSTS[0], network=helper.BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        logger.info("Removing all networks from %s", config.DC_NAME[0])
        if not hl_networks.remove_all_networks(
            datacenter=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove all networks from %s", config.DC_NAME[0]
            )
        super(TestArbitraryVlanDeviceName06, cls).teardown_class()
