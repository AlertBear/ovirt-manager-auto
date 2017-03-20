#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Tests for MultiHost network feature

The following elements will be used for the testing:
1 DC, 1 Cluster, 3 Hosts, 1 template, 2 VMs (running and non-running),
1 Extra cluster, dummy interfaces, interface BONDs
"""

import pytest

import config as multi_host_conf
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion
from art.unittest_lib import attr, NetworkTest, testflow
from fixtures import (
    add_vnics_to_vms, add_vnic_to_template, move_host_to_cluster,
    add_network_to_cluster
)
from rhevmtests.fixtures import start_vm, create_clusters
from rhevmtests.networking.fixtures import (
    NetworkFixtures, setup_networks_fixture, clean_host_interfaces
)


@pytest.fixture(scope="module", autouse=True)
def multi_host_prepare_setup(request):
    """
    Prepare setup of networks for tests
    """
    multi_host = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        network_helper.remove_networks_from_setup(hosts=multi_host.host_0_name)
    request.addfinalizer(fin)

    testflow.setup("Create networks on setup")
    network_helper.prepare_networks_on_setup(
        networks_dict=multi_host_conf.SETUP_NETWORKS_DICT, dc=multi_host.dc_0,
        cluster=multi_host.cluster_0
    )


@attr(tier=2)
@pytest.mark.usefixtures(
    clean_host_interfaces.__name__,
    create_clusters.__name__,
    add_network_to_cluster.__name__,
    move_host_to_cluster.__name__,
    setup_networks_fixture.__name__,
    add_vnics_to_vms.__name__,
    add_vnic_to_template.__name__,
    start_vm.__name__
)
class TestMultiHostNetworkProperties(NetworkTest):
    """
    Tests valid and invalid network properties updates on network attached to
    host, running VM, non-running VM, template and bond

    Tests on networks attached to host:
    1. Update non-VM property on network attached to host
    2. Update VM property on network attached to host
    3. Update VLAN 2 property on network attached to host
    4. Update VLAN 3 property on network attached to host
    5. Remove VLAN from network attached to host
    6. Update MTU 9000 property on network attached to host
    7. Update MTU 1500 property on network attached to host
    8. NEGATIVE: Rename network attached to host

    Tests on networks attached to running VM:
    1. Update MTU 9000 property on network attached to running VM
    2. Update VLAN property on network attached to running VM
    3. NEGATIVE: Update VM property on network used by running VM to
       be non-VM

    Test on networks attached to non-running VM
    1. Update MTU property on network attached to non-running VM
    2. Update VLAN property on network attached to non-running VM
    3. NEGATIVE: Rename network on non-running VM

    Test on networks attached to template:
    1. NEGATIVE: Update VM property on network used by template to be
       non-VM network
    2. Update MTU property on network used by template
    3. Update VLAN property on network used by template
    4. NEGATIVE: Rename network used by template

    Test on networks attached to two hosts:
    1. Update MTU and VLAN properties on network used by two hosts
    2. Update MTU and VLAN properties on network used by two hosts, but on
        different clusters

    Test on networks attached to bond:
    1. Update non-VM property on network used by bond
    2. Update VM property on network used by bond
    3. Update VLAN 9 property on network used by bond
    4. Update VLAN 10 property on network used by bond
    5. Update MTU 9000 property on network used by bond
    6. Update MTU 1500 property on network used by bond
    7. NEGATIVE: Remove VLAN property from network attached to bond

    """
    # General settings
    dc = conf.DC_0

    # MTU settings
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]

    # VLANs
    vlan_2 = conf.VLAN_IDS.pop(0)
    vlan_3 = conf.VLAN_IDS.pop(0)
    vlan_4 = conf.VLAN_IDS.pop(0)
    vlan_5 = conf.VLAN_IDS.pop(0)
    vlan_6 = conf.VLAN_IDS.pop(0)
    vlan_7 = conf.VLAN_IDS.pop(0)
    vlan_8 = conf.VLAN_IDS.pop(0)
    vlan_9 = conf.VLAN_IDS.pop(0)
    vlan_10 = conf.VLAN_IDS.pop(0)

    # BONDs
    bond_0_vm_net = multi_host_conf.BOND_NAMES.pop(0)
    bond_1_non_vm_net = multi_host_conf.BOND_NAMES.pop(0)
    bond_2_net = multi_host_conf.BOND_NAMES.pop(0)
    bond_3_vlan_net = multi_host_conf.BOND_NAMES.pop(0)
    bond_4_mtu_net = multi_host_conf.BOND_NAMES.pop(0)

    # Networks
    vm_network_attached_to_host = multi_host_conf.NETS[1][0]
    non_vm_network_attached_to_host = multi_host_conf.NETS[1][1]
    network_attached_to_host = multi_host_conf.NETS[1][2]
    vlan_network_attached_to_host = multi_host_conf.NETS[1][3]
    network_attached_to_running_vm = multi_host_conf.NETS[1][4]
    network_attached_to_non_running_vm = multi_host_conf.NETS[1][5]
    network_attached_to_template = multi_host_conf.NETS[1][6]
    network_attached_to_two_hosts = multi_host_conf.NETS[1][7]
    network_attached_to_two_hosts_diff_cluster = multi_host_conf.NETS[1][8]
    vm_network_attached_to_bond = multi_host_conf.NETS[1][9]
    non_vm_network_attached_to_bond = multi_host_conf.NETS[1][10]
    network_attached_to_bond = multi_host_conf.NETS[1][11]
    vlan_network_attached_to_bond = multi_host_conf.NETS[1][12]
    mtu_network_attached_to_bond = multi_host_conf.NETS[1][13]

    # setup_networks_fixture params
    hosts_nets_nic_dict = {
        0: {
            "2": {
                "network": network_attached_to_two_hosts_diff_cluster,
                "nic": 2
            },
            "3": {
                "network": network_attached_to_two_hosts,
                "nic": 3
            },
            "10": {
                "network": network_attached_to_host,
                "nic": 10
            },
            "11": {
                "network": vm_network_attached_to_host,
                "nic": 11
            },
            "12": {
                "network": non_vm_network_attached_to_host,
                "nic": 12
            },
            "13": {
                "network": network_attached_to_running_vm,
                "nic": 13
            },
            "14": {
                "network": network_attached_to_non_running_vm,
                "nic": 14
            },
            "15": {
                "network": vm_network_attached_to_bond,
                "nic": bond_0_vm_net,
                "slaves": [15, 16]
            },
            "17": {
                "network": non_vm_network_attached_to_bond,
                "nic": bond_1_non_vm_net,
                "slaves": [17, 18]
            },
            "19": {
                "network": network_attached_to_bond,
                "nic": bond_2_net,
                "slaves": [19, 20]
            },
            "21": {
                "network": vlan_network_attached_to_bond,
                "nic": bond_3_vlan_net,
                "slaves": [21, 22]
            },
            "23": {
                "network": mtu_network_attached_to_bond,
                "nic": bond_4_mtu_net,
                "slaves": [23, 24]
            },
            "25": {
                "network": vlan_network_attached_to_host,
                "nic": 25
            },
            "26": {
                "network": network_attached_to_template,
                "nic": 26
            }
        },
        1: {
            "3": {
                "network": network_attached_to_two_hosts,
                "nic": 3
            }
        },
        2: {
            "2": {
                "network": network_attached_to_two_hosts_diff_cluster,
                "nic": 2
            }
        }
    }

    # add_vnics_to_vms fixture params
    add_vnics_to_vms_params = {
        conf.VM_0: {
            "vnic_name": multi_host_conf.VNICS[1][0],
            "network": network_attached_to_running_vm
        },
        conf.VM_1: {
            "vnic_name": multi_host_conf.VNICS[1][1],
            "network": network_attached_to_non_running_vm
        }
    }

    # start_vm fixture params
    start_vms_dict = {
        conf.VM_0: {
            "host": None
        }
    }

    # add_vnic_to_template fixture params
    template_network = network_attached_to_template
    template_vm_nic = multi_host_conf.VNICS[1][2]
    template_dc = dc
    template_name = conf.TEMPLATE_NAME[0]

    # create_clusters fixture params
    clusters_dict = {
        multi_host_conf.EXTRA_CLUSTER_NAME: {
            "name": multi_host_conf.EXTRA_CLUSTER_NAME,
            "data_center": dc,
            "cpu": conf.CPU_NAME,
            "version": conf.COMP_VERSION
        },
    }

    # add_network_to_cluster fixture params
    cl_name = multi_host_conf.EXTRA_CLUSTER_NAME
    cl_net = network_attached_to_two_hosts_diff_cluster

    # move_host_to_cluster fixture params
    cl_src_cluster = conf.CL_0
    cl_dst_cluster = multi_host_conf.EXTRA_CLUSTER_NAME
    cl_host = 2

    # Test params = [
    #   network name, network properties to update,
    #   True for positive test or False for negative test
    # ]

    # Test params: Update non-VM property on network attached to host
    non_vm_net = [
        vm_network_attached_to_host,
        {
            "bridge": False,
            "nic": 11
        },
        True
    ]

    # Test params: Update VM property on network attached to host
    vm_net = [
        non_vm_network_attached_to_host,
        {
            "bridge": True,
            "nic": 12
        },
        True
    ]

    # Test params: Update VLAN-2 property on network attached to host
    net_vlan_2 = [
        network_attached_to_host,
        {
            "vlan_id": vlan_2,
            "nic": 10
        },
        True
    ]

    # Test params: Update VLAN-3 property on network attached to host
    net_vlan_3 = [
        network_attached_to_host,
        {
            "vlan_id": vlan_3,
            "nic": 10
        },
        True
    ]

    # Test params: Remove VLAN from network attached to host
    remove_vlan_from_network = [
        vlan_network_attached_to_host,
        {
            "vlan_id": None,
            "nic": 25
        },
        True
    ]

    # Test params: Update MTU 9000 property on network attached to host
    net_mtu_9000 = [
        network_attached_to_host,
        {
            "mtu": mtu_9000,
            "nic": 10
        }, True
    ]

    # Test params: Update MTU 1500 property on network attached to host
    net_mtu_1500 = [
        network_attached_to_host,
        {
            "mtu": mtu_1500,
            "nic": 10
        },
        True
    ]

    # Test params: Update MTU 9000 property on network attached to running VM
    net_mtu_on_running_vm = [
        network_attached_to_running_vm,
        {
            "mtu": mtu_9000,
            "nic": 13
        },
        True
    ]

    # Test params: Update VLAN property on network attached to running VM
    net_vlan_on_running_vm = [
        network_attached_to_running_vm,
        {
            "vlan_id": vlan_4,
            "nic": 13
        },
        True
    ]

    # Test params: Update non-VM property on network attached to non-running VM
    net_used_by_non_running_vm_to_be_non_vm = [
        network_attached_to_non_running_vm,
        {
            "bridge": False,
            "nic": 14
        },
        False
    ]

    # Test params: Update MTU property on network attached to non-running VM
    net_mtu_on_non_running_vm = [
        network_attached_to_non_running_vm,
        {
            "mtu": mtu_9000,
            "nic": 14
        },
        True
    ]

    # Test params: Update VLAN property on network attached to non-running VM
    net_vlan_on_non_running_vm = [
        network_attached_to_non_running_vm,
        {
            "vlan_id": vlan_5,
            "nic": 14
        },
        True
    ]

    # Test params: Update MTU property on network used by template
    net_used_by_template_mtu = [
        network_attached_to_template,
        {
            "mtu": mtu_9000,
            "nic": 26
        },
        True
    ]

    # Test params: Update VLAN property on network used by template
    net_used_by_template_vlan = [
        network_attached_to_template,
        {
            "vlan_id": vlan_6,
            "nic": 26
        },
        True
    ]

    # Test params: Update MTU and VLAN properties on network used by two hosts
    net_used_by_hosts_mtu_and_vlan = [
        network_attached_to_two_hosts,
        {
            "vlan_id": vlan_7,
            "mtu": mtu_9000,
            "nic": 3,
            "hosts": [0, 1],
            "matches": 2
        },
        True
    ]

    # Test params: Update MTU and VLAN properties on network used by two hosts,
    # but on different clusters
    net_used_by_hosts_mtu_vlan_diff_cl = [
        network_attached_to_two_hosts_diff_cluster,
        {
            "vlan_id": vlan_8,
            "mtu": mtu_9000,
            "nic": 2,
            "hosts": [0, 2],
            "matches": 2
        },
        True
    ]

    # Test params: Update non-VM property on network used by bond
    non_vm_net_on_bond = [
        vm_network_attached_to_bond,
        {
            "nic": bond_0_vm_net,
            "bridge": False
        },
        True
    ]

    # Test params: Update VM property on network used by bond
    vm_net_on_bond = [
        non_vm_network_attached_to_bond,
        {
            "nic": bond_1_non_vm_net,
            "bridge": True
        },
        True
    ]

    # Test params: Update VLAN 9 property on network used by bond
    vlan_9_on_bond = [
        network_attached_to_bond,
        {
            "nic": bond_2_net,
            "vlan_id": vlan_9
        },
        True
    ]

    # Test params: Update VLAN 10 property on network used by bond
    vlan_10_on_bond = [
        network_attached_to_bond,
        {
            "nic": bond_2_net,
            "vlan_id": vlan_10
        },
        True
    ]

    # Test params: Update MTU 9000 property on network used by bond
    mtu_9000_on_bond = [
        network_attached_to_bond,
        {
            "nic": bond_2_net,
            "mtu": mtu_9000
        },
        True
    ]

    # Test params: Update MTU 1500 property on network used by bond
    mtu_1500_on_bond = [
        mtu_network_attached_to_bond,
        {
            "nic": bond_4_mtu_net,
            "mtu": mtu_1500
        },
        True
    ]

    # Test params: Remove VLAN property on network attached to bond
    remove_vlan_from_bond = [
        vlan_network_attached_to_bond,
        {
            "nic": bond_3_vlan_net,
            "vlan_id": None
        },
        True
    ]

    # Test params: Rename network on host
    rename_net_used_by_host = [
        network_attached_to_host,
        {
            "name": multi_host_conf.NETWORK_RENAME_TEST,
            "nic": 10
        },
        False
    ]

    # Test params: Rename network on non-running VM
    rename_net_used_by_non_running_vm = [
        network_attached_to_non_running_vm,
        {
            "name": multi_host_conf.NETWORK_RENAME_TEST,
            "nic": 14
        },
        False
    ]

    # Test params: Rename network used by template
    rename_net_used_by_template = [
        network_attached_to_template,
        {
            "name": multi_host_conf.NETWORK_RENAME_TEST,
            "nic": 26
        },
        False
    ]

    # Test params: Update VM property on network used by running
    # VM to be non-VM
    net_used_by_running_vm_to_be_non_vm = [
        network_attached_to_running_vm,
        {
            "bridge": False,
            "nic": 13
        },
        False
    ]

    # Test params: Update VM property on network used by template to
    # be non-VM
    net_used_by_template_to_be_non_vm = [
        network_attached_to_template,
        {
            "bridge": False,
            "nic": 26
        },
        False
    ]

    @pytest.mark.parametrize(
        ("net", "params", "positive"),
        [
            # Tests on networks attached to host
            polarion("RHEVM3-4072")(non_vm_net),
            polarion("RHEVM-19355")(vm_net),
            polarion("RHEVM3-4067")(net_vlan_2),
            polarion("RHEVM-19354")(net_vlan_3),
            polarion("RHEVM-19371")(remove_vlan_from_network),
            polarion("RHEVM3-4080")(net_mtu_9000),
            polarion("RHEVM-19364")(net_mtu_1500),
            polarion("RHEVM3-4079")(rename_net_used_by_host),

            # Tests on networks attached to running VM
            polarion("RHEVM3-4074")(net_mtu_on_running_vm),
            polarion("RHEVM-19369")(net_vlan_on_running_vm),
            polarion("RHEVM-19401")(net_used_by_running_vm_to_be_non_vm),

            # Tests on networks attached to non-running VM
            polarion("RHEVM-19361")(net_mtu_on_non_running_vm),
            polarion("RHEVM-19370")(net_vlan_on_non_running_vm),
            polarion("RHEVM-19362")(net_used_by_non_running_vm_to_be_non_vm),
            polarion("RHEVM-19365")(rename_net_used_by_non_running_vm),

            # Tests on networks attached to template
            polarion("RHEVM3-4073")(net_used_by_template_to_be_non_vm),
            polarion("RHEVM-19359")(net_used_by_template_mtu),
            polarion("RHEVM-19360")(net_used_by_template_vlan),
            polarion("RHEVM-19366")(rename_net_used_by_template),

            # Tests on networks attached to multiple hosts
            polarion("RHEVM3-4078")(net_used_by_hosts_mtu_and_vlan),
            polarion("RHEVM3-4077")(net_used_by_hosts_mtu_vlan_diff_cl),

            # Tests on networks attached to bond
            polarion("RHEVM3-4081")(non_vm_net_on_bond),
            polarion("RHEVM-19363")(vm_net_on_bond),
            polarion("RHEVM3-4069")(vlan_9_on_bond),
            polarion("RHEVM-19357")(vlan_10_on_bond),
            polarion("RHVEM3-4068")(mtu_9000_on_bond),
            polarion("RHEVM-19356")(mtu_1500_on_bond),
            polarion("RHEVM-19358")(remove_vlan_from_bond)
        ],
        ids=[
            # Tests on networks attached to host
            "Update non-VM property on network attached to host",
            "Update VM property on network attached to host",
            "Update VLAN 2 property on network attached to host",
            "Update VLAN 3 property on network attached to host",
            "Remove VLAN from network attached to host",
            "Update MTU 9000 property on network attached to host",
            "Update MTU 1500 property on network attached to host",
            "Rename network attached to host",

            # Tests on networks attached to running VM
            "Update MTU 9000 property on network attached to running VM",
            "Update VLAN property on network attached to running VM",
            "Update VM property on network used by running VM to be non-VM",

            # Tests on networks attached to non-running VM
            "Update MTU property on network attached to non-running VM",
            "Update VLAN property on network attached to non-running VM",
            (
                "Update VM property on network used by non-running VM "
                "to be non-VM"
            ),
            "Rename network on non-running VM",

            # Tests on networks attached to template
            (
                "Update VM property on network used by template to be"
                " non-VM network"
            ),
            "Update MTU property on network used by template",
            "Update VLAN property on network used by template",
            "Rename network used by template",

            # Tests on networks attached on multiple hosts
            "Update MTU and VLAN properties on network used by two hosts",
            (
               "Update MTU and VLAN properties on network used by two hosts, "
               "but on different clusters"
            ),

            # Tests on networks attached to bond
            "Update non-VM property on network used by bond",
            "Update VM property on network used by bond",
            "Update VLAN 9 property on network used by bond",
            "Update VLAN 10 property on network used by bond",
            "Update MTU 9000 property on network used by bond",
            "Update MTU 1500 property on network used by bond",
            "Remove VLAN property from network attached to bond"
        ]
    )
    def test_update_network(self, net, params, positive):
        """
        Tests for network properties update
        """
        assert_fail_msg = (
            "Failed to apply a valid network update" if positive else
            "Succeeded to apply an invalid network update"
        )
        neg_prefix_msg = "NEGATIVE: " if not positive else ""

        testflow.step(
            "{neg}Update network: {net_name} with properties: {params}".format(
                neg=neg_prefix_msg, net_name=net, params=params
            )
        )
        assert helper.update_network_and_check_changes(
            net=net, positive=positive, **params
        ), assert_fail_msg
