
"""
Testing Network labels feature.
1 DC, 2 Cluster, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""
from art.rhevm_api.tests_lib.high_level.hosts import deactivate_host_if_up
from art.test_handler.plmanagement.plugins.bz_plugin import bz
from art.unittest_lib import attr
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.clusters import(
    addCluster, removeCluster
)
from art.rhevm_api.tests_lib.low_level.datacenters import(
    addDataCenter, removeDataCenter
)
from art.rhevm_api.tests_lib.low_level.hosts import(
    sendSNRequest, activateHost, updateHost, deactivateHost, getHostNic
)
from art.unittest_lib.network import vlan_int_name

from rhevmtests.networking import config
import logging

from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611

from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.networks import(
    add_label, check_network_on_nic, remove_label, get_label_objects,
    getClusterNetwork, removeNetworkFromCluster, addNetworkToCluster,
    removeNetwork, findNetwork
)

logger = logging.getLogger("Network_Labels_Cases")

HOST0_NICS = None  # filled in setup module
HOST1_NICS = None  # filled in setup module
VLAN_NIC = ""  # filled in setup module
VLAN_BOND = ""  # filled in setup module


#

#
# Test Cases                               #
#


def setup_module():
    """
    obtain host NICs for the first Network Host
    """
    global HOST0_NICS, HOST1_NICS, VLAN_NIC, VLAN_BOND
    HOST0_NICS = config.VDS_HOSTS[0].nics
    HOST1_NICS = config.VDS_HOSTS[1].nics
    VLAN_NIC = vlan_int_name(HOST0_NICS[1], config.VLAN_ID[0])
    VLAN_BOND = vlan_int_name(config.BOND[0], config.VLAN_ID[0])


class TestLabelTestCaseBase(TestCase):

    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not remove_label(
            host_nic_dict={config.HOSTS[0]: HOST0_NICS,
                           config.HOSTS[1]: HOST1_NICS}
        ):
            logger.error("Couldn't remove labels from Hosts ")

        if not remove_net_from_setup(
            host=config.VDS_HOSTS[:2], auto_nics=[0],
            data_center=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            all_net=True
        ):
            logger.error("Cannot remove networks from setup")


@attr(tier=1)
class NetLabels01(TestLabelTestCaseBase):

    """
    Check network label limitation:

    1) Negative case: Try to create a label which does not comply with the
    pattern: numbers, digits, dash or underscore [0-9a-zA-Z_-].
    2) Positive case: Create label with length of 50 chars
    3) Negative case: Try to assign more than one label to network
    4) Positive case: Assign many labels to interface (10)

    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a network and attach it to DC and Cluster
        """
        local_dict = {config.NETWORKS[0]: {"required": "false"}}

        logger.info(
            "Create and attach network %s  to DC and Cluster ",
            config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException("Cannot create network on DC and Cluster")

    @tcms(12040, 332263)
    def test_label_restrictioin(self):
        """
        1) Negative case Try to attach label with incorrect format to the
        network
        2) Attach label with 50 characters to a network
        3) Negative case: Try to assign additional label to the network with
        attached label
        4) Attach 20 labels to the interface on the Host when one of those
        networks is attached to the network and check that the network is
        attached to the Host interface
        """

        special_char_labels = ["asd?f", "dfg/gd"]
        long_label = "a" * 50
        logger.info(
            "Negative case: Try to attach label %s and %s  with incorrect "
            "format to the network %s and fail",
            special_char_labels[0], special_char_labels[1], config.NETWORKS[0]
        )
        for label in special_char_labels:
            if add_label(label=label, networks=[config.NETWORKS[0]]):
                raise NetworkException(
                    "Could add label %s with incorrect format to the network "
                    "%s but shouldn't" % (label, config.NETWORKS[0])
                )

        logger.info(
            "Attach label with 50 characters length to the network %s ",
            config.NETWORKS[0]
        )
        if not add_label(label=long_label, networks=[config.NETWORKS[0]]):
            raise NetworkException(
                "Couldn't add label with 50 characters length to the network "
                "%s but should" % config.NETWORKS[0]
            )

        logger.info(
            "Negative case: Try to attach additional label %s to the network "
            "%s with already attached label and fail",
            config.LABEL_LIST[0], config.NETWORKS[0]
        )

        if add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Could add additional labelto the network %s but shouldn't" %
                config.NETWORKS[0]
            )

        logger.info("Attach 10 labels to the Host NIC %s", HOST0_NICS[1])
        for label in config.LABEL_LIST:
            if not add_label(
                label=label, host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
            ):
                raise NetworkException(
                    "Couldn't add label %s to the Host NIC %s but should" %
                    (label, HOST0_NICS[1])
                )


@attr(tier=1)
class NetLabels02(TestLabelTestCaseBase):

    """
    Check that the label cannot be attached to the Bond when it is used by
    another Host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create bond from 2 phy interfaces
        2) Create VLAN network on DC/Cluster
        3) Create and attach label to the network
        4) Attach label to Host Nic - eth1
        5) Check that the network is attached to the interface (eth1)
        """
        logger.info(
            "Create bond %s on host %s", config.BOND[0], config.HOSTS[0]
        )
        local_dict1 = {None: {
            "nic": config.BOND[0], "slaves": [2, 3], "required": "false"
        }}
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create bond %s on the Host %s" %
                (config.BOND[0], config.HOSTS[0])
            )

        logger.info(
            "Create VLAN network %s on DC and Cluster", config.VLAN_NETWORKS[
                0]
        )
        local_dict2 = {config.VLAN_NETWORKS[0]: {
            "vlan_id": config.VLAN_ID[0], "required": "false"
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict2
        ):
            raise NetworkException(
                "Cannot create VLAN network %s on DC and Cluster" %
                config.VLAN_NETWORKS[0]
            )

        logger.info(
            "Attach label %s to VLAN network %s and to the Host NIC %s",
            config.LABEL_LIST[0], config.VLAN_NETWORKS[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]},
            networks=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to VLAN network %s or to Host NIC %s"
                % (config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
                   HOST0_NICS[1])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            config.VLAN_NETWORKS[0], VLAN_NIC
        )
        if not check_network_on_nic(
            config.VLAN_NETWORKS[0], config.HOSTS[0], VLAN_NIC
        ):
            raise NetworkException(
                "Network %s is not attached to Host NIC %s " %
                (config.VLAN_NETWORKS[0], HOST0_NICS[1])
            )

    @tcms(12040, 333128)
    def test_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface (eth1)
        3) Attach label to the bond and succeed
        """
        logger.info(
            "Negative case: Try to attach label to the bond when that label "
            "is already attached to the interface %s ", HOST0_NICS[1]
        )
        if add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}
        ):
            raise NetworkException(
                "Could attach label to Host NIC bond when shouldn't"
            )

        logger.info(
            "Remove label from the host NIC %s and then try to attach label "
            "to the Bond interface"
        )
        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]},
            labels=[config.LABEL_LIST[0]]
        ):
            raise NetworkException(
                "Couldn't remove label %s from Host NIC %s" %
                (config.LABEL_LIST[0], HOST0_NICS[1])
            )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}
        ):
            raise NetworkException(
                "Couldn't attach label to Host bond %s when should" %
                config.BOND[0]
            )

        logger.info(
            "Check that the network %s is attached to the bond on Host %s",
            config.VLAN_NETWORKS[0], config.HOSTS[0]
        )
        if not check_network_on_nic(
            config.VLAN_NETWORKS[0], config.HOSTS[0], VLAN_BOND
        ):
            raise NetworkException(
                "Network %s is not attached to Bond %s " %
                (config.VLAN_NETWORKS[0], config.BOND[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels02, cls).teardown_class()


@attr(tier=1)
class NetLabels03(TestLabelTestCaseBase):

    """
    1) Put label on Host NIC of one Host
    2) Put label on bond of the second Host
    3) Put label on the network
    4) Check network is attached to both Hosts (appropriate interfaces)
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a network and attach it to DC and Cluster
        Create Bond on the second Host
        """

        local_dict = {config.NETWORKS[0]: {"required": "false"}}

        logger.info(
            "Create and attach network %s to DC and Cluster ",
            config.NETWORKS[0]
        )

        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s on DC and Cluster" %
                config.NETWORKS[0]
            )

        local_dict1 = {None: {
            "nic": config.BOND[0], "slaves": [2, 3], "required": "false"
        }}

        logger.info("Create Bond %s on the second Host", config.BOND[0])
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[1], network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create bond %s on the Host %s" %
                (config.BOND[0], config.HOSTS[1])
            )

    @tcms(12040, 332261)
    def test_label_several_interfaces(self):
        """
        1) Put label on Host NIC of one Host
        2) Put the same label on bond of the second Host
        3) Put label on the network
        4) Check network is attached to both Host (appropriate interfaces)
        """
        logger.info(
            "Attach label %s to Host NIC %s on the Host %s to the Bond %s on "
            "Host %s and to the network %s",
            config.LABEL_LIST[0], HOST0_NICS[1], config.HOSTS[0],
            config.BOND[0], config.HOSTS[1], config.NETWORKS[0]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[1]: [config.BOND[0]],
                           config.HOSTS[0]: [HOST0_NICS[1]]},
            networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s " % config.LABEL_LIST[0]
            )

        logger.info(
            "Check network %s is attached to interface %s on Host %s and to "
            "Bond %s on Host %s", config.NETWORKS[0],
            HOST0_NICS[1], config.HOSTS[0], config.BOND[0], config.HOSTS[1]
        )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s is not attached to NIC %s " %
                (config.NETWORKS[0], HOST0_NICS[1])
            )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[1], config.BOND[0]
        ):
            raise NetworkException(
                "Network %s is not attached to Bond %s " %
                (config.NETWORKS[0], config.BOND[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(
            host_nic_dict={config.HOSTS[1]: [config.BOND[0]]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels03, cls).teardown_class()


@attr(tier=1)
class NetLabels04(TestLabelTestCaseBase):

    """
    1) Create bridgeless network on DC/Cluster
    2) Create VLAN network on DC/Cluster
    3) Put the same label on both networks
    4) Put network label on Host NIC of one Host
    5) Put network label on bond of the second Host
    6) Check that both networks are attached to both Hosts interface and
    Bond appropriately
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create bridgeless network on DC/Cluster
        2) Create VLAN network on DC/Cluster
        3) Create Bond on the second Host
        4) Put the same label on both networks
        """
        local_dict = {config.NETWORKS[0]: {
            "usages": "", "required": "false"},
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0], "required": "false"
        }
        }

        logger.info(
            "Create and attach networks %s and %s to DC and Cluster ",
            config.NETWORKS[0], config.VLAN_NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create networks %s and %s on DC and Cluster" %
                (config.NETWORKS[0], config.VLAN_NETWORKS[0])
            )

        local_dict1 = {None: {"nic": config.BOND[0], "slaves": [2, 3]}}

        logger.info(
            "Create Bond %s on the Host %s ", config.BOND[0], config.HOSTS[1]
        )
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[1], network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException(
                "Cannot create bond on the Host %s" % config.HOSTS[1]
            )

        logger.info(
            "Attach label %s to networks %s and %s", config.LABEL_LIST[0],
            config.NETWORKS[0], config.VLAN_NETWORKS[0]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0],
                                                  config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to networks %s and %s" %
                (config.LABEL_LIST[0], config.NETWORKS[0],
                 config.VLAN_NETWORKS[0])
            )

    @tcms(12040, 332262)
    def test_label_several_networks(self):
        """
        1) Put label on Host NIC of one Host
        2) Put label on bond of the second Host
        4) Check that both networks are attached to both Host (appropriate
        interfaces)
        """
        logger.info(
            "Attach label %s to Host NIC %s and Bond %s on both Hosts "
            "appropriately", config.LABEL_LIST[0], HOST0_NICS[1],
            config.BOND[0]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[1]: [config.BOND[0]],
                           config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
                raise NetworkException(
                    "Couldn't attach label %s to interfaces" %
                    config.LABEL_LIST[0]
                )

        logger.info(
            "Check that network %s and %s are attached to interface %s on Host"
            " %s and to Bond on Host %s", config.NETWORKS[0],
            config.VLAN_NETWORKS[0], HOST0_NICS[1], config.HOSTS[0],
            config.HOSTS[1]
        )
        if not (
                check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[0], VLAN_NIC) and
                check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[1], VLAN_BOND)
        ):
            raise NetworkException(
                "VLAN Network %s is not attached to NIC %s or Bond %s " %
                (config.VLAN_NETWORKS[0], HOST0_NICS[1], config.BOND[0])
            )

        if not (
                check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                     HOST0_NICS[1]) and
                check_network_on_nic(config.NETWORKS[0], config.HOSTS[1],
                                     config.BOND[0])
        ):
            raise NetworkException(
                "Network %s is not attached to NIC %s or Bond %s " %
                (config.NETWORKS[0], HOST0_NICS[1], config.BOND[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[1]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels04, cls).teardown_class()


@attr(tier=1)
class NetLabels05(TestLabelTestCaseBase):

    """
    Check that you can remove network from Host NIC on 2 Hosts by un-labeling
    that Network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create VLAN network on DC/Cluster
        2) Attach label to the VLAN network
        3) Attach label to Host Nic eth1 on both Hosts
        4) Check that network is attached to Host
        """
        local_dict1 = {config.VLAN_NETWORKS[0]: {
            "vlan_id": config.VLAN_ID[0], "required": "false"
        }}
        logger.info(
            "Create VLAN network %s on DC and Cluster", config.VLAN_NETWORKS[
                0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException(
                "Cannot create VLAN network %s on DC and Cluster" %
                config.VLAN_NETWORKS[0]
            )

        logger.info(
            "Attach label %s to VLAN network %s on interfaces %s and %s of "
            "both Hosts appropriately", config.LABEL_LIST[0],
            config.VLAN_NETWORKS[0], HOST0_NICS[1], HOST1_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]],
                           config.HOSTS[1]: [HOST1_NICS[1]]},
            networks=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to VLAN network %s or to Host NIC %s"
                " and %s on both Hosts appropriately" % (
                    config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
                    HOST0_NICS[1], HOST1_NICS[1]
                )
            )

        for host in config.HOSTS[:2]:
            logger.info(
                "Check that the network %s is attached to Host %s before "
                "un-labeling ", config.VLAN_NETWORKS[0], host
            )
            if not check_network_on_nic(
                config.VLAN_NETWORKS[0], host, VLAN_NIC
            ):
                raise NetworkException(
                    "Network %s is not attached to the first NIC on host %s" %
                    (config.VLAN_NETWORKS[0], host)
                )

    @tcms(12040, 332815)
    def test_unlabel_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from eth1 on both Hosts
        """
        logger.info(
            "Remove label %s from the network %s attached to %s and %s on "
            "both Hosts appropriately", config.LABEL_LIST[0],
            config.VLAN_NETWORKS[0], HOST0_NICS[1], HOST1_NICS[1]
        )
        if not remove_label(
            networks=[config.VLAN_NETWORKS[0]], labels=[config.LABEL_LIST[0]]
        ):
            raise NetworkException(
                "Couldn't remove label %s from network %s " %
                (config.LABEL_LIST[0], config.VLAN_NETWORKS[0])
            )

        for host in config.HOSTS[:2]:
            logger.info(
                "Check that the network %s is not attached to Host %s",
                config.VLAN_NETWORKS[0], host
            )
            sample = TimeoutingSampler(
                timeout=config.SAMPLER_TIMEOUT, sleep=1,
                func=check_network_on_nic, network=config.VLAN_NETWORKS[0],
                host=host, nic=VLAN_NIC
            )

            if not sample.waitForFuncStatus(result=False):
                raise NetworkException(
                    "Network %s is attached to first NIC on host %s but "
                    "shouldn't " % (config.VLAN_NETWORKS[0], host)
                )


@attr(tier=1)
class NetLabels06(TestLabelTestCaseBase):

    """
    Check that you can break bond which has network attached to it by
    Un-Labeling
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create vm network on DC/Cluster
        2) Create bond from eth2 and eth3 on 2 Hosts
        3) Create and attach label to the network
        4) Attach label to Bond on both Hosts
        5) Make sure the network was attached to Bond on both Hosts
        """

        local_dict1 = {None: {"nic": config.BOND[0], "slaves": [2, 3]}}

        logger.info("Create bond on both Hosts in the setup")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict1, auto_nics=[0]
        ):
            raise NetworkException("Cannot create bond on both Hosts")

        local_dict2 = {config.NETWORKS[0]: {"required": "false"}}
        logger.info(
            "Create regular network %s on DC and Cluster", config.NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict2
        ):
            raise NetworkException(
                "Cannot create network %s on DC and Cluster" %
                config.NETWORKS[0]
            )

        logger.info(
            "Attach label %s to network %s on Bonds %s of both Hosts",
            config.LABEL_LIST[0], config.NETWORKS[0], config.BOND[0]
        )

        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [config.BOND[0]],
                           config.HOSTS[1]: [config.BOND[0]]},
            networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s or to Host Bond %s on"
                " both Hosts" % (
                    config.LABEL_LIST[0], config.NETWORKS[0], config.BOND[0]
                )
            )

        logger.info(
            "Check network %s is attached to Bond on both Hosts",
            config.NETWORKS[0]
        )
        for host in config.HOSTS[:2]:
            logger.info(
                "Check that the network %s is attached to Hosts %s bond ",
                config.NETWORKS[0], host
            )
            if not check_network_on_nic(
                config.NETWORKS[0], host, config.BOND[0]
            ):
                raise NetworkException(
                    "Network %s was not attached to Bond %s on host %s " %
                    (config.NETWORKS[0], config.BOND[0], host)
                )

    @tcms(12040, 332898)
    def test_break_labeled_bond(self):
        """
        1) Break Bond on both Hosts
        2) Make sure the network was detached from Bond on both Hosts
        3) Make sure that the bond slave interfaces don't have label
        configured
        """

        logger.info("Break bond on both Hosts")
        for i, host_i in enumerate(config.HOSTS[:2]):
            if not sendSNRequest(
                True, host=host_i, auto_nics=[config.VDS_HOSTS[i].nics[0]],
                check_connectivity="true", connectivity_timeout=60,
                force="false"
            ):
                raise NetworkException(
                    "Couldn't break bond on Host %s" % host_i
                )

        for host in config.HOSTS[:2]:
            logger.info(
                "Check that the network %s is not attached to Hosts %s bond ",
                config.NETWORKS[0], host
            )
            if check_network_on_nic(config.NETWORKS[0], host, config.BOND[0]):
                raise NetworkException(
                    "Network %s is attached to Bond %s on host %s when "
                    "shouldn't" % (config.NETWORKS[0], config.BOND[0], host)
                )

        logger.info(
            "Check that the label %s doesn't appear on slaves of both Hosts"
        )
        if get_label_objects(host_nic_dict={
            config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]],
            config.HOSTS[1]: [HOST1_NICS[2], HOST1_NICS[3]]
        }):
            raise NetworkException("Label exists on Bond slaves")


@attr(tier=1)
class NetLabels07(TestLabelTestCaseBase):

    """
    1) Negative case: Try to remove labeled network NET1 from labeled
    interface on the first NIC by setupNetworks
    2) Remove label from interface and make sure the network is detached
    from it
    3) Attach another network to the same interface with setupNetworks
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create bridgeless VLAN network on DC/Cluster
        2) Create and attach label to the VLAN non-VM network
        3) Attach the same label to Host Nic eth1 on one Host
        4) Check that the network is attached to the Host NIC
        """

        local_dict1 = {config.VLAN_NETWORKS[0]: {
            "vlan_id": config.VLAN_ID[0], "required": "false", "usages": ""
        }}

        logger.info(
            "Create VLAN  non-VM network %s on DC and Cluster",
            config.VLAN_NETWORKS[0]
        )
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException(
                "Cannot create VLAN network %s on DC and Cluster" %
                config.VLAN_NETWORKS[0]
            )

        logger.info(
            "Attach label %s to non-VM VLAN network %s and NIC %s ",
            config.LABEL_LIST[0], config.VLAN_NETWORKS[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]},
            networks=[config.VLAN_NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to non-VM VLAN network %s or to "
                "Host NIC %s " % (config.LABEL_LIST[0],
                                  config.VLAN_NETWORKS[0], config.BOND[0])
            )

        logger.info(
            "Check that the network %s is attached to Host %s",
            config.VLAN_NETWORKS[0], config.HOSTS[0]
        )

        if not check_network_on_nic(
            config.VLAN_NETWORKS[0], config.HOSTS[0], VLAN_NIC
        ):
            raise NetworkException(
                "Network %s was not attached to interface %s on host %s " %
                (config.VLAN_NETWORKS[0], HOST0_NICS[1], config.HOSTS[0])
            )

    @tcms(12040, 332578)
    def test_remove_label_host_NIC(self):
        """
       1) Negative case: Try to remove labeled network NET1 from labeled
       interface eth1 with setupNetworks
       2) Remove label from interface and make sure the network is detached
       from it
       3) Attach another network to the same interface with setupNetworks
       """

        logger.info(
            "Try to remove labeled network %s from Host NIC %s with "
            "setupNetwork command ", config.VLAN_NETWORKS[0], HOST0_NICS[1]
        )
        if not sendSNRequest(
            False, host=config.HOSTS[0],
            auto_nics=[config.VDS_HOSTS[0].nics[
                0]], check_connectivity="true",
            connectivity_timeout=60, force="false"
        ):
            raise NetworkException(
                "Could remove labeled network %s from Host NIC % s" %
                (config.VLAN_NETWORKS[0], HOST0_NICS[1])
            )

        logger.info(
            "Remove label %s from Host NIC %s", config.LABEL_LIST[0],
            HOST0_NICS[1]
        )
        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]},
            labels=[config.LABEL_LIST[0]]
        ):
            raise NetworkException(
                "Couldn't remove label %s from Host NIC %s" %
                (config.LABEL_LIST[0], HOST0_NICS[1])
            )

        logger.info(
            "Check that the network %s is not attached to Host %s",
            config.VLAN_NETWORKS[0], config.HOSTS[0]
        )
        if check_network_on_nic(
            config.VLAN_NETWORKS[0], config.HOSTS[0], VLAN_NIC
        ):
            raise NetworkException(
                "Network %s is attached to Host NIC %s on Host %s when "
                "shouldn't" % (config.VLAN_NETWORKS[0], HOST0_NICS[1],
                               config.HOSTS[0])
            )

        logger.info(
            "Create a network %s and attach it to the Host with "
            "setupNetwork action", config.NETWORKS[1]
        )
        vlan_nic = vlan_int_name(HOST0_NICS[1], config.VLAN_ID[1])
        local_dict2 = {config.VLAN_NETWORKS[1]: {
            "vlan_id": config.VLAN_ID[1], "nic": 1, "required": "false",
            "usages": ""
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict2,
            auto_nics=[0, 1]
        ):
            raise NetworkException(
                "Cannot create non-VM VLAN network %s on DC, Cluster and Host"
                % config.VLAN_NETWORKS[1]
            )

        logger.info(
            "Check that the network %s is attached to Host %s",
            config.VLAN_NETWORKS[0], config.HOSTS[0]
        )
        if not check_network_on_nic(
            config.VLAN_NETWORKS[1], config.HOSTS[0], vlan_nic
        ):
            raise NetworkException(
                "Network %s was not attached to interface %s on host %s " %
                (config.VLAN_NETWORKS[1], HOST0_NICS[1], config.HOSTS[0])
            )


@attr(tier=1)
class NetLabels08(TestLabelTestCaseBase):

    """
    Check that the labeled network created in the DC level only will not be
    attached to the labeled Host NIC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create network on DC level only
        """

        local_dict1 = {config.NETWORKS[0]: {"required": "false"}}
        logger.info("Create network %s on DC only ", config.NETWORKS[0])
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], network_dict=local_dict1
        ):
            raise NetworkException("Cannot create network on DC only")

    @tcms(12040, 332580)
    def test_network_on_host(self):
        """
        1) Attach label to that network
        2) Attach label to Host Nic eth1 on Host
        3) Check the network with the same label as Host NIC is not attached to
        Host when it is not attached to the Cluster
        """
        logger.info(
            "Attach label %s to network %s ", config.LABEL_LIST[0],
            config.NETWORKS[0]
        )

        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s " %
                (config.LABEL_LIST[0], config.NETWORKS[0])
            )

        logger.info(
            "Attach the same label %s to Host NIC %s ",
            config.LABEL_LIST[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to Host interface %s on Host %s " %
                (config.LABEL_LIST[0], HOST0_NICS[1], config.HOSTS[0])
            )
        logger.info(
            "Check that the network %s in not attached to Host NIC %s ",
            config.NETWORKS[0], HOST0_NICS[1]
        )
        if check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s was attached to interface %s on host %s but "
                "shouldn't" % (config.NETWORKS[0], HOST0_NICS[1],
                               config.HOSTS[0])
            )


@attr(tier=1)
class NetLabels09(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the VLAN networks appropriately
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 VLAN networks on DC and Cluster
        2) Attach 2 labels to that networks
        3) Attach label_1 to Host Nic eth2
        4) Attach label_2 to Host NIC eth3
        5) Check network_1 is attached to first interface  and network_2 to
        the second interface
        """

        local_dict1 = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                 "required": "false"},
                       config.VLAN_NETWORKS[1]: {"vlan_id": config.VLAN_ID[1],
                                                 "required": "false"}}
        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException("Cannot create network on DC and Cluster")

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
            config.LABEL_LIST[1], config.VLAN_NETWORKS[1]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i], networks=[config.VLAN_NETWORKS[i]]
            ):
                raise NetworkException(
                    "Couldn't attach label %s to network %s " %
                    (config.LABEL_LIST[i], config.VLAN_NETWORKS[i])
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            config.LABEL_LIST[0], HOST0_NICS[2], config.LABEL_LIST[1],
            HOST0_NICS[3]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[i + 2]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host interface %s " %
                    (config.LABEL_LIST[i], HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1],
            HOST0_NICS[2], HOST0_NICS[3]
        )
        for i in range(2):
            vlan_nic = vlan_int_name(HOST0_NICS[i + 2], config.VLAN_ID[i])
            if not check_network_on_nic(
                config.VLAN_NETWORKS[i], config.HOSTS[0], vlan_nic
            ):
                raise NetworkException(
                    "Network %s is not attached toHost NIC %s " %
                    (config.VLAN_NETWORKS[i], HOST0_NICS[i + 2])
                )

    @tcms(12040, 332897)
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info(
            "Unlabel interfaces %s and %s", HOST0_NICS[2], HOST0_NICS[3]
        )
        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]},
            labels=config.LABEL_LIST[:2]
        ):

            raise NetworkException(
                "Couldn't remove label %s from Host NICs %s and %s" %
                (config.LABEL_LIST[0], HOST0_NICS[2], HOST0_NICS[3])
            )

        logger.info(
            "Create Bond from interfaces %s and %s ", HOST0_NICS[2],
            HOST0_NICS[3]
        )
        local_dict = {None: {
            "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create Bond %s " % config.BOND[0])

        logger.info(
            "Attach labels %s and %s to Host Bond %s",
            config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host Bond %s " %
                    (config.LABEL_LIST[i], config.BOND[0])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host Bond %s ",
            config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1], config.BOND[0]
        )
        for i in range(2):
            vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[i])
            if not check_network_on_nic(
                config.VLAN_NETWORKS[i], config.HOSTS[0], vlan_bond
            ):
                raise NetworkException(
                    "Network %s is not attached to Bond %s " %
                    (config.VLAN_NETWORKS[i], config.BOND[0])
                )

        logger.info(
            "Check that label doesn't reside on Bond slaves %s and %s after "
            "Bond creation", HOST0_NICS[2], HOST0_NICS[3]
        )
        if get_label_objects(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]}
        ):
            raise NetworkException("Label exists on Bond slaves ")

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels09, cls).teardown_class()


@attr(tier=1)
class NetLabels10(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the VM non-VLAN  network and VLAN network appropriately and fail
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 networks on DC and Cluster:
           a) VM non-VLAN network
           b) VLAN network
        2) Attach 2 different labels to that networks
        3) Attach one of those labels to Host Nic eth2
        4) Attach another label to Host NIC eth3
        5) Check network_1 is attached to eth2 and network_2 to eth3
        """

        local_dict1 = {
            config.NETWORKS[0]: {"required": "false"},
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0], "required": "false"
            }
        }
        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException("Cannot create networks on DC and Cluster")

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            config.LABEL_LIST[0], config.NETWORKS[0],
            config.LABEL_LIST[1], config.VLAN_NETWORKS[0]
        )
        for i, net in enumerate([config.NETWORKS[0], config.VLAN_NETWORKS[0]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException(
                    "Couldn't attach label %s to network %s " %
                    (config.LABEL_LIST[i], net)
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            config.LABEL_LIST[0], HOST0_NICS[2], config.LABEL_LIST[1],
            HOST0_NICS[3]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[i + 2]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host interface %s " %
                    (config.LABEL_LIST[i], HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            config.NETWORKS[0], config.VLAN_NETWORKS[0],
            HOST0_NICS[2], HOST0_NICS[3]
        )
        vlan_nic = vlan_int_name(HOST0_NICS[3], config.VLAN_ID[0])
        for nic, network in (
            (HOST0_NICS[2], config.NETWORKS[0]),
            (vlan_nic, config.VLAN_NETWORKS[0])
        ):
            if not check_network_on_nic(network, config.HOSTS[0], nic):
                raise NetworkException(
                    "Network %s is not attached to Host NIC %s " %
                    (network, nic)
                )

    @tcms(12040, 361751)
    def test_create_bond(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        logger.info(
            "Unlabel interfaces %s and %s", HOST0_NICS[2], HOST0_NICS[3]
        )

        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]},
            labels=config.LABEL_LIST[:2]
        ):
            raise NetworkException(
                "Couldn't remove label %s from Host NICs %s and %s" %
                (config.LABEL_LIST[0], HOST0_NICS[2], HOST0_NICS[3])
            )
        logger.info(
            "Try to create Bond from interfaces %s and %s ",
            HOST0_NICS[2], HOST0_NICS[3]
        )

        local_dict = {None: {
            "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Couldn't create Bond %s " %
                config.BOND[0])

        logger.info(
            "Negative: Attach label %s and %s  to Host Bond %s ",
            config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0]
        )
        if (
                add_label(
                    label=config.LABEL_LIST[0], host_nic_dict={
                        config.HOSTS[0]: [config.BOND[0]]
                    }
                ) and
                add_label(
                    label=config.LABEL_LIST[1], host_nic_dict={
                        config.HOSTS[0]: [config.BOND[0]]
                    }
                )
        ):
            raise NetworkException(
                "Could attach labels to Host Bond %s " % config.BOND[0]
            )

        logger.info(
            "Check that the networks %s is attached to Host Bond %s ",
            config.NETWORKS[0], config.BOND[0]
        )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], config.BOND[0]
        ):
            raise NetworkException(
                "Network %s is not attached to Host NIC %s " %
                (config.VLAN_NETWORKS[0], config.BOND[0])
            )

        logger.info(
            "Check that the networks %s is not attached to Host Bond %s ",
            config.VLAN_NETWORKS[0], config.BOND[0]
        )
        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[0])
        if check_network_on_nic(
            config.VLAN_NETWORKS[0], config.HOSTS[0], vlan_bond
        ):
            raise NetworkException(
                "Network %s is attached to Host NIC %s " %
                (config.VLAN_NETWORKS[0], config.BOND[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels10, cls).teardown_class()


@attr(tier=1)
class NetLabels11(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the VM non-VLAN  network and non-VM network appropriately and fail
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 networks on DC and Cluster:
           a) VM non-VLAN network
           b) non-VM network
        2) Attach 2 different labels to that networks
        3) Attach one of those labels to Host Nic eth2
        4) Attach another label to Host NIC eth3
        5) Check network_1 is attached to eth2 and network_2 to eth3
        """

        local_dict1 = {
            config.NETWORKS[0]: {"required": "false"},
            config.NETWORKS[1]: {"required": "false", "usages": ""}
        }

        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException("Cannot create networks on DC and Cluster")

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            config.LABEL_LIST[0], config.NETWORKS[0],
            config.LABEL_LIST[1], config.NETWORKS[1]
        )
        for i, net in enumerate([config.NETWORKS[0], config.NETWORKS[1]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException(
                    "Couldn't attach label %s to network %s " %
                    (config.LABEL_LIST[i], net)
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            config.LABEL_LIST[0], HOST0_NICS[2], config.LABEL_LIST[1],
            HOST0_NICS[3]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[i + 2]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host interface %s " %
                    (config.LABEL_LIST[i], HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            config.NETWORKS[0], config.NETWORKS[1],
            HOST0_NICS[2], HOST0_NICS[3]
        )
        for nic, network in (
            (HOST0_NICS[2], config.NETWORKS[0]),
            (HOST0_NICS[3], config.NETWORKS[1])
        ):
            if not check_network_on_nic(network, config.HOSTS[0], nic):
                raise NetworkException(
                    "Network %s is not attached to Host NIC %s " %
                    (network, nic)
                )

    @tcms(12040, 361750)
    def test_create_bond(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        logger.info(
            "Unlabel interfaces %s and %s", HOST0_NICS[2], HOST0_NICS[3]
        )

        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]},
            labels=config.LABEL_LIST[:2]
        ):
            raise NetworkException(
                "Couldn't remove label %s from Host NICs %s and %s" %
                (config.LABEL_LIST[0], HOST0_NICS[2], HOST0_NICS[3])
            )
        logger.info(
            "Create Bond from interfaces %s and %s ",
            HOST0_NICS[2], HOST0_NICS[3]
        )

        local_dict = {None: {
            "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException(
                "Couldn't create Bond %s " %
                config.BOND[0])

        logger.info(
            "Negative: Attach label %s and %s  to Host Bond %s ",
            config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0]
        )
        if (
                add_label(
                    label=config.LABEL_LIST[0], host_nic_dict={
                        config.HOSTS[0]: [config.BOND[0]]
                    }
                ) and
                add_label(
                    label=config.LABEL_LIST[1], host_nic_dict={
                        config.HOSTS[0]: [config.BOND[0]]
                    }
                )
        ):
            raise NetworkException(
                "Could attach labels to Host Bond %s " % config.BOND[0]
            )

        logger.info(
            "Check that the networks %s is attached to Host Bond %s ",
            config.NETWORKS[0], config.BOND[0]
        )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], config.BOND[0]
        ):
            raise NetworkException(
                "Network %s is not attached to Host NIC %s " %
                (config.VLAN_NETWORKS[0], config.BOND[0])
            )

        logger.info(
            "Check that the networks %s is not attached to Host Bond %s ",
            config.NETWORKS[1], config.BOND[0]
        )
        if check_network_on_nic(
            config.NETWORKS[1], config.HOSTS[0], config.BOND[0]
        ):
            raise NetworkException(
                "Network %s is attached to Host NIC %s " %
                (config.NETWORKS[1], config.BOND[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels11, cls).teardown_class()


@attr(tier=1)
class NetLabels12(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the non-VM and VLAN networks appropriately
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 1 VLAN and 1 non-VM non-VLAN networks on DC and Cluster
        2) Attach 2 labels to that networks
        3) Attach label_1 to Host Nic eth2
        4) Attach label_2 to Host NIC eth3
        5) Check network_1 is attached to eth2 and network_2 to eth3
        """

        local_dict1 = {
            config.NETWORKS[0]: {"usages": "", "required": "false"},
            config.VLAN_NETWORKS[1]: {
                "vlan_id": config.VLAN_ID[1], "required": "false"
            }
        }
        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict1
        ):
            raise NetworkException("Cannot create network on DC and Cluster")

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            config.LABEL_LIST[0], config.NETWORKS[0],
            config.LABEL_LIST[1], config.VLAN_NETWORKS[1]
        )
        for i, net in enumerate([config.NETWORKS[0], config.VLAN_NETWORKS[1]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException(
                    "Couldn't attach label %s to network %s " %
                    (config.LABEL_LIST[i], net)
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            config.LABEL_LIST[0], HOST0_NICS[2],
            config.LABEL_LIST[1], HOST0_NICS[3]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[i + 2]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host interface %s " %
                    (config.LABEL_LIST[i], HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            config.NETWORKS[0], config.VLAN_NETWORKS[1],
            HOST0_NICS[2], HOST0_NICS[3]
        )
        vlan_nic = vlan_int_name(HOST0_NICS[3], config.VLAN_ID[1])
        for nic, network in (
            (HOST0_NICS[2], config.NETWORKS[0]),
            (vlan_nic, config.VLAN_NETWORKS[1])
        ):
            if not check_network_on_nic(network, config.HOSTS[0], nic):
                raise NetworkException(
                    "Network %s is not attached to Host NIC %s " %
                    (network, nic)
                )

    @tcms(12040, 361752)
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info(
            "Unlabel interfaces %s and %s", HOST0_NICS[2], HOST0_NICS[3]
        )
        if not remove_label(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]},
            labels=config.LABEL_LIST[:2]
        ):
            raise NetworkException(
                "Couldn't remove labels from Host NICs %s and %s" %
                (HOST0_NICS[2], HOST0_NICS[3])
            )

        logger.info(
            "Create Bond from interfaces %s and %s ",
            HOST0_NICS[2], HOST0_NICS[3]
        )
        local_dict = {None: {
            "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]
        }}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
        ):
            raise NetworkException("Cannot create Bond %s " % config.BOND[0])

        logger.info(
            "Attach labels %s and %s to Host Bond %s",
            config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0]
        )
        for i in range(2):
            if not add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to Host Bond %s " %
                    (config.LABEL_LIST[i], config.BOND[0])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host Bond %s ",
            config.NETWORKS[0], config.VLAN_NETWORKS[1], config.BOND[0]
        )

        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[1])
        for (net, nic) in (
            (config.NETWORKS[0], config.BOND[0]),
            (config.VLAN_NETWORKS[1], vlan_bond)
        ):
            if not check_network_on_nic(net, config.HOSTS[0], nic):
                raise NetworkException(
                    "Network %s is not attached to Bond %s " %
                    (net, config.BOND[0])
                )

        logger.info(
            "Check that label doesn't reside on Bond slaves %s and %s after "
            "Bond creation", HOST0_NICS[2], HOST0_NICS[3]
        )
        if get_label_objects(
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[2], HOST0_NICS[3]]}
        ):
            raise NetworkException("Label exists on Bond slaves ")

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not remove_label(host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels12, cls).teardown_class()


@attr(tier=1)
class NetLabels13(TestLabelTestCaseBase):

    """
    1)Check that when a labeled network is detached from a cluster,
    the network will be removed from any labeled interface within that cluster.
    2) The same will happen when the network is removed from the DC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create a network on DC/Cluster
        2) Create and attach label to the network
        3) Attach label to Host Nic - eth1
        4) Check that the network is attached to the interface (eth1)
        """

        logger.info("Create network %s on DC and Cluster", config.NETWORKS[0])
        local_dict = {config.NETWORKS[0]: {"required": "false"}}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s on DC and CLuster" %
                config.NETWORKS[0]
            )

        logger.info(
            "Attach label %s to network %s ", config.LABEL_LIST[0],
            config.NETWORKS[0]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s" %
                (config.LABEL_LIST[0], config.NETWORKS[0])
            )

        logger.info(
            "Attach the label %s to Host NIC %s",
            config.LABEL_LIST[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to Host NIC %s" %
                (config.LABEL_LIST[0], HOST0_NICS[1])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )

        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s is not attached to Host NIC %s " %
                (config.NETWORKS[0], HOST0_NICS[1])
            )

    @tcms(12040, 332889)
    def test_remove_net_from_cluster_dc(self):
        """
        1) Remove network from the Cluster
        2) Check that the network is not attached to the Host interface
        anymore and not attached to the Cluster
        3) Reassign network to the Cluster
        4) Check that the network is attached to the interface after
        reattaching it to the Cluster
        5) Remove network from the DC
        6) Check that network is not attached to Host NIC
        7) Check that network doesn't exist in DC
        """
        logger.info(
            "Remove labeled network %s from Cluster %s",
            config.NETWORKS[0], config.CLUSTER_NAME[0]
        )
        if not removeNetworkFromCluster(
            True, config.NETWORKS[0], config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Couldn't remove network %s from Cluster %s " %
                (config.NETWORKS[0], config.CLUSTER_NAME[0])
            )

        logger.info(
            "Check that the network %s is not attached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=net_exist_on_nic
        )

        if not sample.waitForFuncStatus(result=False):
            raise NetworkException(
                "Network %s is attached to NIC %s "
                % (config.NETWORKS[0], HOST0_NICS[1])
            )
        logger.info(
            "Check that the network %s is not attached to the Cluster%s",
            config.NETWORKS[0], config.CLUSTER_NAME[0]
        )
        try:
            getClusterNetwork(config.CLUSTER_NAME[0], config.NETWORKS[0])
            raise NetworkException(
                "Network %s is attached to Cluster %s but shouldn't " %
                (config.NETWORKS[0], config.CLUSTER_NAME[0])
            )
        except EntityNotFound:
            logger.info("Network not found on the Cluster as expected")

        logger.info(
            "Reattach labeled network %s to Cluster %s ",
            config.NETWORKS[0], config.CLUSTER_NAME[0]
        )
        if not addNetworkToCluster(
            True, config.NETWORKS[0], config.CLUSTER_NAME[0], required=False
        ):
            raise NetworkException(
                "Couldn't reattach network %s to Cluster %s " %
                (config.NETWORKS[0], config.CLUSTER_NAME[0])
            )

        logger.info(
            "Check that the network %s is reattached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=check_network_on_nic,
            network=config.NETWORKS[
                0], host=config.HOSTS[0], nic=HOST0_NICS[1]
        )

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException(
                "Network %s is not attached to NIC %s "
                % (config.NETWORKS[0], HOST0_NICS[1])
            )

        logger.info(
            "Remove labeled network %s from DataCenter %s",
            config.NETWORKS[0], config.DC_NAME[0]
        )
        if not removeNetwork(True, config.NETWORKS[0], config.DC_NAME[0]):
            raise NetworkException(
                "Couldn't remove network %s from DC %s " %
                (config.NETWORKS[0], config.DC_NAME[0])
            )

        logger.info(
            "Check that the network %s is not attached to Host NIC %s and not "
            "attached to DC %s", config.NETWORKS[0], HOST0_NICS[1],
            config.DC_NAME[0]
        )
        try:
            findNetwork(config.NETWORKS[0], config.DC_NAME[0])
            raise NetworkException(
                "Network %s found on DC, but shouldn't" % config.NETWORKS[0]
            )
        except EntityNotFound:
            logger.info("Network not found on DC as expected")

        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=net_exist_on_nic
        )

        if not sample.waitForFuncStatus(result=False):
            raise NetworkException(
                "Network %s is attached to NIC %s, but shouldn't "
                % (config.NETWORKS[0], HOST0_NICS[1])
            )


@attr(tier=1)
class NetLabels14(TestLabelTestCaseBase):

    """
    1)Check that after moving a Host with labeled interface from one DC to
    another, the network label feature is functioning as usual
    2) Check that it's impossible to move the Host with labeled interface
    to the Cluster on DC that doesn't support Network labels
    """
    __test__ = True

    dc_name2 = "new_DC_case14"
    cl_name2 = "new_CL_case14"
    uncomp_dc = "uncomp_DC_case14"
    uncomp_cl = "uncomp_CL_case14"
    uncomp_cpu = "Intel Conroe Family"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create a new DC and Cluster of the current version
        3) Create a network in a new DC
        4) Create a new DC and Cluster of 3.0 version(not supporting network
         labels feature)
        """
        logger.info(
            "Attach the label %s to Host NIC %s",
            config.LABEL_LIST[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to Host NIC %s" %
                (config.LABEL_LIST[0], HOST0_NICS[1])
            )

        logger.info(
            "Create new DC and Cluster in the setup of the current version"
        )
        if not (
                addDataCenter(positive=True, name=cls.dc_name2,
                              storage_type=config.STORAGE_TYPE,
                              version=config.COMP_VERSION, local=False) and
                addCluster(positive=True, name=cls.cl_name2,
                           data_center=cls.dc_name2,
                           version=config.COMP_VERSION,
                           cpu=config.CPU_NAME)
        ):
            raise NetworkException(
                "Couldn't add a new DC and Cluster to the setup"
            )

        logger.info(
            "Create network %s on new DC and Cluster", config.NETWORKS[0]
        )
        local_dict = {config.NETWORKS[0]: {"required": "false"}}
        if not createAndAttachNetworkSN(
            data_center=cls.dc_name2, cluster=cls.cl_name2,
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s on DC and CLuster" %
                config.NETWORKS[0]
            )

        logger.info(
            "Create new DC and Cluster in the setup of the 3.0 version"
        )
        if not (
                addDataCenter(positive=True, name=cls.uncomp_dc,
                              storage_type=config.STORAGE_TYPE,
                              version=config.VERSION[0], local=False) and
                addCluster(positive=True, name=cls.uncomp_cl,
                           data_center=cls.uncomp_dc,
                           version=config.VERSION[0],
                           cpu=cls.uncomp_cpu)
        ):
            raise NetworkException(
                "Couldn't add a DC and Cluster of %s version to the setup" %
                config.VERSION[0]
            )

    @bz({"1184454": {"engine": ["rest", "sdk", "java"], "version": ["3.5"]}})
    @tcms(12040, 332959)
    def test_move_host_supported_dc_cl(self):
        """
        1) Move the Host from the original DC to the newly created DC
        2) Attach label to the network in the new DC
        3) Check that the network is attached to the Host NIC
        4) Remove label from the network
        5) Move Host back to the original DC/Cluster
        """

        logger.info(
            "Deactivate host, move it to the new DC %s and reactivate it",
            self.dc_name2
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Attach the Host to the new DC/Cluster")
        if not updateHost(True, host=config.HOSTS[0], cluster=self.cl_name2):
            raise NetworkException("Cannot move host to another DC")

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info(
            "Attach label %s to network %s ", config.LABEL_LIST[0],
            config.NETWORKS[0]
        )

        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s" %
                (config.LABEL_LIST[0], config.NETWORKS[0])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )
        sample = TimeoutingSampler(
            timeout=config.SAMPLER_TIMEOUT, sleep=1, func=check_network_on_nic,
            network=config.NETWORKS[
                0], host=config.HOSTS[0], nic=HOST0_NICS[1]
        )
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException(
                "Network %s is not attached to NIC %s " %
                (config.NETWORKS[0], HOST0_NICS[1])
            )

        logger.info(
            "Remove label %s from network %s ", config.LABEL_LIST[0],
            config.NETWORKS[0]
        )
        if not remove_label(
            labels=config.LABEL_LIST[0], networks=[config.NETWORKS[0]]
        ):
            raise NetworkException(
                "Couldn't remove label %s from network %s " %
                (config.LABEL_LIST[0], config.NETWORKS[0])
            )

        logger.info(
            "Deactivate host, move it back to the original DC %s and "
            "reactivate it", config.DC_NAME[0]
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Attach Host to original DC/Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException("Cannot move host to the original DC")

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

    @bz({"1184454": {"engine": ["rest", "sdk", "java"], "version": ["3.5"]}})
    @tcms(12040, 337364)
    def test_move_host_unsupported_dc_cl(self):
        """
        1) Try to move the Host to the DC with 3.0 version
        2) Activate the Host in original DC after a move action failure
        """
        logger.info(
            "Deactivate host and try to move it to the  DC %s "
            "with unsupported version (3.0) of Cluster %s ",
            self.uncomp_dc, self.uncomp_cl
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Negative: Try to attach Host to another DC/Cluster")
        if not updateHost(False, host=config.HOSTS[0], cluster=self.uncomp_cl):
            raise NetworkException(
                "Could move host to another DC/Cluster when shouldn't"
            )

        logger.info("Move host to the original DC and Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Cannot move host to original DC and Cluster"
            )

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

    @classmethod
    def teardown_class(cls):
        """
        1) Remove label from Host NIC
        Remove created DCs and Clusters from the setup.
        """
        logger.info(
            "Removing the DC %s and %s with appropriate Clusters",
            cls.dc_name2, cls.uncomp_dc
        )

        for dc, cl in (
            (cls.dc_name2, cls.cl_name2), (cls.uncomp_dc, cls.uncomp_cl)
        ):
            if not removeDataCenter(positive=True, datacenter=dc):
                logger.error("Failed to remove datacenter %s", dc)
            if not removeCluster(positive=True, cluster=cl):
                logger.error("Failed to remove cluster %s ", cl)
        super(NetLabels14, cls).teardown_class()


@attr(tier=1)
class NetLabels15(TestLabelTestCaseBase):

    """
    Check that after moving a Host with labeled interface between all the
    Cluster versions for the 3.1 DC, the network label feature is functioning
    as expected
    """
    __test__ = True

    dc_name2 = "new_DC_31_case15"
    cl_name2 = "new_CL_case15"
    comp_cl_name = [
        "".join(["COMP_CL3_case15-", str(i)]) for i in range(
            1, len(config.VERSION)
        )
    ]

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create a new DC with 3.1 version (the lowest version that all its
        clusters support network labels feature)
        3) Create Clusters for all supported versions for that DC (3.1 and
        above)
        4) Create the networks on all those Clusters
        """

        logger.info(
            "Attach the label %s to Host NIC %s",
            config.LABEL_LIST[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to Host NIC %s" %
                (config.LABEL_LIST[0], HOST0_NICS[1])
            )

        logger.info(
            "Create new DC %s with 3.1 version in the setup ", cls.dc_name2
        )
        if not addDataCenter(
            positive=True, name=cls.dc_name2, storage_type=config.STORAGE_TYPE,
            version=config.VERSION[1], local=False
        ):
            raise NetworkException(
                "Couldn't add a new DC %s to the setup" % cls.dc_name2
            )

        logger.info(
            "Create Clusters with all supported version for labeling for DC "
            "%s ", cls.dc_name2
        )
        for ver, cluster in zip(config.VERSION[1:], cls.comp_cl_name):
            if not addCluster(
                positive=True, name=cluster, data_center=cls.dc_name2,
                version=ver, cpu=config.CPU_NAME
            ):
                raise NetworkException(
                    "Couldn't add a new Cluster %s with version %s to the "
                    "setup" % (cluster, ver)
                )

        logger.info("Create networks for all the Clusters of the new DC")
        for index, cluster in enumerate(cls.comp_cl_name):
            local_dict = {config.NETWORKS[index]: {"required": "false"}}
            if not createAndAttachNetworkSN(
                data_center=cls.dc_name2, cluster=cluster,
                network_dict=local_dict
            ):
                raise NetworkException(
                    "Cannot create network %s for CLuster %s" %
                    (config.NETWORKS[index], cluster)
                )

    @bz({"1184454": {"engine": ["rest", "sdk", "java"], "version": ["3.5"]}})
    @tcms(12040, 332896)
    def test_move_host_supported_cl(self):
        """
        1) Move the Host to the 3.1 Cluster
        2) Attach label to the network in the 3.1 Cluster
        3) Check that the network is attached to the Host NIC
        4) Remove label from the network
        5) Repeat the 4 steps above when moving from 3.1 Cluster up
        till you reach 3.4 Cluster
        """
        logger.info(
            "Move the Host with labeled interface between all Clusters of the"
            " 3.1 DC and check that Network labels feature works for each "
            "Cluster version"
        )

        logger.info("Deactivate host")
        assert (deactivateHost(True, host=config.HOSTS[0]))

        for index, cluster in enumerate(self.comp_cl_name):
            logger.info("Move Host to the Cluster %s ", cluster)
            if not updateHost(True, host=config.HOSTS[0], cluster=cluster):
                raise NetworkException(
                    "Cannot move host to cluster %s" % cluster
                )

            if index is not 0:
                logger.info(
                    "Check network %s doesn't reside on Host in Cluster %s",
                    config.NETWORKS[index], cluster
                )
                sample = TimeoutingSampler(
                    timeout=config.SAMPLER_TIMEOUT, sleep=1,
                    func=net_exist_on_nic
                )

                if not sample.waitForFuncStatus(result=False):
                    raise NetworkException(
                        "Network %s is not attached to NIC %s" %
                        (config.NETWORKS[index - 1], HOST0_NICS[1])
                    )

            logger.info(
                "Add label to network %s in Cluster %s",
                config.NETWORKS[index], cluster
            )
            if not add_label(
                label=config.LABEL_LIST[0], networks=[config.NETWORKS[index]]
            ):
                raise NetworkException(
                    "Cannot add label to network %s" % config.NETWORKS[index]
                )

            logger.info(
                "Check network %s resides on Host in Cluster %s",
                config.NETWORKS[index], cluster
            )
            sample = TimeoutingSampler(
                timeout=config.SAMPLER_TIMEOUT, sleep=1,
                func=check_network_on_nic, network=config.NETWORKS[index],
                host=config.HOSTS[0], nic=HOST0_NICS[1]
            )

            if not sample.waitForFuncStatus(result=True):
                raise NetworkException(
                    "Network %s is not attached to NIC %s " %
                    (config.NETWORKS[index], HOST0_NICS[1])
                )

    @classmethod
    def teardown_class(cls):
        """
        1) Move host back to its original Cluster
        2) Remove DC in 3.1 with all its Clusters from the setup.
        3) Call super to remove all labels and networks from setup
        """
        logger.info(
            "Deactivate host, move it to the original Cluster %s and "
            "reactivate it", config.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        if not deactivate_host_if_up(config.HOSTS[0]):
            logger.error("Couldn't deactivate Host %s", config.HOSTS[0])

        logger.info("Attach host to original DC/Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=config.CLUSTER_NAME[0]
        ):
            logger.error("Cannot move host to original Cluster")

        logger.info("Activate Host")
        if not activateHost(True, host=config.HOSTS[0]):
            logger.error("Couldn't activate host %s", config.HOSTS[0])

        logger.info("Removing the DC %s with all its Clusters", cls.dc_name2)
        for cl in cls.comp_cl_name:
            if not removeCluster(positive=True, cluster=cl):
                logger.error("Failed to remove cluster %s", cl)
        if not removeDataCenter(positive=True, datacenter=cls.dc_name2):
            logger.error("Failed to remove datacenter %s", cls.dc_name2)
        super(NetLabels15, cls).teardown_class()


@attr(tier=1)
class NetLabels16(TestLabelTestCaseBase):

    """
    1) Check that moving a Host with Labeled VM network attached to it's NIC
    (with the same label) to another Cluster that has another non-VM network
    with the same network label will detach the network from the origin
    Cluster and will attach the Network from the destination Cluster to the
    Host NIC
    2) Check that moving a Host with Labeled non-VM network attached to it's
    NIC (with the same label) to another Cluster that has another VM
    network with the same network label will detach the network from the origin
    Cluster and will attach the Network from the destination Cluster to the
    Host NIC
    """
    __test__ = True

    cl_name2 = "new_CL_case16"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create a VM network on the DC/Cluster, that the Host resides on
        3) Add the same label to the network as on the Host NIC
        4) Create a new Cluster for current DC
        5) Create a non-VM network in a new Cluster
        6) Add the same label to non-VM network as for VM network in 3)
        7) Check that the VM network1 is attached to the Host NIC
        """
        logger.info(
            "Create a VM network %s on original DC/Cluster",
            config.NETWORKS[0]
        )
        local_dict = {config.NETWORKS[0]: {"required": "false"}}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create VM network %s on DC and CLuster" %
                config.NETWORKS[0]
            )

        logger.info(
            "Attach label %s to network %s and Host NIC %s",
            config.LABEL_LIST[0], config.NETWORKS[0], HOST0_NICS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[0]],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s and Host NIC %s "
                % (config.LABEL_LIST[0], config.NETWORKS[0], HOST0_NICS[1])
            )

        logger.info(
            "Create a new Cluster in the setup for the current version"
        )
        if not addCluster(
            positive=True, name=cls.cl_name2, data_center=config.DC_NAME[0],
            version=config.COMP_VERSION, cpu=config.CPU_NAME
        ):
            raise NetworkException("Couldn't add a new Cluster to the setup")

        logger.info("Create network %s on new Cluster", config.NETWORKS[1])
        local_dict = {config.NETWORKS[1]: {"usages": "", "required": "false"}}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=cls.cl_name2,
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s on DC and CLuster %s " %
                (config.NETWORKS[1], cls.cl_name2)
            )

        logger.info(
            "Attach the same label %s to non-VM network %s as in original "
            "Cluster ", config.LABEL_LIST[0], config.NETWORKS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[1]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s" %
                (config.LABEL_LIST[0], config.NETWORKS[1])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )

        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "VM Network %s is not attached to Host NIC %s " %
                (config.NETWORKS[0], HOST0_NICS[1])
            )

    @bz({"1184454": {"engine": ["rest", "sdk", "java"], "version": ["3.5"]}})
    @tcms(12040, 333115)
    def test_move_host_cluster_same_label(self):
        """
        1) Move the Host from the original DC/Cluster to the newly created
        Cluster
        2) Check that the non-VM network2 is attached to the Host NIC in a
        new Cluster
        3) Move Host back to the original DC/Cluster
        4) Check that the VM network1 is attached to the Host NIC again
        """
        logger.info(
            "Deactivate host, move it to the new Cluster %s and reactivate it",
            self.cl_name2
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Attach host to another DC/Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=self.cl_name2
        ):
            raise NetworkException(
                "Cannot move host to another Cluster %s" % self.cl_name2
            )

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info(
            "Check that the non-VM network %s is attached to Host NIC %s",
            config.NETWORKS[1], HOST0_NICS[1]
        )
        if not check_network_on_nic(
            config.NETWORKS[1], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "non-VM Network %s is not attached to Host NIC %s " %
                (config.NETWORKS[1], HOST0_NICS[1])
            )

        logger.info(
            "Deactivate host again, move it to the original Cluster %s and "
            "reactivate it", config.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Attach Host to original DC/Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Cannot move host to the original Cluster %s" %
                config.CLUSTER_NAME[0]
            )

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info(
            "Check that the VM network %s is attached to Host NIC %s",
            config.NETWORKS[0], HOST0_NICS[1]
        )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "VM Network %s is not attached to Host NIC %s " %
                (config.NETWORKS[1], HOST0_NICS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove newly created Cluster from the setup.
        """
        logger.info(
            "Removing newly created cluster %s from the setup", cls.cl_name2
        )
        if not removeCluster(positive=True, cluster=cls.cl_name2):
            logger.error("Failed to remove cluster %s ", cls.cl_name2)
        super(NetLabels16, cls).teardown_class()


@attr(tier=1)
class NetLabels17(TestLabelTestCaseBase):

    """
    Negative test cases:
    1) Check it is not possible to have 2 bridged networks on the same host
    interface
    2) Check it is not possible to have 2 bridgeless networks on the same
    host interface
    3) Check it is not possible to have bridged + bridgeless network on the
    same host interface
    4) Check it is not possible to have bridged and VLAN network on the same
    host interface
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create:
            a) 4 bridged networks on DC/Cluster
            b) 3 bridgeless networks on DC/Cluster
            c) 1 VLAN network on DC/Cluster
        2) Add label1 to the sw1 and sw2 VM networks
        3) Add label2 to the sw3 and sw4 non-VM networks
        4) Add label3 to sw5 and sw6 VM and non-VM networks
        5) Add label4 to sw7 and sw8 VM and VLAN networks
        """
        local_dict = {
            config.NETWORKS[0]: {"required": "false"},
            config.NETWORKS[1]: {"required": "false"},
            config.NETWORKS[2]: {"usages": "", "required": "false"},
            config.NETWORKS[3]: {"usages": "", "required": "false"},
            config.NETWORKS[4]: {"required": "false"},
            config.NETWORKS[5]: {"usages": "", "required": "false"},
            config.NETWORKS[6]: {"required": "false"},
            config.NETWORKS[7]: {
                "vlan_id": config.VLAN_ID[0], "required": "false"
            }
        }

        logger.info("Create and attach all 8 networks to DC and Cluster")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create 8 networks on DC and Cluster"
            )

        for i in range(0, 8, 2):
            logger.info(
                "Attach label %s to networks %s and %s",
                config.LABEL_LIST[i], config.NETWORKS[i],
                config.NETWORKS[i + 1]
            )
            if not add_label(
                label=config.LABEL_LIST[i], networks=config.NETWORKS[i:i + 2]
            ):
                raise NetworkException(
                    "Couldn't attach label %s to networks" %
                    config.LABEL_LIST[i]
                )

    @tcms(12040, 332911)
    def test_label_restrictioin(self):
        """
        1) Put label1 on Host NIC of the Host
        2) Check that the networks sw1 and sw2 are not attached to the Host
        3) Replace label1 with label2 on Host NIC of the Host
        4) Check that the networks sw3 and sw4 are not attached to the Host
        5) Replace label2 with label3 on Host NIC of the Host
        6) Check that the networks sw5 and sw6 are not attached to the Host
        7) Replace label3 with label4 on Host NIC of the Host
        8) Check that the networks sw7 and sw8 are not attached to the Host
        """
        for i in range(0, 8, 2):
            logger.info(
                "Attach label %s to Host NIC %s ",
                config.LABEL_LIST[i], HOST0_NICS[1]
            )
            if add_label(
                label=config.LABEL_LIST[i],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
            ):
                raise NetworkException(
                    "Could attach label %s to interface %s" %
                    (config.LABEL_LIST[i], HOST0_NICS[1])
                )

            logger.info(
                "Check that network %s and %s are not attached to interface ",
                config.NETWORKS[i], config.NETWORKS[i + 1]
            )
            for net in (config.NETWORKS[i], config.NETWORKS[i + 1]):
                if check_network_on_nic(net, config.HOSTS[0], HOST0_NICS[1]):
                    raise NetworkException(
                        "Network %s is attached to NIC %s " %
                        (net, HOST0_NICS[1])
                    )

            logger.info("Remove label from Host NIC %s", HOST0_NICS[1])
            if not remove_label(
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
            ):
                raise NetworkException(
                    "Couldn't remove label from Host %s int %s" %
                    (config.HOSTS[0], [HOST0_NICS[1]])
                )


@attr(tier=1)
class NetLabels18(TestLabelTestCaseBase):

    """
    1) Check that when adding a new labeled VM network to the system which
    has another VM network with the same label attached to the Host, will not
    attach the new network to the Host
    2) Check that when adding a new labeled non-VM network to the system which
    has another non-VM network with the same label attached to the Host, will
    not attach the new network to the Host
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Create 2 bridged and 2 bridgeless networks on DC/Cluster
        2) Add label1 to the sw1 VM network
        3) Add label2 to the sw2 non-VM network
        4) Add label1 to the Host NIC on eth1
        5) Add label2 to the Host NIC on eth2
        6) Check that the VM network sw1 is attached to the Host
        """
        local_dict = {config.NETWORKS[0]: {"required": "false"},
                      config.NETWORKS[1]: {"required": "false", "usages": ""},
                      config.NETWORKS[2]: {"required": "false"},
                      config.NETWORKS[3]: {"required": "false", "usages": ""}}

        logger.info("Create and attach networks to DC and Cluster ")
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=local_dict
        ):
            raise NetworkException(
                "Cannot create network %s and %s on DC and Cluster" %
                (config.NETWORKS[0], config.NETWORKS[1])
            )

        for i in range(2):
            logger.info(
                "Attach label %s to network %s and Host NIC %s",
                config.LABEL_LIST[i], config.NETWORKS[i], HOST0_NICS[i + 1]
            )
            if not add_label(
                label=config.LABEL_LIST[i], networks=[config.NETWORKS[i]],
                host_nic_dict={config.HOSTS[0]: [HOST0_NICS[i + 1]]}
            ):
                raise NetworkException(
                    "Couldn't attach label %s to network %s or Host NIC %s "
                    % (config.LABEL_LIST[i], config.NETWORKS[i],
                       HOST0_NICS[i + 1])
                )

            logger.info(
                "Check that network %s is attached to interface %s ",
                config.NETWORKS[i], HOST0_NICS[i + 1]
            )
            if not check_network_on_nic(
                config.NETWORKS[i], config.HOSTS[0], HOST0_NICS[i + 1]
            ):
                raise NetworkException(
                    "Network %s is not attached to NIC %s " %
                    (config.NETWORKS[0], HOST0_NICS[1])
                )

    @tcms(12040, 332910)
    def test_label_restrictioin_vm(self):
        """
        1) Put the same label on the sw3 VM network as on network sw1
        2) Check that the new VM network sw3 is not attached to the Host NIC
        3) Check that sw1 is still attached to the Host NIC
        """

        logger.info(
            "Attach the same label %s to networks %s",
            config.LABEL_LIST[0], config.NETWORKS[2]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=[config.NETWORKS[2]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s" %
                (config.LABEL_LIST[0], config.NETWORKS[2])
            )

        logger.info(
            "Check that network %s is not attached to interface %s ",
            config.NETWORKS[2], HOST0_NICS[1]
        )
        if check_network_on_nic(
            config.NETWORKS[2], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s is attached to NIC%s " %
                (config.NETWORKS[2], HOST0_NICS[1])
            )

        logger.info(
            "Check that original network %s is still attached to "
            "interface %s ", config.NETWORKS[0], HOST0_NICS[1]
        )
        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException("Network %s is not attached to NIC %s " %
                                   (config.NETWORKS[0], HOST0_NICS[1])
                                   )

        @tcms(12040, 333061)
        def test_label_restrictioin_non_vm(self):
            """
        1) Attach the same label on the sw4 VM network as on network sw2
        2) Check that the new non-VM network sw4 is not attached to the Host
        NIC
        3) Check that sw2 is still attached to the Host NIC
        """

        logger.info(
            "Attach the same label %s to networks %s",
            config.LABEL_LIST[1], config.NETWORKS[3])
        if not add_label(
            label=config.LABEL_LIST[1], networks=[config.NETWORKS[3]]
        ):
            raise NetworkException(
                "Couldn't attach label %s to network %s" %
                (config.LABEL_LIST[1], config.NETWORKS[3])
            )

        logger.info(
            "Check that network %s is not attached to interface %s ",
            config.NETWORKS[3], HOST0_NICS[2]
        )
        if check_network_on_nic(
            config.NETWORKS[3], config.HOSTS[0], HOST0_NICS[2]
        ):
            raise NetworkException(
                "Network %s is attached to NIC %s " %
                (config.NETWORKS[3], HOST0_NICS[2])
            )

        logger.info(
            "Check that original network %s is still attached to "
            "interface %s ", config.NETWORKS[1], HOST0_NICS[2]
        )
        if not check_network_on_nic(
            config.NETWORKS[1], config.HOSTS[0], HOST0_NICS[2]
        ):
            raise NetworkException(
                "Network %s is not attached to NIC %s " %
                (config.NETWORKS[1], HOST0_NICS[2])
            )


@attr(tier=1)
class NetLabels19(TestLabelTestCaseBase):

    """
    Check that after moving a Host with labeled network red attached to the
    labeled interface (label=lb1) to another Cluster with network blue
    labeled with lb1, the network blue will be attached to the labeled
    interface.
    """
    __test__ = True

    cl_name2 = "new_CL_case19"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create additional Cluster on the original DC
        4) Create network sw1 on the original Cluster
        5) Create network sw2 on newly created Cluster
        6) Attach the same label as on the Host NIC to networks sw1 and sw2
        7) Check that the network sw1 is attached to the Host NIC
        """
        logger.info("Create a new Cluster on original DC ")
        if not addCluster(
            positive=True, name=cls.cl_name2, data_center=config.DC_NAME[0],
            version=config.COMP_VERSION, cpu=config.CPU_NAME
        ):
            raise NetworkException(
                "Couldn't add a new Cluster %s to the setup" % cls.cl_name2
            )

        logger.info(
            "Create networks %s and %s on original and new Clusters "
            "respectively", config.NETWORKS[0], config.NETWORKS[1])
        local_dict1 = {config.NETWORKS[0]: {"required": "false"}}
        local_dict2 = {config.NETWORKS[1]: {"required": "false"}}
        if not (
                createAndAttachNetworkSN(
                    data_center=config.DC_NAME[0],
                    cluster=config.CLUSTER_NAME[0],
                    network_dict=local_dict1) and
                createAndAttachNetworkSN(
                    data_center=config.DC_NAME[0],
                    cluster=cls.cl_name2,
                    network_dict=local_dict2)
        ):
            raise NetworkException(
                "Cannot create networks %s and %s for appropriate CLusters "
                % (config.NETWORKS[0], config.NETWORKS[1])
            )

        logger.info(
            "Attach the same label %s to the Host NIC %s and to "
            "networks %s and %s", config.LABEL_LIST[0],
            HOST0_NICS[1], config.NETWORKS[0], config.NETWORKS[1]
        )
        if not add_label(
            label=config.LABEL_LIST[0], networks=config.NETWORKS[:2],
            host_nic_dict={config.HOSTS[0]: [HOST0_NICS[1]]}
        ):
            raise NetworkException(
                "Couldn't attach label %s to networks or Host NIC"
            )

        logger.info(
            "Check that network %s is attached to interface %s ",
            config.NETWORKS[0], HOST0_NICS[1]
        )

        if not check_network_on_nic(
            config.NETWORKS[0], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s is not attached to NIC%s " %
                (config.NETWORKS[0], HOST0_NICS[1])
            )

    @bz({"1184454": {"engine": ["rest", "sdk", "java"], "version": ["3.5"]}})
    @tcms(12040, 332962)
    def test_move_host(self):
        """
        1) Move the Host from the original Cluster to the newly created one
        2) Check that the network sw2 is attached to the Host NIC
        """
        logger.info(
            "Move the Host with labeled interface to the newly created Cluster"
            " %s ", self.cl_name2
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))

        logger.info("Attach Host to the new DC/Cluster")
        if not updateHost(True, host=config.HOSTS[0], cluster=self.cl_name2):
            raise NetworkException("Cannot move host to the new Cluster")

        logger.info("Activate Host")
        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info(
            "Check that different network %s is attached to interface %s ",
            config.NETWORKS[1], HOST0_NICS[1]
        )
        if not check_network_on_nic(
            config.NETWORKS[1], config.HOSTS[0], HOST0_NICS[1]
        ):
            raise NetworkException(
                "Network %s is not attached to NIC%s " %
                (config.NETWORKS[1], HOST0_NICS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Move host back to its original Cluster
        2) Remove label from Host NIC
        3) Remove additional Cluster from the setup
        """
        logger.info(
            "Deactivate host, move it to the original Cluster %s and "
            "reactivate it", config.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", config.HOSTS[0])
        if not deactivateHost(True, host=config.HOSTS[0]):
            logger.error("Couldn't deactivate Host %s", config.HOSTS[0])

        logger.info("Attach Host to original DC/Cluster")
        if not updateHost(
            True, host=config.HOSTS[0], cluster=config.CLUSTER_NAME[0]
        ):
            logger.error("Cannot move host to original Cluster")

        logger.info("Activate Host")
        if not activateHost(True, host=config.HOSTS[0]):
            logger.error("Couldn't activate host %s", config.HOSTS[0])

        logger.info("Removing the Cluster %s from the setup", cls.cl_name2)
        if not removeCluster(positive=True, cluster=cls.cl_name2):
            logger.error("Failed to remove cluster %s ", cls.cl_name2)
        super(NetLabels19, cls).teardown_class()


def net_exist_on_nic():
    """
    helper function that checks if network is located on eth1 of the host
    """
    return (getHostNic(config.HOSTS[0], HOST0_NICS[1]).get_network() is
            not None)
