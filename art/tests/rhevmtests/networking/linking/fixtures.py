#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for linking
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as linking_conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def prepare_setup_linking(request):
    """
    Prepare setup
    """
    linking = NetworkFixtures()

    def fin2():
        """
        Remove networks from setup
        """
        linking.remove_networks_from_setup(hosts=linking.host_0_name)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=linking.vm_0)
    request.addfinalizer(fin1)

    assert network_helper.run_vm_once_specific_host(
        vm=linking.vm_0, host=linking.host_0_name, wait_for_up_status=True
    )
    assert hl_networks.createAndAttachNetworkSN(
        data_center=linking.dc_0, cluster=linking.cluster_0,
        host=linking.vds_0_host, network_dict=linking_conf.VLAN_NET_DICT,
        auto_nics=[0, 1]
    )


@pytest.fixture(scope="class")
def teardown_all_cases_linking(request, prepare_setup_linking):
    """
    Teardown for all cases
    """
    linking = NetworkFixtures()
    nic_list = request.node.cls.nic_list
    vm = request.node.cls.vm

    def fin():
        """
        Update vNIC and remove vNICs from VM
        """
        for nic in nic_list:
            if vm == linking.vm_0:
                ll_vms.updateNic(
                    positive=True, vm=vm, nic=nic, plugged=False
                )
            ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def fixture_case_01(request, teardown_all_cases_linking):
    """
    Fixture for case01
    """
    vm = request.node.cls.vm
    nic1 = request.node.cls.nic1
    net = request.node.cls.net
    assert ll_vms.addNic(
        positive=True, vm=vm, name=nic1, network=net
    )


@pytest.fixture(scope="class")
def fixture_case_02(request, teardown_all_cases_linking):
    """
    Fixture for case02
    """
    vm = request.node.cls.vm
    nic_list = request.node.cls.nic_list
    int_type_list = request.node.cls.int_type_list
    net_list = request.node.cls.net_list
    plug_values = request.node.cls.plug_values
    link_values = request.node.cls.link_values
    for int_type, nic, net, plug_value, link_value in zip(
        int_type_list, nic_list, net_list, plug_values, link_values
    ):
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic, network=net,
            interface=int_type, plugged=plug_value, linked=link_value
        )


@pytest.fixture(scope="class")
def fixture_case_03(request, teardown_all_cases_linking):
    """
    Fixture for case03
    """
    linking = NetworkFixtures()
    vm = request.node.cls.vm
    net = request.node.cls.net
    nic1 = request.node.cls.nic1

    def fin():
        """
        Remove network
        """
        ll_networks.removeNetwork(
            positive=True, network=net, data_center=linking.dc_0
        )
    request.addfinalizer(fin)

    local_dict = {
        net: {
            "required": "false"
        }
    }
    assert hl_networks.createAndAttachNetworkSN(
        data_center=linking.dc_0, cluster=linking.cluster_0,
        network_dict=local_dict
    )
    assert ll_vms.addNic(
        positive=True, vm=vm, name=nic1, network=net
    )


@pytest.fixture(scope="class")
def fixture_case_04(request, teardown_all_cases_linking):
    """
    Fixture for case04
    """
    linking = NetworkFixtures()
    vm = request.node.cls.vm
    net = request.node.cls.net
    nic1 = request.node.cls.nic1
    vprofile = request.node.cls.vprofile

    def fin():
        """
        Remove vNIC profile
        """
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=vprofile, network=net
        )
    request.addfinalizer(fin)

    assert ll_networks.add_vnic_profile(
        positive=True, name=vprofile, cluster=linking.cluster_0,
        network=net, port_mirroring=True
    )
    assert ll_vms.addNic(
        positive=True, vm=vm, name=nic1, vnic_profile=vprofile, network=net
    )


@pytest.fixture(scope="class")
def fixture_case_05(request, teardown_all_cases_linking):
    """
    Fixture for case05
    """
    vm = request.node.cls.vm
    net = request.node.cls.net
    nic_list = request.node.cls.nic_list
    plug_states = request.node.cls.plug_states

    for nic, plug_state in zip(nic_list, plug_states):
        assert ll_vms.addNic(
            positive=True, vm=vm, name=nic, network=net, plugged=plug_state
        )


@pytest.fixture(scope="class")
def fixture_case_06(request, teardown_all_cases_linking):
    """
    Fixture for case06
    """
    linking = NetworkFixtures()
    vm = request.node.cls.vm
    nic1 = request.node.cls.nic1
    net1 = request.node.cls.net1
    net2 = request.node.cls.net2
    vprofile = request.node.cls.vprofile

    def fin2():
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=vm)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove vNIC profile
        """
        ll_networks.remove_vnic_profile(
            positive=True, vnic_profile_name=vprofile, network=net2
        )
    request.addfinalizer(fin1)

    assert ll_vms.addNic(
        positive=True, vm=vm, name=nic1, network=net1
    )
    assert ll_networks.add_vnic_profile(
        positive=True, name=vprofile, cluster=linking.cluster_0,
        network=net2, port_mirroring=True
    )
