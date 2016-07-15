#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for labels
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_host
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.unittest_lib.network as ul_network
import config as label_conf
import helper
import rhevmtests.networking.config as conf
from rhevmtests.networking.fixtures import NetworkFixtures


class Labels(NetworkFixtures):
    """
    Fixtures for labels
    """
    pass


@pytest.fixture(scope="module")
def labels_prepare_setup(request):
    """
    Prepare setup
    """
    labels = Labels()

    def fin():
        """
        Finalizer for remove networks
        """
        labels.remove_networks_from_setup(
            hosts=[labels.host_0_name, labels.host_1_name]
        )
    request.addfinalizer(fin)

    labels.prepare_networks_on_setup(
        networks_dict=label_conf.NET_DICT, dc=labels.dc_0,
        cluster=labels.cluster_0
    )


@pytest.fixture(scope="class")
def all_classes_teardown(request, labels_prepare_setup):
    """
    Teardown fixture for all cases
    """
    labels = Labels()

    def fin():
        """
         Remove networks from host.
        """
        for host in [labels.host_0_name, labels.host_1_name]:
            hl_host_network.clean_host_interfaces(host_name=host)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def case_01_fixture(request, all_classes_teardown):
    """
    fixture for case01:
        1) Create bond from 2 phy interfaces
        2) Create and attach label to the network
        3) Attach label to Host Nic
    """
    labels = Labels()
    bond = request.node.cls.bond
    net_1 = request.node.cls.net_1
    label_1 = request.node.cls.label_1
    vlan_id_1 = request.node.cls.vlan_id_1
    vlan_nic = ul_network.vlan_int_name(labels.host_0_nics[1], vlan_id_1)
    network_host_api_dict = {
        "add": {
            "1": {
                "slaves": label_conf.DUMMYS[:2],
                "nic": bond,
            }
        }
    }

    assert hl_host_network.setup_networks(
        labels.host_0_name, **network_host_api_dict
    )

    assert helper.add_label_and_check_network_on_nic(
        positive=True, label=label_1, networks=[net_1],
        host_nic_dict={
            labels.host_0_name: [labels.host_0_nics[1]]
        },
        vlan_nic=vlan_nic
    )


@pytest.fixture(scope="class")
def case_02_fixture(request, all_classes_teardown):
    """
    fixture for case02:
        1) Create bond from 2 dummys on 2 Hosts.
        2) Attach label network to Host Nic and bond on both Hosts
        3) Make sure the networks was attached to Host Nic and Bond on both
        Hosts.
    """
    labels = Labels()
    bond = request.node.cls.bond
    vlan_id = request.node.cls.vlan_id
    label_1 = request.node.cls.label_1
    label_2 = request.node.cls.label_2
    net_1 = request.node.cls.net_1
    net_2 = request.node.cls.net_2

    network_host_api_dict = {
        "add": {
            "1": {
                "slaves": label_conf.DUMMYS[:2],
                "nic": bond
            }
        }
    }

    for host in (labels.host_0_name, labels.host_1_name):
        assert hl_host_network.setup_networks(
            host_name=host, **network_host_api_dict
        )

    nic_dict = {
        labels.host_0_name: [labels.host_0_nics[1]],
        labels.host_1_name: [labels.host_1_nics[1]]
    }
    bond_dict = {
        labels.host_0_name: [bond],
        labels.host_1_name: [bond]
    }
    vlan_nic_1 = ul_network.vlan_int_name(labels.host_0_nics[1], vlan_id)
    vlan_nic_2 = ul_network.vlan_int_name(labels.host_1_nics[1], vlan_id)
    nic_list = [vlan_nic_2, vlan_nic_1]
    bond_list = [bond, bond]

    for label, dict_nic, net, nic in (
        (label_1, nic_dict, net_1, nic_list),
        (label_2, bond_dict, net_2, bond_list)
    ):
        assert helper.add_label_and_check_network_on_nic(
            positive=True, label=label, host_nic_dict=dict_nic,
            networks=[net], nic_list=nic
        )


@pytest.fixture(scope="class")
def case_03_fixture(request, all_classes_teardown):
    """
   fixture for case03:
       1) Create and attach label to the VLAN non-VM network
       2) Attach the same label to Host Nic on one Host
   """
    labels = Labels()
    net_1 = request.node.cls.net_1
    vlan_id = request.node.cls.vlan_id
    label_1 = request.node.cls.label_1

    vlan_nic = ul_network.vlan_int_name(labels.host_0_nics[1], vlan_id)
    assert helper.add_label_and_check_network_on_nic(
        positive=True, label=label_1, networks=[net_1],
        host_nic_dict={
            labels.host_0_name: [labels.host_0_nics[1]]
        },
        vlan_nic=vlan_nic
    )


@pytest.fixture(scope="class")
def case_04_fixture(request, all_classes_teardown):
    """
    fixture for case04:
        Create network on DC level only.
    """
    labels = Labels()
    net_1 = request.node.cls.net_1

    local_dict1 = {
        net_1: {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=labels.dc_0, network_dict=local_dict1
    )


@pytest.fixture(scope="class")
def case_05_fixture(request, all_classes_teardown):
    """
    fixture for case05:
        1) Attach label to each network.
        2) Attach label to each dummy interface.
    """
    labels = Labels()
    nets = request.node.cls.nets
    labels_list = request.node.cls.labels
    vlan_id_list = request.node.cls.vlan_id_list
    dummys_list = request.node.cls.dummys_list

    for label, net in zip(labels_list, nets):
        assert hl_networks.create_and_attach_label(
            label=label, networks=[net]
        )

    for i, (label, dummy, net, vlan_id) in enumerate(zip(
        labels_list, dummys_list, nets, vlan_id_list
    )):
        nic = ul_network.vlan_int_name(dummy, vlan_id) if i < 3 else dummy
        assert helper.add_label_and_check_network_on_nic(
            positive=True, label=label, add_net_to_label=False,
            networks=[net], nic_list=[nic],
            host_nic_dict={
                labels.host_0_name: [dummy]
            },
        )


@pytest.fixture(scope="class")
def case_06_fixture(request, all_classes_teardown):
    """
    fixture for case06:
        1) Create and attach label to the network.
        2) Attach label to Host Nic.
    """
    labels = Labels()
    net_1 = request.node.cls.net_1
    label_1 = request.node.cls.label_1

    assert helper.add_label_and_check_network_on_nic(
        positive=True, label=label_1, networks=[net_1],
        host_nic_dict={
            labels.host_0_name: [labels.host_0_nics[1]]
        }, nic_list=[labels.host_0_nics[1]]
    )


@pytest.fixture(scope="class")
def case_07_fixture(request, all_classes_teardown):
    """
   fixture for case08:
        1) Create label on the NIC of the Host
        2) Create a new DC with 3.6 version (the lowest version that all its
        clusters support network labels feature)
        3) Create Clusters for all supported versions for that DC (3.6 and
        above)
        5) Create a VM network in the first cluster
        6) Create a non VM network in the second cluster
        7) Create a VLAN VM network in the third cluster
        8) Create a VLAN non VM network the fourth cluster
        9) Attach label to each dummy interface
        10) Deactivate host and move the host to 3.6 cluster
   """
    labels = Labels()
    dc_name2 = request.node.cls.dc_name2
    comp_cl_name = request.node.cls.comp_cl_name
    labels_list = request.node.cls.labels
    dummys = request.node.cls.dummys

    def fin():
        """
        Finalizer for:
            1) Move host back to its original cluster
            2) Remove DC in 3.6 with all its clusters from the setup.
            3) Remove all labels and networks from setup
        """
        hl_host.deactivate_host_if_up(conf.HOST_1_NAME)

        ll_hosts.updateHost(
            positive=True, host=labels.host_1_name, cluster=labels.cluster_0
        )

        ll_hosts.activateHost(positive=True, host=labels.host_1_name)

        for cl in comp_cl_name:
            ll_clusters.removeCluster(positive=True, cluster=cl)

        ll_datacenters.remove_datacenter(positive=True, datacenter=dc_name2)
    request.addfinalizer(fin)

    assert ll_datacenters.addDataCenter(
        positive=True, name=dc_name2,
        version=conf.COMP_VERSION_4_0[0], local=False
    )

    for index, cluster in enumerate(comp_cl_name):
        assert ll_clusters.addCluster(
            positive=True, name=cluster, data_center=dc_name2,
            version=conf.COMP_VERSION_4_0[index], cpu=conf.CPU_NAME
        )

        assert hl_networks.createAndAttachNetworkSN(
            data_center=dc_name2, cluster=cluster,
            network_dict=label_conf.local_dict
        )

    for index, (dummy, label) in enumerate(zip(dummys, labels_list)):
        assert hl_networks.create_and_attach_label(
            label=label, host_nic_dict={
                labels.host_1_name: [dummy]
            }
        )

    assert ll_hosts.deactivateHost(positive=True, host=labels.host_1_name)


@pytest.fixture(scope="class")
def case_08_fixture(request, all_classes_teardown):
    """
    fixture for case10:
        1) Add label_1 to the net_1 and net_2 VM networks
        2) Add label_2 to the net_3 and net_4 non-VM networks
        3) Add label_3 to the net_5 and net_6 VM and non-VM networks
    """

    label_1 = request.node.cls.label_1
    label_2 = request.node.cls.label_2
    label_3 = request.node.cls.label_3
    net_1 = request.node.cls.net_1
    net_2 = request.node.cls.net_2
    net_3 = request.node.cls.net_3
    net_4 = request.node.cls.net_4
    net_5 = request.node.cls.net_5
    net_6 = request.node.cls.net_6

    for label, net1, net2 in (
        (label_1, net_1, net_2),
        (label_2, net_3, net_4),
        (label_3, net_5, net_6)
    ):
        assert hl_networks.create_and_attach_label(
            label=label, networks=[net1, net2]
        )


@pytest.fixture(scope="class")
def case_09_fixture(request, all_classes_teardown):
    """
    fixture for case11:
        1) Add label_1 to the net_1 VM network
        2) Add label_2 to the net_2 non-VM network
        3) Add label_1 to the Host NIC
        4) Add label_2 to the Host NIC
    """
    labels = Labels()
    net_1 = request.node.cls.net_1
    net_2 = request.node.cls.net_2
    label_1 = request.node.cls.label_1
    label_2 = request.node.cls.label_2

    for label, nic, net in (
        (label_1, labels.host_0_nics[1], net_1),
        (label_2, labels.host_0_nics[2], net_2)
    ):
        assert helper.add_label_and_check_network_on_nic(
            positive=True, label=label, networks=[net],
            host_nic_dict={
                conf.HOST_0_NAME: [nic]
            }, nic_list=[nic]
        )
