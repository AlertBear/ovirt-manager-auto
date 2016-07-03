#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import pytest
import helper
import copy
from rhevmtests.virt import config
import rhevmtests.virt.helper as virt_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    clusters as ll_clusters,
)
import art.rhevm_api.tests_lib.high_level.vms as hl_vms


@pytest.fixture(scope="module")
def cpu_hot_plug_setup(request):
    """
    Setup/teardown for cpu hotplug module.
    Setup: Creates a vm with pig load tool from glance.
    Teardown: Removes vm from engine.
    """
    def fin():
        """
        Finalizer for cpu hot plug test module
        """
        ll_vms.safely_remove_vms([config.CPU_HOTPLUG_VM])
    request.addfinalizer(fin)
    if not config.PPC_ARCH:
        virt_helper.create_vm_from_glance_image(
            image_name=config.MIGRATION_IMAGE_VM,
            vm_name=config.CPU_HOTPLUG_VM
        )
    assert ll_vms.updateVm(
        positive=True,
        vm=config.CPU_HOTPLUG_VM,
        memory=config.GB * 4,
        memory_guaranteed=config.GB * 2,
        os_type=config.OS_RHEL_7
    )


@pytest.fixture(scope='function')
def base_setup_fixture(request, cpu_hot_plug_setup):
    """
    Update vm cpu socket and core
    """
    args = request.node.get_marker("args_marker")
    params = args.kwargs if args else {}

    def fin():
        """
        Finalizer for base cpu hot plug cases
        """
        ll_vms.stop_vms_safely([config.CPU_HOTPLUG_VM])
    request.addfinalizer(fin)
    update_params = copy.deepcopy(config.CPU_HOTPLUG_VM_PARAMS)
    for key, val in params.iteritems():
        val = config.HOSTS[val] if key == 'placement_host' else val
        update_params[key] = val
    assert ll_vms.updateVm(
        True, config.CPU_HOTPLUG_VM,
        **update_params
    )
    ll_vms.start_vms([config.CPU_HOTPLUG_VM], wait_for_status=config.VM_UP)


@pytest.fixture(scope='function')
def migrate_vm_for_test(request):
    """
    Load vm and migrate it in order to hot plug vm while migrating
    """
    def fin():
        """
        Cancel migration if vm is still migrating
        """
        if (
            ll_vms.get_vm_state(config.CPU_HOTPLUG_VM) in
            config.MIGRATING_STATUSES
        ):
            hl_vms.cancel_vm_migrate(config.CPU_HOTPLUG_VM)
    request.addfinalizer(fin)
    virt_helper.load_vm_memory_with_load_tool(
        config.CPU_HOTPLUG_VM, load=3000, time_to_run=120
    )
    assert ll_vms.migrateVm(True, config.CPU_HOTPLUG_VM, wait=False)


@pytest.fixture(scope='function')
def set_cpu_toplogy(request):
    """
    Set value of cpu topology according to the host
    """
    def fin():
        """
        Set values in configuration file back to default
        """
        config.CPU_TOPOLOGY = []
        config.CPU_HOTPLUG_VM_PARAMS['cpu_cores'] = 1
    request.addfinalizer(fin)
    cpu_number = helper.get_number_of_cores(config.VDS_HOSTS[0]) * 2
    config.CPU_TOPOLOGY = helper.calculate_the_cpu_topology(cpu_number)
    config.CPU_HOTPLUG_VM_PARAMS['cpu_cores'] = config.CPU_TOPOLOGY[1]


@pytest.fixture(scope='function')
def enable_cluster_cpu_threading(request):
    """
    Enable cluster cpu threading in order to use host threads as cpus
    """
    def fin():
        """
        Disable cluster cpu threading
        """
        ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], threads=False
        )
    request.addfinalizer(fin)
    assert ll_clusters.updateCluster(
        True, config.CLUSTER_NAME[0], threads=True
    )
