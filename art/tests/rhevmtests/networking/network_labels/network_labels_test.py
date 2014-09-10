
"""
Testing Network labels feature.
1 DC, 2 Cluster, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""
from art.unittest_lib import attr
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.clusters import addCluster, \
    removeCluster
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter
from art.rhevm_api.tests_lib.low_level.hosts import sendSNRequest, activateHost, \
    updateHost, deactivateHost, getHostNic
from art.unittest_lib.network import vlan_int_name

from rhevmtests.networking import config
import logging

from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611

from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, remove_all_networks
from art.rhevm_api.tests_lib.low_level.networks import add_label,\
    check_network_on_nic, remove_label, get_label_objects, getClusterNetwork, \
    removeNetworkFromCluster, addNetworkToCluster, removeNetwork, findNetwork

logger = logging.getLogger(__name__)

VLAN_NIC = vlan_int_name(config.HOST_NICS[1], config.VLAN_ID[0])
VLAN_BOND = vlan_int_name(config.BOND[0], config.VLAN_ID[0])
# #######################################################################

########################################################################
#                             Test Cases                               #
########################################################################


class LabelTestCaseBase(TestCase):
    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        logger.info("Starting teardown")
        if not remove_label(host_nic_dict={config.HOSTS[0]: config.HOST_NICS,
                                           config.HOSTS[1]: config.HOST_NICS}):
            raise NetworkException("Couldn't remove labels from Hosts ")

        if not (remove_all_networks(datacenter=config.DC_NAME[0],
                                    mgmt_network=config.MGMT_BRIDGE) and
                createAndAttachNetworkSN(host=config.HOSTS, network_dict={},
                                         auto_nics=[config.HOST_NICS[0]])):
            raise NetworkException("Cannot remove network from setup")


@attr(tier=1)
class NetLabels01(LabelTestCaseBase):
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

        logger.info("Create and attach network %s  to DC and Cluster ",
                    config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict):
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
        long_label = "a"*50
        logger.info("Negative case: Try to attach label %s and %s  with "
                    "incorrect format to the network %s and fail",
                    special_char_labels[0], special_char_labels[1],
                    config.NETWORKS[0])
        for label in special_char_labels:
            if add_label(label=label, networks=[config.NETWORKS[0]]):
                raise NetworkException("Could add label %s with incorrect "
                                       "format to the network %s but shouldn't"
                                       % (label, config.NETWORKS[0]))

        logger.info("Attach label with 50 characters length to the "
                    "network %s ", config.NETWORKS[0])
        if not add_label(label=long_label, networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't add label with 50 characters "
                                   "length to the network %s but should" %
                                   config.NETWORKS[0])

        logger.info("Negative case: Try to attach additional label %s to the"
                    " network %s with already attached label and fail",
                    config.LABEL_LIST[0], config.NETWORKS[0])

        if add_label(label=config.LABEL_LIST[0],
                     networks=[config.NETWORKS[0]]):
            raise NetworkException("Could add additional labelto the network "
                                   "%s but shouldn't" % config.NETWORKS[0])

        logger.info("Attach 10 labels to the Host NIC %s", config.HOST_NICS[1])
        for label in config.LABEL_LIST:
            if not add_label(label=label,
                             host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[1]]}):
                raise NetworkException("Couldn't add label %s to the Host "
                                       "NIC %s but should" %
                                       (label, config.HOST_NICS[1]))


@attr(tier=1)
class NetLabels02(LabelTestCaseBase):
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
        logger.info("Create bond %s on host %s", config.BOND[0],
                    config.HOSTS[0])
        local_dict1 = {None: {'nic': config.BOND[0],
                              'slaves': [config.HOST_NICS[2],
                                         config.HOST_NICS[3]],
                              'required': 'false'}}
        if not createAndAttachNetworkSN(host=config.HOSTS[0],
                                        network_dict=local_dict1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create bond %s on the Host %s" %
                                   (config.BOND[0], config.HOSTS[0]))

        logger.info("Create VLAN network %s on DC and Cluster",
                    config.VLAN_NETWORKS[0])
        local_dict2 = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                 "required": "false"}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict2):
            raise NetworkException("Cannot create VLAN network %s on DC and "
                                   "Cluster" % config.VLAN_NETWORKS[0])

        logger.info("Attach label %s to VLAN network %s and to the Host NIC "
                    "%s", config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
                    config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]:
                                        [config.HOST_NICS[1]]},
                         networks=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to VLAN network "
                                   "%s or to Host NIC %s" %
                                   (config.LABEL_LIST[0],
                                    config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1]))

        logger.info("Check that the network %s is attached to Host NIC %s",
                    config.VLAN_NETWORKS[0], VLAN_NIC)
        if not check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                    VLAN_NIC):
            raise NetworkException("Network %s is not attached to "
                                   "Host NIC %s " %
                                   (config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1]))

    @tcms(12040, 333128)
    def test_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface (eth1)
        3) Attach label to the bond and succeed
        """
        logger.info("Negative case: Try to attach label to the bond when "
                    "that label is already attached to the interface %s ",
                    config.HOST_NICS[1])
        if add_label(label=config.LABEL_LIST[0],
                     host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            raise NetworkException("Could attach label to Host NIC bond when "
                                   "shouldn't")

        logger.info("Remove label from the host NIC %s and then try to "
                    "attach label to the Bond interface")
        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[1]]},
                            labels=[config.LABEL_LIST[0]]):
            raise NetworkException("Couldn't remove label %s from Host NIC %s"
                                   % (config.LABEL_LIST[0],
                                      config.HOST_NICS[1]))
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}):
            raise NetworkException("Couldn't attach label to Host bond %s "
                                   "when should" % config.BOND[0])

        logger.info("Check that the network %s is attached to the bond "
                    "on Host %s", config.VLAN_NETWORKS[0], config.HOSTS[0])
        if not check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                    VLAN_BOND):
            raise NetworkException("Network %s is not attached to Bond %s " %
                                   (config.VLAN_NETWORKS[0],
                                    config.BOND[0]))


@attr(tier=1)
class NetLabels03(LabelTestCaseBase):
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

        logger.info("Create and attach network %s to DC and Cluster ",
                    config.NETWORKS[0])

        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create network %s on DC and "
                                   "Cluster" % config.NETWORKS[0])

        local_dict1 = {None: {'nic': config.BOND[0],
                              'slaves': [config.HOST_NICS[2],
                                         config.HOST_NICS[3]],
                              'required': 'false'}}

        logger.info("Create Bond %s on the second Host", config.BOND[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[1],
                                        network_dict=local_dict1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create bond %s on the Host %s" %
                                   (config.BOND[0], config.HOSTS[1]))

    @tcms(12040, 332261)
    def test_label_several_interfaces(self):
        """
        1) Put label on Host NIC of one Host
        2) Put the same label on bond of the second Host
        3) Put label on the network
        4) Check network is attached to both Host (appropriate interfaces)
        """
        logger.info("Attach label %s to Host NIC %s on the Host %s to the "
                    "Bond %s on Host %s and to the network %s",
                    config.LABEL_LIST[0], config.HOST_NICS[1], config.HOSTS[0],
                    config.BOND[0], config.HOSTS[1], config.NETWORKS[0])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[1]: [config.BOND[0]],
                                        config.HOSTS[0]:
                                        [config.HOST_NICS[1]]},
                         networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s " %
                                   config.LABEL_LIST[0])

        logger.info("Check network %s is attached to interface %s on Host %s "
                    "and to Bond %s on Host %s", config.NETWORKS[0],
                    config.HOST_NICS[1], config.HOSTS[0], config.BOND[0],
                    config.HOSTS[1])
        if not check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                    config.HOST_NICS[1]):
            raise NetworkException("Network %s is not attached to NIC %s " %
                                   (config.NETWORKS[0],
                                    config.HOST_NICS[1]))
        if not check_network_on_nic(config.NETWORKS[0],
                                    config.HOSTS[1],
                                    config.BOND[0]):
            raise NetworkException("Network %s is not attached to Bond %s " %
                                   (config.NETWORKS[0],
                                    config.BOND[0]))


@attr(tier=1)
class NetLabels04(LabelTestCaseBase):
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
        local_dict = {config.NETWORKS[0]: {"usages": "",
                                           "required": "false"},
                      config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                "required": "false"}}

        logger.info("Create and attach networks %s and %s to DC and Cluster ",
                    config.NETWORKS[0], config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create networks %s and %s on DC "
                                   "and Cluster" % (config.NETWORKS[0],
                                                    config.VLAN_NETWORKS[0]))

        local_dict1 = {None: {"nic": config.BOND[0],
                              "slaves": [config.HOST_NICS[2],
                                         config.HOST_NICS[3]]}}

        logger.info("Create Bond %s on the Host %s ", config.BOND[0],
                    config.HOSTS[1])
        if not createAndAttachNetworkSN(host=config.HOSTS[1],
                                        network_dict=local_dict1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create bond on the Host %s" %
                                   config.HOSTS[1])

        logger.info("Attach label %s to networks %s and %s",
                    config.LABEL_LIST[0], config.NETWORKS[0],
                    config.VLAN_NETWORKS[0])
        if not add_label(label=config.LABEL_LIST[0],
                         networks=[config.NETWORKS[0],
                                   config.VLAN_NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to networks %s "
                                   "and %s" %
                                   (config.LABEL_LIST[0], config.NETWORKS[0],
                                    config.VLAN_NETWORKS[0]))

    @tcms(12040, 332262)
    def test_label_several_networks(self):
        """
        1) Put label on Host NIC of one Host
        2) Put label on bond of the second Host
        4) Check that both networks are attached to both Host (appropriate
        interfaces)
        """
        logger.info("Attach label %s to Host NIC %s and Bond %s on both "
                    "Hosts appropriately", config.LABEL_LIST[0],
                    config.HOST_NICS[1], config.BOND[0])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[1]: [config.BOND[0]],
                                        config.HOSTS[0]:
                                        [config.HOST_NICS[1]]}):
                raise NetworkException("Couldn't attach label %s to "
                                       "interfaces" % config.LABEL_LIST[0])

        logger.info("Check that network %s and %s are attached to interface "
                    "%s on Host %s and to Bond on Host %s", config.NETWORKS[0],
                    config.VLAN_NETWORKS[0], config.HOST_NICS[1],
                    config.HOSTS[0], config.HOSTS[1])
        if not (check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[0], VLAN_NIC) and
                check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[1], VLAN_BOND)):
            raise NetworkException("VLAN Network %s is not attached to NIC "
                                   "%s or Bond %s " % (config.VLAN_NETWORKS[0],
                                                       config.HOST_NICS[1],
                                                       config.BOND[0]))

        if not (check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                     config.HOST_NICS[1]) and
                check_network_on_nic(config.NETWORKS[0], config.HOSTS[1],
                                     config.BOND[0])):
            raise NetworkException("Network %s is not attached to NIC %s "
                                   "or Bond %s " % (config.NETWORKS[0],
                                                    config.HOST_NICS[1],
                                                    config.BOND[0]))


@attr(tier=1)
class NetLabels05(LabelTestCaseBase):
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
        local_dict1 = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                 "required": "false"}}
        logger.info("Create VLAN network %s on DC and "
                    "Cluster", config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create VLAN network %s on DC and "
                                   "Cluster" % config.VLAN_NETWORKS[0])

        logger.info("Attach label %s to VLAN network %s on interface %s of "
                    "both Hosts", config.LABEL_LIST[0],
                    config.VLAN_NETWORKS[0], config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]: [config.HOST_NICS[1]],
                                        config.HOSTS[1]:
                                            [config.HOST_NICS[1]]},
                         networks=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to VLAN network "
                                   "%s or to Host NIC %s on both Hosts" %
                                   (config.LABEL_LIST[0],
                                    config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1]))

        for host in config.HOSTS[:2]:
            logger.info("Check that the network %s is attached to Host %s"
                        "before un-labeling ", config.VLAN_NETWORKS[0], host)
            if not check_network_on_nic(config.VLAN_NETWORKS[0], host,
                                        VLAN_NIC):
                raise NetworkException("Network %s is not attached to NIC %s "
                                       "on host %s" % (config.VLAN_NETWORKS[0],
                                                       config.HOST_NICS[1],
                                                       host))

    @tcms(12040, 332815)
    def test_unlabel_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from eth1 on both Hosts
        """
        logger.info("Remove label %s from the network %s attached to %s on "
                    "both Hosts ", config.LABEL_LIST[0],
                    config.VLAN_NETWORKS[0],
                    config.HOST_NICS[1])
        if not remove_label(networks=[config.VLAN_NETWORKS[0]],
                            labels=[config.LABEL_LIST[0]]):
            raise NetworkException("Couldn't remove label %s from network %s "
                                   % (config.LABEL_LIST[0],
                                      config.VLAN_NETWORKS[0]))

        for host in config.HOSTS[:2]:
            logger.info("Check that the network %s is not attached to Host "
                        "%s", config.VLAN_NETWORKS[0], host)
            sample = TimeoutingSampler(timeout=60, sleep=1,
                                       func=check_network_on_nic,
                                       network=config.VLAN_NETWORKS[0],
                                       host=host, nic=VLAN_NIC)

            if not sample.waitForFuncStatus(result=False):
                raise NetworkException("Network %s is attached to NIC %s "
                                       "on host %s but shouldn't " %
                                       (config.VLAN_NETWORKS[0],
                                        config.HOST_NICS[1], host))


@attr(tier=1)
class NetLabels06(LabelTestCaseBase):
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

        local_dict1 = {None: {'nic': config.BOND[0],
                              'slaves': [config.HOST_NICS[2],
                                         config.HOST_NICS[3]]}}

        logger.info("Create bond on both Hosts in the setup")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[:2],
                                        network_dict=local_dict1,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create bond on the Host")

        local_dict2 = {config.NETWORKS[0]: {"required": "false"}}
        logger.info("Create regular network %s on DC and Cluster",
                    config.NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict2):
            raise NetworkException("Cannot create network %s on DC and "
                                   "Cluster" % config.NETWORKS[0])

        logger.info("Attach label %s to network %s on Bonds %s of both Hosts",
                    config.LABEL_LIST[0], config.NETWORKS[0], config.BOND[0])

        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]: [config.BOND[0]],
                                        config.HOSTS[1]: [config.BOND[0]]},
                         networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to network "
                                   "%s or to Host Bond %s on both Hosts" %
                                   (config.LABEL_LIST[0], config.NETWORKS[0],
                                    config.BOND[0]))

        logger.info("Check network %s is attached to Bond on both Hosts",
                    config.NETWORKS[0])
        for host in config.HOSTS[:2]:
            logger.info("Check that the network %s is attached to Hosts "
                        "%s bond ", config.NETWORKS[0], host)
            if not check_network_on_nic(config.NETWORKS[0], host,
                                        config.BOND[0]):
                raise NetworkException("Network %s was not attached to Bond "
                                       "%s on host %s " %
                                       (config.NETWORKS[0], config.BOND[0],
                                        host))

    @tcms(12040, 332898)
    def test_break_labeled_bond(self):
        """
        1) Break Bond on both Hosts
        2) Make sure the network was detached from Bond on both Hosts
        3) Make sure that the bond slave interfaces don't have label
        configured
        """

        logger.info("Break bond on both Hosts")
        for host_i in config.HOSTS[:2]:
            if not sendSNRequest(True, host=host_i,
                                 auto_nics=[config.HOST_NICS[0]],
                                 check_connectivity='true',
                                 connectivity_timeout=60,
                                 force='false'):
                raise NetworkException("Couldn't break bond on Host %s" %
                                       host_i)

        for host in config.HOSTS[:2]:
            logger.info("Check that the network %s is not attached to Hosts "
                        "%s bond ", config.NETWORKS[0], host)
            if check_network_on_nic(config.NETWORKS[0], host,
                                    config.BOND[0]):
                raise NetworkException("Network %s is attached to Bond "
                                       "%s on host %s when shouldn't" %
                                       (config.NETWORKS[0], config.BOND[0],
                                        host))

        logger.info("Check that the label %s doesn't appear on slaves of "
                    "both Hosts")
        if get_label_objects(host_nic_dict={
            config.HOSTS[0]: [config.HOST_NICS[2], config.HOST_NICS[3]],
            config.HOSTS[1]: [config.HOST_NICS[2], config.HOST_NICS[3]]
        }):
            raise NetworkException("Label exists on Bond slaves")


@attr(tier=1)
class NetLabels07(LabelTestCaseBase):
    """
    1) Negative case: Try to remove labeled network NET1 from labeled
    interface eth1 by setupNetworks
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

        local_dict1 = {config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                 "required": "false",
                                                 "usages": ""}}

        logger.info("Create VLAN  non-VM network %s on DC and Cluster",
                    config.VLAN_NETWORKS[0])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create VLAN network %s on DC and "
                                   "Cluster" % config.VLAN_NETWORKS[0])

        logger.info("Attach label %s to non-VM VLAN network %s and NIC %s ",
                    config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
                    config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={
                             config.HOSTS[0]: [config.HOST_NICS[1]]},
                         networks=[config.VLAN_NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to non-VM VLAN"
                                   "network %s or to Host NIC %s " %
                                   (config.LABEL_LIST[0],
                                    config.VLAN_NETWORKS[0],
                                    config.BOND[0]))

        logger.info("Check that the network %s is attached to Host "
                    "%s", config.VLAN_NETWORKS[0], config.HOSTS[0])

        if not check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                    VLAN_NIC):
            raise NetworkException("Network %s was not attached to interface "
                                   "%s on host %s " %
                                   (config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1], config.HOSTS[0]))

    @tcms(12040, 332578)
    def test_remove_label_host_NIC(self):
        """
       1) Negative case: Try to remove labeled network NET1 from labeled
       interface eth1 with setupNetworks
       2) Remove label from interface and make sure the network is detached
       from it
       3) Attach another network to the same interface with setupNetworks
       """

        logger.info("Try to remove labeled network %s from Host NIC %s with "
                    "setupNetwork command ", config.VLAN_NETWORKS[0],
                    config.HOST_NICS[1])
        if not sendSNRequest(False, host=config.HOSTS[0],
                             auto_nics=[config.HOST_NICS[0]],
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            raise NetworkException("Could remove labeled network %s from "
                                   "Host NIC % s" % (config.VLAN_NETWORKS[0],
                                                     config.HOST_NICS[1]))

        logger.info("Remove label %s from Host NIC %s", config.LABEL_LIST[0],
                    config.HOST_NICS[1])
        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[1]]},
                            labels=[config.LABEL_LIST[0]]):
            raise NetworkException("Couldn't remove label %s from Host NIC %s"
                                   % (config.LABEL_LIST[0],
                                      config.HOST_NICS[1]))

        logger.info("Check that the network %s is not attached to Host "
                    "%s", config.VLAN_NETWORKS[0], config.HOSTS[0])
        if check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                VLAN_NIC):
            raise NetworkException("Network %s is attached to "
                                   "Host NIC %s on Host %s when shouldn't" %
                                   (config.VLAN_NETWORKS[0],
                                    config.HOST_NICS[1], config.HOSTS[0]))

        logger.info("Create a network %s and attach it to the Host with "
                    "setupNetwork action", config.NETWORKS[1])
        vlan_nic = vlan_int_name(config.HOST_NICS[1], config.VLAN_ID[1])
        local_dict2 = {config.VLAN_NETWORKS[1]: {"vlan_id": config.VLAN_ID[1],
                                                 'nic': config.HOST_NICS[1],
                                                 "required": "false",
                                                 "usages": ""}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict2,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[1]]):
            raise NetworkException("Cannot create non-VM VLAN network %s on "
                                   "DC, Cluster and Host" %
                                   config.VLAN_NETWORKS[1])

        logger.info("Check that the network %s is attached to Host "
                    "%s", config.VLAN_NETWORKS[0], config.HOSTS[0])
        if not check_network_on_nic(config.VLAN_NETWORKS[1], config.HOSTS[0],
                                    vlan_nic):
            raise NetworkException("Network %s was not attached to interface "
                                   "%s on host %s " %
                                   (config.VLAN_NETWORKS[1],
                                    config.HOST_NICS[1], config.HOSTS[0]))


@attr(tier=1)
class NetLabels08(LabelTestCaseBase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create network on DC only")

    @tcms(12040, 332580)
    def test_network_on_host(self):
        """
        1) Attach label to that network
        2) Attach label to Host Nic eth1 on Host
        3) Check the network with the same label as Host NIC is not attached to
        Host when it is not attached to the Cluster
        """
        logger.info("Attach label %s to network %s ",
                    config.LABEL_LIST[0], config.NETWORKS[0])

        if not add_label(label=config.LABEL_LIST[0],
                         networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to network "
                                   "%s " % (config.LABEL_LIST[0],
                                            config.NETWORKS[0]))

        logger.info("Attach the same label %s to Host NIC %s ",
                    config.LABEL_LIST[0], config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]:
                                        [config.HOST_NICS[1]]}):
            raise NetworkException("Couldn't attach label %s to Host "
                                   "interface %s on Host %s " %
                                   (config.LABEL_LIST[0],
                                    config.HOST_NICS[1], config.HOSTS[0]))
        logger.info("Check that the network %s in not attached to Host NIC "
                    "%s ", config.NETWORKS[0], config.HOST_NICS[1])
        if check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                config.HOST_NICS[1]):
            raise NetworkException("Network %s was attached to interface "
                                   "%s on host %s but shouldn't" %
                                   (config.NETWORKS[0],
                                    config.HOST_NICS[1], config.HOSTS[0]))


@attr(tier=1)
class NetLabels09(LabelTestCaseBase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create network on DC and Cluster")

        logger.info("Attach label %s to network %s and label %s to network "
                    "%s ", config.LABEL_LIST[0], config.VLAN_NETWORKS[0],
                    config.LABEL_LIST[1], config.VLAN_NETWORKS[1])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             networks=[config.VLAN_NETWORKS[i]]):
                raise NetworkException("Couldn't attach label %s to network "
                                       "%s " % (config.LABEL_LIST[i],
                                                config.VLAN_NETWORKS[i]))

        logger.info("Attach label %s to Host NIC %s and label %s to Host "
                    "NIC %s ", config.LABEL_LIST[0], config.HOST_NICS[2],
                    config.LABEL_LIST[1], config.HOST_NICS[3])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[i + 2]]}):
                raise NetworkException("Couldn't attach label %s to Host "
                                       "interface %s " %
                                       (config.LABEL_LIST[i],
                                        config.HOST_NICS[i + 2]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "interfaces %s and %s appropriately",
                    config.VLAN_NETWORKS[0], config.VLAN_NETWORKS[1],
                    config.HOST_NICS[2], config.HOST_NICS[3])
        for i in range(2):
            vlan_nic = vlan_int_name(config.HOST_NICS[i + 2],
                                     config.VLAN_ID[i])
            if not check_network_on_nic(config.VLAN_NETWORKS[i],
                                        config.HOSTS[0], vlan_nic):
                raise NetworkException("Network %s is not attached toHost NIC"
                                       " %s " % (config.VLAN_NETWORKS[i],
                                                 config.HOST_NICS[i + 2]))

    @tcms(12040, 332897)
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info("Unlabel interfaces %s and %s", config.HOST_NICS[2],
                    config.HOST_NICS[3])
        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[2],
                                            config.HOST_NICS[3]]},
                            labels=config.LABEL_LIST[:2]):

            raise NetworkException("Couldn't remove label %s from Host NICs "
                                   "%s and %s" % (config.LABEL_LIST[0],
                                                  config.HOST_NICS[2],
                                                  config.HOST_NICS[3]))

        logger.info("Create Bond from interfaces %s and %s ",
                    config.HOST_NICS[2], config.HOST_NICS[3])
        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create Bond %s " % config.BOND[0])

        logger.info("Attach labels %s and %s to Host Bond %s",
                    config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.BOND[0]]}):
                raise NetworkException("Couldn't attach label %s to Host Bond "
                                       "%s " % (config.LABEL_LIST[i],
                                                config.BOND[0]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "Bond %s ", config.VLAN_NETWORKS[0],
                    config.VLAN_NETWORKS[1], config.BOND[0])
        for i in range(2):
            vlan_bond = vlan_int_name(config.BOND[0],
                                      config.VLAN_ID[i])
            if not check_network_on_nic(config.VLAN_NETWORKS[i],
                                        config.HOSTS[0], vlan_bond):
                raise NetworkException("Network %s is not attached to "
                                       "Bond %s " % (config.VLAN_NETWORKS[i],
                                                     config.BOND[0]))

        logger.info("Check that label doesn't reside on Bond slaves %s and "
                    "%s after Bond creation", config.HOST_NICS[2],
                    config.HOST_NICS[3])
        if get_label_objects(host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[2],
                                             config.HOST_NICS[3]]}):
            raise NetworkException("Label exists on Bond slaves ")


@attr(tier=1)
class NetLabels10(LabelTestCaseBase):
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

        local_dict1 = {config.NETWORKS[0]: {"required": "false"},
                       config.VLAN_NETWORKS[0]: {"vlan_id": config.VLAN_ID[0],
                                                 "required": "false"}}
        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create networks on DC and Cluster")

        logger.info("Attach label %s to network %s and label %s to network "
                    "%s ", config.LABEL_LIST[0], config.NETWORKS[0],
                    config.LABEL_LIST[1], config.VLAN_NETWORKS[0])
        for i, net in enumerate([config.NETWORKS[0], config.VLAN_NETWORKS[0]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException("Couldn't attach label %s to network "
                                       "%s " % (config.LABEL_LIST[i], net))

        logger.info("Attach label %s to Host NIC %s and label %s to Host "
                    "NIC %s ", config.LABEL_LIST[0], config.HOST_NICS[2],
                    config.LABEL_LIST[1], config.HOST_NICS[3])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[i + 2]]}):
                raise NetworkException("Couldn't attach label %s to Host "
                                       "interface %s " %
                                       (config.LABEL_LIST[i],
                                        config.HOST_NICS[i + 2]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "interfaces %s and %s appropriately",
                    config.NETWORKS[0], config.VLAN_NETWORKS[0],
                    config.HOST_NICS[2], config.HOST_NICS[3])
        vlan_nic = vlan_int_name(config.HOST_NICS[3], config.VLAN_ID[0])
        for nic, network in ((config.HOST_NICS[2], config.NETWORKS[0]),
                             (vlan_nic, config.VLAN_NETWORKS[0])):
            if not check_network_on_nic(network, config.HOSTS[0],
                                        nic):
                raise NetworkException("Network %s is not attached to "
                                       "Host NIC %s " %
                                       (network, nic))

    @tcms(12040, 361751)
    def test_create_bond(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        logger.info("Unlabel interfaces %s and %s", config.HOST_NICS[2],
                    config.HOST_NICS[3])

        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[2],
                                            config.HOST_NICS[3]]},
                            labels=config.LABEL_LIST[:2]):
            raise NetworkException("Couldn't remove label %s from Host NICs "
                                   "%s and %s" % (config.LABEL_LIST[0],
                                                  config.HOST_NICS[2],
                                                  config.HOST_NICS[3]))
        logger.info("Try to create Bond from interfaces %s and %s ",
                    config.HOST_NICS[2], config.HOST_NICS[3])

        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Couldn't create Bond %s " % config.BOND[0])

        logger.info("Negative: Attach label %s and %s  to Host Bond %s ",
                    config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0])
        if (add_label(label=config.LABEL_LIST[0],
                      host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}) and
                add_label(label=config.LABEL_LIST[1],
                          host_nic_dict={config.HOSTS[0]: [config.BOND[0]]})):
            raise NetworkException("Could attach labels to Host Bond %s " %
                                   config.BOND[0])

        logger.info("Check that the networks %s is attached to Host Bond %s ",
                    config.NETWORKS[0], config.BOND[0])
        if not check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                    config.BOND[0]):
            raise NetworkException("Network %s is not attached to "
                                   "Host NIC %s " %
                                   (config.VLAN_NETWORKS[0], config.BOND[0]))

        logger.info("Check that the networks %s is not attached to Host Bond "
                    "%s ", config.VLAN_NETWORKS[0], config.BOND[0])
        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[0])
        if check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                vlan_bond):
            raise NetworkException("Network %s is attached to Host NIC %s " %
                                   (config.VLAN_NETWORKS[0], config.BOND[0]))


@attr(tier=1)
class NetLabels11(LabelTestCaseBase):
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

        local_dict1 = {config.NETWORKS[0]: {"required": "false"},
                       config.NETWORKS[1]: {"required": "false", "usages": ""}}

        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create networks on DC and Cluster")

        logger.info("Attach label %s to network %s and label %s to network "
                    "%s ", config.LABEL_LIST[0], config.NETWORKS[0],
                    config.LABEL_LIST[1], config.NETWORKS[1])
        for i, net in enumerate([config.NETWORKS[0], config.NETWORKS[1]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException("Couldn't attach label %s to network "
                                       "%s " % (config.LABEL_LIST[i], net))

        logger.info("Attach label %s to Host NIC %s and label %s to Host "
                    "NIC %s ", config.LABEL_LIST[0], config.HOST_NICS[2],
                    config.LABEL_LIST[1], config.HOST_NICS[3])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[i + 2]]}):
                raise NetworkException("Couldn't attach label %s to Host "
                                       "interface %s " %
                                       (config.LABEL_LIST[i],
                                        config.HOST_NICS[i + 2]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "interfaces %s and %s appropriately",
                    config.NETWORKS[0], config.NETWORKS[1],
                    config.HOST_NICS[2], config.HOST_NICS[3])
        for nic, network in ((config.HOST_NICS[2], config.NETWORKS[0]),
                             (config.HOST_NICS[3], config.NETWORKS[1])):
            if not check_network_on_nic(network, config.HOSTS[0],
                                        nic):
                raise NetworkException("Network %s is not attached to "
                                       "Host NIC %s " %
                                       (network, nic))

    @tcms(12040, 361750)
    def test_create_bond(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        logger.info("Unlabel interfaces %s and %s", config.HOST_NICS[2],
                    config.HOST_NICS[3])

        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[2],
                                            config.HOST_NICS[3]]},
                            labels=config.LABEL_LIST[:2]):
            raise NetworkException("Couldn't remove label %s from Host NICs "
                                   "%s and %s" % (config.LABEL_LIST[0],
                                                  config.HOST_NICS[2],
                                                  config.HOST_NICS[3]))
        logger.info("Create Bond from interfaces %s and %s ",
                    config.HOST_NICS[2], config.HOST_NICS[3])

        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Couldn't create Bond %s " % config.BOND[0])

        logger.info("Negative: Attach label %s and %s  to Host Bond %s ",
                    config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0])
        if (add_label(label=config.LABEL_LIST[0],
                      host_nic_dict={config.HOSTS[0]: [config.BOND[0]]}) and
                add_label(label=config.LABEL_LIST[1],
                          host_nic_dict={config.HOSTS[0]: [config.BOND[0]]})):
            raise NetworkException("Could attach labels to Host Bond %s " %
                                   config.BOND[0])

        logger.info("Check that the networks %s is attached to Host Bond %s ",
                    config.NETWORKS[0], config.BOND[0])
        if not check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                    config.BOND[0]):
            raise NetworkException("Network %s is not attached to "
                                   "Host NIC %s " %
                                   (config.VLAN_NETWORKS[0], config.BOND[0]))

        logger.info("Check that the networks %s is not attached to Host Bond "
                    "%s ", config.NETWORKS[1], config.BOND[0])
        if check_network_on_nic(config.NETWORKS[1], config.HOSTS[0],
                                config.BOND[0]):
            raise NetworkException("Network %s is attached to Host NIC %s " %
                                   (config.NETWORKS[1], config.BOND[0]))


@attr(tier=1)
class NetLabels12(LabelTestCaseBase):
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

        local_dict1 = {config.NETWORKS[0]: {"usages": "", "required": "false"},
                       config.VLAN_NETWORKS[1]: {"vlan_id": config.VLAN_ID[1],
                                                 "required": "false"}}
        logger.info("Attach networks to DC and Cluster")
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict1):
            raise NetworkException("Cannot create network on DC and Cluster")

        logger.info("Attach label %s to network %s and label %s to network "
                    "%s ", config.LABEL_LIST[0], config.NETWORKS[0],
                    config.LABEL_LIST[1], config.VLAN_NETWORKS[1])
        for i, net in enumerate([config.NETWORKS[0], config.VLAN_NETWORKS[1]]):
            if not add_label(label=config.LABEL_LIST[i], networks=[net]):
                raise NetworkException("Couldn't attach label %s to network "
                                       "%s " % (config.LABEL_LIST[i], net))

        logger.info("Attach label %s to Host NIC %s and label %s to Host "
                    "NIC %s ", config.LABEL_LIST[0], config.HOST_NICS[2],
                    config.LABEL_LIST[1], config.HOST_NICS[3])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[i + 2]]}):
                raise NetworkException("Couldn't attach label %s to Host "
                                       "interface %s " %
                                       (config.LABEL_LIST[i],
                                        config.HOST_NICS[i + 2]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "interfaces %s and %s appropriately",
                    config.NETWORKS[0], config.VLAN_NETWORKS[1],
                    config.HOST_NICS[2], config.HOST_NICS[3])
        vlan_nic = vlan_int_name(config.HOST_NICS[3], config.VLAN_ID[1])
        for nic, network in ((config.HOST_NICS[2], config.NETWORKS[0]),
                             (vlan_nic, config.VLAN_NETWORKS[1])):
            if not check_network_on_nic(network, config.HOSTS[0],
                                        nic):
                raise NetworkException("Network %s is not attached to "
                                       "Host NIC %s " % (network, nic))

    @tcms(12040, 361752)
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info("Unlabel interfaces %s and %s", config.HOST_NICS[2],
                    config.HOST_NICS[3])
        if not remove_label(host_nic_dict={config.HOSTS[0]:
                                           [config.HOST_NICS[2],
                                            config.HOST_NICS[3]]},
                            labels=config.LABEL_LIST[:2]):
            raise NetworkException("Couldn't remove labels from Host NICs "
                                   "%s and %s" % (config.HOST_NICS[2],
                                                  config.HOST_NICS[3]))

        logger.info("Create Bond from interfaces %s and %s ",
                    config.HOST_NICS[2], config.HOST_NICS[3])
        local_dict = {None: {"nic": config.BOND[0], "mode": 1,
                             "slaves": [config.HOST_NICS[2],
                                        config.HOST_NICS[3]]}}
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        host=config.HOSTS[0],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Cannot create Bond %s " % config.BOND[0])

        logger.info("Attach labels %s and %s to Host Bond %s",
                    config.LABEL_LIST[0], config.LABEL_LIST[1], config.BOND[0])
        for i in range(2):
            if not add_label(label=config.LABEL_LIST[i],
                             host_nic_dict={config.HOSTS[0]:
                                            [config.BOND[0]]}):
                raise NetworkException("Couldn't attach label %s to Host Bond "
                                       "%s " % (config.LABEL_LIST[i],
                                                config.BOND[0]))

        logger.info("Check that the networks %s and %s  are attached to Host "
                    "Bond %s ", config.NETWORKS[0],
                    config.VLAN_NETWORKS[1], config.BOND[0])

        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[1])
        for (net, nic) in ((config.NETWORKS[0], config.BOND[0]),
                           (config.VLAN_NETWORKS[1], vlan_bond)):
            if not check_network_on_nic(net, config.HOSTS[0], nic):
                raise NetworkException("Network %s is not attached to "
                                       "Bond %s " % (net, config.BOND[0]))

        logger.info("Check that label doesn't reside on Bond slaves %s and "
                    "%s after Bond creation", config.HOST_NICS[2],
                    config.HOST_NICS[3])
        if get_label_objects(host_nic_dict={config.HOSTS[0]:
                                            [config.HOST_NICS[2],
                                             config.HOST_NICS[3]]}):
            raise NetworkException("Label exists on Bond slaves ")


@attr(tier=1)
class NetLabels13(LabelTestCaseBase):
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
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[0],
                                        cluster=config.CLUSTER_NAME[0],
                                        network_dict=local_dict):
            raise NetworkException("Cannot create network %s on DC and "
                                   "CLuster" % config.NETWORKS[0])

        logger.info("Attach label %s to network %s ",
                    config.LABEL_LIST[0], config.NETWORKS[0])
        if not add_label(label=config.LABEL_LIST[0],
                         networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to network "
                                   "%s" % (config.LABEL_LIST[0],
                                           config.NETWORKS[0]))

        logger.info("Attach the label %s to Host NIC %s",
                    config.LABEL_LIST[0], config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0],
                         host_nic_dict={config.HOSTS[0]:
                                        [config.HOST_NICS[1]]}):
            raise NetworkException("Couldn't attach label %s to Host NIC %s" %
                                   (config.LABEL_LIST[0], config.HOST_NICS[1]))

        logger.info("Check that the network %s is attached to Host NIC %s",
                    config.NETWORKS[0], config.HOST_NICS[1])

        if not check_network_on_nic(config.NETWORKS[0], config.HOSTS[0],
                                    config.HOST_NICS[1]):
            raise NetworkException("Network %s is not attached to "
                                   "Host NIC %s " %
                                   (config.NETWORKS[0], config.HOST_NICS[1]))

    @tcms(12040, 332889)
    def test_remove_net_from_cluster_dc(self):
        """
        2) Remove network from the Cluster
        3) Check that the network is not attached to the Host interface
        anymore and not attached to the Cluster
        4) Reassign network to the Cluster
        5) Check that the network is attached to the interface after
        reattaching it to the Cluster
        6) Remove network from the DC
        7) Check that network is not attached to Host NIC
        8) Check that network doesn't exist in DC
        """
        logger.info("Remove labeled network %s from Cluster %s",
                    config.NETWORKS[0], config.CLUSTER_NAME[0])
        if not removeNetworkFromCluster(True, config.NETWORKS[0],
                                        config.CLUSTER_NAME[0]):
            raise NetworkException("Couldn't remove network %s from Cluster "
                                   "%s " % (config.NETWORKS[0],
                                            config.CLUSTER_NAME[0]))

        logger.info("Check that the network %s is not attached to Host NIC "
                    "%s", config.NETWORKS[0], config.HOST_NICS[1])
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=net_exist_on_nic)

        if not sample.waitForFuncStatus(result=False):
            raise NetworkException("Network %s is not attached to NIC %s "
                                   % (config.NETWORKS[0], config.HOST_NICS[1]))
        logger.info("Check that the network %s is not attached to the Cluster"
                    "%s", config.NETWORKS[0], config.CLUSTER_NAME[0])
        try:
            getClusterNetwork(config.CLUSTER_NAME[0], config.NETWORKS[0])
            raise NetworkException("Network %s is attached to Cluster %s "
                                   "but shouldn't " % (config.NETWORKS[0],
                                                       config.CLUSTER_NAME[0]))
        except EntityNotFound:
            logger.info("Network not found on the Cluster")

        logger.info("Reattach labeled network %s to Cluster %s ",
                    config.NETWORKS[0], config.CLUSTER_NAME)
        if not addNetworkToCluster(True, config.NETWORKS[0],
                                   config.CLUSTER_NAME[0], required=False):
            raise NetworkException("Couldn't reattach network %s to Cluster "
                                   "%s " % (config.NETWORKS[0],
                                            config.CLUSTER_NAME[0]))

        logger.info("Check that the network %s is reattached to Host NIC %s",
                    config.NETWORKS[0], config.HOST_NICS[1])
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=check_network_on_nic,
                                   network=config.NETWORKS[0],
                                   host=config.HOSTS[0],
                                   nic=config.HOST_NICS[1])

        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Network %s is not attached to NIC %s "
                                   % (config.NETWORKS[0], config.HOST_NICS[1]))

        logger.info("Remove labeled network %s from DataCenter %s",
                    config.NETWORKS[0], config.DC_NAME[0])
        if not removeNetwork(True, config.NETWORKS[0], config.DC_NAME[0]):
            raise NetworkException("Couldn't remove network %s from DC "
                                   "%s " % (config.NETWORKS[0],
                                            config.DC_NAME[0]))

        logger.info("Check that the network %s is not attached to Host NIC "
                    "%s and not attached to DC %s", config.NETWORKS[0],
                    config.HOST_NICS[1], config.DC_NAME[0])
        try:
            findNetwork(config.NETWORKS[0], config.DC_NAME[0])
            raise NetworkException("Network %s found on DC, but shouldn't" %
                                   config.NETWORKS[0])
        except EntityNotFound:
            logger.info("Network not found on DC")

        if getHostNic(config.HOSTS[0], config.HOST_NICS[1]).get_network():
            raise NetworkException("Network %s found on NIC %s when removed "
                                   "from DC but shouldn't" %
                                   (config.NETWORKS[0], config.HOST_NICS[1]))


@attr(tier=1)
class NetLabels14(LabelTestCaseBase):
    """
    1)Check that after moving a Host with labeled interface from one DC to
    another, the network label feature is functioning as usual
    2) Check that it's impossible to move the Host with labeled interface
    to the Cluster on DC that doesn't support Network labels
    """
    __test__ = True

    dc_name2 = "new_DC"
    cl_name2 = "new_CL"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create a new DC and Cluster of the current version
        3) Create a network in a new DC
        4) Create a new DC and Cluster of 3.0 version(not supporting network
         labels feature)
        """
        logger.info("Attach the label %s to Host NIC %s",
                    config.LABEL_LIST[0], config.HOST_NICS[1])
        if not add_label(label=config.LABEL_LIST[0], host_nic_dict={
                         config.HOSTS[0]: [config.HOST_NICS[1]]}):
            raise NetworkException("Couldn't attach label %s to Host NIC %s" %
                                   (config.LABEL_LIST[0], config.HOST_NICS[1]))

        logger.info("Create new DC and Cluster in the setup of the current "
                    "version")
        if not (addDataCenter(positive=True, name=cls.dc_name2,
                              storage_type=config.STORAGE_TYPE,
                              version=config.COMP_VERSION, local=False) and
                addCluster(positive=True, name=cls.cl_name2,
                           data_center=cls.dc_name2,
                           version=config.COMP_VERSION,
                           cpu=config.CPU_NAME)):
            raise NetworkException("Couldn't add a new DC and Cluster to "
                                   "the setup")

        logger.info("Create network %s on new DC and Cluster",
                    config.NETWORKS[0])
        local_dict = {config.NETWORKS[0]: {"required": "false"}}
        if not createAndAttachNetworkSN(data_center=cls.dc_name2,
                                        cluster=cls.cl_name2,
                                        network_dict=local_dict):
            raise NetworkException("Cannot create network %s on DC and "
                                   "CLuster" % config.NETWORKS[0])

        logger.info("Create new DC and Cluster in the setup of the 3.0 "
                    "version")
        if not (addDataCenter(positive=True, name=config.UNCOMP_DC_NAME,
                              storage_type=config.STORAGE_TYPE,
                              version=config.VERSION[0], local=False) and
                addCluster(positive=True, name=config.UNCOMP_CL_NAME[0],
                           data_center=config.UNCOMP_DC_NAME,
                           version=config.VERSION[0],
                           cpu=config.CPU_NAME)):
            raise NetworkException("Couldn't add a DC and Cluster of %s "
                                   "version to the setup" % config.VERSION[0])

    @tcms(12040, 332959)
    def test_move_host_supported_dc_cl(self):
        """
        1) Move the Host from the original DC to the newly created DC
        2) Attach label to the network in the new DC
        3) Check that the network is attached to the Host NIC
        4) Remove label from the network
        5) Move Host back to the original DC/Cluster
        """

        logger.info("Deactivate host, move it to the new DC %s and "
                    "reactivate it", self.dc_name2)
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=self.cl_name2):
            raise NetworkException("Cannot move host to another DC")
        assert (activateHost(True, host=config.HOSTS[0]))

        logger.info("Attach label %s to network %s ",
                    config.LABEL_LIST[0], config.NETWORKS[0])

        if not add_label(label=config.LABEL_LIST[0],
                         networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't attach label %s to network "
                                   "%s" % (config.LABEL_LIST[0],
                                           config.NETWORKS[0]))

        logger.info("Check that the network %s is attached to Host NIC %s",
                    config.NETWORKS[0], config.HOST_NICS[1])
        sample = TimeoutingSampler(timeout=60, sleep=1,
                                   func=check_network_on_nic,
                                   network=config.NETWORKS[0],
                                   host=config.HOSTS[0],
                                   nic=config.HOST_NICS[1])
        if not sample.waitForFuncStatus(result=True):
            raise NetworkException("Network %s is not attached to NIC %s "
                                   % (config.NETWORKS[0], config.HOST_NICS[1]))

        logger.info("Remove label %s from network %s ", config.LABEL_LIST[0],
                    config.NETWORKS[0])
        if not remove_label(labels=config.LABEL_LIST[0],
                            networks=[config.NETWORKS[0]]):
            raise NetworkException("Couldn't remove label %s from network %s "
                                   % (config.LABEL_LIST[0],
                                      config.NETWORKS[0]))

        logger.info("Deactivate host, move it back to the original DC %s and "
                    "reactivate it", config.DC_NAME[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to the original DC")
        assert (activateHost(True, host=config.HOSTS[0]))

    @tcms(12040, 337364)
    def test_move_host_unsupported_dc_cl(self):
        """
        1) Try to move the Host to the DC with 3.0 version
        2) Activate the Host in original DC after a move action failure
        """
        logger.info("Deactivate host and try to move it to the  DC %s "
                    "with unsupported version (3.0) of Cluster %s ",
                    config.UNCOMP_DC_NAME, config.UNCOMP_CL_NAME[0])
        assert (deactivateHost(True, host=config.HOSTS[0]))
        if not updateHost(False, host=config.HOSTS[0],
                          cluster=config.UNCOMP_CL_NAME[0]):
            raise NetworkException("Could move host to another DC/Cluster "
                                   "when shouldn't")

        logger.info("Move host to the original DC and Cluster and activate it")
        if not updateHost(True, host=config.HOSTS[0],
                          cluster=config.CLUSTER_NAME[0]):
            raise NetworkException("Cannot move host to original DC and "
                                   "Cluster ")
        assert (activateHost(True, host=config.HOSTS[0]))

    @classmethod
    def teardown_class(cls):
        """
        1) Remove label from Host NIC
        Remove created DCs and Clusters from the setup.
        """
        logger.info("Removing the DC %s and %s with appropriate Clusters",
                    cls.dc_name2, config.UNCOMP_DC_NAME)

        for dc, cl in ((cls.dc_name2, cls.cl_name2),
                       (config.UNCOMP_DC_NAME, config.UNCOMP_CL_NAME[0])):
            if not removeDataCenter(positive=True, datacenter=dc):
                raise NetworkException("Failed to remove datacenter %s" % dc)
            if not removeCluster(positive=True, cluster=cl):
                raise NetworkException("Failed to remove cluster %s " % cl)
        super(NetLabels14, cls).teardown_class()


def net_exist_on_nic():
    """
    helper function that checks if network is located on eth1 of the host
    """
    if getHostNic(config.HOSTS[0], config.HOST_NICS[1]).get_network() is None:
        return False
    return True
