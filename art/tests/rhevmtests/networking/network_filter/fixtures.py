#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""

import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as nf_conf
import rhevmtests.networking.config as conf
from rhevmtests import networking
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def network_filter_prepare_setup(request):
    """
    Prepare setup
    """
    network_filter = NetworkFixtures()

    def fin():
        """
        Remove networks from setup
        """
        network_filter.remove_networks_from_setup(
            hosts=network_filter.host_0_name
        )
    request.addfinalizer(fin)

    network_filter.prepare_networks_on_setup(
        networks_dict=nf_conf.NETS_DICT, dc=network_filter.dc_0,
        cluster=network_filter.cluster_0
    )


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profiles
    """

    def fin():
        """
        Remove NIC from VM
        """
        networking.remove_unneeded_vnic_profiles()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_dc_cluster(request):
    """
    Create old version(3.6) of DC/Cluster
    """
    ext_dc = request.node.cls.ext_dc
    ext_cl = request.node.cls.ext_cl

    def fin():
        """
        Remove DC and cluster
        """
        hl_networks.remove_basic_setup(datacenter=ext_dc, cluster=ext_cl)
    request.addfinalizer(fin)

    assert hl_networks.create_basic_setup(
        datacenter=ext_dc, cluster=ext_cl, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION_4_0[0], cpu=conf.CPU_NAME
    )


@pytest.fixture(scope="class")
def attach_network_to_host(request):
    """
    Attach network to host NIC
    """
    network_filter = NetworkFixtures()
    net = request.node.cls.net

    def fin():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=network_filter.host_0_name
        )
    request.addfinalizer(fin)

    sn_dict = {
        "add": {
            "1": {
                "network": net,
                "nic": network_filter.host_0_nics[1]
            }
        }
    }
    assert hl_host_network.setup_networks(
        host_name=network_filter.host_0_name, **sn_dict
    )


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Start VM
    """
    network_filter = NetworkFixtures()
    vm = request.node.cls.vm

    def fin1():
        """
        Stop VM
        """
        network_filter.stop_vm(positive=True, vm=vm)
    request.addfinalizer(fin1)

    assert network_filter.run_vm_once_specific_host(
        vm=vm, host=network_filter.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def restore_vnic_profile_filter(request):
    """
    Restore vNIC profile network filter
    """
    NetworkFixtures()
    net = request.node.cls.net

    def fin():
        """
        Update vNIC profile with default network filter
        """
        ll_networks.update_vnic_profile(
            name=net, network=net, network_filter=conf.VDSM_NO_MAC_SPOOFING
        )
        request.addfinalizer(fin)


@pytest.fixture(scope="class")
def remove_vnic_from_vm(request):
    """
    Remove vNIC from VM
    """
    NetworkFixtures()
    vm = request.node.cls.vm
    nic1 = request.node.cls.nic1

    def fin():
        """
        Remove vNIC from VM
        """
        ll_vms.removeNic(positive=True, vm=vm, nic=nic1)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_vnic_to_vm(request):
    """
    Add vNIC to VM
    """
    NetworkFixtures()
    vm = request.node.cls.vm
    nic1 = request.node.cls.nic1
    net = request.node.cls.net
    assert ll_vms.addNic(positive=True, vm=vm, name=nic1, network=net)
