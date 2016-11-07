#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import pytest
import copy
from rhevmtests.virt import config
import rhevmtests.virt.helper as virt_helper
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms


@pytest.fixture(scope="module")
def cpu_hot_plug_setup(request):
    """
    Setup/teardown for cpu hotplug module.
    Setup: Creates a vm from template.
    Teardown: Removes vm from engine.
    """
    vm_name = config.CPU_HOTPLUG_VM

    def fin():
        """
        Finalizer for cpu hot plug test module
        """
        ll_vms.safely_remove_vms(config.CPU_HOTPLUG_VMS_NAME)

    request.addfinalizer(fin)
    virt_helper.create_vm_from_template(
        vm_name=vm_name
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        memory=config.GB * 4,
        memory_guaranteed=config.GB * 2,
        os_type=config.OS_RHEL_7
    )


@pytest.fixture()
def create_vm_from_glance(request):
    """
    Setup: Creates a vm with pig load tool from glance.
    Teardown: Removes vm from engine.
    """
    vm_name = config.CPU_HOTPLUG_VM_LOAD

    def fin():
        """
        Finalizer for cpu hot plug test
        """
        ll_vms.safely_remove_vms(config.CPU_HOTPLUG_VMS_NAME)

    request.addfinalizer(fin)
    virt_helper.create_vm_from_glance_image(
        image_name=config.MIGRATION_IMAGE_VM,
        vm_name=vm_name
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        memory=config.GB * 4,
        memory_guaranteed=config.GB * 2,
        os_type=config.OS_RHEL_7
    )
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    )


@pytest.fixture(scope='function')
def base_setup_fixture(request, cpu_hot_plug_setup):
    """
    Update vm cpu socket and core
    """
    vm_name = config.CPU_HOTPLUG_VM
    args = request.node.get_marker("args_marker")
    params = args.kwargs if args else {}

    def fin():
        """
        Finalizer for base cpu hot plug cases
        """
        ll_vms.stop_vms_safely([vm_name])

    request.addfinalizer(fin)
    update_params = copy.deepcopy(config.CPU_HOTPLUG_VM_PARAMS)
    for key, val in params.iteritems():
        val = config.HOSTS[val] if key == 'placement_host' else val
        update_params[key] = val
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        **update_params
    )
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    )


@pytest.fixture(scope='function')
def migrate_vm_for_test(request, create_vm_from_glance):
    """
    Load vm and migrate it in order to hot plug vm while migrating
    """
    vm_name = config.CPU_HOTPLUG_VM_LOAD

    def fin():
        """
        Cancel migration if vm is still migrating
        """
        if ll_vms.get_vm_state(vm_name) in config.MIGRATING_STATUSES:
            hl_vms.cancel_vm_migrate(vm_name)

    request.addfinalizer(fin)
    virt_helper.load_vm_memory_with_load_tool(
        vm_name=vm_name,
        load=2000,
        time_to_run=120
    )
    assert ll_vms.migrateVm(True, vm=vm_name, wait=False)
