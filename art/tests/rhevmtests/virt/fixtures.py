#! /usr/bin/python
# -*- coding: utf-8 -*-


import pytest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms


@pytest.fixture(scope="class")
def remove_vm(request):
    """
    Remove vm safely
    """

    vm_name = request.cls.vm_name

    def fin():
        ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vms(request):
    """
    Start VM's
    """
    vms = request.node.cls.vm_name
    wait_for_vms_ip = getattr(request.node.cls, "wait_for_vms_ip", True)

    def fin():
        """
        Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=[vms])
    request.addfinalizer(fin)

    ll_vms.start_vms(
        vm_list=[vms],
        wait_for_ip=wait_for_vms_ip,

    )