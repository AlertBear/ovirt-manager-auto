#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
import rhevmtests.networking.helper as network_helper
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
        network_helper.remove_unneeded_vnic_profiles()
    request.addfinalizer(fin)


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
    vm = request.node.cls.vm_name
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
    vm = request.node.cls.vm_name
    nic1 = request.node.cls.nic1
    net = request.node.cls.net
    testflow.setup("Add vNIC %s to VM %s", nic1, vm)
    assert ll_vms.addNic(positive=True, vm=vm, name=nic1, network=net)
