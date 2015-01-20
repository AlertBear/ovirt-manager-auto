"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import logging
from rhevmtests.networking import config
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup
)

logger = logging.getLogger("Bridgeless_Networks_Cases")


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class TestBridgelessCase1(TestCase):
    """
    Create and attach Non-VM network
    """
    __test__ = True

    def test_bridgeless_network(self):
        """
        Create and attach Non-VM network
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1,
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM network %s to DC/Cluster and Host",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0],
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
                host=config.VDS_HOSTS[0], data_center=config.DC_NAME[0],
                auto_nics=[0], network=[config.NETWORKS[0]],
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )


@attr(tier=1)
class TestBridgelessCase2(TestCase):
    """
    Create and attach Non-VM with VLAN network
    """
    __test__ = True

    def test_vlan_bridgeless_network(self):
        """
        Create and attach Non-VM with VLAN network
        """
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM VLAN network %s to DC/Cluster and Host",
            config.VLAN_NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1],
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], data_center=config.DC_NAME[0],
            auto_nics=[0], network=[config.VLAN_NETWORKS[0]],
        ):
            logger.error(
                "Cannot remove network %s from setup", config.VLAN_NETWORKS[0]
            )


@attr(tier=1)
class TestBridgelessCase3(TestCase):
    """
    Create and attach Non-VM network with VLAN over BOND
    """
    __test__ = True

    def test_bond_bridgeless_network(self):
        """
        Create and attach Non-VM network with VLAN over BOND
        """
        local_dict = {
            None: {
                "nic": config.BOND[0], "mode": 1,
                "slaves": [2, 3],
            },
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0],
                "vlan_id": config.VLAN_ID[0],
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM network with VLAN %s over BOND to "
            "DC/Cluster and Host", config.VLAN_NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0],
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], data_center=config.DC_NAME[0],
            auto_nics=[0], network=[config.VLAN_NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", config.VLAN_NETWORKS[0]
            )


@attr(tier=1)
class TestBridgelessCase4(TestCase):
    """
    Create and attach Non-VM network over BOND
    """
    __test__ = True

    def test_bond_bridgeless_network(self):
        """
        Create and attach bridgeless network over BOND
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": config.BOND[0], "mode": 1,
                "slaves": [2, 3],
                "required": "false",
                "usages": "",
            },
        }

        logger.info(
            "Create and attach Non-VM network %s over BOND to DC/Cluster and "
            "Host", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0],
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], data_center=config.DC_NAME[0],
            auto_nics=[0], network=[config.NETWORKS[0]],
        ):
            logger.error(
                "Cannot remove network %s from setup", config.NETWORKS[0]
            )
