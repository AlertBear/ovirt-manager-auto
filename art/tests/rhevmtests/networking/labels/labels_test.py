#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Network labels feature.
1 DC, 2 Clusters, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""

import logging
import time

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.unittest_lib.network as ul_network
import config as label_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.core_api import apis_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import (
    case_01_fixture, case_02_fixture, case_03_fixture, case_04_fixture,
    case_05_fixture, case_06_fixture, case_07_fixture, case_08_fixture,
    case_09_fixture
)

logger = logging.getLogger("Labels_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(case_01_fixture.__name__)
class TestNetLabels01(NetworkTest):

    """
    Check network label:
    1) Check that the label cannot be attached to the Bond when it is used by
        another Host NIC
    2) Check that the label can attach to several interface.
    3) check that the label can attach to several interface with several
        networks on label.
    """
    __test__ = True
    bond = "bond01"
    net_1 = label_conf.NETS[1][0]
    net_2 = label_conf.NETS[1][1]
    net_3 = label_conf.NETS[1][2]
    net_4 = label_conf.NETS[1][3]
    label_1 = label_conf.LABEL_NAME[1][0]
    label_2 = label_conf.LABEL_NAME[1][1]
    label_3 = label_conf.LABEL_NAME[1][2]
    vlan_id_1 = label_conf.VLAN_IDS[1]
    vlan_id_2 = label_conf.VLAN_IDS[2]

    @polarion("RHEVM3-4104")
    def test_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface
        3) Attach label to the bond and succeed
        """
        vlan_bond = ul_network.vlan_int_name(self.bond, self.vlan_id_1)

        testflow.step(
            "Try to attach label %s to the bond %s when that label "
            "is already attached to the interface %s ",
            self.label_1, self.bond, conf.HOST_0_NICS[1]
        )
        self.assertTrue(
            helper.add_label_and_check_network_on_nic(
                positive=False, label=self.label_1, host_nic_dict={
                    conf.HOST_0_NAME: [self.bond]
                }
            )
        )
        testflow.step(
            "Remove label %s from the host NIC %s and then try to attach label"
            "to the Bond interface %s", self.label_1, conf.HOST_0_NICS[1],
            self.bond
        )
        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                },
                labels=[self.label_1]
            )
        )
        self.assertTrue(
            helper.add_label_and_check_network_on_nic(
                positive=True, label=self.label_1, add_net_to_label=False,
                networks=[self.net_1],
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond]
                }, vlan_nic=vlan_bond
            )
        )

        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond]
                },
                labels=[self.label_1]
            )
        )

    @polarion("RHEVM3-4106")
    def test_label_several_interfaces(self):
        """
        1) Put label on host NIC of one host
        2) Put the same label on bond of the second Host
        3) Put label on the network
        4) Check network is attached to both Host (appropriate interfaces)
        5) Remove label from interface
        """

        testflow.step(
            "Attach label %s to bond %s on the first host %s,"
            "and attach the same label %s to host NIC %s "
            "on the second host %s and attach label %s on the network %s and "
            "check if network %s is attached to both Host ",
            self.label_2, self.bond, conf.HOST_0_NAME, self.label_2,
            conf.HOST_1_NICS[1], conf.HOST_1_NAME, self.label_2, self.net_2,
            self.net_2
        )
        self.assertTrue(
            helper.add_label_and_check_network_on_nic(
                positive=True, label=self.label_2, host_nic_dict={
                    conf.HOST_0_NAME: [self.bond],
                    conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
                },
                networks=[self.net_2],
                nic_list=[conf.HOST_1_NICS[1], self.bond]
            )
        )

        testflow.step(
            "Remove label %s from the bond %s on the first host %s and from"
            "host NIC %s on the second host %s", self.label_2, self.bond,
            conf.HOST_0_NAME, conf.HOST_1_NICS[1], conf.HOST_1_NAME
        )
        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond],
                    conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
                },
                labels=[self.label_2]
            )
        )

    @polarion("RHEVM3-4107")
    def test_label_several_networks(self):
        """
        1) Put label on bond of the one host
        2) Put label on host NIC of the second host
        """
        vlan_bond = ul_network.vlan_int_name(self.bond, self.vlan_id_2)
        vlan_nic = ul_network.vlan_int_name(
            conf.HOST_1_NICS[1], self.vlan_id_2
        )
        net_list = [self.net_3, self.net_4]

        nic_dict = {conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]}
        nic_list = [conf.HOST_1_NICS[1], vlan_nic]
        bond_dict = {conf.HOST_0_NAME: [self.bond]}
        bond_list = [self.bond, vlan_bond]

        testflow.step(
            "Attach label %s to bond %s and host NIC %s on both Hosts "
            "appropriately and check that network %s and %s are attached to "
            "bond %s on host %s and to host NIC %s on host %s",
            self.label_3, self.bond, conf.HOST_1_NICS[1], self.net_3,
            self.net_4, self.bond, conf.HOST_0_NAME, conf.HOST_1_NICS[1],
            conf.HOST_1_NAME
        )
        for dict_nic, nic, add_network in (
            (nic_dict, nic_list, True), (bond_dict, bond_list, False)
        ):
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=True, label=self.label_3, host_nic_dict=dict_nic,
                    networks=net_list, nic_list=nic,
                    add_net_to_label=add_network
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(case_02_fixture.__name__)
class TestNetLabels02(NetworkTest):

    """
    1) Check that you can remove network from Host NIC on 2 Hosts by
    un-labeling that Network.
    2) Check that you can break bond which has network attached to it by
    Un-Labeling
    """
    __test__ = True
    bond = "bond02"
    net_1 = label_conf.NETS[2][0]
    net_2 = label_conf.NETS[2][1]
    label_1 = label_conf.LABEL_NAME[2][0]
    label_2 = label_conf.LABEL_NAME[2][1]
    vlan_id = label_conf.VLAN_IDS[3]

    @polarion("RHEVM3-4127")
    def test_unlabel_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from host NIC on both Hosts
        """
        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], self.vlan_id)

        testflow.step(
            "Remove label %s from the network %s", self.label_1, self.net_1
        )
        self.assertTrue(
            ll_networks.remove_label(
                networks=[self.net_1], labels=[self.label_1]
            )
        )

        for host in conf.HOSTS[:2]:
            testflow.step(
                "Check that the network %s is not attached to host %s",
                self.net_1, host
            )
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=ll_networks.check_network_on_nic,
                network=self.net_1, host=host, nic=vlan_nic
            )

            self.assertTrue(
                sample.waitForFuncStatus(result=False)
            )

    @polarion("RHEVM3-4122")
    def test_break_labeled_bond(self):
        """
        1) Break bond on both Hosts
        2) Make sure that the bond slave interfaces don't have label confured
        """
        kwargs = {
            "remove": {
                'networks': [self.net_2],
                'bonds': [self.bond],
                'labels': [self.label_2]
            }
        }

        testflow.step(
            "Break bond on both hosts (%s, %s)",
            conf.HOST_0_NAME, conf.HOST_1_NAME
        )
        for host_name in conf.HOSTS[:2]:
            self.assertTrue(
                hl_host_network.setup_networks(host_name, **kwargs)
            )

        testflow.step(
            "Check that the label %s doesn't appear on slaves of both Hosts",
            self.label_2
        )
        self.assertFalse(
            ll_networks.get_label_objects(
                host_nic_dict={
                    conf.HOST_0_NAME: [
                        label_conf.DUMMYS[0], label_conf.DUMMYS[1]
                    ],
                    conf.HOST_1_NAME: [
                        label_conf.DUMMYS[0], label_conf.DUMMYS[1]
                    ]
                }
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_03_fixture.__name__)
class TestNetLabels03(NetworkTest):

    """
    1) Negative case: Try to remove labeled network NET1 from labeled
    interface on the first NIC by setupNetworks
    2) Remove label from interface and make sure the network is detached
    from it
    3) Attach another network to the same interface with setupNetworks
    """
    __test__ = True

    net_1 = label_conf.NETS[3][0]
    net_2 = label_conf.NETS[3][1]
    label_1 = label_conf.LABEL_NAME[3][0]
    vlan_id = label_conf.VLAN_IDS[4]
    vlan_id_1 = label_conf.VLAN_IDS[5]

    @polarion("RHEVM3-4130")
    def test_remove_label_host_NIC(self):
        """
       1) Negative case: Try to remove labeled network NET1 from labeled
       interface with setupNetworks
       2) Remove label from interface and make sure the network is detached
       from it
       3) Attach another network to the same interface with setupNetworks
       """
        testflow.step(
            "Try to remove labeled network %s from Host NIC %s with "
            "setupNetwork", self.net_1, conf.HOST_0_NAME
        )

        self.assertFalse(
            hl_host_network.remove_networks_from_host(
                host_name=conf.HOST_0_NAME, networks=[self.net_1]
            )
        )

        testflow.step(
            "Remove label %s from interface %s and make sure the network "
            "is detached from it", self.label_1, conf.HOST_0_NICS[1]
        )
        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                },
                labels=[self.label_1]
            )
        )

        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], self.vlan_id)

        self.assertFalse(
            ll_networks.check_network_on_nic(
                network=self.net_1, host=conf.HOST_0_NAME, nic=vlan_nic
            )
        )

        vlan_nic = ul_network.vlan_int_name(
            conf.HOST_0_NICS[1], self.vlan_id_1
        )

        local_dict2 = {
            self.net_2: {
                "vlan_id": self.vlan_id_1,
                "required": "false",
                "usages": ""
            }
        }

        network_host_api_dict = {
            "add": {
                "1": {
                    "network": self.net_2,
                    "nic":  conf.HOST_0_NICS[1],
                }
            }
        }

        testflow.step(
            "Attach another network %s to the same interface %s "
            "with setupNetworks and check that the network %s "
            "is attached to host %s", self.net_2, conf.HOST_0_NICS[1],
            self.net_2, conf.HOST_0_NAME
        )
        self.assertTrue(
            hl_networks.createAndAttachNetworkSN(
                data_center=conf.DC_0, cluster=conf.CL_0,
                network_dict=local_dict2
            )
        )

        self.assertTrue(
            hl_host_network.setup_networks(
                conf.HOST_0_NAME, **network_host_api_dict
            )
        )

        self.assertTrue(
            ll_networks.check_network_on_nic(
                network=self.net_2, host=conf.HOST_0_NAME, nic=vlan_nic
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_04_fixture.__name__)
class TestNetLabels04(NetworkTest):

    """
    Check that the labeled network created in the DC level only will not be
    attached to the labeled Host NIC
    """
    __test__ = True

    net_1 = label_conf.NETS[4][0]
    label_1 = label_conf.LABEL_NAME[4][0]

    @polarion("RHEVM3-4113")
    def test_network_on_host(self):
        """
        1) Attach label to the network
        2) Attach label to Host Nic
        3) Check the network with the same label as host NIC is not attached to
        Host when it is not attached to the cluster
        """
        testflow.step(
            "Attach label %s to the network %s and to host NIC %s and check "
            "that the network %s with the same label as host NIC isn't "
            "attached to host %s when it is not attached to the cluster %s",
            self.label_1, self.net_1, conf.HOST_0_NICS[1], self.net_1,
            conf.HOST_0_NAME, conf.CL_0
        )
        self.assertTrue(
            helper.add_label_and_check_network_on_nic(
                positive=True, label=self.label_1, network_on_nic=False,
                networks=[self.net_1],
                host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                }, nic_list=[conf.HOST_0_NICS[1]]
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_05_fixture.__name__)
class TestNetLabels05(NetworkTest):

    """
    1) Create bond from labeled interfaces when those labels are attached to
    the VLAN networks appropriately.
    2) Create bond from labeled interfaces when those labels are attached to
    the non-VM and VLAN networks appropriately.
    3) Create bond from labeled interfaces when those labels are attached to
    the VM non-VLAN  network and non-VM network appropriately and fail.
    4)Create bond from labeled interfaces when those labels are attached to two
    VM non-VLAN network appropriately and fail.
    """
    __test__ = True
    bond_1 = "bond051"
    bond_2 = "bond052"
    bond_3 = "bond053"
    bond_4 = "bond054"
    nets = label_conf.NETS[5][:8]
    net_1 = nets[0]
    net_2 = nets[1]
    net_3 = nets[2]
    net_4 = nets[3]
    net_5 = nets[4]
    net_6 = nets[5]
    net_7 = nets[6]
    net_8 = nets[7]
    labels = label_conf.LABEL_NAME[5][:8]
    label_1 = labels[0]
    label_2 = labels[1]
    label_3 = labels[2]
    label_4 = labels[3]
    label_5 = labels[4]
    label_6 = labels[5]
    label_7 = labels[6]
    label_8 = labels[7]
    vlan_id_list = label_conf.VLAN_IDS[6:9]
    vlan_id_1 = label_conf.VLAN_IDS[6]
    vlan_id_2 = label_conf.VLAN_IDS[7]
    vlan_id_3 = label_conf.VLAN_IDS[8]
    dummys_list = label_conf.DUMMYS[:6]
    dummy_1 = label_conf.DUMMYS[0]
    dummy_2 = label_conf.DUMMYS[1]
    dummy_3 = label_conf.DUMMYS[2]
    dummy_4 = label_conf.DUMMYS[3]
    dummy_5 = label_conf.DUMMYS[4]
    dummy_6 = label_conf.DUMMYS[5]
    dummy_7 = label_conf.DUMMYS[6]
    dummy_8 = label_conf.DUMMYS[7]

    @polarion("RHEVM3-4116")
    def test_create_bond(self):
        """
        1) Remove labels from two interfaces.
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """

        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.dummy_1, self.dummy_2]
                },
                labels=self.labels[:2]
            )
        )

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": label_conf.DUMMYS[:2],
                    "nic": self.bond_1,
                    "mode": 1
                }
            }
        }

        testflow.step(
            "Create bond %s from labeled interfaces when those labels (%s, %s)"
            " are attached to the VLAN networks (%s, %s) appropriately",
            self.bond_1, self.label_1, self.label_2, self.net_1, self.net_2
        )

        self.assertTrue(
            hl_host_network.setup_networks(
                conf.HOST_0_NAME, **network_host_api_dict
            )
        )

        for label, vlan_id, net in (
            (self.label_1, self.vlan_id_1, self.net_1),
            (self.label_2, self.vlan_id_2, self.net_2)
        ):
            vlan_bond = ul_network.vlan_int_name(self.bond_1, vlan_id)
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=True, label=label, add_net_to_label=False,
                    networks=[net], host_nic_dict={
                        conf.HOST_0_NAME: [self.bond_1]
                    }, vlan_nic=vlan_bond
                )
            )

        self.assertFalse(
            ll_networks.get_label_objects(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.dummy_1, self.dummy_2]
                }
            )
        )

    @polarion("RHEVM3-4100")
    def test_create_bond_with_non_vm_and_vlan_network(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """

        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.dummy_3, self.dummy_4]
                },
                labels=self.labels[2:4]
            )
        )

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": label_conf.DUMMYS[2:4],
                    "nic": self.bond_2,
                    "mode": 1
                }
            }
        }

        testflow.step(
            "Create bond %s from labeled interfaces when those labels (%s, %s)"
            " are attached to the non-VM and VLAN networks (%s, %s) "
            "appropriately ",
            self.bond_2, self.label_3, self.label_4, self.net_3, self.net_4
        )

        self.assertTrue(
            hl_host_network.setup_networks(
                conf.HOST_0_NAME, **network_host_api_dict
            )
        )

        vlan_bond = ul_network.vlan_int_name(
            self.bond_2, label_conf.VLAN_IDS[8]
        )
        bond_list = [vlan_bond]
        nic_list = [self.bond_2]

        for label, nic, net in (
            (self.label_3, bond_list, self.net_3),
            (self.label_4, nic_list, self.net_4)
        ):
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=True, label=label, add_net_to_label=False,
                    networks=[net], host_nic_dict={
                        conf.HOST_0_NAME: [self.bond_2]
                    }, nic_list=nic
                )
            )

        self.assertFalse(
            ll_networks.get_label_objects(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.dummy_3, self.dummy_4]
                }
            )
        )

    @polarion("RHEVM3-4102")
    def test_create_bond_with_vm_and_non_vm(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """

        self.assertTrue(
            ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [self.dummy_5, self.dummy_6]
                },
                labels=self.labels[4:6]
            )
        )

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": label_conf.DUMMYS[4:6],
                    "nic": self.bond_3,
                    "mode": 1
                }
            }
        }

        testflow.step(
            "Try to create bond %s from labeled interfaces when those "
            "labels (%s, %s) are attached to the VM non-VLAN network %s "
            "and non-VM network %s appropriately and fail",
            self.bond_3, self.label_5, self.label_6, self.net_5, self.net_6
        )
        self.assertTrue(
            hl_host_network.setup_networks(
                conf.HOST_0_NAME, **network_host_api_dict
            )
        )

        self.assertFalse(
            hl_networks.create_and_attach_label(
                label=self.label_5,
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_3]
                }
            ) and
            hl_networks.create_and_attach_label(
                label=self.label_6,
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_3]
                }
            )
        )

        self.assertTrue(
            ll_networks.check_network_on_nic(
                network=self.net_5, host=conf.HOST_0_NAME, nic=self.bond_3
            )
        )

        self.assertFalse(
            ll_networks.check_network_on_nic(
                network=self.net_6, host=conf.HOST_0_NAME, nic=self.bond_3
            )
        )

    @polarion("RHEVM3-4101")
    def test_create_bond_with_two_vm_non_vlan(self):
        """
        1) Negative: Create bond from labeled interfaces
        2) Check that both networks reside on appropriate interfaces
        """

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": label_conf.DUMMYS[6:8],
                    "nic": self.bond_4,
                    "mode": 1
                }
            }
        }

        testflow.step(
            "Try to create bond %s from labeled interfaces when those "
            "labels (%s, %s) are attached to two VM non-VLAN network "
            "(%s, %s) appropriately and fail",
            self.bond_4, self.label_7, self.label_8, self.net_7, self.net_8
        )

        self.assertTrue(
            hl_host_network.setup_networks(
                conf.HOST_0_NAME, **network_host_api_dict
            )
        )

        self.assertFalse(
            hl_networks.create_and_attach_label(
                label=self.label_7,
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_4]
                }
            ) and
            hl_networks.create_and_attach_label(
                label=self.label_8,
                host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_4]
                }
            )
        )

        self.assertTrue(
            ll_networks.check_network_on_nic(
                network=self.net_7, host=conf.HOST_0_NAME, nic=self.bond_4
            )
        )

        self.assertFalse(
            ll_networks.check_network_on_nic(
                network=self.net_8, host=conf.HOST_0_NAME, nic=self.bond_4
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_06_fixture.__name__)
class TestNetLabels06(NetworkTest):

    """
    1)Check that when a labeled network is detached from a cluster,
    the network will be removed from any labeled interface within that cluster.
    2) The same will happen when the network is removed from the DC
    """
    __test__ = True
    net_1 = label_conf.NETS[6][0]
    label_1 = label_conf.LABEL_NAME[6][0]
    cl_1 = conf.CL_0
    dc_1 = conf.DC_0

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
        testflow.step(
            "Remove labeled network %s from cluster %s",
            self.net_1, self.cl_1
        )

        self.assertTrue(
            ll_networks.remove_network_from_cluster(
                positive=True, network=self.net_1, cluster=self.cl_1
            )
        )

        testflow.step(
            "Check that the network %s is not attached to host NIC %s",
            self.net_1, conf.HOST_0_NICS[1]
        )

        self.assertFalse(
            ll_networks.check_network_on_nic(
                network=self.net_1, host=conf.HOST_0_NAME,
                nic=conf.HOST_0_NICS[1]
            )
        )

        testflow.step(
            "Reassign network %s to the Cluster %s", self.net_1, self.cl_1
        )

        self.assertTrue(
            ll_networks.add_network_to_cluster(
                positive=True, network=self.net_1, cluster=self.cl_1,
                required=False
            )
        )

        testflow.step(
            "Check that the network %s is attached to the interface after"
            "reattaching it to the Cluster %s", self.net_1, self.cl_1
        )

        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic,
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        )
        assert sample.waitForFuncStatus(result=True)

        testflow.step(
            "Remove network %s from the DC %s", self.net_1, self.dc_1
        )

        self.assertTrue(
            ll_networks.removeNetwork(
                positive=True, network=self.net_1, data_center=self.dc_1
            )
        )

        testflow.step(
            "Check that network %s is not attached to host NIC %s",
            self.net_1, conf.HOST_0_NICS[1]
        )

        self.assertFalse(
            ll_networks.check_network_on_nic(
                network=self.net_1, host=conf.HOST_0_NAME,
                nic=conf.HOST_0_NICS[1]
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(case_07_fixture.__name__)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestNetLabels07(NetworkTest):

    """
    Check that after moving a Host with labeled interface between all the
    Cluster versions for the 3.6 DC, the network label feature is functioning
    as expected
    """
    __test__ = True

    labels = label_conf.LABEL_NAME[7][:4]
    dc_name2 = "new_DC_3_6_case07"
    comp_cl_name = [
        "Cluster_%s_case07" % conf.COMP_VERSION_4_0[i]
        for i in range(len(conf.COMP_VERSION_4_0) - 1)
        ]

    dummys = label_conf.DUMMYS[:4]
    nets = label_conf.NETS[7][:4]
    vlan_id_list = label_conf.VLAN_IDS[9:11]
    sleep_timeout = 30

    @polarion("RHEVM3-4124")
    def test_move_host_supported_cl(self):
        """
        1) Attach label to the network .
        2) Check that the network is attached to the host NIC
        3) Remove label from the network
        4) Repeat the 2 steps above when moving from 3.6 cluster up
        to all support cluster
        """

        for cluster in self.comp_cl_name:
            testflow.step(
                "Move the host %s to cluster %s", conf.HOST_1_NAME, cluster
            )

            self.assertTrue(
                ll_hosts.updateHost(
                    positive=True, host=conf.HOST_1_NAME, cluster=cluster
                )
            )

            logger.info(
                "Sleep for %s. after moving host to new cluster "
                "setupNetworks is called and we need to wait untill "
                "it's done", self.sleep_timeout
            )

            time.sleep(self.sleep_timeout)

            for i, (lb, net, dummy) in enumerate(
                zip(self.labels, self.nets, self.dummys)
            ):
                testflow.step(
                    "Attach label %s to the network %s", lb, net
                )

                network_helper.call_function_and_wait_for_sn(
                    func=hl_networks.create_and_attach_label, content=net,
                    label=lb, networks=[net]
                )

                nic = (
                    ul_network.vlan_int_name(dummy, label_conf.VLAN_IDS[i+7])
                    if i > 1 else dummy
                )

                testflow.step(
                    "Check that the network %s is attach to the host NIC %s",
                    net, dummy
                )
                sample = apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                    func=ll_networks.check_network_on_nic,
                    network=net, host=conf.HOST_1_NAME, nic=nic
                )

                self.assertTrue(sample.waitForFuncStatus(result=True))

                self.assertTrue(
                    ll_networks.remove_label(
                        host_nic_dict={
                            conf.HOST_1_NAME: [dummy]
                        },
                        networks=[net], labels=[lb]
                    )
                )
                self.assertTrue(sample.waitForFuncStatus(result=False))


@attr(tier=2)
@pytest.mark.usefixtures(case_08_fixture.__name__)
class TestNetLabels08(NetworkTest):

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
    label_1 = label_conf.LABEL_NAME[8][0]
    label_2 = label_conf.LABEL_NAME[8][1]
    label_3 = label_conf.LABEL_NAME[8][2]
    net_1 = label_conf.NETS[8][0]
    net_2 = label_conf.NETS[8][1]
    net_3 = label_conf.NETS[8][2]
    net_4 = label_conf.NETS[8][3]
    net_5 = label_conf.NETS[8][4]
    net_6 = label_conf.NETS[8][5]

    @polarion("RHEVM3-4121")
    def test_label_restrictioin(self):
        """
        1) Put label_1 on Host NIC of the Host
        2) Check that the networks net_1 and net_2 are not attached to the Host
        3) Replace label_1 with label_2 on Host NIC of the Host
        4) Check that the networks net_3 and net_4 are not attached to the Host
        5) Replace label_2 with label_3 on Host NIC of the Host
        6) Check that the networks net_5 and net_6 are not attached to the Host
        7) Replace label_3 with label_4 on Host NIC of the Host
        """

        for label, net1, net2 in (
            (self.label_1, self.net_1, self.net_2),
            (self.label_2, self.net_3, self.net_4),
            (self.label_3, self.net_5, self.net_6)
        ):
            testflow.step(
                "Try to attach label %s to host NIC %s and attach "
                "both networks (%s, %s) to the label %s and check if that "
                "networks  are not attached to the host %s",
                label, conf.HOST_0_NICS[1], net1, net2, label, conf.HOST_0_NAME
            )
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=False, label=label, network_on_nic=False,
                    add_net_to_label=False, networks=[net1, net2],
                    host_nic_dict={
                        conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                    }, nic_list=[conf.HOST_0_NICS[1], conf.HOST_0_NICS[1]]
                )
            )

            self.assertTrue(
                ll_networks.remove_label(
                    host_nic_dict={
                        conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                    }
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(case_09_fixture.__name__)
class TestNetLabels09(NetworkTest):

    """
    1) Check that when adding a new labeled VM network to the system which
    has another VM network with the same label attached to the Host, will not
    attach the new network to the Host
    2) Check that when adding a new labeled non-VM network to the system which
    has another non-VM network with the same label attached to the Host, will
    not attach the new network to the Host
    """
    __test__ = True

    net_1 = label_conf.NETS[9][0]
    net_2 = label_conf.NETS[9][1]
    net_3 = label_conf.NETS[9][2]
    net_4 = label_conf.NETS[9][3]
    label_1 = label_conf.LABEL_NAME[9][0]
    label_2 = label_conf.LABEL_NAME[9][1]

    @polarion("RHEVM3-4117")
    def test_label_restrictioin_vm(self):
        """
        1) Put the same label on the net_3 VM network as on network net_1
        2) Check that the new VM network net_3 is not attached to the Host NIC
        3) Check that net_1 is still attached to the Host NIC
        """

        testflow.step(
            "Check that when adding a new labeled VM network %s to the system "
            "which has another VM network %s with the same label %s attached "
            "to the host %s, will not attach the new network %s to the host",
            self.net_3, self.net_1, self.label_1, conf.HOST_0_NAME, self.net_3
        )
        for positive, net, network_on_nic in (
            (True, self.net_3, False), (False, self.net_1, True)
        ):
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=positive, network_on_nic=network_on_nic,
                    label=self.label_1, networks=[net], host_nic_dict={
                        conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                    }, attach_to_host=False, nic_list=[conf.HOST_0_NICS[1]]
                )
            )

    @polarion("RHEVM3-4118")
    def test_label_restrictioin_non_vm(self):
        """
        1) Attach the same label on the net_4 VM network as on network net_2
        2) Check that the new non-VM network net_4 is not attached to the Host
            NIC
        3) Check that net_2 is still attached to the Host NIC
        """

        testflow.step(
            "Check that when adding a new labeled non-VM network %s to "
            "the system which has another non-VM network %s with the "
            "same label %s attached to the host %s, will not attach "
            "the new network to the host", self.net_4, self.net_2,
            self.label_2, conf.HOST_0_NAME
        )
        for positive, net, network_on_nic in (
            (True, self.net_4, False), (False, self.net_2, True)
        ):
            self.assertTrue(
                helper.add_label_and_check_network_on_nic(
                    positive=positive, network_on_nic=network_on_nic,
                    label=self.label_2, networks=[net], host_nic_dict={
                        conf.HOST_0_NAME: [conf.HOST_0_NICS[2]]
                    }, attach_to_host=False, nic_list=[conf.HOST_0_NICS[2]]
                )
            )
