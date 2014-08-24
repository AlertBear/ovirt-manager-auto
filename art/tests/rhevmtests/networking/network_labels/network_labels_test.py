
"""
Testing Network labels feature.
1 DC, 2 Cluster, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""
from art.unittest_lib.network import vlan_int_name

from rhevmtests.networking import config
import logging

from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.exceptions import NetworkException
from art.test_handler.tools import tcms  # pylint: disable=E0611

from art.rhevm_api.tests_lib.high_level.networks import \
    createAndAttachNetworkSN, remove_all_networks
from art.rhevm_api.tests_lib.low_level.networks import add_label,\
    check_network_on_nic, remove_label

logger = logging.getLogger(__name__)

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

        vlan_nic = vlan_int_name(config.HOST_NICS[1], config.VLAN_ID[0])
        logger.info("Check that the network %s is attached to Host NIC %s",
                    config.VLAN_NETWORKS[0], vlan_nic)
        if not check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                    vlan_nic):
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

        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[0])
        logger.info("Check that the network %s is attached to the bond "
                    "on Host %s", config.VLAN_NETWORKS[0], config.HOSTS[0])
        if not check_network_on_nic(config.VLAN_NETWORKS[0], config.HOSTS[0],
                                    vlan_bond):
            raise NetworkException("Network %s is not attached to Bond %s " %
                                   (config.VLAN_NETWORKS[0],
                                    config.BOND[0]))


class NetLabels3(LabelTestCaseBase):
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


class NetLabels4(LabelTestCaseBase):
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
        vlan_nic = vlan_int_name(config.HOST_NICS[1], config.VLAN_ID[0])
        vlan_bond = vlan_int_name(config.BOND[0], config.VLAN_ID[0])
        if not (check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[0], vlan_nic) and
                check_network_on_nic(config.VLAN_NETWORKS[0],
                                     config.HOSTS[1], vlan_bond)):
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
