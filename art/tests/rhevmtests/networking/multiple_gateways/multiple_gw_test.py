#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
"""

import logging
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

IP = config.MG_IP_ADDR
NETMASK = config.NETMASK
GATEWAY = config.MG_GATEWAY
SUBNET = config.SUBNET
TIMEOUT = config.CONNECT_TIMEOUT
HOST_NICS = None  # Filled in setup_module
logger = logging.getLogger("Multiple_Gateway_Cases")

# #######################################################################

########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    """
    obtain host NICs for the first Network Host
    """
    global HOST_NICS
    HOST_NICS = config.VDS_HOSTS[0].nics


@attr(tier=2)
class TestGatewaysCase1(TestCase):
    """
    Verify you can configure additional network beside MGMT with gateway
    Verify you can remove network configured with gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration (including gateway)
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": False, "bootproto": "static",
                "address": [IP], "netmask": [NETMASK], "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3949")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3965")
    def test_detach_gw_net(self):
        """
        Remove network with gw configuration from setup
        """
        if not ll_hosts.sendSNRequest(
            True, host=config.HOSTS[0],
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=TIMEOUT, force=False
        ):
            raise exceptions.NetworkException(
                "Couldn't remove %s with gateway from setup" %
                config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from DC/CLuster", config.NETWORKS[0])
        if not ll_networks.removeNetwork(True, network=config.NETWORKS[0]):
            logger.error(
                "Cannot remove network %s from DC/Cluster", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase2(TestCase):
    """
    Verify you can configure additional VLAN network with static IP and gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical tagged network on DC/Cluster/Hosts.
        Configure it with static IP configuration.
        """

        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "nic": 1, "vlan_id": config.VLAN_ID[0], "required": False,
                "bootproto": "static", "address": [IP], "netmask": [NETMASK],
                "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0, 1]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3953")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """

        logger.info("Remove network %s from setup", config.VLAN_NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.VLAN_NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.VLAN_NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase3(TestCase):
    """
    Verify you can configure additional bridgeless network with static IP.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical non-vm network on DC/Cluster/Hosts
        Configure it with static IP configuration
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "usages": "", "required": False,
                "bootproto": "static", "address": [IP], "netmask": [NETMASK],
                "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3954")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase4(TestCase):
    """
    Verify you can configure additional display network with static ip config.
    Mgmt network should be static
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical display network on DC/Cluster/Hosts
        Configure it with static IP configuration
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "cluster_usages": "display", "required": False,
                "bootproto": "static", "address": [IP], "netmask": [NETMASK],
                "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3956")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup %s", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase5(TestCase):
    """
    Try to assign to vm network incorrect static IP and gw addresses
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        local_dict1 = {
            config.NETWORKS[0]: {
                "nic": 1, "required": False
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3958")
    def test_check_incorrect_config(self):
        """
        Try to create logical  network on DC/Cluster/Hosts
        Configure it with static IP configuration and incorrect gateway or IP
        """

        logger.info(
            "Trying to attach network %s with incorrect IP on NIC %s. "
            "The test should fail to do it", config.NETWORKS[0], HOST_NICS[1]
        )
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic=HOST_NICS[1], network=config.NETWORKS[0],
            boot_protocol="static", address="1.1.1.298", netmask=NETMASK,
            gateway=GATEWAY
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate SNNIC object")
        net_obj.append(out["host_nic"])
        if not ll_hosts.sendSNRequest(
            False, host=config.HOSTS[0], nics=net_obj,
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=TIMEOUT, force=False
        ):
            raise exceptions.NetworkException(
                "Can setupNetworks when shouldn't"
            )

        logger.info(
            "Trying to attach network %s with incorrect gateway on NIC %s."
            " The test should fail to do it", config.NETWORKS[0], HOST_NICS[1]
        )
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic=HOST_NICS[1], network=config.NETWORKS[0],
            boot_protocol="static", address=IP, netmask=NETMASK,
            gateway="1.1.1.289"
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate SNNIC object")
        net_obj.append(out["host_nic"])
        if not ll_hosts.sendSNRequest(
            False, host=config.HOSTS[0], nics=net_obj,
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=TIMEOUT, force=False
        ):
            raise exceptions.NetworkException(
                "Can setupNetworks when shouldn't"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase6(TestCase):
    """
    Verify you can configure additional network with gateway 0.0.0.0
    """
    __test__ = True

    @polarion("RHEVM3-3966")
    def test_check_ip_rule(self):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration and gateway of 0.0.0.0
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": False, "bootproto": "static",
                "address": [IP], "netmask": [NETMASK], "gateway": ["0.0.0.0"]
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase7(TestCase):
    """
    Verify you can add additional NIC to the already created bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration on bond of 2 NICs
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": "bond0", "slaves": [2, 3], "required": False,
                "bootproto": "static", "address": [IP], "netmask": [NETMASK],
                "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s"
            )

    @polarion("RHEVM3-3963")
    def test_check_ip_rule(self):
        """
        Add additional NIC to the bond and check IP rule
        """
        logger.info("Checking IP rule before adding 3rd NIC")
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

        logger.info("Generating network object for 3 NIC bond ")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="bond0", network=config.NETWORKS[0],
            slaves=[HOST_NICS[2], HOST_NICS[3], HOST_NICS[1]],
            boot_protocol="static", address=IP, netmask=NETMASK,
            gateway=GATEWAY
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate SNNIC object")
        net_obj.append(out["host_nic"])
        if not ll_hosts.sendSNRequest(
            True, host=config.HOSTS[0], nics=net_obj,
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=TIMEOUT, force=False
        ):
            raise exceptions.NetworkException(
                "Cannot update bond to have 2 NICs"
            )

        logger.info("Checking IP rule after adding 3rd NIC")
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration after updating BOND"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase8(TestCase):
    """
    Verify you can remove Nic from bond having network with gw configured on it
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts and attach it to bond.
        Bond should have 3 NICs
        Configure it with static IP configuration (including gateway)
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": "bond0", "slaves": [2, 3, 1], "required": False,
                "bootproto": "static", "address": [IP], "netmask": [NETMASK],
                "gateway": [GATEWAY]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3964")
    def test_check_ip_rule(self):
        """
        Check the appearance of the subnet with ip rule command
        Remove a NIC from bond and check ip rule again
        """
        logger.info("Checking the IP rule before removing one NIC from bond")
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

        logger.info("Generating network object for 2 NIC bond ")
        net_obj = []
        rc, out = ll_hosts.genSNNic(
            nic="bond0", network=config.NETWORKS[0],
            slaves=[HOST_NICS[2], HOST_NICS[3]], boot_protocol="static",
            address=IP, netmask=NETMASK, gateway=GATEWAY
        )
        if not rc:
            raise exceptions.NetworkException("Cannot generate SNNIC object")
        net_obj.append(out["host_nic"])
        if not ll_hosts.sendSNRequest(
            True, host=config.HOSTS[0], nics=net_obj,
            auto_nics=[config.VDS_HOSTS[0].nics[0]], check_connectivity="true",
            connectivity_timeout=TIMEOUT, force=False
        ):
            raise exceptions.NetworkException(
                "Cannot update bond to have 2 NICs"
            )

        logger.info("Checking the IP rule after removing one NIC from bond")
        if not ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration after removing NIC from bond"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=2)
class TestGatewaysCase9(TestCase):
    """
    Verify you can configure additional network without gateway
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create logical vm network on DC/Cluster/Hosts
        Configure it with static IP configuration without gateway
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": False, "bootproto": "static",
                "address": [IP], "netmask": [NETMASK]
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise exceptions.NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3955")
    def test_check_ip_rule(self):
        """
        Check correct configuration with ip rule function
        """
        if ll_networks.checkIPRule(
            config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Gateway is configured when shouldn't"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network %s from setup", config.NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=config.HOSTS[0], network=[config.NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )
