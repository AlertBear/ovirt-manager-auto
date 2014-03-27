"""
Testing bridgeless (Non-VM) Network feature.
1 DC, 1 Cluster, 1 Host will be created for testing.
Bridgeless (Non-VM) Network will be tested for untagged, tagged,
bond scenarios.
"""

from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
import logging
import config

from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import\
    createAndAttachNetworkSN, removeNetFromSetup

logger = logging.getLogger(__name__)


########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


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
        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                           "required": "false",
                                           "usages": ""}}

        logger.info("Create and attach Non-VM network to DC/Cluster "
                    "and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove network from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  data_center=config.DC_NAME,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


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
        local_dict = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                "nic": config.HOST_NICS[1],
                                                "required": "false",
                                                "usages": ""}}

        logger.info("Create and attach Non-VM VLAN network to DC/Cluster"
                    "and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  data_center=config.DC_NAME,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


class BridgelessCase3(TestCase):
    """
    Create and attach Non-VM network with VLAN over BOND
    """
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
        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "vlan_id": config.VLAN_ID[0],
                                                "required": "false",
                                                "usages": ""}}

        logger.info("Create and attach Non-VM network with VLAN "
                    "over BOND to DC/Cluster and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  data_center=config.DC_NAME,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")


class BridgelessCase4(TestCase):
    """
    Create and attach Non-VM network over BOND
    """
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
        local_dict = {config.NETWORKS[0]: {"nic": config.BOND[0], "mode": 1,
                                           "slaves": [config.HOST_NICS[2],
                                                      config.HOST_NICS[3]],
                                           "required": "false",
                                           "usages": ""}}

        logger.info("Create and attach Non-VM network "
                    "over BOND to DC/Cluster and Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Remove network from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  data_center=config.DC_NAME,
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]]):
            raise NetworkException("Cannot remove network from setup")
