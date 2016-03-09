#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Network labels feature.
1 DC, 2 Clusters, 2 Hosts will be created for testing.
Network Labels feature will be tested for untagged, tagged,
bond scenarios and for VM and non-VM networks
"""

import helper
import logging
import config as conf
from art import unittest_lib
from art.unittest_lib import attr
from art.core_api import apis_utils
import rhevmtests.networking as networking
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.unittest_lib.network as ul_network
import rhevmtests.networking.helper as networking_helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.hosts as hl_host
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Labels_Cases")


def setup_module():
    """
    Running cleanup
    Obtain host NICs for the first Network Host
    Create dummy interfaces
    Create networks
    """
    networking.network_cleanup()
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.VDS_1_HOST = conf.VDS_HOSTS[1]
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_1_NAME = conf.HOSTS[1]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    conf.HOST_1_NICS = conf.VDS_1_HOST.nics

    for vds_host in (conf.VDS_0_HOST, conf.VDS_1_HOST):
        networking_helper.prepare_dummies(
            host_resource=vds_host, num_dummy=conf.NUM_DUMMYS
        )
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.NET_DICT, dc=conf.DC_0,
        cluster=conf.CL_0
    )


def teardown_module():
    """
    Cleans the environment
    """
    networking_helper.remove_networks_from_setup(hosts=conf.HOSTS[:2])
    for vds_host in (conf.VDS_0_HOST, conf.VDS_1_HOST):
        networking_helper.delete_dummies(host_resource=vds_host)


@attr(tier=2)
class TestLabelTestCaseBase(unittest_lib.NetworkTest):

    """
    base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        """
        for host in [conf.HOST_0_NAME, conf.HOST_1_NAME]:
            hl_host_network.clean_host_interfaces(host_name=host)


class TestNetLabels01(TestLabelTestCaseBase):

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
    net_1 = conf.NETS[1][0]
    net_2 = conf.NETS[1][1]
    net_3 = conf.NETS[1][2]
    net_4 = conf.NETS[1][3]
    label_1 = conf.LABEL_NAME[1][0]
    label_2 = conf.LABEL_NAME[1][1]
    label_3 = conf.LABEL_NAME[1][2]
    vlan_id_1 = conf.VLAN_IDS[1]
    vlan_id_2 = conf.VLAN_IDS[2]

    @classmethod
    def setup_class(cls):
        """
        1) Create bond from 2 phy interfaces
        2) Create and attach label to the network
        3) Attach label to Host Nic
        """
        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], cls.vlan_id_1)

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond,
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        helper.add_label_and_check_network_on_nic(
            positive=True, label=cls.label_1, networks=[cls.net_1],
            host_nic_dict={
                conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
            },
            vlan_nic=vlan_nic
        )

    @polarion("RHEVM3-4104")
    def test_same_label_on_host(self):
        """
        1) Try to attach already attached label to bond and fail
        2) Remove label from interface
        3) Attach label to the bond and succeed
        """
        vlan_bond = ul_network.vlan_int_name(self.bond, self.vlan_id_1)

        helper.add_label_and_check_network_on_nic(
            positive=False, label=self.label_1, host_nic_dict={
                conf.HOST_0_NAME: [self.bond]
            }
        )
        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
            },
            labels=[self.label_1]
        ):
            raise conf.NET_EXCEPTION()

        helper.add_label_and_check_network_on_nic(
            positive=True, label=self.label_1, add_net_to_label=False,
            networks=[self.net_1],
            host_nic_dict={
                conf.HOST_0_NAME: [self.bond]
            }, vlan_nic=vlan_bond
        )

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [self.bond]
            },
            labels=[self.label_1]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4106")
    def test_label_several_interfaces(self):
        """
        1) Put label on host NIC of one host
        2) Put the same label on bond of the second Host
        3) Put label on the network
        4) Check network is attached to both Host (appropriate interfaces)
        5) Remove label from interface
        """

        helper.add_label_and_check_network_on_nic(
            positive=True, label=self.label_2, host_nic_dict={
                conf.HOST_0_NAME: [self.bond],
                conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
            },
            networks=[self.net_2], nic_list=[conf.HOST_1_NICS[1], self.bond]
        )

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [self.bond],
                conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
            },
            labels=[self.label_2]
        ):
            raise conf.NET_EXCEPTION()

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

        for dict_nic, nic, add_network in (
            (nic_dict, nic_list, True), (bond_dict, bond_list, False)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=True, label=self.label_3, host_nic_dict=dict_nic,
                networks=net_list, nic_list=nic, add_net_to_label=add_network
            )


class TestNetLabels02(TestLabelTestCaseBase):

    """
    1) Check that you can remove network from Host NIC on 2 Hosts by
    un-labeling that Network.
    2) Check that you can break bond which has network attached to it by
    Un-Labeling
    """
    __test__ = True
    bond = "bond02"
    net_1 = conf.NETS[2][0]
    net_2 = conf.NETS[2][1]
    label_1 = conf.LABEL_NAME[2][0]
    label_2 = conf.LABEL_NAME[2][1]
    vlan_id = conf.VLAN_IDS[3]

    @classmethod
    def setup_class(cls):
        """
        1) Create bond from 2 dummys on 2 Hosts.
        2) Attach label network to Host Nic and bond on both Hosts
        3) Make sure the networks was attached to Host Nic and Bond on both
        Hosts.
        """

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": cls.bond
                }
            }
        }
        for host in (conf.HOST_0_NAME, conf.HOST_1_NAME):
            if not hl_host_network.setup_networks(
                host, **network_host_api_dict
            ):
                raise conf.NET_EXCEPTION()

        nic_dict = {
            conf.HOST_0_NAME: [conf.HOST_0_NICS[1]],
            conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
        }

        bond_dict = {
            conf.HOST_0_NAME: [cls.bond], conf.HOST_1_NAME: [cls.bond]
        }

        vlan_nic_1 = ul_network.vlan_int_name(conf.HOST_0_NICS[1], cls.vlan_id)
        vlan_nic_2 = ul_network.vlan_int_name(conf.HOST_1_NICS[1], cls.vlan_id)
        nic_list = [vlan_nic_2, vlan_nic_1]
        bond_list = [cls.bond, cls.bond]

        for label, dict_nic, net, nic in (
            (cls.label_1, nic_dict, cls.net_1, nic_list),
            (cls.label_2, bond_dict, cls.net_2, bond_list)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=True, label=label, host_nic_dict=dict_nic,
                networks=[net], nic_list=nic
            )

    @polarion("RHEVM3-4127")
    def test_unlabel_network(self):
        """
        1) Remove label from the network
        2) Make sure the network was detached from eth1 on both Hosts
        """
        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], self.vlan_id)

        if not ll_networks.remove_label(
            networks=[self.net_1], labels=[self.label_1]
        ):
            raise conf.NET_EXCEPTION()

        for host in conf.HOSTS[:2]:
            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=ll_networks.check_network_on_nic,
                network=self.net_1, host=host, nic=vlan_nic
            )

            if not sample.waitForFuncStatus(result=False):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4122")
    def test_break_labeled_bond(self):
        """
        1) Break Bond on both Hosts
        2) Make sure that the bond slave interfaces don't have label confured
        """
        kwargs = {
            "remove": {
                'networks': [self.net_2],
                'bonds': [self.bond],
                'labels': [self.label_2]
            }
        }

        for host_name in conf.HOSTS[:2]:
            if not hl_host_network.setup_networks(host_name, **kwargs):
                raise conf.NET_EXCEPTION()

        if ll_networks.get_label_objects(host_nic_dict={
            conf.HOST_0_NAME: [conf.DUMMYS[0], conf.DUMMYS[1]],
            conf.HOST_1_NAME: [conf.DUMMYS[0], conf.DUMMYS[1]]
        }):
            raise conf.NET_EXCEPTION()


class TestNetLabels03(TestLabelTestCaseBase):

    """
    1) Negative case: Try to remove labeled network NET1 from labeled
    interface on the first NIC by setupNetworks
    2) Remove label from interface and make sure the network is detached
    from it
    3) Attach another network to the same interface with setupNetworks
    """
    __test__ = True

    net_1 = conf.NETS[3][0]
    net_2 = conf.NETS[3][1]
    label_1 = conf.LABEL_NAME[3][0]
    vlan_id = conf.VLAN_IDS[4]
    vlan_id_1 = conf.VLAN_IDS[5]

    @classmethod
    def setup_class(cls):
        """
        1) Create and attach label to the VLAN non-VM network
        2) Attach the same label to Host Nic eth1 on one Host
        """
        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], cls.vlan_id)

        helper.add_label_and_check_network_on_nic(
            positive=True, label=cls.label_1, networks=[cls.net_1],
            host_nic_dict={
                conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
            },
            vlan_nic=vlan_nic
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

        if hl_host_network.remove_networks_from_host(
            host_name=conf.HOST_0_NAME, networks=[self.net_1]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.remove_label(
            host_nic_dict={conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]},
            labels=[self.label_1]
        ):
            raise conf.NET_EXCEPTION()

        vlan_nic = ul_network.vlan_int_name(conf.HOST_0_NICS[1], self.vlan_id)

        if ll_networks.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=vlan_nic
        ):
            raise conf.NET_EXCEPTION()

        vlan_nic = ul_network.vlan_int_name(
            conf.HOST_0_NICS[1], self.vlan_id_1
        )

        local_dict2 = {
            self.net_2: {
                "vlan_id": self.vlan_id_1,
                "nic": 1,
                "required": "false",
                "usages": ""
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, cluster=conf.CL_0, host=conf.VDS_0_HOST,
            network_dict=local_dict2, auto_nics=[0, 1]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_2, host=conf.HOST_0_NAME, nic=vlan_nic
        ):
            raise conf.NET_EXCEPTION()


class TestNetLabels04(TestLabelTestCaseBase):

    """
    Check that the labeled network created in the DC level only will not be
    attached to the labeled Host NIC
    """
    __test__ = True

    net_1 = conf.NETS[4][0]
    label_1 = conf.LABEL_NAME[4][0]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC level only
        """

        local_dict1 = {
            cls.net_1: {
                "required": "false"
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, network_dict=local_dict1
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4113")
    def test_network_on_host(self):
        """
        1) Attach label to the network
        2) Attach label to Host Nic
        3) Check the network with the same label as Host NIC is not attached to
        Host when it is not attached to the Cluster
        """

        helper.add_label_and_check_network_on_nic(
            positive=True, label=self.label_1, network_on_nic=False,
            networks=[self.net_1],
            host_nic_dict={
                conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
            }, nic_list=[conf.HOST_0_NICS[1]]
        )


class TestNetLabels05(TestLabelTestCaseBase):

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
    nets = conf.NETS[5][:8]
    net_1 = nets[0]
    net_2 = nets[1]
    net_3 = nets[2]
    net_4 = nets[3]
    net_5 = nets[4]
    net_6 = nets[5]
    net_7 = nets[6]
    net_8 = nets[7]
    labels = conf.LABEL_NAME[5][:8]
    label_1 = labels[0]
    label_2 = labels[1]
    label_3 = labels[2]
    label_4 = labels[3]
    label_5 = labels[4]
    label_6 = labels[5]
    label_7 = labels[6]
    label_8 = labels[7]
    vlan_id_list = conf.VLAN_IDS[6:9]
    vlan_id_1 = conf.VLAN_IDS[6]
    vlan_id_2 = conf.VLAN_IDS[7]
    vlan_id_3 = conf.VLAN_IDS[8]
    dummys_list = conf.DUMMYS[:6]
    dummy_1 = conf.DUMMYS[0]
    dummy_2 = conf.DUMMYS[1]
    dummy_3 = conf.DUMMYS[2]
    dummy_4 = conf.DUMMYS[3]
    dummy_5 = conf.DUMMYS[4]
    dummy_6 = conf.DUMMYS[5]
    dummy_7 = conf.DUMMYS[6]
    dummy_8 = conf.DUMMYS[7]

    @classmethod
    def setup_class(cls):
        """
        1) Attach label to each network
        2) Attach label to each dummy interface
        """

        for label, net in zip(cls.labels, cls.nets):
            if not hl_networks.create_and_attach_label(
                label=label, networks=[net]
            ):
                raise conf.NET_EXCEPTION()

        for i, (label, dummy, net, vlan_id) in enumerate(zip(
            cls.labels, cls.dummys_list, cls.nets, cls.vlan_id_list
        )):
            nic = ul_network.vlan_int_name(dummy, vlan_id) if i < 3 else dummy
            helper.add_label_and_check_network_on_nic(
                positive=True, label=label, add_net_to_label=False,
                networks=[net], nic_list=[nic],
                host_nic_dict={
                    conf.HOST_0_NAME: [dummy]
                },
            )

    @polarion("RHEVM3-4116")
    def test_create_bond(self):
        """
        1) Remove labels from two interfaces.
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [self.dummy_1, self.dummy_2]
            },
            labels=self.labels[:2]
        ):
            raise conf.NET_EXCEPTION()

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[:2],
                    "nic": self.bond_1,
                    "mode": 1
                }
            }
        }

        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        for label, vlan_id, net in (
            (self.label_1, self.vlan_id_1, self.net_1),
            (self.label_2, self.vlan_id_2, self.net_2)
        ):
            vlan_bond = ul_network.vlan_int_name(self.bond_1, vlan_id)
            helper.add_label_and_check_network_on_nic(
                positive=True, label=label, add_net_to_label=False,
                networks=[net], host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_1]
                }, vlan_nic=vlan_bond
            )

        if ll_networks.get_label_objects(
            host_nic_dict={
                conf.HOST_0_NAME: [self.dummy_1, self.dummy_2]
            }
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4100")
    def test_create_bond_with_non_vm_and_vlan_network(self):
        """
        1) Remove labels from both interfaces
        2) Create bond from labeled interfaces
        3) Attach label networks to the bond.
        2) Check that both networks reside now on bond
        3) Check that label doesn't reside on slaves of the bond
        """

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [self.dummy_3, self.dummy_4]
            },
            labels=self.labels[2:4]
        ):
            raise conf.NET_EXCEPTION()

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[2:4],
                    "nic": self.bond_2,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        vlan_bond = ul_network.vlan_int_name(self.bond_2, conf.VLAN_IDS[8])
        bond_list = [vlan_bond]
        nic_list = [self.bond_2]

        for label, nic, net in (
            (self.label_3, bond_list, self.net_3),
            (self.label_4, nic_list, self.net_4)
        ):

            helper.add_label_and_check_network_on_nic(
                positive=True, label=label, add_net_to_label=False,
                networks=[net], host_nic_dict={
                    conf.HOST_0_NAME: [self.bond_2]
                }, nic_list=nic
            )
        if ll_networks.get_label_objects(
            host_nic_dict={
                conf.HOST_0_NAME: [self.dummy_3, self.dummy_4]
            }
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4102")
    def test_create_bond_with_vm_and_non_vm(self):
        """
        1) Unlabel both interfaces
        2) Negative: Try to create bond from labeled interfaces
        3) Check that both networks reside on appropriate interfaces after
        failure in second step
        """

        if not ll_networks.remove_label(
            host_nic_dict={
                conf.HOST_0_NAME: [self.dummy_5, self.dummy_6]
            },
            labels=self.labels[4:6]
        ):
            raise conf.NET_EXCEPTION()

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[4:6],
                    "nic": self.bond_3,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        if (
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
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_5, host=conf.HOST_0_NAME, nic=self.bond_3
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.check_network_on_nic(
            network=self.net_6, host=conf.HOST_0_NAME, nic=self.bond_3
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4101")
    def test_create_bond_with_two_vm_non_vlan(self):
        """
        1) Negative: Create bond from labeled interfaces
        2) Check that both networks reside on appropriate interfaces
        """

        network_host_api_dict = {
            "add": {
                "1": {
                    "slaves": conf.DUMMYS[6:8],
                    "nic": self.bond_4,
                    "mode": 1
                }
            }
        }
        if not hl_host_network.setup_networks(
            conf.HOST_0_NAME, **network_host_api_dict
        ):
            raise conf.NET_EXCEPTION()

        if (
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
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_7, host=conf.HOST_0_NAME, nic=self.bond_4
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.check_network_on_nic(
            network=self.net_8, host=conf.HOST_0_NAME, nic=self.bond_4
        ):
            raise conf.NET_EXCEPTION()


class TestNetLabels06(TestLabelTestCaseBase):

    """
    1)Check that when a labeled network is detached from a cluster,
    the network will be removed from any labeled interface within that cluster.
    2) The same will happen when the network is removed from the DC
    """
    __test__ = True
    net_1 = conf.NETS[6][0]
    label_1 = conf.LABEL_NAME[6][0]
    cl_1 = conf.CL_0
    dc_1 = conf.DC_0

    @classmethod
    def setup_class(cls):
        """
        1) Create and attach label to the network
        2) Attach label to Host Nic
        """

        helper.add_label_and_check_network_on_nic(
            positive=True, label=cls.label_1, networks=[cls.net_1],
            host_nic_dict={
                conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
            }, nic_list=[conf.HOST_0_NICS[1]]
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

        if not ll_networks.remove_network_from_cluster(
            positive=True, network=self.net_1, cluster=self.cl_1
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.add_network_to_cluster(
            positive=True, network=self.net_1, cluster=self.cl_1,
            required=False
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.removeNetwork(
            positive=True, network=self.net_1, data_center=self.dc_1
        ):
            raise conf.NET_EXCEPTION()

        if ll_networks.check_network_on_nic(
            network=self.net_1, host=conf.HOST_0_NAME, nic=conf.HOST_0_NICS[1]
        ):
            raise conf.NET_EXCEPTION()


class TestNetLabels07(TestLabelTestCaseBase):

    """
    1)Check that after moving a Host with labeled interface from one DC to
    another, the network label feature is functioning as usual
    2) Check that it's impossible to move the Host with labeled interface
    to the Cluster on DC that doesn't support Network labels
    """
    __test__ = True

    net_1 = conf.NETS[7][0]
    label_1 = conf.LABEL_NAME[7][0]
    cl_1 = conf.CL_0
    dc_name2 = "new_DC_case07"
    cl_name2 = "new_CL_case07"
    uncomp_dc = "uncomp_DC_case07"
    uncomp_cl = "uncomp_CL_case07"
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

        if not hl_networks.create_and_attach_label(
            label=cls.label_1,
            host_nic_dict={
                conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
            }
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.create_basic_setup(
            datacenter=cls.dc_name2, storage_type=conf.STORAGE_TYPE,
            version=conf.COMP_VERSION, cluster=cls.cl_name2, cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION()

        local_dict = {
            cls.net_1: {
                "required": "false"
            }
        }
        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict, dc=cls.dc_name2, cluster=cls.cl_name2
        )

        if not hl_networks.create_basic_setup(
            datacenter=cls.uncomp_dc, storage_type=conf.STORAGE_TYPE,
            version=conf.VERSION[0], cluster=cls.uncomp_cl, cpu=cls.uncomp_cpu
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4126")
    def test_move_host_supported_dc_cl(self):
        """
        1) Move the Host from the original DC to the newly created DC
        2) Attach label to the network in the new DC
        3) Check that the network is attached to the Host NIC
        4) Remove label from the network
        """

        if not hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.create_and_attach_label(
            label=self.label_1, networks=[self.net_1]
        ):
            conf.NET_EXCEPTION()

        sample = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT, sleep=1,
            func=ll_networks.check_network_on_nic, network=self.net_1,
            host=conf.HOST_1_NAME, nic=conf.HOST_1_NICS[1]
        )
        if not sample.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION()

        if not ll_networks.remove_label(
            labels=self.label_1, networks=[self.net_1]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4115")
    def test_move_host_unsupported_dc_cl(self):
        """
        1) Try to move the Host to the DC with 3.0 version
        2) Activate the Host in original DC after a move action failure
        """

        if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        if not ll_hosts.updateHost(
            positive=False, host=conf.HOST_1_NAME, cluster=self.uncomp_cl
        ):
            raise conf.NET_EXCEPTION()

        if not ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1) Move Host back to the original DC/Cluster
        2) Remove created DCs and Clusters from the setup.
        """

        hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=cls.cl_1
        )
        for dc, cl in (
            (cls.dc_name2, cls.cl_name2), (cls.uncomp_dc, cls.uncomp_cl)
        ):
            ll_datacenters.remove_datacenter(positive=True, datacenter=dc)
            ll_clusters.removeCluster(positive=True, cluster=cl)
        super(TestNetLabels07, cls).teardown_class()


@unittest_lib.common.skip_class_if(conf.PPC_ARCH, conf.PPC_SKIP_MESSAGE)
class TestNetLabels08(TestLabelTestCaseBase):

    """
    Check that after moving a Host with labeled interface between all the
    Cluster versions for the 3.1 DC, the network label feature is functioning
    as expected
    """
    __test__ = True

    labels = conf.LABEL_NAME[8][:5]
    dc_name2 = "new_DC_31_case08"
    cl_name2 = "new_CL_case08"
    comp_cl_name = [
        "".join(["COMP_CL3_case08-", str(i)]) for i in range(
            1, len(conf.VERSION)
        )
        ]
    dummys = conf.DUMMYS[:5]
    nets = conf.NETS[8][:5]

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
        if not ll_datacenters.addDataCenter(
            positive=True, name=cls.dc_name2, storage_type=conf.STORAGE_TYPE,
            version=conf.VERSION[1], local=False
        ):
            raise conf.NET_EXCEPTION()

        for ver, cluster in zip(conf.VERSION[1:], cls.comp_cl_name):
            if not ll_clusters.addCluster(
                positive=True, name=cluster, data_center=cls.dc_name2,
                version=ver, cpu=conf.CPU_NAME
            ):
                raise conf.NET_EXCEPTION()

        for index, cluster in enumerate(cls.comp_cl_name):
            local_dict = {
                conf.NETS[8][index]: {
                    "required": "false"
                }
            }
            networking_helper.prepare_networks_on_setup(
                networks_dict=local_dict, dc=cls.dc_name2, cluster=cluster
            )

    @polarion("RHEVM3-4124")
    def test_move_host_supported_cl(self):
        """
        1) Attach label to each dummy interface.
        2) Attach label to the network in the 3.1 Cluster
        3) Move the Host to the 3.1 Cluster
        4) Check that the network is attached to the Host NIC
        5) Remove label from the network
        6) Repeat the 4 steps above when moving from 3.1 Cluster up
        till you reach 3.4 Cluster
        """
        if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
            raise conf.NET_EXCEPTION()

        for lb, dummy, net in zip(self.labels, self.dummys, self.nets):
            if not hl_networks.create_and_attach_label(
                label=lb,
                host_nic_dict={
                    conf.HOST_1_NAME: [dummy]
                }
            ):
                raise conf.NET_EXCEPTION()

            if not hl_networks.create_and_attach_label(
                label=lb, networks=[net]
            ):
                raise conf.NET_EXCEPTION()

        for net, dummy, cluster in zip(
            self.nets, self.dummys, self.comp_cl_name
        ):
            if not ll_hosts.updateHost(
                positive=True, host=conf.HOST_1_NAME, cluster=cluster
            ):
                raise conf.NET_EXCEPTION()

            sample = apis_utils.TimeoutingSampler(
                timeout=conf.SAMPLER_TIMEOUT, sleep=1,
                func=ll_networks.check_network_on_nic,
                network=net, host=conf.HOST_1_NAME, nic=dummy
            )

            if not sample.waitForFuncStatus(result=True):
                raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1) Move host back to its original Cluster
        2) Remove DC in 3.1 with all its Clusters from the setup.
        3) Call super to remove all labels and networks from setup
        """

        hl_host.deactivate_host_if_up(conf.HOST_1_NAME)

        ll_hosts.updateHost(
            positive=True, host=conf.HOST_1_NAME, cluster=conf.CL_0
        )

        ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME)

        for cl in cls.comp_cl_name:
            ll_clusters.removeCluster(positive=True, cluster=cl)

        ll_datacenters.remove_datacenter(
            positive=True, datacenter=cls.dc_name2
        )
        super(TestNetLabels08, cls).teardown_class()


class TestNetLabels09(TestLabelTestCaseBase):

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

    net_1 = conf.NETS[9][0]
    net_2 = conf.NETS[9][1]
    label_1 = conf.LABEL_NAME[9][0]
    cl_name2 = "new_CL_case09"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create a VM network on the DC/Cluster, that the Host resides on
        3) Add the same label to the network as on the Host NIC
        4) Create a new Cluster for current DC
        5) Create a non-VM network in a new Cluster
        6) Add the same label to non-VM network as for VM network in 3)
        """

        if not hl_networks.create_and_attach_label(
            label=cls.label_1, networks=[cls.net_1],
            host_nic_dict={
                conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]
            }
        ):
            conf.NET_EXCEPTION()

        if not ll_clusters.addCluster(
            positive=True, name=cls.cl_name2, data_center=conf.DC_0,
            version=conf.COMP_VERSION, cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION()

        local_dict = {
            cls.net_2: {
                "usages": "", "required": "false"
            }
        }
        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict, dc=conf.DC_0, cluster=cls.cl_name2
        )

        if not hl_networks.create_and_attach_label(
            label=cls.label_1, networks=[cls.net_2]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=cls.net_1, host=conf.HOST_1_NAME, nic=conf.HOST_1_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

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

        if not hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_2, host=conf.HOST_1_NAME,
            nic=conf.HOST_1_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

        if not hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=conf.CL_0
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_1, host=conf.HOST_1_NAME,
            nic=conf.HOST_1_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1) Remove newly created Cluster from the setup.
        """

        ll_clusters.removeCluster(positive=True, cluster=cls.cl_name2)
        super(TestNetLabels09, cls).teardown_class()


class TestNetLabels10(TestLabelTestCaseBase):

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
    label_1 = conf.LABEL_NAME[10][0]
    label_2 = conf.LABEL_NAME[10][1]
    label_3 = conf.LABEL_NAME[10][2]
    net_1 = conf.NETS[10][0]
    net_2 = conf.NETS[10][1]
    net_3 = conf.NETS[10][2]
    net_4 = conf.NETS[10][3]
    net_5 = conf.NETS[10][4]
    net_6 = conf.NETS[10][5]

    @classmethod
    def setup_class(cls):
        """
        1) Add label_1 to the net_1 and net_2 VM networks
        2) Add label_2 to the net_3 and net_4 non-VM networks
        3) Add label_3 to the net_5 and net_6 VM and non-VM networks
        """

        for label, net1, net2 in (
            (cls.label_1, cls.net_1, cls.net_2),
            (cls.label_2, cls.net_3, cls.net_4),
            (cls.label_3, cls.net_5, cls.net_6)
        ):
            if not hl_networks.create_and_attach_label(
                label=label, networks=[net1, net2]
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4121")
    def test_label_restrictioin(self):
        """
        1) Put label1 on Host NIC of the Host
        2) Check that the networks net_1 and net_2 are not attached to the Host
        3) Replace label_1 with label_2 on Host NIC of the Host
        4) Check that the networks net_3 and net4 are not attached to the Host
        5) Replace label_2 with label_3 on Host NIC of the Host
        6) Check that the networks net5 and net6 are not attached to the Host
        7) Replace label_3 with label_4 on Host NIC of the Host
        """

        for label, net1, net2 in (
            (self.label_1, self.net_1, self.net_2),
            (self.label_2, self.net_3, self.net_4),
            (self.label_3, self.net_5, self.net_6)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=False, label=label, network_on_nic=False,
                add_net_to_label=False, networks=[net1, net2],
                host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                }, nic_list=[conf.HOST_0_NICS[1], conf.HOST_0_NICS[1]]
            )
            if not ll_networks.remove_label(
                host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                }
            ):
                raise conf.NET_EXCEPTION()


class TestNetLabels11(TestLabelTestCaseBase):

    """
    1) Check that when adding a new labeled VM network to the system which
    has another VM network with the same label attached to the Host, will not
    attach the new network to the Host
    2) Check that when adding a new labeled non-VM network to the system which
    has another non-VM network with the same label attached to the Host, will
    not attach the new network to the Host
    """
    __test__ = True

    net_1 = conf.NETS[11][0]
    net_2 = conf.NETS[11][1]
    net_3 = conf.NETS[11][2]
    net_4 = conf.NETS[11][3]
    label_1 = conf.LABEL_NAME[11][0]
    label_2 = conf.LABEL_NAME[11][1]

    @classmethod
    def setup_class(cls):
        """
        1) Add label_1 to the net_1 VM network
        2) Add label_2 to the net_2 non-VM network
        3) Add label_1 to the Host NIC
        4) Add label_2 to the Host NIC
        """

        for label, nic, net in (
            (cls.label_1, conf.HOST_0_NICS[1], cls.net_1),
            (cls.label_2, conf.HOST_0_NICS[2], cls.net_2)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=True, label=label, networks=[net],
                host_nic_dict={
                    conf.HOST_0_NAME: [nic]
                }, nic_list=[nic]
            )

    @polarion("RHEVM3-4117")
    def test_label_restrictioin_vm(self):
        """
        1) Put the same label on the net3 VM network as on network net_1
        2) Check that the new VM network net3 is not attached to the Host NIC
        3) Check that net_1 is still attached to the Host NIC
        """

        for positive, net, network_on_nic in (
            (True, self.net_3, False), (False, self.net_1, True)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=positive, network_on_nic=network_on_nic,
                label=self.label_1, networks=[net], host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[1]]
                }, attach_to__host=False, nic_list=[conf.HOST_0_NICS[1]]
            )

    @polarion("RHEVM3-4118")
    def test_label_restrictioin_non_vm(self):
        """
        1) Attach the same label on the net_4 VM network as on network net_2
        2) Check that the new non-VM network net4 is not attached to the Host
            NIC
        3) Check that net_2 is still attached to the Host NIC
        """

        for positive, net, network_on_nic in (
            (True, self.net_4, False), (False, self.net_2, True)
        ):
            helper.add_label_and_check_network_on_nic(
                positive=positive, network_on_nic=network_on_nic,
                label=self.label_2, networks=[net], host_nic_dict={
                    conf.HOST_0_NAME: [conf.HOST_0_NICS[2]]
                }, attach_to__host=False, nic_list=[conf.HOST_0_NICS[2]]
            )


class TestNetLabels12(TestLabelTestCaseBase):

    """
    Check that after moving a Host with labeled network red attached to the
    labeled interface (label=lb1) to another Cluster with network blue
    labeled with lb1, the network blue will be attached to the labeled
    interface.
    """
    __test__ = True

    net_1 = conf.NETS[12][0]
    net_2 = conf.NETS[12][1]
    label_1 = conf.LABEL_NAME[12][0]
    cl_name2 = "new_CL_case12"

    @classmethod
    def setup_class(cls):
        """
        1) Create label on the NIC of the Host
        2) Create additional Cluster on the original DC
        4) Create network net1 on the original Cluster
        5) Create network net2 on newly created Cluster
        6) Attach the same label as on the Host NIC to networks net_1 and net_2
        7) Check that the network net_1 is attached to the Host NIC
        """

        if not ll_clusters.addCluster(
            positive=True, name=cls.cl_name2, data_center=conf.DC_0,
            version=conf.COMP_VERSION, cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION()

        local_dict2 = {
            cls.net_2: {
                "required": "false"
            }
        }

        networking_helper.prepare_networks_on_setup(
            networks_dict=local_dict2, dc=conf.DC_0, cluster=cls.cl_name2
        )

        net_list = [cls.net_1, cls.net_2]

        if not hl_networks.create_and_attach_label(
            label=cls.label_1, networks=net_list,
            host_nic_dict={conf.HOST_1_NAME: [conf.HOST_1_NICS[1]]}
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=cls.net_1, host=conf.HOST_1_NAME, nic=conf.HOST_1_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4125")
    def test_move_host(self):
        """
        1) Move the Host from the original Cluster to the newly created one
        2) Check that the network net_2 is attached to the Host NIC
        """
        if not hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=self.cl_name2
        ):
            raise conf.NET_EXCEPTION()

        if not ll_networks.check_network_on_nic(
            network=self.net_2, host=conf.HOST_1_NAME, nic=conf.HOST_1_NICS[1]
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1) Move host back to its original Cluster
        2) Remove label from Host NIC
        3) Remove additional Cluster from the setup
        """

        hl_host.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=conf.CL_0
        )

        ll_clusters.removeCluster(positive=True, cluster=cls.cl_name2)
        super(TestNetLabels12, cls).teardown_class()
