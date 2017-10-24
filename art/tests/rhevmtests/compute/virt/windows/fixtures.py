#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for Windows testing
"""
import pytest

import config
import helper
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.compute.virt.windows.helper as win_helper
from art import test_handler
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    clusters as ll_cluster,
    templates as ll_templates
)
from art.unittest_lib import testflow

test_handler.find_test_file.__test__ = False


@pytest.fixture(scope="module")
def remove_seal_templates(request):
    """
    Remove seal templates
    """

    def fin():
        ll_templates.remove_templates(
            positive=True, templates=config.WINDOWS_SEAL_TEMPLATES
        )

    request.addfinalizer(fin)


@pytest.fixture(scope="module")
def update_cluster(request):
    """
    Update cluster CPU and migration policy to 'minimal_downtime'
    (to reduce migration time)
    """
    cpu_type = config.CPU_NAME

    def fin():
        """
        Restore CPU type and migration policy
        """
        testflow.teardown("Restore cpu type and migration policy")
        assert ll_cluster.updateCluster(
            positive=True,
            cluster=config.CLUSTER_NAME[0],
            cpu=cpu_type,
            migration_policy_id=config.MIGRATION_POLICY_LEGACY,
            migration_bandwidth=config.BANDWIDTH
        )

    request.addfinalizer(fin)
    testflow.setup(
        "Update cluster CPU and migration policy to 'minimal_downtime'"
    )
    status = ll_cluster.updateCluster(
        positive=True,
        cluster=config.CLUSTER_NAME[0],
        cpu=config.CPU_TYPE_MIN,
        migration_policy_id=config.MIGRATION_POLICY_MINIMAL_DOWNTIME,
        migration_bandwidth=config.BANDWIDTH
    )
    if not status:
        pytest.skip(config.SKIP_MESSAGE_CPU)


@pytest.fixture(scope="module")
def set_product_keys(request):
    """
    Set windows product keys
    Setup: Copy product keys file to engine and restart engine
    TearDown: Remove product keys file from engine and restart engine
    """

    def fin():
        """
        Remove product keys file from engine and restart engine
        """
        testflow.teardown(
            "Remove product keys file from engine and restart engine"
        )
        assert config.ENGINE_HOST.fs.remove(
            path=config.REMOTE_KEY_PRODUCT_FILE
        )
        config.ENGINE.restart()

    request.addfinalizer(fin)
    if config.ENGINE_HOST.fs.exists(path=config.REMOTE_KEY_PRODUCT_FILE):
        assert config.ENGINE_HOST.fs.remove(
            path=config.REMOTE_KEY_PRODUCT_FILE
        )
    testflow.setup("Copy product keys file to engine and restart engine")
    config.ENGINE_HOST.fs.put(
        path_src=test_handler.find_test_file(
            path=config.LOCAL_KEY_PRODUCT_FILE
        ), path_dst=config.REMOTE_KEY_PRODUCT_FILE
    )
    config.ENGINE.restart()


@pytest.fixture(scope='class')
def create_windows_vms(request, update_cluster, set_product_keys):
    """
    Setup: Create and start windows VMs according to vms list, and start vm
    by demand
    Teardown: Remove all VMs
    """
    start_vm = getattr(request.cls, "start_vm", True)
    vms_name = getattr(request.cls, "vms_name", config.WINDOWS_VM_NAMES)

    def fin():
        """
        Remove all windows VM
        """
        testflow.teardown("Remove windows VMS %s", vms_name)
        ll_vms.safely_remove_vms(vms_name)

    request.addfinalizer(fin)
    win_helper.create_and_start_windows_vm(
        template_names=helper.get_windows_templates(vms=vms_name),
        vms_names=vms_name, start_vm=start_vm
    )


@pytest.fixture(scope='class')
def create_windows_vms_from_sealed_template(
    request, update_cluster, set_product_keys, remove_seal_templates
):
    """
    Init windows case
    Setup: Create and windows vm from sealed template
    Teardown: Remove VMs
    """
    vms = config.WINDOWS_SEAL_VMS

    def fin():
        """
        Remove windows VM
        """
        testflow.teardown("Remove windows VMS %s", vms)
        ll_vms.safely_remove_vms(vms)

    request.addfinalizer(fin)
    win_helper.create_and_start_windows_vm(
        template_names=config.WINDOWS_SEAL_TEMPLATES,
        vms_names=vms, start_vm=False
    )


@pytest.fixture()
def remove_vm_from_storage_domain(request):
    """
    Fixture for snapshot tests
    Remove vm from export domain
    """
    export_domain = request.cls.export_domain

    def fin():
        """
        Remove vm from export domain
        """
        for vm_name in config.WINDOWS_VM_NAMES:
            virt_helper.remove_vm_from_storage_domain(
                vm_name=vm_name,
                export_domain=export_domain
            )

    request.addfinalizer(fin)


@pytest.fixture()
def stop_vms(request):
    """
    Stop windows VMs
    """

    def fin():
        """
        Stop windows VMs
        """
        ll_vms.stop_vms_safely(config.WINDOWS_VM_NAMES)

    request.addfinalizer(fin)


@pytest.fixture()
def update_sysprep_with_custom_file(request):
    """
    1. Update sysprep with custom file
    2. Run VM
    """

    vm_name = request.getfixturevalue('vm_name')
    os_type = request.getfixturevalue('os_type')
    win_version = request.getfixturevalue('win_version')

    testflow.setup("Create sysprep file")
    custom_script = helper.init_sysprep_file(
        windows_version=win_version, os_type=os_type
    )
    config.INIT_PARAMS_CUSTOM_FILE['custom_script'] = custom_script
    testflow.setup("Start VM with sysprep file")
    assert ll_vms.runVmOnce(
        positive=True, vm=vm_name, use_sysprep=True,
        wait_for_state=config.VM_UP,
        initialization=ll_vms.init_initialization_obj(
            config.INIT_PARAMS_CUSTOM_FILE
        )
    ), "Failed to start VM %s " % vm_name


@pytest.fixture()
def update_sysprep_parameters(request):
    """
    1. Update sysprep parameters
    2. Run VM
    """

    vm_name = request.getfixturevalue('vm_name')
    os_type = request.getfixturevalue('os_type')

    testflow.setup("Update VM initialization parameters")
    configuration = helper.get_sysprep_configuration(
        os_type=os_type
    )
    assert ll_vms.updateVm(
        positive=True, vm=vm_name,
        initialization=ll_vms.init_initialization_obj(configuration)
    )
    testflow.setup("Start VM")
    assert ll_vms.runVmOnce(
        positive=True, vm=vm_name, use_sysprep=True,
        wait_for_state=config.VM_UP
    ), "Failed to start VM %s " % vm_name
