#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""

import pytest

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests import networking
from rhevmtests.networking import helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNIC profiles
    """

    def fin():
        """
        Remove NIC from VM
        """
        testflow.teardown("Remove unneeded vNIC profiles")
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
        testflow.teardown(
            "Remove datacenter %s and cluster %s", ext_dc, ext_cl
        )
        assert hl_networks.remove_basic_setup(
            datacenter=ext_dc, cluster=ext_cl
        )
    request.addfinalizer(fin)

    testflow.setup("Create datacenter %s and cluster %s", ext_dc, ext_cl)
    assert hl_networks.create_basic_setup(
        datacenter=ext_dc, cluster=ext_cl,
        version=conf.COMP_VERSION_4_0[0], cpu=conf.CPU_NAME
    )


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Start VM
    """
    network_filter = NetworkFixtures()
    vm = request.node.cls.vm
    host = network_filter.host_0_name

    def fin1():
        """
        Stop VM
        """
        testflow.teardown("Stop VM %s", vm)
        assert ll_vms.stopVm(positive=True, vm=vm)
    request.addfinalizer(fin1)

    testflow.setup("Start VM %s on host %s", vm, host)
    assert network_helper.run_vm_once_specific_host(
        vm=vm, host=host, wait_for_up_status=True
    )


@pytest.fixture(scope="class")
def restore_vnic_profile_filter(request):
    """
    Restore vNIC profile network filter
    """
    NetworkFixtures()
    net = request.node.cls.net
    no_spoof = conf.VDSM_NO_MAC_SPOOFING

    def fin():
        """
        Update vNIC profile with default network filter
        """
        testflow.teardown("Set vNIC profile %s with filter %s", net, no_spoof)
        assert ll_networks.update_vnic_profile(
            name=net, network=net, network_filter=no_spoof
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
        testflow.teardown("Remove vNIC %s from VM %s", nic1, vm)
        assert ll_vms.removeNic(positive=True, vm=vm, nic=nic1)
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
    testflow.setup("Add vNIC %s to VM %s", nic1, vm)
    assert ll_vms.addNic(positive=True, vm=vm, name=nic1, network=net)
