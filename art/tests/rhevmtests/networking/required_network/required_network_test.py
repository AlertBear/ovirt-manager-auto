#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing RequiredNetwork network feature.
1 DC, 1 Cluster, 1 Hosts will be created for testing.
"""
import logging
from rhevmtests.networking import config
from art.unittest_lib import NetworkTest as TestCase, attr
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from art.rhevm_api.tests_lib.high_level.networks import (
    createAndAttachNetworkSN, validateNetwork, remove_all_networks
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    ifdownNic, waitForHostsStates, ifupNic, check_host_nic_status,
)
from art.rhevm_api.tests_lib.low_level.networks import (
    isNetworkRequired, updateClusterNetwork
)

logger = logging.getLogger("Required_Network_Cases")
HOST_NICS = None  # filled in setup module

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    """
    obtain host NICs
    """
    global HOST_NICS
    HOST_NICS = config.VDS_HOSTS[0].nics


class TearDownRequiredNetwork(TestCase):
    """
    Teardown class for RequiredNetwork job
    """
    @classmethod
    def teardown_class(cls):
        logger.info("Set all host interfaces up")
        for nic in HOST_NICS[1:]:
            if not check_host_nic_status(
                host=config.HOSTS[0], username=config.HOSTS_USER,
                password=config.HOSTS_PW, nic=nic, status="up"
            ):
                logger.info("Set %s up", nic)
                if not ifupNic(
                    host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
                    nic=nic, wait=False
                ):
                    logger.error("Failed to turn %s up", nic)

        logger.info("Set %s status to UP if not up", config.HOSTS[0])
        if not activate_host_if_not_up(config.HOSTS[0]):
            logger.error("Failed to activate %s", config.HOSTS[0])

        logger.info("Remove all networks from setup")
        if not (remove_all_networks(
            datacenter=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]) and createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0])
                ):
            logger.error("Cannot remove networks from setup")


@attr(tier=2)
class TestRequiredNetwork01(TearDownRequiredNetwork):
    """
    VM Network
    Check that MGMT network is required by default and try to set it to
    non required.
    """
    __test__ = True

    @polarion("RHEVM3-3753")
    def test_mgmt(self):
        """
        Check that MGMT network is required by default and try to set it to
        non required.
        """
        logger.info(
            "Checking that %s is required by default", config.MGMT_BRIDGE
        )
        if not isNetworkRequired(
            network=config.MGMT_BRIDGE, cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "%s is not required by default" % config.MGMT_BRIDGE
            )

        logger.info("Editing %s to be non-required", config.MGMT_BRIDGE)
        if updateClusterNetwork(
            positive=True, cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE, required="false"
        ):
            raise NetworkException(
                "%s is set to non required" % config.MGMT_BRIDGE
            )

##############################################################################


@attr(tier=2)
class TestRequiredNetwork02(TearDownRequiredNetwork):
    """
    VM Network
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
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "required": "false"
            }
        }
        logger.info(
            "Attach %s to DC/Cluster/Host(%s)", config.NETWORKS[0],
            HOST_NICS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3757")
    def test_1operational_network(self):
        """
        Validate that sw1 is operational.
        """
        logger.info("Check that %s status is operational", config.NETWORKS[0])
        if not validateNetwork(
            positive=True, cluster=config.CLUSTER_NAME[0],
            network=config.NETWORKS[0], tag="status", val="operational"
        ):
            raise NetworkException(
                "%s status is not operational" % config.NETWORKS[0]
            )

    @polarion("RHEVM3-3738")
    def test_2nonrequired(self):
        """
        Turn down eth1 and check that Host is OPERATIONAL
        """
        logger.info("Turn %s down", HOST_NICS[1])
        if not ifdownNic(
            host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
            nic=HOST_NICS[1]
        ):
            raise NetworkException(
                "Failed to turn down %s" % HOST_NICS[1]
            )

        logger.info("Check that %s is UP", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0], timeout=70
        ):
            raise NetworkException("%s status is not UP" % config.HOSTS[0])


##############################################################################


@attr(tier=2)
class TestRequiredNetwork03(TearDownRequiredNetwork):
    """
    VM Network
    Set sw1 as required, turn eth1 down and check that host status is
    non-operational
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw1 as required and turn eth1 down
        """
        local_dict = {config.NETWORKS[0]: {
            "nic": 1, "required": "true"}
        }

        logger.info(
            "Attach %s to DC/Cluster/Host(%s)", config.NETWORKS[0],
            HOST_NICS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.NETWORKS[0]
            )

        logger.info("Turn %s down", HOST_NICS[1])
        if not ifdownNic(
            host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
            nic=HOST_NICS[1]
        ):
            raise NetworkException("Failed to turn down %s" % HOST_NICS[1])

    @polarion("RHEVM3-3750")
    def test_operational(self):
        """
        Check that Host is non-operational
        """
        logger.info("Check that %s is non-operational", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0],
            states="non_operational", timeout=100
        ):
            raise NetworkException(
                "%s status is not non-operational" % config.HOSTS[0]
            )


##############################################################################


@attr(tier=2)
class TestRequiredNetwork04(TearDownRequiredNetwork):
    """
    VLAN over BOND
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
        logger.info(
            "Create and attach %s over %s(%s,%s)", config.VLAN_NETWORKS[0],
            config.BOND[0], HOST_NICS[2], HOST_NICS[3]
        )
        local_dict = {
            None: {"nic": config.BOND[0], "slaves": [2, 3]},
            config.VLAN_NETWORKS[0]: {
                "nic": config.BOND[0], "required": "true",
                "vlan_id": config.VLAN_ID[0]
            }
        }

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create and attach %s over %s" %
                (config.VLAN_NETWORKS[0], config.BOND[0])
            )

    @polarion("RHEVM3-3752")
    def test_1nonoperational_bond_down(self):
        """
        Check that host in non-operational after turn down both BOND slaves
        """
        for nic in HOST_NICS[2:4]:
            logger.info("Turn %s down", nic)
            if not ifdownNic(
                host=config.HOSTS_IP[0], root_password=config.HOSTS_PW, nic=nic
            ):
                raise NetworkException("Failed to turn down %s" % nic)

        logger.info("Check that %s is non-operational", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0],
            states="non_operational", timeout=300
        ):
            raise NetworkException(
                "%s status is not non-operational" % config.HOSTS[0]
            )

    @polarion("RHEVM3-3745")
    def test_2nonoperational_bond_down(self):
        """
        Check that host is operational after turn up one slave
        """
        logger.info("Turn %s ip", HOST_NICS[2])
        if not ifupNic(
            host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
            nic=HOST_NICS[2]
        ):
            raise NetworkException("Failed to turn up %s" % HOST_NICS[2])

        logger.info("Check that %s is operational", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0], timeout=300
        ):
            raise NetworkException(
                "%s status is not operational" % config.HOSTS[0]
            )


##############################################################################


@attr(tier=2)
class TestRequiredNetwork05(TearDownRequiredNetwork):
    """
    VLAN Network
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
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "true"
            }
        }
        logger.info(
            "Attach %s network to DC/Cluster/Host(%s)",
            config.VLAN_NETWORKS[0], HOST_NICS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create and attach network %s" % config.VLAN_NETWORKS[0]
            )

    @polarion("RHEVM3-3752")
    def test_nonoperational(self):
        """
        Check that host in non-operational after turn down eth1
        """
        logger.info("Turn %s down", HOST_NICS[1])
        if not ifdownNic(
            host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
            nic=HOST_NICS[1]
        ):
            raise NetworkException(
                "Failed to turn down %s" % HOST_NICS[1]
            )

        logger.info("Check that %s is non-operational", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0],
            states="non_operational", timeout=100
        ):
            raise NetworkException(
                "%s status is not non-operational" % config.HOSTS[0]
            )


##############################################################################


@attr(tier=2)
class TestRequiredNetwork06(TearDownRequiredNetwork):
    """
    Non-VM Network
    Add sw1 as required, attach it to the host.
    Check that host is non-operational after ifdown required network eth1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create sw1 network as non-required and attach it to the host.
        """
        local_dict = {
            config.NETWORKS[0]: {
                "nic": 1, "usages": "", "required": "true"
            }
        }
        logger.info(
            "Attach %s network to DC/Cluster/Host(%s)", config.NETWORKS[0],
            HOST_NICS[1]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0]
        ):
            raise NetworkException("Cannot create and attach networks")

    @polarion("RHEVM3-3744")
    def test_nonoperational(self):
        """
        Check that host in non-operational after turn down eth1
        """
        logger.info("Turn %s down", HOST_NICS[1])
        if not ifdownNic(
            host=config.HOSTS_IP[0], root_password=config.HOSTS_PW,
            nic=HOST_NICS[1]
        ):
            raise NetworkException(
                "Failed to turn down %s" % HOST_NICS[1]
            )

        logger.info("Check that %s is non-operational", config.HOSTS[0])
        if not waitForHostsStates(
            positive=True, names=config.HOSTS[0],
            states="non_operational", timeout=100
        ):
            raise NetworkException(
                "%s status is not non-operational" % config.HOSTS[0]
            )
