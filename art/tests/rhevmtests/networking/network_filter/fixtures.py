#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for network filter
"""

import pytest

import rhevmtests.helpers as global_helper
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
import rhevmtests.networking.config as conf
import config as nf_conf
from art.unittest_lib import testflow
from rhevmtests import networking
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
            name=net, network=net, network_filter=no_spoof,
            data_center=conf.DC_0
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


@pytest.fixture(scope="class")
def update_network_filter_on_profile(request):
    """
    Update network filter vNIC profile
    """
    network_filter = request.cls.network_filter
    vnic_profile = getattr(request.node.cls, "vnic_profile", conf.MGMT_BRIDGE)
    datacenter = getattr(request.node.cls, "datacenter", conf.DC_0)

    ll_networks.update_vnic_profile(
        name=vnic_profile, network=conf.MGMT_BRIDGE,
        data_center=datacenter, network_filter=network_filter
    )


@pytest.fixture()
def update_vnic_clean_traffic_param(request):
    """
    Update vNIC with clean traffic filter params
    """
    vnic = request.getfixturevalue("vnic")
    positive = request.getfixturevalue("positive")
    vm = request.cls.vm
    if not nf_conf.VM_INFO:
        ip = hl_vms.get_vm_ip(vm_name=vm, start_vm=False)
        vm_resource = global_helper.get_host_resource(
            ip=ip, password=conf.VDC_ROOT_PASSWORD
        )
        nf_conf.VM_INFO["ip"] = ip
        nf_conf.VM_INFO["resource"] = vm_resource

    filter_ip = nf_conf.VM_INFO.get("ip") if positive else nf_conf.FAKE_IP_1

    def fin():
        """
        Remove clean traffic from vNIC
        """
        filter_obj = ll_vms.get_vnic_network_filter_parameters(
            vm=vm, nic=vnic
        )[0]
        assert ll_vms.delete_vnic_network_filter_parameters(
            nf_object=filter_obj
        )
    request.addfinalizer(fin)

    assert ll_vms.add_vnic_network_filter_parameters(
        vm=vm, nic=vnic, param_name=nf_conf.IP_NAME, param_value=filter_ip
    )
    assert ll_vms.restartVm(vm=vm)
