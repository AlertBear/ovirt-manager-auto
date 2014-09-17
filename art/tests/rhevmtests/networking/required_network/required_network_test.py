"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""
import logging
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from rhevmtests.networking import config
from art.unittest_lib import NetworkTest as TestCase, attr
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN,
    validateNetwork,
    remove_all_networks)
from art.rhevm_api.tests_lib.low_level.hosts import (
    ifdownNic,
    waitForHostsStates,
    ifupNic, getHostNicAttr)
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.networks import isNetworkRequired, \
    updateClusterNetwork

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class TearDownRequiredNetwork(TestCase):
    """
    Teardown class for RequiredNetwork job
    """
    @classmethod
    def teardown_class(cls):
        logger.info("Set all host interfaces up")
        for nic in config.HOST_NICS[1:]:
            host_nic_stat = getHostNicAttr(config.HOSTS[0], nic,
                                           'status.state')
            if host_nic_stat[1]["attrValue"] == "up":
                continue
            logger.info("Set %s up", nic)
            if not ifupNic(host=config.HOSTS[0], root_password=config.HOSTS_PW,
                           nic=nic, wait=False):
                raise NetworkException("Failed to turn %s up" % nic)

        logger.info("Set host status to UP if not up")
        if not activate_host_if_not_up(config.HOSTS[0]):
            raise NetworkException("Failed to activate the host")

        logger.info("Remove all networks from setup")
        if not (remove_all_networks(datacenter=config.DC_NAME[0],
                                    mgmt_network=config.MGMT_BRIDGE,
                                    cluster=config.CLUSTER_NAME[0]) and
                createAndAttachNetworkSN(host=config.HOSTS[0],
                                         network_dict={},
                                         auto_nics=[config.HOST_NICS[0]])):

            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class RequiredNetwork01(TearDownRequiredNetwork):
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
                                 cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("mgmt network is not required by default")

        logger.info("Editing mgmt network to be non-required")
        if updateClusterNetwork(positive=True, cluster=config.CLUSTER_NAME[0],
                                network=config.MGMT_BRIDGE, required='false'):
            raise NetworkException("mgmt network is set to non required")

    @classmethod
    def teardown_class(cls):
        """
        No need to run teardown
        """
        logger.info("No need to run teardown")

##############################################################################


@attr(tier=1)
class RequiredNetwork02(TearDownRequiredNetwork):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
        if not validateNetwork(positive=True, cluster=config.CLUSTER_NAME[0],
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


##############################################################################


@attr(tier=1)
class RequiredNetwork03(TearDownRequiredNetwork):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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


##############################################################################


@attr(tier=1)
class RequiredNetwork04(TearDownRequiredNetwork):
    """
    VLAN-OVER-BOND
    Add sw162 as required, attach it to the host and check that sw162 status is
    operational.
    Check that host is non-operational after ifdown required networks eth2
    and eth3
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw162 network as required and attach it to the host bond.
        """
        logger.info("Create and attach network over BOND")
        local_dict = {None: {"nic": config.BOND[0],
                             "slaves": [
                                 config.HOST_NICS[2],
                                 config.HOST_NICS[3]]},
                      config.VLAN_NETWORKS[0]: {"nic": config.BOND[0],
                                                "required": "true",
                                                "vlan_id": config.VLAN_ID[0]}}

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create and attach network")

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


##############################################################################


@attr(tier=1)
class RequiredNetwork05(TearDownRequiredNetwork):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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


##############################################################################


@attr(tier=1)
class RequiredNetwork06(TearDownRequiredNetwork):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
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
