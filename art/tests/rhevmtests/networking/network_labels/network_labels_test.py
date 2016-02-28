#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Network labels feature.
1 DC, 2 Cluster, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""

import time
import logging
import config as conf
from art import unittest_lib
from art.unittest_lib import attr
from art.core_api import apis_utils
from art.core_api import apis_exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.unittest_lib.network as ul_network
import rhevmtests.networking.helper as networking_helper
import art.rhevm_api.tests_lib.high_level.hosts as hl_host
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Network_Labels_Cases")


class TestLabelTestCaseBase(unittest_lib.NetworkTest):

    """
    base class which provides  teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        for i in range(2):
            logger.info("Removing all networks from %s", conf.HOSTS[i])
            if not hl_host_network.clean_host_interfaces(
                host_name=conf.HOSTS[i]
            ):
                logger.error(
                    "Failed to remove all networks from %s", conf.HOSTS[i]
                )


@attr(tier=2)
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

    @polarion("RHEVM3-4105")
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
            special_char_labels[0], special_char_labels[1], conf.NETS[1][0]
        )
        for label in special_char_labels:
            if ll_networks.add_label(
                label=label, networks=[conf.NETS[1][0]]
            ):
                raise conf.NET_EXCEPTION(
                    "Could add label %s with incorrect format to the network "
                    "%s but shouldn't" % (label, conf.NETS[1][0])
                )

        logger.info(
            "Attach label with 50 characters length to the network %s ",
            conf.NETS[1][0]
        )
        if not ll_networks.add_label(
            label=long_label, networks=[conf.NETS[1][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add label with 50 characters length to the network "
                "%s but should" % conf.NETS[1][0]
            )

        logger.info(
            "Negative case: Try to attach additional label %s to the network "
            "%s with already attached label and fail",
            conf.LABEL_NAME[1][0], conf.NETS[1][0]
        )

        if ll_networks.add_label(
            label=conf.LABEL_NAME[1][0], networks=[conf.NETS[1][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Could add additional label to the network %s but shouldn't" %
                conf.NETS[1][0]
            )

        logger.info(
            "Attach 10 labels to the Host NIC %s", conf.HOST0_NICS[1]
        )
        for label in conf.LABEL_NAME[1]:
            if not ll_networks.add_label(
                label=label,
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't add label %s to the Host NIC %s but should" %
                    (label, conf.HOST0_NICS[1])
                )


@attr(tier=2)
class NetLabels02(TestLabelTestCaseBase):

    """
    Check that the label cannot be attached to the Bond when it is used by
    another Host NIC
    """
    __test__ = True
    bond = "bond02"

    @classmethod
    def setup_class(cls):
        """
        1) Create bond from 2 phy interfaces
        2) Create and attach label to the network
        3) Attach label to Host Nic - eth1
        4) Check that the network is attached to the interface (eth1)
        """
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[1]
        )
        logger.info(
            "Create bond %s on host %s", cls.bond, conf.HOSTS[0]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond,
                    "required": "false"
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create bond %s on the Host %s" %
                (cls.bond, conf.HOSTS[0])
            )

        logger.info(
            "Attach label %s to VLAN network %s and to the Host NIC %s",
            conf.LABEL_NAME[2][0], conf.NETS[2][0],
            conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[2][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]},
            networks=[conf.NETS[2][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to VLAN network %s or to Host NIC %s"
                % (
                    conf.LABEL_NAME[2][0], conf.NETS[2][0],  conf.HOST0_NICS[1]
                )
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            conf.NETS[2][0], vlan_nic
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[2][0], host=conf.HOSTS[0], nic=vlan_nic
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Host NIC %s " %
                (conf.NETS[2][0], conf.HOST0_NICS[1])
            )

    @polarion("RHEVM3-4104")
    def test_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface (eth1)
        3) Attach label to the bond and succeed
        """
        vlan_bond = ul_network.vlan_int_name(
            self.bond, conf.VLAN_IDS[1]
        )
        logger.info(
            "Negative case: Try to attach label to the bond when that label "
            "is already attached to the interface %s ", conf.HOST0_NICS[1]
        )
        if ll_networks.add_label(
            label=conf.LABEL_NAME[2][0],
            host_nic_dict={conf.HOSTS[0]: [self.bond]}
        ):
            raise conf.NET_EXCEPTION(
                "Could attach label to Host NIC bond when shouldn't"
            )

        logger.info(
            "Remove label from the host NIC %s and then try to attach label "
            "to the Bond interface"
        )
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]},
            labels=[conf.LABEL_NAME[2][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from Host NIC %s" %
                (conf.LABEL_NAME[2][0], conf.HOST0_NICS[1])
            )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[2][0],
            host_nic_dict={conf.HOSTS[0]: [self.bond]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label to Host bond %s when should" % self.bond
            )

        logger.info(
            "Check that the network %s is attached to the bond on Host %s",
            conf.NETS[2][0], conf.HOSTS[0]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[2][0], host=conf.HOSTS[0], nic=vlan_bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Bond %s " %
                (conf.NETS[2][0], self.bond)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels02, cls).teardown_class()


@attr(tier=2)
class NetLabels03(TestLabelTestCaseBase):

    """
    1) Put label on Host NIC of one Host
    2) Put label on bond of the second Host
    3) Put label on the network
    4) Check network is attached to both Hosts (appropriate interfaces)
    """
    __test__ = True
    bond = "bond03"

    @classmethod
    def setup_class(cls):
        """
        Create Bond on the second Host
        """
        logger.info(
            "Create bond %s on second host %s", cls.bond, conf.HOSTS[1]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond,
                    "required": "false"
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[1], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create bond %s on the Host %s" %
                (cls.bond, conf.HOSTS[1])
            )

    @polarion("RHEVM3-4106")
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
            conf.LABEL_NAME[3][0], conf.HOST0_NICS[1], conf.HOSTS[0],
            self.bond, conf.HOSTS[1], conf.NETS[3][0]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[3][0],
            host_nic_dict={conf.HOSTS[1]: [self.bond],
                           conf.HOSTS[0]: [conf.HOST0_NICS[1]]},
            networks=[conf.NETS[3][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s " % conf.LABEL_NAME[3][0]
            )

        logger.info(
            "Check network %s is attached to interface %s on Host %s and to "
            "Bond %s on Host %s", conf.NETS[3][0], conf.HOST0_NICS[1],
            conf.HOSTS[0], self.bond, conf.HOSTS[1]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[3][0], host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s " %
                (conf.NETS[3][0], conf.HOST0_NICS[1])
            )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[3][0], host=conf.HOSTS[1], nic=self.bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Bond %s " %
                (conf.NETS[3][0], self.bond)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[1]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels03, cls).teardown_class()


@attr(tier=2)
class NetLabels04(TestLabelTestCaseBase):

    """
    1) Put the same label on both networks
    2) Put network label on Host NIC of one Host
    3) Put network label on bond of the second Host
    4) Check that both networks are attached to both Hosts interface and
    Bond appropriately
    """
    __test__ = True
    bond = "bond04"

    @classmethod
    def setup_class(cls):
        """
        1) Create Bond on the second Host
        2) Put the same label on both networks
        """

        logger.info(
            "Create bond %s on second host %s", cls.bond, conf.HOSTS[1]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[1], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create bond %s on the Host %s" %
                (cls.bond, conf.HOSTS[1])
            )

        logger.info(
            "Attach label %s to networks %s and %s", conf.LABEL_NAME[4][0],
            conf.NETS[4][0], conf.NETS[4][1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[4][0],
            networks=[conf.NETS[4][0], conf.NETS[4][1]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to networks %s and %s" %
                (
                    conf.LABEL_NAME[4][0], conf.NETS[4][0], conf.NETS[4][1]

                )
            )

    @polarion("RHEVM3-4107")
    def test_label_several_networks(self):
        """
        1) Put label on Host NIC of one Host
        2) Put label on bond of the second Host
        4) Check that both networks are attached to both Host (appropriate
        interfaces)
        """
        vlan_bond = ul_network.vlan_int_name(self.bond, conf.VLAN_IDS[2])
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[2]
        )
        logger.info(
            "Attach label %s to Host NIC %s and Bond %s on both Hosts "
            "appropriately", conf.LABEL_NAME[4][0], conf.HOST0_NICS[1],
            self.bond
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[4][0],
            host_nic_dict={
                conf.HOSTS[1]: [self.bond],
                conf.HOSTS[0]: [conf.HOST0_NICS[1]]
            }
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to interfaces" %
                conf.LABEL_NAME[4][0]
            )

        logger.info(
            "Check that network %s and %s are attached to interface %s on Host"
            " %s and to Bond on Host %s", conf.NETS[4][0],
            conf.NETS[4][1], conf.HOST0_NICS[1], conf.HOSTS[0],
            conf.HOSTS[1]
        )
        if not (
                ll_networks.check_network_on_nic(
                    network=conf.NETS[4][1], host=conf.HOSTS[0], nic=vlan_nic
                ) and
                ll_networks.check_network_on_nic(
                    network=conf.NETS[4][1], host=conf.HOSTS[1], nic=vlan_bond
                )
        ):
            raise conf.NET_EXCEPTION(
                "VLAN Network %s is not attached to NIC %s or Bond %s " %
                (conf.NETS[4][1], conf.HOST0_NICS[1], self.bond)
            )

        if not (
                ll_networks.check_network_on_nic(
                    network=conf.NETS[4][0], host=conf.HOSTS[0],
                    nic=conf.HOST0_NICS[1]
                ) and
                ll_networks.check_network_on_nic(
                    network=conf.NETS[4][0], host=conf.HOSTS[1], nic=self.bond)
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s or Bond %s " %
                (conf.NETS[4][0], conf.HOST0_NICS[1], self.bond)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[1]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels04, cls).teardown_class()


@attr(tier=2)
class NetLabels05(TestLabelTestCaseBase):

    """
    Check that you can remove network from Host NIC on 2 Hosts by un-labeling
    that Network
    """
    __test__ = True
    bond = "bond05"

    @classmethod
    def setup_class(cls):
        """
        1) Attach label to the VLAN network
        2) Attach label to Host Nic eth1 on both Hosts
        3) Check that network is attached to Host
        """
        logger.info(
            "Attach label %s to VLAN network %s on interfaces %s and %s of "
            "both Hosts appropriately", conf.LABEL_NAME[5][0],
            conf.NETS[5][0], conf.HOST0_NICS[1], conf.HOST1_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[5][0],
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[1]],
                conf.HOSTS[1]: [conf.HOST1_NICS[1]]
            },
            networks=[conf.NETS[5][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to VLAN network %s or to Host NIC %s"
                " and %s on both Hosts appropriately" % (
                    conf.LABEL_NAME[5][0], conf.NETS[5][0],
                    conf.HOST0_NICS[1], conf.HOST1_NICS[1]
                )
            )

        for idx, host in enumerate(conf.HOSTS[:2]):
            vlan_nic = ul_network.vlan_int_name(
                conf.VDS_HOSTS[idx].nics[1], conf.VLAN_IDS[3]
            )
            logger.info(
                "Check that the network %s is attached to Host %s before "
                "un-labeling ", conf.NETS[5][0], host
            )
            if not ll_networks.check_network_on_nic(
                network=conf.NETS[5][0], host=host, nic=vlan_nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to the first NIC on host %s" %
                    (conf.NETS[5][0], host)
                )

    @polarion("RHEVM3-4127")
    def test_unlabel_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from eth1 on both Hosts
        """
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[3]
        )
        logger.info(
            "Remove label %s from the network %s attached to %s and %s on "
            "both Hosts appropriately", conf.LABEL_NAME[5][0],
            conf.NETS[5][0], conf.HOST0_NICS[1], conf.HOST1_NICS[1]
        )
        if not ll_networks.remove_label(
            networks=[conf.NETS[5][0]],
            labels=[conf.LABEL_NAME[5][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from network %s " %
                (conf.LABEL_NAME[5][0], conf.NETS[5][0])
            )

        for host in conf.HOSTS[:2]:
            logger.info(
                "Check that the network %s is not attached to Host %s",
                conf.NETS[5][0], host
            )
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=ll_networks.check_network_on_nic,
                network=conf.NETS[5][0], host=host, nic=vlan_nic
            )

            if not sample.waitForFuncStatus(result=False):
                raise conf.NET_EXCEPTION(
                    "Network %s is attached to first NIC on host %s but "
                    "shouldn't " % (conf.NETS[5][0], host)
                )


@attr(tier=2)
class NetLabels06(TestLabelTestCaseBase):

    """
    Check that you can break bond which has network attached to it by
    Un-Labeling
    """
    __test__ = True
    bond = "bond06"

    @classmethod
    def setup_class(cls):
        """
        1) Create bond from eth2 and eth3 on 2 Hosts
        2) Create and attach label to the network
        3) Attach label to Bond on both Hosts
        4) Make sure the network was attached to Bond on both Hosts
        """
        logger.info(
            "Create bond %s on second host %s", cls.bond, conf.HOSTS[1]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond
                }
            }
        }
        for i in range(2):
            if not hl_host_network.setup_networks(
                conf.HOSTS[i], **network_host_api_dict
            ):
                raise conf.NET_EXCEPTION(
                    "Cannot create bond %s on the Host %s" %
                    (cls.bond, conf.HOSTS[i])
                )
        logger.info(
            "Attach label %s to network %s on Bonds %s of both Hosts",
            conf.LABEL_NAME[6][0], conf.NETS[6][0], cls.bond
        )

        if not ll_networks.add_label(
            label=conf.LABEL_NAME[6][0],
            host_nic_dict={
                conf.HOSTS[0]: [cls.bond],
                conf.HOSTS[1]: [cls.bond]
            },
            networks=[conf.NETS[6][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s or to Host Bond %s on"
                " both Hosts" % (
                    conf.LABEL_NAME[6][0], conf.NETS[6][0], cls.bond
                )
            )

        logger.info(
            "Check network %s is attached to Bond on both Hosts",
            conf.NETS[6][0]
        )
        for host in conf.HOSTS[:2]:
            logger.info(
                "Check that the network %s is attached to Hosts %s bond ",
                conf.NETS[6][0], host
            )
            if not ll_networks.check_network_on_nic(
                network=conf.NETS[6][0], host=host, nic=cls.bond
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s was not attached to Bond %s on host %s " %
                    (conf.NETS[6][0], cls.bond, host)
                )

    @polarion("RHEVM3-4122")
    def test_break_labeled_bond(self):
        """
        1) Break Bond on both Hosts
        2) Make sure that the bond slave interfaces don't have label
        confured
        """

        logger.info("Break bond on both Hosts")
        for host_name in conf.HOSTS[:2]:
            if not hl_host_network.clean_host_interfaces(
                host_name=host_name
            ):
                raise conf.NET_EXCEPTION()

        logger.info(
            "Check that the label %s doesn't appear on slaves of both Hosts"
        )
        if ll_networks.get_label_objects(host_nic_dict={
            conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]],
            conf.HOSTS[1]: [conf.HOST1_NICS[2], conf.HOST1_NICS[3]]
        }):
            raise conf.NET_EXCEPTION("Label exists on Bond slaves")


@attr(tier=2)
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
        1) Create and attach label to the VLAN non-VM network
        2) Attach the same label to Host Nic eth1 on one Host
        3) Check that the network is attached to the Host NIC
        """
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[4]
        )
        logger.info(
            "Attach label %s to non-VM VLAN network %s and NIC %s ",
            conf.LABEL_NAME[7][0], conf.NETS[7][0],
            conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[7][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]},
            networks=[conf.NETS[7][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to non-VM VLAN network %s or to "
                "Host NIC %s " % (
                    conf.LABEL_NAME[7][0], conf.NETS[7][0], conf.HOST0_NICS[1]
                )
            )

        logger.info(
            "Check that the network %s is attached to Host %s",
            conf.NETS[7][0], conf.HOSTS[0]
        )

        if not ll_networks.check_network_on_nic(
            network=conf.NETS[7][0], host=conf.HOSTS[0], nic=vlan_nic
        ):
            raise conf.NET_EXCEPTION(
                "Network %s was not attached to interface %s on host %s " %
                (
                    conf.NETS[7][0], conf.HOST0_NICS[1],
                    conf.HOSTS[0]
                )
            )

    @polarion("RHEVM3-4130")
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
            "setupNetwork command ",
            conf.NETS[7][0], conf.HOST0_NICS[1]
        )

        if hl_host_network.remove_networks_from_host(
            host_name=conf.HOSTS[0], networks=[conf.NETS[7][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Could remove labeled network %s from Host NIC % s" %
                (conf.NETS[7][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Remove label %s from Host NIC %s", conf.LABEL_NAME[7][0],
            conf.HOST0_NICS[1]
        )
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]},
            labels=[conf.LABEL_NAME[7][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from Host NIC %s" %
                (conf.LABEL_NAME[7][0], conf.HOST0_NICS[1])
            )
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[4]
        )
        logger.info(
            "Check that the network %s is not attached to Host %s",
            conf.NETS[7][0], conf.HOSTS[0]
        )
        if ll_networks.check_network_on_nic(
            network=conf.NETS[7][0], host=conf.HOSTS[0], nic=vlan_nic
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to Host NIC %s on Host %s when "
                "shouldn't" % (
                    conf.NETS[7][0], conf.HOST0_NICS[1],
                    conf.HOSTS[0]
                )
            )

        logger.info(
            "Create a network %s and attach it to the Host with "
            "setupNetwork action", conf.NETS[7][1]
        )
        vlan_nic1 = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[5]
        )
        local_dict2 = {
            conf.NETS[7][1]: {
                "vlan_id": conf.VLAN_IDS[5], "nic": 1, "required": "false",
                "usages": ""
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME[0], cluster=conf.CLUSTER_NAME[0],
            host=conf.VDS_HOSTS[0], network_dict=local_dict2,
            auto_nics=[0, 1]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create non-VM VLAN network %s on DC, Cluster and Host"
                % conf.NETS[7][1]
            )
        logger.info(
            "Check that the network %s is attached to Host %s",
            conf.NETS[7][1], conf.HOSTS[0]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[7][1], host=conf.HOSTS[0], nic=vlan_nic1
        ):
            raise conf.NET_EXCEPTION(
                "Network %s was not attached to interface %s on host %s " %
                (
                    conf.NETS[7][1], conf.HOST0_NICS[1],
                    conf.HOSTS[0]
                )
            )


@attr(tier=2)
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

        local_dict1 = {conf.NETS[8][0]: {"required": "false"}}
        logger.info("Create network %s on DC only ", conf.NETS[8][0])
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME[0], network_dict=local_dict1
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create network on DC only"
            )

    @polarion("RHEVM3-4113")
    def test_network_on_host(self):
        """
        1) Attach label to the network
        2) Attach label to Host Nic eth1 on Host
        3) Check the network with the same label as Host NIC is not attached to
        Host when it is not attached to the Cluster
        """
        logger.info(
            "Attach label %s to network %s ", conf.LABEL_NAME[8][0],
            conf.NETS[8][0]
        )

        if not ll_networks.add_label(
            label=conf.LABEL_NAME[8][0], networks=[conf.NETS[8][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s " %
                (conf.LABEL_NAME[8][0], conf.NETS[8][0])
            )

        logger.info(
            "Attach the same label %s to Host NIC %s ",
            conf.LABEL_NAME[8][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[8][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to Host interface %s on Host %s " %
                (
                    conf.LABEL_NAME[8][0], conf.HOST0_NICS[1],
                    conf.HOSTS[0]
                )
            )
        logger.info(
            "Check that the network %s in not attached to Host NIC %s ",
            conf.NETS[8][0], conf.HOST0_NICS[1]
        )
        if ll_networks.check_network_on_nic(
            network=conf.NETS[8][0], host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s was attached to interface %s on host %s but "
                "shouldn't" % (
                    conf.NETS[8][0], conf.HOST0_NICS[1],
                    conf.HOSTS[0]
                )
            )


@attr(tier=2)
class NetLabels09(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the VLAN networks appropriately
    """
    __test__ = True
    bond = "bond09"

    @classmethod
    def setup_class(cls):
        """
        1) Attach 2 labels to that networks
        2) Attach label_1 to Host Nic eth2
        3) Attach label_2 to Host NIC eth3
        4) Check network_1 is attached to first interface  and network_2 to
        the second interface
        """

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            conf.LABEL_NAME[9][0], conf.NETS[9][0],
            conf.LABEL_NAME[9][1], conf.NETS[9][1]
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[9][i],
                networks=[conf.NETS[9][i]]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to network %s " %
                    (conf.LABEL_NAME[9][i], conf.NETS[9][i])
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            conf.LABEL_NAME[9][0], conf.HOST0_NICS[2],
            conf.LABEL_NAME[9][1], conf.HOST0_NICS[3]
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[9][i],
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[i + 2]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to Host interface %s " %
                    (conf.LABEL_NAME[9][i], conf.HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            conf.NETS[9][0], conf.NETS[9][1],
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        for i in range(2):
            vlan_nic = ul_network.vlan_int_name(
                conf.HOST0_NICS[i + 2], conf.VLAN_IDS[i+6]
            )
            if not ll_networks.check_network_on_nic(
                network=conf.NETS[9][i], host=conf.HOSTS[0], nic=vlan_nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached toHost NIC %s " %
                    (conf.NETS[9][i], conf.HOST0_NICS[i + 2])
                )

    @polarion("RHEVM3-4116")
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info(
            "Unlabel interfaces %s and %s",
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]]
            },
            labels=conf.LABEL_NAME[9][:2]
        ):

            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from Host NICs %s and %s" %
                (
                    conf.LABEL_NAME[9][0], conf.HOST0_NICS[2],
                    conf.HOST0_NICS[3]
                )
            )

        logger.info(
            "Create bond %s on host %s", self.bond, conf.HOSTS[0]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": self.bond,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create Bond %s " % self.bond
            )

        logger.info(
            "Attach labels %s and %s to Host Bond %s",
            conf.LABEL_NAME[9][0], conf.LABEL_NAME[9][1], self.bond
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[9][i],
                host_nic_dict={conf.HOSTS[0]: [self.bond]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to Host Bond %s " %
                    (conf.LABEL_NAME[9][i], self.bond)
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host Bond %s ",
            conf.NETS[9][0], conf.NETS[9][1], self.bond
        )
        for i in range(2):
            vlan_bond = ul_network.vlan_int_name(
                self.bond, conf.VLAN_IDS[i+6]
            )
            if not ll_networks.check_network_on_nic(
                network=conf.NETS[9][i], host=conf.HOSTS[0], nic=vlan_bond
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to Bond %s " %
                    (conf.NETS[9][i], self.bond)
                )

        logger.info(
            "Check that label doesn't reside on Bond slaves %s and %s after "
            "Bond creation", conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        if ll_networks.get_label_objects(
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]]
            }
        ):
            raise conf.NET_EXCEPTION("Label exists on Bond slaves ")

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels09, cls).teardown_class()


@attr(tier=2)
class NetLabels10(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to two
    VM non-VLAN network appropriately and fail
    """
    __test__ = True
    bond = "bond10"

    @classmethod
    def setup_class(cls):
        """
        1) Attach 2 different labels to the networks
        """

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            conf.LABEL_NAME[10][0], conf.NETS[10][0],
            conf.LABEL_NAME[10][1], conf.NETS[10][1]
        )
        for i, net in enumerate([conf.NETS[10][0], conf.NETS[10][1]]):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[10][i], networks=[net]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to network %s " %
                    (conf.LABEL_NAME[10][i], net)
                )

    @polarion("RHEVM3-4101")
    def test_create_bond(self):
        """
        1) Create bond from labeled interfaces
        2) Check that both networks reside on appropriate interfaces
        """
        logger.info(
            "Create bond %s on host %s", self.bond, conf.HOSTS[0]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": self.bond,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't create Bond %s " % self.bond)

        logger.info(
            "Negative: Attach label %s and %s to Host Bond %s ",
            conf.LABEL_NAME[10][0], conf.LABEL_NAME[10][1], self.bond
        )
        if (
                ll_networks.add_label(
                    label=conf.LABEL_NAME[10][0], host_nic_dict={
                        conf.HOSTS[0]: [self.bond]
                    }
                ) and
                ll_networks.add_label(
                    label=conf.LABEL_NAME[10][1], host_nic_dict={
                        conf.HOSTS[0]: [self.bond]
                    }
                )
        ):
            raise conf.NET_EXCEPTION(
                "Could attach labels to Host Bond %s " % self.bond
            )

        logger.info(
            "Check that the networks %s is attached to Host Bond %s ",
            conf.NETS[10][0], self.bond
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[10][0], host=conf.HOSTS[0], nic=self.bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Host NIC %s " %
                (conf.NETS[10][0], self.bond)
            )

        logger.info(
            "Check that the networks %s is not attached to Host Bond %s ",
            conf.NETS[10][1], self.bond
        )

        if ll_networks.check_network_on_nic(
            network=conf.NETS[10][1], host=conf.HOSTS[0], nic=self.bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to Host NIC %s " %
                (conf.NETS[10][1], self.bond)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels10, cls).teardown_class()


@attr(tier=2)
class NetLabels11(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the VM non-VLAN  network and non-VM network appropriately and fail
    """
    __test__ = True
    bond = "bond11"

    @classmethod
    def setup_class(cls):
        """
        1) Attach 2 different labels to the networks
        2) Attach one of those labels to Host Nic eth2
        3) Attach another label to Host NIC eth3
        4) Check network_1 is attached to eth2 and network_2 to eth3
        """

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            conf.LABEL_NAME[11][0], conf.NETS[11][0],
            conf.LABEL_NAME[11][1], conf.NETS[11][1]
        )
        for i, net in enumerate([conf.NETS[11][0], conf.NETS[11][1]]):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[11][i], networks=[net]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to network %s " %
                    (conf.LABEL_NAME[11][i], net)
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            conf.LABEL_NAME[11][0], conf.HOST0_NICS[2],
            conf.LABEL_NAME[11][1], conf.HOST0_NICS[3]
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[11][i],
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[i + 2]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to Host interface %s " %
                    (conf.LABEL_NAME[11][i], conf.HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            conf.NETS[11][0], conf.NETS[11][1],
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        for nic, network in (
            (conf.HOST0_NICS[2], conf.NETS[11][0]),
            (conf.HOST0_NICS[3], conf.NETS[11][1])
        ):
            if not ll_networks.check_network_on_nic(
                network=network, host=conf.HOSTS[0], nic=nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to Host NIC %s " %
                    (network, nic)
                )

    @polarion("RHEVM3-4102")
    def test_create_bond(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """
        logger.info(
            "Unlabel interfaces %s and %s",
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]]
            },
            labels=conf.LABEL_NAME[11][:2]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from Host NICs %s and %s" %
                (
                    conf.LABEL_NAME[11][0], conf.HOST0_NICS[2],
                    conf.HOST0_NICS[3]
                )
            )
        logger.info(
            "Create bond %s on host %s", self.bond, conf.HOSTS[0]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": self.bond,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't create Bond %s " % self.bond)

        logger.info(
            "Negative: Attach label %s and %s  to Host Bond %s ",
            conf.LABEL_NAME[11][0], conf.LABEL_NAME[11][1], self.bond
        )
        if (
                ll_networks.add_label(
                    label=conf.LABEL_NAME[11][0], host_nic_dict={
                        conf.HOSTS[0]: [self.bond]
                    }
                ) and
                ll_networks.add_label(
                    label=conf.LABEL_NAME[11][1], host_nic_dict={
                        conf.HOSTS[0]: [self.bond]
                    }
                )
        ):
            raise conf.NET_EXCEPTION(
                "Could attach labels to Host Bond %s " % self.bond
            )

        logger.info(
            "Check that the networks %s is attached to Host Bond %s ",
            conf.NETS[11][0], self.bond
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[11][0], host=conf.HOSTS[0], nic=self.bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Host NIC %s " %
                (conf.NETS[11][0], self.bond)
            )

        logger.info(
            "Check that the networks %s is not attached to Host Bond %s ",
            conf.NETS[11][1], self.bond
        )
        if ll_networks.check_network_on_nic(
            network=conf.NETS[11][1], host=conf.HOSTS[0], nic=self.bond
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to Host NIC %s " %
                (conf.NETS[11][1], self.bond)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels11, cls).teardown_class()


@attr(tier=2)
class NetLabels12(TestLabelTestCaseBase):

    """
    Create bond from labeled interfaces when those labels are attached to
    the non-VM and VLAN networks appropriately
    """
    __test__ = True
    bond = "bond12"

    @classmethod
    def setup_class(cls):
        """
        1) Attach 2 labels to the networks
        2) Attach label_1 to Host Nic eth2
        3) Attach label_2 to Host NIC eth3
        4) Check network_1 is attached to eth2 and network_2 to eth3
        """

        logger.info(
            "Attach label %s to network %s and label %s to network %s ",
            conf.LABEL_NAME[12][0], conf.NETS[12][0],
            conf.LABEL_NAME[12][1], conf.NETS[12][1]
        )
        for i, net in enumerate([conf.NETS[12][0], conf.NETS[12][1]]):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[12][i], networks=[net]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to network %s " %
                    (conf.LABEL_NAME[12][i], net)
                )

        logger.info(
            "Attach label %s to Host NIC %s and label %s to Host NIC %s ",
            conf.LABEL_NAME[12][0], conf.HOST0_NICS[2],
            conf.LABEL_NAME[12][1], conf.HOST0_NICS[3]
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[12][i],
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[i + 2]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to Host interface %s " %
                    (conf.LABEL_NAME[12][i], conf.HOST0_NICS[i + 2])
                )

        logger.info(
            "Check that the networks %s and %s  are attached to Host "
            "interfaces %s and %s appropriately",
            conf.NETS[12][0], conf.NETS[12][1],
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[3], conf.VLAN_IDS[8]
        )
        for nic, network in (
            (conf.HOST0_NICS[2], conf.NETS[12][0]),
            (vlan_nic, conf.NETS[12][1])
        ):
            if not ll_networks.check_network_on_nic(
                network=network, host=conf.HOSTS[0], nic=nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to Host NIC %s " %
                    (network, nic)
                )

    @polarion("RHEVM3-4100")
    def test_create_bond(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) All labels to the bond interface
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """
        logger.info(
            "Unlabel interfaces %s and %s",
            conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]]
            },
            labels=conf.LABEL_NAME[12][:2]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove labels from Host NICs %s and %s" %
                (conf.HOST0_NICS[2], conf.HOST0_NICS[3])
            )

        logger.info(
            "Create bond %s on host %s", self.bond, conf.HOSTS[0]
        )
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": self.bond,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't create Bond %s " % self.bond)

        logger.info(
            "Attach labels %s and %s to Host Bond %s",
            conf.LABEL_NAME[12][0], conf.LABEL_NAME[12][1], self.bond
        )
        for i in range(2):
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[12][i],
                host_nic_dict={conf.HOSTS[0]: [self.bond]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to Host Bond %s " %
                    (conf.LABEL_NAME[12][i], self.bond)
                )

        logger.info(
            "Check that the networks %s and %s are attached to Host Bond %s ",
            conf.NETS[12][0], conf.NETS[12][1], self.bond
        )

        vlan_bond = ul_network.vlan_int_name(self.bond, conf.VLAN_IDS[8])
        for (net, nic) in (
            (conf.NETS[12][0], self.bond),
            (conf.NETS[12][1], vlan_bond)
        ):
            if not ll_networks.check_network_on_nic(
                network=net, host=conf.HOSTS[0], nic=nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to Bond %s " %
                    (net, self.bond)
                )

        logger.info(
            "Check that label doesn't reside on Bond slaves %s and %s after "
            "Bond creation", conf.HOST0_NICS[2], conf.HOST0_NICS[3]
        )
        if ll_networks.get_label_objects(
            host_nic_dict={
                conf.HOSTS[0]: [conf.HOST0_NICS[2], conf.HOST0_NICS[3]]
            }
        ):
            raise conf.NET_EXCEPTION("Label exists on Bond slaves ")

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels12, cls).teardown_class()


@attr(tier=2)
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
        1) Create and attach label to the network
        2) Attach label to Host Nic - eth1
        3) Check that the network is attached to the interface (eth1)
        """

        logger.info(
            "Attach label %s to network %s ", conf.LABEL_NAME[12][0],
            conf.NETS[13][0]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[13][0], networks=[conf.NETS[13][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s" %
                (conf.LABEL_NAME[13][0], conf.NETS[13][0])
            )

        logger.info(
            "Attach the label %s to Host NIC %s",
            conf.LABEL_NAME[13][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[13][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to Host NIC %s" %
                (conf.LABEL_NAME[13][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            conf.NETS[13][0], conf.HOST0_NICS[1]
        )

        if not ll_networks.check_network_on_nic(
            network=conf.NETS[13][0], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to Host NIC %s " %
                (conf.NETS[13][0], conf.HOST0_NICS[1])
            )

    @polarion("RHEVM3-4129")
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
            conf.NETS[13][0], conf.CLUSTER_NAME[0]
        )
        if not ll_networks.removeNetworkFromCluster(
            True, conf.NETS[13][0], conf.CLUSTER_NAME[0]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove network %s from Cluster %s " %
                (conf.NETS[13][0], conf.CLUSTER_NAME[0])
            )

        logger.info(
            "Check that the network %s is not attached to Host NIC %s",
            conf.NETS[13][0], conf.HOST0_NICS[1]
        )
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic, network=conf.NETS[13][0],
            host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        )

        if not sample.waitForFuncStatus(result=False):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to NIC %s "
                % (conf.NETS[13][0], conf.HOST0_NICS[1])
            )
        logger.info(
            "Check that the network %s is not attached to the Cluster%s",
            conf.NETS[13][0], conf.CLUSTER_NAME[0]
        )
        try:
            ll_networks.get_cluster_network(
                conf.CLUSTER_NAME[0], conf.NETS[13][0]
            )
            raise conf.NET_EXCEPTION(
                "Network %s is attached to Cluster %s but shouldn't " %
                (conf.NETS[13][0], conf.CLUSTER_NAME[0])
            )
        except apis_exceptions.EntityNotFound:
            logger.info("Network not found on the Cluster as expected")

        logger.info(
            "Reattach labeled network %s to Cluster %s ",
            conf.NETS[13][0], conf.CLUSTER_NAME[0]
        )
        if not ll_networks.addNetworkToCluster(
            True, conf.NETS[13][0], conf.CLUSTER_NAME[0], required=False
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't reattach network %s to Cluster %s " %
                (conf.NETS[13][0], conf.CLUSTER_NAME[0])
            )

        logger.info(
            "Check that the network %s is reattached to Host NIC %s",
            conf.NETS[13][0], conf.HOST0_NICS[1]
        )
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic, network=conf.NETS[13][0],
            host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        )

        if not sample.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s "
                % (conf.NETS[13][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Remove labeled network %s from DataCenter %s",
            conf.NETS[13][0], conf.DC_NAME[0]
        )
        if not ll_networks.removeNetwork(
            True, conf.NETS[13][0], conf.DC_NAME[0]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove network %s from DC %s " %
                (conf.NETS[13][0], conf.DC_NAME[0])
            )

        logger.info(
            "Check that the network %s is not attached to Host NIC %s and not "
            "attached to DC %s", conf.NETS[13][0], conf.HOST0_NICS[1],
            conf.DC_NAME[0]
        )
        try:
            ll_networks.findNetwork(conf.NETS[13][0], conf.DC_NAME[0])
            raise conf.NET_EXCEPTION(
                "Network %s found on DC, but shouldn't" % conf.NETS[13][0]
            )
        except apis_exceptions.EntityNotFound:
            logger.info("Network not found on DC as expected")

        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic, network=conf.NETS[13][0],
            host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        )

        if not sample.waitForFuncStatus(result=False):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to NIC %s, but shouldn't "
                % (conf.NETS[13][0], conf.HOST0_NICS[1])
            )


@attr(tier=2)
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
            conf.LABEL_NAME[14][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[14][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to Host NIC %s" %
                (conf.LABEL_NAME[14][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Create new DC and Cluster in the setup of the current version"
        )
        if not (
                ll_datacenters.addDataCenter(
                    positive=True, name=cls.dc_name2,
                    storage_type=conf.STORAGE_TYPE,
                    version=conf.COMP_VERSION, local=False
                ) and
                ll_clusters.addCluster(
                    positive=True, name=cls.cl_name2,
                    data_center=cls.dc_name2,
                    version=conf.COMP_VERSION,
                    cpu=conf.CPU_NAME
                )
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add a new DC and Cluster to the setup"
            )

        logger.info(
            "Create network %s on new DC and Cluster", conf.NETS[14][0]
        )
        local_dict = {conf.NETS[14][0]: {"required": "false"}}
        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict, dc=cls.dc_name2, cluster=cls.cl_name2
        )

        logger.info(
            "Create new DC and Cluster in the setup of the 3.0 version"
        )
        if not (
                ll_datacenters.addDataCenter(
                    positive=True, name=cls.uncomp_dc,
                    storage_type=conf.STORAGE_TYPE,
                    version=conf.VERSION[0], local=False
                ) and
                ll_clusters.addCluster(
                    positive=True, name=cls.uncomp_cl,
                    data_center=cls.uncomp_dc,
                    version=conf.VERSION[0],
                    cpu=cls.uncomp_cpu
                )
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add a DC and Cluster of %s version to the setup" %
                conf.VERSION[0]
            )

    @polarion("RHEVM3-4126")
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
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Attach the Host to the new DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION("Cannot move host to another DC")

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

        logger.info(
            "Attach label %s to network %s ", conf.LABEL_NAME[14][0],
            conf.NETS[14][0]
        )

        if not ll_networks.add_label(
            label=conf.LABEL_NAME[14][0], networks=[conf.NETS[14][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s" %
                (conf.LABEL_NAME[14][0], conf.NETS[14][0])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            conf.NETS[14][0], conf.HOST0_NICS[1]
        )
        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic, network=conf.NETS[14][0],
            host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
        )
        if not sample.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s " %
                (conf.NETS[14][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Remove label %s from network %s ", conf.LABEL_NAME[14][0],
            conf.NETS[14][0]
        )
        if not ll_networks.remove_label(
            labels=conf.LABEL_NAME[14][0], networks=[conf.NETS[14][0]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't remove label %s from network %s " %
                (conf.LABEL_NAME[14][0], conf.NETS[14][0])
            )

        logger.info(
            "Deactivate host, move it back to the original DC %s and "
            "reactivate it", conf.DC_NAME[0]
        )
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Attach Host to original DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=conf.CLUSTER_NAME[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host to the original DC"
            )

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

    @polarion("RHEVM3-4115")
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
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Negative: Try to attach Host to another DC/Cluster")
        if not ll_hosts.updateHost(
            False, host=conf.HOSTS[0], cluster=self.uncomp_cl
        ):
            raise conf.NET_EXCEPTION(
                "Could move host to another DC/Cluster when shouldn't"
            )

        logger.info("Move host to the original DC and Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=conf.CLUSTER_NAME[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host to original DC and Cluster"
            )

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

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
            if not ll_datacenters.removeDataCenter(
                positive=True, datacenter=dc
            ):
                logger.error("Failed to remove datacenter %s", dc)
            if not ll_clusters.removeCluster(positive=True, cluster=cl):
                logger.error("Failed to remove cluster %s ", cl)
        super(NetLabels14, cls).teardown_class()


@attr(tier=2)
@unittest_lib.common.skip_class_if(conf.PPC_ARCH, conf.PPC_SKIP_MESSAGE)
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
            1, len(conf.VERSION)
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
            conf.LABEL_NAME[15][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[15][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to Host NIC %s" %
                (conf.LABEL_NAME[15][0], conf.HOST0_NICS[1])
            )

        logger.info(
            "Create new DC %s with 3.1 version in the setup ", cls.dc_name2
        )
        if not ll_datacenters.addDataCenter(
            positive=True, name=cls.dc_name2, storage_type=conf.STORAGE_TYPE,
            version=conf.VERSION[1], local=False
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add a new DC %s to the setup" % cls.dc_name2
            )

        logger.info(
            "Create Clusters with all supported version for labeling for DC "
            "%s ", cls.dc_name2
        )
        for ver, cluster in zip(conf.VERSION[1:], cls.comp_cl_name):
            if not ll_clusters.addCluster(
                positive=True, name=cluster, data_center=cls.dc_name2,
                version=ver, cpu=conf.CPU_NAME
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't add a new Cluster %s with version %s to the "
                    "setup" % (cluster, ver)
                )

        logger.info("Create networks for all the Clusters of the new DC")
        for index, cluster in enumerate(cls.comp_cl_name):
            local_dict = {conf.NETS[15][index]: {"required": "false"}}
            networking_helper.prepare_networks_on_setup(
                networks_dict=local_dict, dc=cls.dc_name2,
                cluster=cluster
            )

    @polarion("RHEVM3-4124")
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
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        for index, cluster in enumerate(self.comp_cl_name):
            logger.info("Move Host to the Cluster %s ", cluster)
            if not ll_hosts.updateHost(
                True, host=conf.HOSTS[0], cluster=cluster
            ):
                raise conf.NET_EXCEPTION(
                    "Cannot move host to cluster %s" % cluster
                )
            sleep_timeout = conf.TIMEOUT / 2
            logger.info(
                "Sleep for %s. after moving host to new cluster "
                "setupNetworks is called and we need to wait untill "
                "it's done", sleep_timeout
            )
            time.sleep(sleep_timeout)
            if index is not 0:
                logger.info(
                    "Check network %s doesn't reside on Host in Cluster %s",
                    conf.NETS[15][index], cluster
                )
                sample = apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                    func=ll_networks.check_network_on_nic,
                    network=conf.NETS[15][index],
                    host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
                )

                if not sample.waitForFuncStatus(result=False):
                    raise conf.NET_EXCEPTION(
                        "Network %s is not attached to NIC %s" %
                        (conf.NETS[15][index - 1], conf.HOST0_NICS[1])
                    )

            logger.info(
                "Add label to network %s in Cluster %s",
                conf.NETS[15][index], cluster
            )
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[15][0], networks=[conf.NETS[15][index]]
            ):
                raise conf.NET_EXCEPTION(
                    "Cannot add label to network %s" % conf.NETS[15][index]
                )

            logger.info(
                "Check network %s resides on Host in Cluster %s",
                conf.NETS[15][index], cluster
            )
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=ll_networks.check_network_on_nic,
                network=conf.NETS[15][index],
                host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
            )

            if not sample.waitForFuncStatus(result=True):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to NIC %s " %
                    (conf.NETS[15][index], conf.HOST0_NICS[1])
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
            "reactivate it", conf.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        if not hl_host.deactivate_host_if_up(conf.HOSTS[0]):
            logger.error("Couldn't deactivate Host %s", conf.HOSTS[0])

        logger.info("Attach host to original DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=conf.CLUSTER_NAME[0]
        ):
            logger.error("Cannot move host to original Cluster")

        logger.info("Activate Host")
        if not ll_hosts.activateHost(True, host=conf.HOSTS[0]):
            logger.error("Couldn't activate host %s", conf.HOSTS[0])

        logger.info("Removing the DC %s with all its Clusters", cls.dc_name2)
        for cl in cls.comp_cl_name:
            if not ll_clusters.removeCluster(positive=True, cluster=cl):
                logger.error("Failed to remove cluster %s", cl)
        if not ll_datacenters.removeDataCenter(
            positive=True, datacenter=cls.dc_name2
        ):
            logger.error("Failed to remove datacenter %s", cls.dc_name2)
        super(NetLabels15, cls).teardown_class()


@attr(tier=2)
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
            "Attach label %s to network %s and Host NIC %s",
            conf.LABEL_NAME[16][0], conf.NETS[16][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[16][0], networks=[conf.NETS[16][0]],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s and Host NIC %s " %
                (
                    conf.LABEL_NAME[16][0], conf.NETS[16][0],
                    conf.HOST0_NICS[1]
                )
            )

        logger.info(
            "Create a new Cluster in the setup for the current version"
        )
        if not ll_clusters.addCluster(
            positive=True, name=cls.cl_name2, data_center=conf.DC_NAME[0],
            version=conf.COMP_VERSION, cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add a new Cluster to the setup"
            )

        logger.info("Create network %s on new Cluster", conf.NETS[16][1])
        local_dict = {conf.NETS[16][1]: {"usages": "", "required": "false"}}
        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict, dc=conf.DC_NAME[0],
            cluster=cls.cl_name2
        )

        logger.info(
            "Attach the same label %s to non-VM network %s as in original "
            "Cluster ", conf.LABEL_NAME[16][0], conf.NETS[16][1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[16][0], networks=[conf.NETS[16][1]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s" %
                (conf.LABEL_NAME[16][0], conf.NETS[16][1])
            )

        logger.info(
            "Check that the network %s is attached to Host NIC %s",
            conf.NETS[16][0], conf.HOST0_NICS[1]
        )

        if not ll_networks.check_network_on_nic(
            network=conf.NETS[16][0], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "VM Network %s is not attached to Host NIC %s " %
                (conf.NETS[16][0], conf.HOST0_NICS[1])
            )

    @polarion("RHEVM3-4108")
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
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Attach host to another DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host to another Cluster %s" % self.cl_name2
            )

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

        logger.info(
            "Check that the non-VM network %s is attached to Host NIC %s",
            conf.NETS[16][1], conf.HOST0_NICS[1]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[16][1], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "non-VM Network %s is not attached to Host NIC %s " %
                (conf.NETS[16][1], conf.HOST0_NICS[1])
            )

        logger.info(
            "Deactivate host again, move it to the original Cluster %s and "
            "reactivate it", conf.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Attach Host to original DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=conf.CLUSTER_NAME[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host to the original Cluster %s" %
                conf.CLUSTER_NAME[0]
            )

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

        logger.info(
            "Check that the VM network %s is attached to Host NIC %s",
            conf.NETS[16][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[16][0], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "VM Network %s is not attached to Host NIC %s " %
                (conf.NETS[16][0], conf.HOST0_NICS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove newly created Cluster from the setup.
        """
        logger.info(
            "Removing newly created cluster %s from the setup", cls.cl_name2
        )
        if not ll_clusters.removeCluster(positive=True, cluster=cls.cl_name2):
            logger.error("Failed to remove cluster %s ", cls.cl_name2)
        super(NetLabels16, cls).teardown_class()


@attr(tier=2)
class NetLabels17(TestLabelTestCaseBase):

    """
    Negative test cases:
    1) Check it is not possible to have 2 bridged networks on the same host
    interface
    2) Check it is not possible to have 2 bridgeless networks on the same
    host interface
    3) Check it is not possible to have bridged + bridgeless network on the
    same host interface
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Add label1 to the sw1 and sw2 VM networks
        2) Add label2 to the sw3 and sw4 non-VM networks
        3) Add label3 to sw5 and sw6 VM and non-VM networks
        """

        for i in range(0, 6, 2):
            logger.info(
                "Attach label %s to networks %s and %s",
                conf.LABEL_NAME[17][i], conf.NETS[17][i],
                conf.NETS[i + 1]
            )
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[17][i],
                networks=conf.NETS[17][i:i + 2]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to networks" %
                    conf.LABEL_NAME[17][i]
                )

    @polarion("RHEVM3-4121")
    def test_label_restrictioin(self):
        """
        1) Put label1 on Host NIC of the Host
        2) Check that the networks sw1 and sw2 are not attached to the Host
        3) Replace label1 with label2 on Host NIC of the Host
        4) Check that the networks sw3 and sw4 are not attached to the Host
        5) Replace label2 with label3 on Host NIC of the Host
        6) Check that the networks sw5 and sw6 are not attached to the Host
        7) Replace label3 with label4 on Host NIC of the Host
        """
        for i in range(0, 6, 2):
            logger.info(
                "Attach label %s to Host NIC %s ",
                conf.LABEL_NAME[17][i], conf.HOST0_NICS[1]
            )
            if ll_networks.add_label(
                label=conf.LABEL_NAME[17][i],
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Could attach label %s to interface %s" %
                    (conf.LABEL_NAME[17][i], conf.HOST0_NICS[1])
                )

            logger.info(
                "Check that network %s and %s are not attached to interface ",
                conf.NETS[17][i], conf.NETS[17][i + 1]
            )
            for net in (conf.NETS[17][i], conf.NETS[17][i + 1]):
                if ll_networks.check_network_on_nic(
                    network=net, host=conf.HOSTS[0], nic=conf.HOST0_NICS[1]
                ):
                    raise conf.NET_EXCEPTION(
                        "Network %s is attached to NIC %s " %
                        (net, conf.HOST0_NICS[1])
                    )

            logger.info("Remove label from Host NIC %s", conf.HOST0_NICS[1])
            if not ll_networks.remove_label(
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't remove label from Host %s int %s" %
                    (conf.HOSTS[0], [conf.HOST0_NICS[1]])
                )


@attr(tier=2)
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
        1) Add label1 to the sw1 VM network
        2) Add label2 to the sw2 non-VM network
        3) Add label1 to the Host NIC on eth1
        4) Add label2 to the Host NIC on eth2
        5) Check that the VM network sw1 is attached to the Host
        """

        for i in range(2):
            logger.info(
                "Attach label %s to network %s and Host NIC %s",
                conf.LABEL_NAME[18][i], conf.NETS[18][i],
                conf.HOST0_NICS[i + 1]
            )
            if not ll_networks.add_label(
                label=conf.LABEL_NAME[18][i], networks=[conf.NETS[18][i]],
                host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[i + 1]]}
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to network %s or Host NIC %s "
                    % (conf.LABEL_NAME[18][i], conf.NETS[18][i],
                       conf.HOST0_NICS[i + 1])
                )

            logger.info(
                "Check that network %s is attached to interface %s ",
                conf.NETS[18][i], conf.HOST0_NICS[i + 1]
            )
            if not ll_networks.check_network_on_nic(
                network=conf.NETS[18][i], host=conf.HOSTS[0],
                nic=conf.HOST0_NICS[i + 1]
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to NIC %s " %
                    (conf.NETS[18][0], conf.HOST0_NICS[1])
                )

    @polarion("RHEVM3-4117")
    def test_label_restrictioin_vm(self):
        """
        1) Put the same label on the sw3 VM network as on network sw1
        2) Check that the new VM network sw3 is not attached to the Host NIC
        3) Check that sw1 is still attached to the Host NIC
        """

        logger.info(
            "Attach the same label %s to networks %s",
            conf.LABEL_NAME[18][0], conf.NETS[18][2]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[18][0], networks=[conf.NETS[18][2]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s" %
                (conf.LABEL_NAME[18][0], conf.NETS[18][2])
            )

        logger.info(
            "Check that network %s is not attached to interface %s ",
            conf.NETS[18][2], conf.HOST0_NICS[1]
        )
        if ll_networks.check_network_on_nic(
            network=conf.NETS[18][2], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to NIC%s " %
                (conf.NETS[18][2], conf.HOST0_NICS[1])
            )

        logger.info(
            "Check that original network %s is still attached to "
            "interface %s ", conf.NETS[18][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[18][0], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s " %
                (conf.NETS[18][0], conf.HOST0_NICS[1])
            )

        @polarion("RHEVM3-4118")
        def test_label_restrictioin_non_vm(self):
            """
        1) Attach the same label on the sw4 VM network as on network sw2
        2) Check that the new non-VM network sw4 is not attached to the Host
        NIC
        3) Check that sw2 is still attached to the Host NIC
        """

        logger.info(
            "Attach the same label %s to networks %s",
            conf.LABEL_NAME[18][1], conf.NETS[18][3])
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[18][1], networks=[conf.NETS[18][3]]
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to network %s" %
                (conf.LABEL_NAME[18][1], conf.NETS[18][3])
            )

        logger.info(
            "Check that network %s is not attached to interface %s ",
            conf.NETS[18][3], conf.HOST0_NICS[2]
        )
        if ll_networks.check_network_on_nic(
            network=conf.NETS[18][3], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[2]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is attached to NIC %s " %
                (conf.NETS[18][3], conf.HOST0_NICS[2])
            )

        logger.info(
            "Check that original network %s is still attached to "
            "interface %s ", conf.NETS[18][1], conf.HOST0_NICS[2]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[18][1], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[2]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC %s " %
                (conf.NETS[18][1], conf.HOST0_NICS[2])
            )


@attr(tier=2)
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
        if not ll_clusters.addCluster(
            positive=True, name=cls.cl_name2, data_center=conf.DC_NAME[0],
            version=conf.COMP_VERSION, cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't add a new Cluster %s to the setup" % cls.cl_name2
            )

        logger.info(
            "Create network %s on new Clusters ", conf.NETS[19][1]
        )
        local_dict2 = {conf.NETS[19][1]: {"required": "false"}}
        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict2, dc=conf.DC_NAME[0],
            cluster=cls.cl_name2
        )

        logger.info(
            "Attach the same label %s to the Host NIC %s and to "
            "networks %s and %s", conf.LABEL_NAME[19][0],
            conf.HOST0_NICS[1], conf.NETS[19][0], conf.NETS[19][1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[19][0], networks=conf.NETS[19][:2],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to networks or Host NIC"
            )

        logger.info(
            "Check that network %s is attached to interface %s ",
            conf.NETS[19][0], conf.HOST0_NICS[1]
        )

        if not ll_networks.check_network_on_nic(
            network=conf.NETS[19][0], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC%s " %
                (conf.NETS[19][0], conf.HOST0_NICS[1])
            )

    @polarion("RHEVM3-4125")
    def test_move_host(self):
        """
        1) Move the Host from the original Cluster to the newly created one
        2) Check that the network sw2 is attached to the Host NIC
        """
        logger.info(
            "Move the Host with labeled interface to the newly created Cluster"
            " %s ", self.cl_name2
        )
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        assert (ll_hosts.deactivateHost(True, host=conf.HOSTS[0]))

        logger.info("Attach Host to the new DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host to the new Cluster"
            )

        logger.info("Activate Host")
        assert (ll_hosts.activateHost(True, host=conf.HOSTS[0]))

        logger.info(
            "Check that different network %s is attached to interface %s ",
            conf.NETS[19][1], conf.HOST0_NICS[1]
        )
        if not ll_networks.check_network_on_nic(
            network=conf.NETS[19][1], host=conf.HOSTS[0],
            nic=conf.HOST0_NICS[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network %s is not attached to NIC%s " %
                (conf.NETS[19][1], conf.HOST0_NICS[1])
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
            "reactivate it", conf.CLUSTER_NAME[0]
        )
        logger.info("Deactivate Host %s", conf.HOSTS[0])
        if not ll_hosts.deactivateHost(True, host=conf.HOSTS[0]):
            logger.error("Couldn't deactivate Host %s", conf.HOSTS[0])

        logger.info("Attach Host to original DC/Cluster")
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[0], cluster=conf.CLUSTER_NAME[0]
        ):
            logger.error("Cannot move host to original Cluster")

        logger.info("Activate Host")
        if not ll_hosts.activateHost(True, host=conf.HOSTS[0]):
            logger.error("Couldn't activate host %s", conf.HOSTS[0])

        logger.info("Removing the Cluster %s from the setup", cls.cl_name2)
        if not ll_clusters.removeCluster(positive=True, cluster=cls.cl_name2):
            logger.error("Failed to remove cluster %s ", cls.cl_name2)
        super(NetLabels19, cls).teardown_class()


@attr(tier=2)
class NetLabels20(TestLabelTestCaseBase):
    """
    1) Check that it is possible to have 1 VM untagged network and VLAN
       network on the same host interface
    2) Check that it is possible to have 1 VM untagged and VLAN network
       on the same bond
    """
    __test__ = True
    bond = "bond20"

    @classmethod
    def setup_class(cls):
        """
        1) Create:
            a) Bond on host
            b) 2 VM network on DC/Cluster
            c) 2 VLAN network on DC/Cluster
        2) Add label1 and label2 to VM and VLAN networks
        """

        logger.info("Create %s on %s", cls.bond, conf.HOSTS[0])
        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond,
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOSTS[0], **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create %s on %s" % (cls.bond, conf.HOSTS[0])
            )
        for i in range(0, 3, 2):
            logger.info(
                "Attach label %s to networks %s and %s",
                conf.LABEL_NAME[20][i], conf.NETS[20][i], conf.NETS[20][i+1]
            )

            if not ll_networks.add_label(
                label=conf.LABEL_NAME[20][i],
                networks=[conf.NETS[20][i], conf.NETS[20][i+1]]
            ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to networks %s and %s" %
                    (
                        conf.LABEL_NAME[20][i], conf.NETS[20][i],
                        conf.NETS[20][i+1]
                    )
                )

    @polarion("RHEVM3-13511")
    def test_label_vm_vlan(self):
        """
        Check that untagged VM and VLAN networks are attached to the Host
        """
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST0_NICS[1], conf.VLAN_IDS[9]
        )
        logger.info(
            "Attach label %s to host NIC %s ",
            conf.LABEL_NAME[20][0], conf.HOST0_NICS[1]
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[20][0],
            host_nic_dict={conf.HOSTS[0]: [conf.HOST0_NICS[1]]}
        ):
                raise conf.NET_EXCEPTION(
                    "Couldn't attach label %s to host NIC %s" %
                    (conf.LABEL_NAME[20][0], conf.HOST0_NICS[1])
                )

        for net in (conf.NETS[20][0], conf.NETS[20][1]):
            logger.info(
                "Check that network %s attach to host NIC %s",
                net, conf.HOST0_NICS[1]
            )

            host_nic = (
                vlan_nic if net == conf.NETS[20][1]
                else conf.HOST0_NICS[1]
            )

            if not ll_networks.check_network_on_nic(
                network=net, host=conf.HOSTS[0], nic=host_nic
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to host NIC %s " %
                    (net, conf.HOST0_NICS[1])
                )

    @polarion("RHEVM3-13894")
    def test_label_bond_vm_vlan(self):
        """
        Check that the untagged VM and VLAN networks are attached to the bond
        """
        vlan_bond = ul_network.vlan_int_name(self.bond, conf.VLAN_IDS[10])
        logger.info(
            "Attach label %s to bond %s ",
            conf.LABEL_NAME[20][2], self.bond
        )
        if not ll_networks.add_label(
            label=conf.LABEL_NAME[20][2],
            host_nic_dict={conf.HOSTS[0]: [self.bond]}
        ):
            raise conf.NET_EXCEPTION(
                "Couldn't attach label %s to bond %s" %
                (conf.LABEL_NAME[20][2], self.bond)
            )

        for net in (conf.NETS[20][2], conf.NETS[20][3]):
            logger.info(
                "Check that network %s attach to bond %s",
                net, self.bond
            )

            bond = (
                vlan_bond if net == conf.NETS[20][3]
                else self.bond
            )

            if not ll_networks.check_network_on_nic(
                network=net, host=conf.HOSTS[0], nic=bond
            ):
                raise conf.NET_EXCEPTION(
                    "Network %s is not attached to bond %s " %
                    (net, self.bond)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove label from the bond.
        Call the parent teardown
        """
        logger.info("Removing label from bond")
        if not ll_networks.remove_label(
            host_nic_dict={conf.HOSTS[0]: [cls.bond]}
        ):
            logger.error("Couldn't remove labels from Bond ")
        super(NetLabels20, cls).teardown_class()
