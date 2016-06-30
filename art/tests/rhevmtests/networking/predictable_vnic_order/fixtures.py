#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for predictable_vnic_order
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.fixtures import NetworkFixtures


@pytest.fixture(scope="module")
def prepare_setup_predictable_vnic_order(request):
    """
    Seal the VM
    Remove all vNICs from the VM
    """
    NetworkFixtures()

    def fin():
        """
        Add vNIC to the VM
        Seal the VM
        """
        ll_vms.addNic(
            positive=True, vm=conf.LAST_VM, name=conf.NIC_NAME[0],
            network=conf.MGMT_BRIDGE
        )

        network_helper.seal_vm(
            vm=conf.LAST_VM, root_password=conf.VMS_LINUX_PW
        )
    request.addfinalizer(fin)

    assert helper.seal_last_vm_and_remove_vnics()


@pytest.fixture(scope="class")
def fixture_case01(request, prepare_setup_predictable_vnic_order):
    """
    Add 4 vNICs to the VM
    Reorder the vNICs
    """
    NetworkFixtures()

    def fin2():
        """
        Seal the VM
        Remove vNICs from the VM
        """
        helper.seal_last_vm_and_remove_vnics()
    request.addfinalizer(fin2)

    def fin1():
        """
        Stop VM
        """
        ll_vms.stopVm(positive=True, vm=conf.LAST_VM)
    request.addfinalizer(fin1)

    assert helper.add_vnics_to_vm()
    assert ll_vms.reorder_vm_mac_address(vm_name=conf.LAST_VM)
