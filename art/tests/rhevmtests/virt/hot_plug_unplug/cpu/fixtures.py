#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import copy
import pytest
import helper
from art.unittest_lib.common import testflow
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    vms as ll_vms,
    hosts as ll_hosts
)
from rhevmtests.virt import config
import rhevmtests.helpers as gen_helper
import rhevmtests.virt.helper as virt_helper


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
        testflow.teardown(
            "Stop and remove vms %s", config.CPU_HOTPLUG_VMS_NAME
        )
        ll_vms.safely_remove_vms(config.CPU_HOTPLUG_VMS_NAME)

    request.addfinalizer(fin)
    testflow.setup("Create vm %s for CPU hotplug test", vm_name)
    virt_helper.create_vm_from_template(
        vm_name=vm_name
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        memory=config.GB,
        max_memory=gen_helper.get_gb(4),
        os_type=config.VM_OS_TYPE,
        compare=False
    )


@pytest.fixture(scope="module")
def create_vm_for_load(request):
    """
    Setup: Creates a vm with pig load tool from template.
    Teardown: Removes vm from engine.
    """
    vm_name = config.CPU_HOTPLUG_VM_LOAD

    def fin():
        """
        Finalizer for cpu hot plug test
        """
        testflow.teardown("Stop and remove vm %s", vm_name)
        ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)
    testflow.setup("Create VM %s", vm_name)
    assert virt_helper.create_vm_from_template(vm_name)
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        memory=gen_helper.get_gb(4),
        max_memory=gen_helper.get_gb(8),
        memory_guaranteed=gen_helper.get_gb(2),
        os_type=config.VM_OS_TYPE,
        compare=False
    )
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    )


@pytest.fixture(scope='function')
def update_vm_to_ha(request, cpu_hot_plug_setup):
    """
    Enable HA VM
    """
    vm_name = config.CPU_HOTPLUG_VM
    args = request.node.get_marker("args_marker")
    params = args.kwargs if args else {}

    def fin():
        """
        Disable HA VM
        """
        testflow.teardown("Stop VM")
        assert ll_vms.stop_vms_safely(vms_list=[vm_name])
        testflow.teardown("Disable HA on VM")
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, highly_available=False
        )

    request.addfinalizer(fin)
    testflow.setup("Stop VM")
    assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    testflow.setup("Enable HA on VM")
    assert ll_vms.updateVm(positive=True, vm=vm_name, highly_available=True)
    init_and_start_vm(params, vm_name)


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
        testflow.teardown("Stop vm %s", vm_name)
        ll_vms.stop_vms_safely([vm_name])

    request.addfinalizer(fin)
    init_and_start_vm(params, vm_name)


def init_and_start_vm(params, vm_name):
    update_params = copy.deepcopy(config.CPU_HOTPLUG_VM_PARAMS)
    testflow.setup("Restore VM %s configuration to default.", vm_name)
    for key, val in params.iteritems():
        val = config.HOSTS[val] if key == 'placement_host' else val
        update_params[key] = val
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        **update_params
    )
    testflow.setup("Start vm %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_status=config.VM_UP,
        wait_for_ip=True
    )


@pytest.fixture(scope='function')
def migrate_vm_for_test(request, create_vm_for_load):
    """
    Load vm and migrate it in order to hot plug vm while migrating
    """
    args = request.node.get_marker("args_marker")
    params = args.kwargs if args else {'hot_plug_cpu_before': False}
    vm_name = config.CPU_HOTPLUG_VM_LOAD

    def fin():
        """
        1. Cancel migration if vm is still migrating
        2. Stop VM
        3. Restore cpu to 1
        """
        testflow.teardown("Cancel migration if vm is still migrating")
        if ll_vms.get_vm_state(vm_name) in config.MIGRATING_STATUSES:
            hl_vms.cancel_vm_migrate(vm_name)
        testflow.teardown("Stop VM %s", vm_name)
        ll_vms.stop_vms_safely([vm_name])
        testflow.teardown("Restore cpu to 1 socket")
        assert ll_vms.updateVm(
            True, config.CPU_HOTPLUG_VM_LOAD, cpu_socket=1
        ), "Failed to update CPU."

    request.addfinalizer(fin)

    if params["hot_plug_cpu_before"]:
        testflow.setup("Start VM %s", vm_name)
        ll_vms.start_vms(vm_list=[vm_name])
        testflow.setup("Hot plug cpu to 4 cpu")
        assert ll_vms.updateVm(
            True, config.CPU_HOTPLUG_VM_LOAD, cpu_socket=4
        ), "hot plug CPU failed."

    testflow.setup("Run load on VM %s.", vm_name)
    assert virt_helper.load_vm_memory_with_load_tool(
        vm_name=vm_name,
        load=2000,
        time_to_run=120
    )
    assert ll_vms.migrateVm(True, vm=vm_name, wait=False)


@pytest.fixture(scope='function')
def set_cpu_toplogy(request):
    """
    Set value of cpu topology according to the host
    """

    def fin():
        """
        Set values in configuration file back to default
        """
        testflow.teardown("Set values in configuration file back to default")
        config.CPU_TOPOLOGY = []
        config.CPU_HOTPLUG_VM_PARAMS['cpu_cores'] = 1

    request.addfinalizer(fin)
    testflow.setup("Set cpu topology parameter")
    host = ll_vms.get_vm_host(vm_name=config.CPU_HOTPLUG_VM)
    host_threads = ll_hosts.get_host_threads(host_name=host)
    cpu_number = (
        min(helper.get_number_of_cores(config.VDS_HOSTS[0]), 16) * host_threads
    )
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
        testflow.teardown("Disable threads in cluster level")
        ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], threads=False
        )

    request.addfinalizer(fin)
    testflow.setup("Enable threads in cluster level")
    assert ll_clusters.updateCluster(
        True, config.CLUSTER_NAME[0], threads=True
    )
