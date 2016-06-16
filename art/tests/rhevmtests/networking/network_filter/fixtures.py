#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""

import pytest
from rhevmtests import networking
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as nf_conf
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
from rhevmtests.networking.fixtures import (
    NetworkFixtures, network_cleanup_fixture
)  # flake8: noqa


@pytest.fixture(scope="module")
def network_filter_prepare_setup(request, network_cleanup_fixture):
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
def case_03_fixture(request, network_filter_prepare_setup):
    """
    Start VM
    """
    network_filter = NetworkFixtures()
    vm = request.node.cls.vm
    net = request.node.cls.net
    nic1 = request.node.cls.nic1

    def fin4():
        """
        Clean host interfaces
        """
        hl_host_network.clean_host_interfaces(
            host_name=network_filter.host_0_name
        )
    request.addfinalizer(fin4)

    def fin3():
        """
        Update vNIC profile with default network filter
        """
        ll_networks.update_vnic_profile(
            name=net, network=net, network_filter=conf.VDSM_NO_MAC_SPOOFING
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove vNIC from VM
        """
        ll_vms.removeNic(positive=True, vm=vm, nic=nic1)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM
        """
        network_filter.stop_vm(positive=True, vm=vm)
    request.addfinalizer(fin1)

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
    assert network_filter.run_vm_once_specific_host(
        vm=vm, host=network_filter.host_0_name,
        wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def case_04_fixture(request, network_filter_prepare_setup):
    """
    Add NIC to VM
    """
    vm = request.node.cls.vm
    nic = request.node.cls.nic1
    net = request.node.cls.net

    def fin():
        """
        Remove NIC from VM
        """
        ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin)

    assert ll_vms.addNic(positive=True, vm=vm, name=nic, network=net)


@pytest.fixture(scope="class")
def case_05_fixture(request, network_cleanup_fixture):
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
def case_06_fixture(request, network_cleanup_fixture):
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
