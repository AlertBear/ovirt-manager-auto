#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest

import config
import rhevmtests.compute.virt.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    external_import as ll_external_import,
    vms as ll_vms
)
from art.unittest_lib import testflow


@pytest.fixture(scope='class', params=['kvm', 'vmware'])
def v2v_import_fixture(request):
    """
    Imports vm from the external provider like VMWare, KVM and waits for its
    conversion
    """
    def fin():
        """
        Remove created vm safely if it exists
        """
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    vm_name = getattr(request.node.cls, 'vm_name', 'v2v_test_automation_vm')
    provider = request.param
    vm_conf = config.EXTERNAL_VM_IMPORTS.get(provider)
    vm_name_ext = vm_conf['name']
    testflow.step(
        "Importing {vm_name_ext} VM from {provider_name} as {vm_name}".format(
            vm_name_ext=vm_name_ext,
            provider_name=vm_conf['provider'],
            vm_name=vm_name
        )
    )
    assert ll_external_import.import_vm_from_external_provider(**vm_conf)
    vm_status = ll_vms.get_vm(vm_name).get_status_detail()
    testflow.step(
        "Waiting for event of successful import, vm status is {}".format(
            vm_status
        )
    )
    assert helper.wait_for_v2v_import_event(
        vm_name_ext, vm_conf['cluster'], timeout=3600
    )
    testflow.step("Check that VM status_detail is None")
    assert ll_vms.get_vm(vm_name).get_status_detail() is None
    assert ll_vms.get_vm(vm_name).get_status() == 'down'
