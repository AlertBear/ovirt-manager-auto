#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for predictable_vnic_order
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as vnic_order_conf
import helper
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def prepare_setup_predictable_vnic_order(request):
    """
    Create VM from template
    Remove nic1 from VM
    Add 4 vNICs to VM
    Reorder vNICs mac addresses
    """
    NetworkFixtures()
    vm = vnic_order_conf.VM_NAME
    template = conf.TEMPLATE_NAME[0]
    nic_1 = conf.NIC_NAME[0]

    def fin2():
        """
        remove VM
        """
        testflow.teardown("Remove VM %s", vm)
        ll_vms.removeVm(positive=True, vm=vm)
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM
        """
        testflow.teardown("Stop Vm %s", vm)
        ll_vms.stopVm(positive=True, vm=vm)
    request.addfinalizer(fin1)

    testflow.setup("Create VM %s from template %s", vm, template)
    assert ll_vms.addVm(
        positive=True, name=vm, cluster=conf.CL_0, template=template,
    )
    testflow.setup("Remove vNIC %s from VM %s", nic_1, vm)
    assert ll_vms.removeNic(positive=True, vm=vm, nic=nic_1)
    testflow.setup("Add 4 vNICs to VM %s", vm)
    assert helper.add_vnics_to_vm()
    testflow.setup("Reorder MACs on VM %s", vm)
    assert ll_vms.reorder_vm_mac_address(vm_name=vm)
