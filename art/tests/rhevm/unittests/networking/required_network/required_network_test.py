"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""
import logging
import config
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, validateNetwork, removeNetFromSetup
from art.rhevm_api.tests_lib.low_level.hosts import ifdownNic,\
    waitForHostsStates, ifupNic, waitForHostNicState, activateHost
from art.test_handler.tools import tcms
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.networks import isNetworkRequired, \
    updateClusterNetwork

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class RequiredNetwork01(TestCase):
    """
    VM-Network
    Check that mgmt network is required by default and try to set it to
    non required.
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        No need to run setup class
        """
        logger.info("No need to run setup class")

    @tcms(5868, 166462)
    def test_mgmt(self):
        """
        Check that mgmt network is required by default and try to set it to
        non required.
        """
        logger.info("Checking that mgmt network is required by default")
        if not isNetworkRequired(network=config.MGMT_BRIDGE,
                                 cluster=config.CLUSTER_NAME):
            raise NetworkException("mgmt network is not required by default")

        logger.info("Editing mgmt network to be non-required")
        if updateClusterNetwork(positive=True, cluster=config.CLUSTER_NAME,
                                network=config.MGMT_BRIDGE, required='false'):
            raise NetworkException("mgmt network is set to non required")

    @classmethod
    def teardown_class(cls):
        """
        No need to run teardown
        """
        logger.info("No need to run teardown")

##############################################################################


class RequiredNetwork02(TestCase):
    """
    VM-Network
    Add sw1 as non-required, attach it to the host and check that sw1 status is
    operational.
    Check that host is operational after ifdown non-required network eth1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw1 network as non-required and attach it to the host.
        """
        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                           "required": "false"}}
        logger.info("Attach sw1 network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

    @tcms(5868, 167539)
    def test_1operational_network(self):
        """
        Validate that sw1 is operational.
        """
        logger.info("Check that sw1 status is operational")
        if not validateNetwork(positive=True, cluster=config.CLUSTER_NAME,
                               network=config.NETWORKS[0], tag='status',
                               val='operational'):
            raise NetworkException("sw1 status is not operational")

    @tcms(5868, 165850)
    def test_2nonrequired(self):
        """
        Turn down eth1 and check that Host is OPERATIONAL
        """
        logger.info("Turn eth1 down")
        if not ifdownNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to turn down eth1")

        logger.info("Check that host is UP")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  timeout=70):
            raise NetworkException("Host status is not UP")

    @classmethod
    def teardown_class(cls):
        """
        Turn eth1 up and remove networks from setup
        """
        logger.info("Turn eth1 up")
        if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                       nic=config.HOST_NICS[1], wait=False):
            raise NetworkException("Failed to turn eth1 up")

        logger.info("Remove all networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Failed to remove sw1 from setup")

##############################################################################


class RequiredNetwork03(TestCase):
    """
    VM-Network
    Set sw1 as required, turn eth1 down and check that host status is
    non-operational
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw1 as required and turn eth1 down
        """
        local_dict = {config.NETWORKS[0]: {"nic": config.HOST_NICS[1],
                                           "required": "true"}}

        logger.info("Attach sw1 network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

        logger.info("Turn eth1 down")
        if not ifdownNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to turn down eth1")

    @tcms(5868, 165851)
    def test_operational(self):
        """
        Check that Host is non-operational
        """
        logger.info("Check that host is non-operational")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  states="non_operational", timeout=100):
            raise NetworkException("Host status is not non-operational")

    @classmethod
    def teardown_class(cls):
        """
        Turn on eth1, set host status to up and remove sw1 from setup
        """
        logger.info("Turn eth1 up")
        if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                       nic=config.HOST_NICS[1], wait=False):
            raise NetworkException("Failed to turn eth1 up")

        logger.info("Set host status to UP")
        if not activateHost(positive=True, host=config.HOSTS[0]):
            raise NetworkException("Failed to set host status to UP")

        logger.info("Remove all networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Failed to remove networks from setup")

##############################################################################


class RequiredNetwork04(TestCase):
    """
    VLAN-OVER-BOND
    Add sw162 as required, attach it to the host and check that sw162 status is
    operational.
    Check that host is non-operational after ifdown required networks eth2
    and eth3
    """
    __test__ = len(config.HOST_NICS) >= 4

    @classmethod
    def setup_class(cls):
        """
        Create sw162 network as required and attach it to the host bond.
        """
        local_dict = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {'nic': config.BOND[0],
                                                'vlan_id': config.VLAN_ID[0],
                                                'required': 'true'}}
        logger.info("Attach sw162 network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

    @tcms(5868, 166460)
    def test_1operational_nic_down(self):
        """
        Check that host in operational after turn down eth2
        """
        logger.info("Turn eth2")
        if not ifdownNic(host=config.HOSTS[0],
                         root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[2]):
            raise NetworkException("Failed to turn down eth2")

        logger.info("Check that host is up")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  timeout=70):
            raise NetworkException("Host status is not UP")

    def test_2nonoperational_bond_down(self):
        """
        Check that host in non-operational after turn down eth3
        """
        logger.info("Turn eth3 down")
        if not ifdownNic(host=config.HOSTS[0],
                         root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[3]):
            raise NetworkException("Failed to turn down eth3")

        logger.info("Check that host is non-operational")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  states="non_operational", timeout=100):
            raise NetworkException("Host status is not non-operational")

    @classmethod
    def teardown_class(cls):
        """
        Turn eth2 and eth3 up and remove networks from setup
        """
        logger.info("Turn eth2 and eth3 status to be up")
        for i in range(2, 4):
            if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                           nic=config.HOST_NICS[i], wait=False):
                raise NetworkException("Failed to turn up eth2 %s",
                                       config.HOST_NICS[i])

        logger.info("Set host status to UP")
        if not activateHost(positive=True, host=config.HOSTS[0]):
            raise NetworkException("Failed to activate host")

        logger.info("Remove all networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Failed to remove networks from setup")

##############################################################################


class RequiredNetwork05(TestCase):
    """
    VLAN-Network
    Add sw162 as required, attach it to the host and check that sw1 status is
    operational.
    Check that host is non-operational after ifdown required network eth1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw162 network as required and attach it to the host.
        """
        local_dict = {config.VLAN_NETWORKS[0]: {'vlan_id': config.VLAN_ID[0],
                                                'nic': config.HOST_NICS[1],
                                                'required': 'true'}}
        logger.info("Attach sw162 network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create and attach networks")

    @tcms(5868, 166460)
    def test_nonoperational(self):
        """
        Check that host in non-operational after turn down eth1
        """
        logger.info("Turn eth1 down")
        if not ifdownNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to turn down eth1")

        logger.info("Check that host is non-operational")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  states="non_operational", timeout=100):
            raise NetworkException("Host status is not non-operational")

    @classmethod
    def teardown_class(cls):
        """
        Turn eth1 up and remove networks from setup
        """
        logger.info("Turn up eth1")
        if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                       nic=config.HOST_NICS[1], wait=False):
            raise NetworkException("Failed to turn up eth1")

        logger.info("Set host status to UP")
        if not activateHost(positive=True, host=config.HOSTS[0]):
            raise NetworkException("Failed to activate host")

        logger.info("Remove all networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.VLAN_NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Failed to remove networks from setup")

##############################################################################


class RequiredNetwork06(TestCase):
    """
    Non-VM-Network
    Add sw1 as required, attach it to the host.
    Check that host is non-operational after ifdown required network eth1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw1 network as non-required and attach it to the host.
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'usages': "",
                                           'required': 'true'}}
        logger.info("Attach sw1 network to DC/Cluster/Host")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME,
                                        cluster=config.CLUSTER_NAME,
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach networks")

    @tcms(5868, 217612)
    def test_nonoperational(self):
        """
        Check that host in non-operational after turn down eth1
        """
        logger.info("Turn eth1 down")
        if not ifdownNic(host=config.HOSTS[0],
                         root_password=config.HOSTS_PW,
                         nic=config.HOST_NICS[1]):
            raise NetworkException("Failed to turn down eth1")

        logger.info("Check that host is non-operational")
        if not waitForHostsStates(positive=True, names=config.HOSTS[0],
                                  states="non_operational", timeout=100):
            raise NetworkException("Host status is not non-operational")

    @classmethod
    def teardown_class(cls):
        """
        Turn eth1 up and remove networks from setup
        """
        logger.info("Turn up eth1")
        if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                       nic=config.HOST_NICS[1], wait=False):
            raise NetworkException("Failed to turn up eth1")

        logger.info("Set host status to UP")
        if not activateHost(positive=True, host=config.HOSTS[0]):
            raise NetworkException("Failed to activate host")

        logger.info("Remove all networks from setup")
        if not removeNetFromSetup(host=config.HOSTS[0],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=[config.NETWORKS[0]],
                                  data_center=config.DC_NAME):
            raise NetworkException("Failed to remove networks from setup")

##############################################################################
