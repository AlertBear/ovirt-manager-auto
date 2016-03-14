#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Multiple Gateways feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
"Multiple Gateway will be tested for untagged, tagged, bond scenarios.
It will cover scenarios for VM/non-VM networks.
Only static IP configuration is tested.
"""

import config
import logging
from art.unittest_lib import attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as exceptions
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

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
class TestGatewaysCase01(TestCase):
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
                "bootproto": "static", "address": [config.IPS[1]],
                "netmask": [NETMASK], "gateway": [GATEWAY]
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
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
class TestGatewaysCase02(TestCase):
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
                "bootproto": "static", "address": [config.IPS[2]],
                "netmask": [NETMASK], "gateway": [GATEWAY]
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
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
class TestGatewaysCase03(TestCase):
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
                "bootproto": "static", "address": [config.IPS[3]],
                "netmask": [NETMASK], "gateway": [GATEWAY]
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
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
class TestGatewaysCase04(TestCase):
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

        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1,
                "bootproto": "static",
                "address": ["5.5.5.298"],
                "netmask": [NETMASK],
                "gateway": [GATEWAY],
                "required": "false",
            },
        }

        if hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise exceptions.NetworkException()

        logger.info(
            "Trying to attach network %s with incorrect gateway on NIC %s."
            " The test should fail to do it", config.NETWORKS[0], HOST_NICS[1]
        )

        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1,
                "bootproto": "static",
                "address": [config.IPS[4]],
                "netmask": [NETMASK],
                "gateway": ["5.5.5.289"],
                "required": "false",
            },
        }

        if hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise exceptions.NetworkException()

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
class TestGatewaysCase05(TestCase):
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
                "address": [config.IPS[5]], "netmask": [NETMASK],
                "gateway": ["0.0.0.0"]
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
class TestGatewaysCase06(TestCase):
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
                "nic": config.BOND[0], "slaves": [-2, -1], "required": False,
                "bootproto": "static", "address": [config.IPS[6]],
                "netmask": [NETMASK], "gateway": [GATEWAY]
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
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0],
                "slaves": [-3, -2, -1],
                "bootproto": "static",
                "address": [config.IPS[6]],
                "netmask": [NETMASK],
                "gateway": [GATEWAY],
                "required": "false",
            },
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise exceptions.NetworkException()

        logger.info("Checking IP rule after adding 3rd NIC")
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
class TestGatewaysCase07(TestCase):
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
                "nic": config.BOND[0], "slaves": [-2, -3, -1],
                "required": False, "bootproto": "static",
                "address": [config.IPS[7]], "netmask": [NETMASK],
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
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
        ):
            raise exceptions.NetworkException(
                "Incorrect gateway configuration for %s" % config.NETWORKS[0]
            )

        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0],
                "slaves": [-2, -1],
                "bootproto": "static",
                "address": [config.IPS[7]],
                "netmask": [NETMASK],
                "gateway": [GATEWAY],
                "required": "false",
            },
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise exceptions.NetworkException()

        logger.info("Checking the IP rule after removing one NIC from bond")
        if not ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
class TestGatewaysCase08(TestCase):
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
                "address": [config.IPS[8]], "netmask": [NETMASK]
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
        if ll_networks.check_ip_rule(
            vds_resource=config.VDS_HOSTS[0], subnet=SUBNET
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
