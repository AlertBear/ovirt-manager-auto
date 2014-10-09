"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from rhevmtests.networking import config
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup

logger = logging.getLogger(__name__)


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class BridgelessCase1(TestCase):
    """
    Create and attach Non-VM network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup class
        """

    @istest
    def bridgeless_network(self):
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.VDS_HOSTS[0].nics[1],
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM network to DC/Cluster and Host"
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            host=config.HOSTS[0],
            network_dict=local_dict,
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
        ):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(
                host=config.HOSTS[0],
                data_center=config.DC_NAME[0],
                auto_nics=[config.VDS_HOSTS[0].nics[0]],
                network=[config.NETWORKS[0]],
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class BridgelessCase2(TestCase):
    """
    Create and attach Non-VM with VLAN network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup class
        """

    @istest
    def vlan_bridgeless_network(self):
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": config.VDS_HOSTS[0].nics[1],
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM VLAN network to DC/Cluster and Host"
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict,
            auto_nics=[
                config.VDS_HOSTS[0].nics[0],
                config.VDS_HOSTS[0].nics[1],
            ],
        ):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(
            host=config.HOSTS[0],
            data_center=config.DC_NAME[0],
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
            network=[config.VLAN_NETWORKS[0]],
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class BridgelessCase3(TestCase):
    """
    Create and attach Non-VM network with VLAN over BOND
    """
    # FIXME: try to move to __init__, otherwise move to setup_module
    __test__ = len(config.HOST_NICS) >= 4

    @classmethod
    def setup_class(cls):
        """
        No need to run setup class
        """

    @istest
    def bond_bridgeless_network(self):
        """
        Create and attach Non-VM network with VLAN over BOND
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": 1,
                "slaves": [
                    config.VDS_HOSTS[0].nics[2],
                    config.VDS_HOSTS[0].nics[3],
                ],
            },
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "vlan_id": config.VLAN_ID[0],
                "required": "false",
                "usages": "",
            },
        }

        logger.info("Create and attach Non-VM network with VLAN "
                    "over BOND to DC/Cluster and Host")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            host=config.HOSTS[0],
            network_dict=local_dict,
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
        ):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(
            host=config.HOSTS[0],
            data_center=config.DC_NAME[0],
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
            network=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class BridgelessCase4(TestCase):
    """
    Create and attach Non-VM network over BOND
    """
    # FIXME: try to move to __init__, otherwise move to setup_module
    __test__ = len(config.HOST_NICS) >= 4

    @classmethod
    def setup_class(cls):
        """
        No need to run setup class
        """

    @istest
    def bond_bridgeless_network(self):
        """
        Create and attach bridgeless network over BOND
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "mode": 1,
                "slaves": [
                    config.VDS_HOSTS[0].nics[2],
                    config.VDS_HOSTS[0].nics[3],
                ],
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM network over BOND to DC/Cluster and Host"
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            host=config.HOSTS[0],
            network_dict=local_dict,
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
        ):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(
            host=config.HOSTS[0],
            data_center=config.DC_NAME[0],
            auto_nics=[config.VDS_HOSTS[0].nics[0]],
            network=[config.NETWORKS[0]],
        ):
            raise NetworkException("Cannot remove network from setup")
