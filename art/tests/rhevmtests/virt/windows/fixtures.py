#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for Windows testing
"""
import pytest
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks,
    clusters as ll_cluster
)
import rhevmtests.virt.helper as virt_helper
import windows_helper
import config


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
def create_windows_vms(request, update_cluster):
    """
    Init Window module
    Setup: Create windows VMs: win_7, win_2008R2, win2012
    Teardown: Remove all VMs
    """

    def fin():
        """
        Remove all windows VM
        """
        testflow.teardown("Remove windows VMS %s", config.WINDOWS_VM_NAMES)
        ll_vms.safely_remove_vms(config.WINDOWS_VM_NAMES)

    request.addfinalizer(fin)
    testflow.setup("Create Windows VMS %s", config.WINDOWS_VM_NAMES)
    windows_templates_names = [
        config.TEMPLATE_NAME[1], config.TEMPLATE_NAME[2],
        config.TEMPLATE_NAME[3]
    ]
    for vm_name, template_name in zip(
        config.WINDOWS_VM_NAMES, windows_templates_names
    ):
        assert virt_helper.create_vm_from_template(
            vm_name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=template_name,
            vm_parameters=config.VM_PARAMETERS[vm_name]
        )
        if vm_name == config.WINDOWS_2012:
            testflow.setup("update disk interface to IDE for windows 2012")
            first_disk_id = ll_disks.getObjDisks(
                name=vm_name, get_href=False
            )[0].id
            assert ll_disks.updateDisk(
                positive=True,
                vmName=vm_name,
                id=first_disk_id,
                bootable=True,
                interface=config.INTERFACE_IDE
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


@pytest.fixture(scope="class")
def start_windows_vms(request):
    """
    Start/Stop VM's
    """
    vms = config.WINDOWS_VM_NAMES
    wait_for_ip = getattr(request.cls, "wait_for_ip", False)

    def fin():
        """
        Stop VM's
        """
        testflow.teardown("Stop vms %s", vms)
        ll_vms.stop_vms_safely(vms_list=vms)

    request.addfinalizer(fin)
    testflow.setup("Start vms %s and wait for IP", vms)
    ll_vms.start_vms(
        vm_list=vms,
        wait_for_ip=wait_for_ip,
        wait_for_status=config.VM_UP,
        max_workers=3
    )
