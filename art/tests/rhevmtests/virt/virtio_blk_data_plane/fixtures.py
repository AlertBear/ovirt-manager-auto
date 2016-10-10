#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for virtio data plane test
"""
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks,
    storagedomains as ll_sd,
)
from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks
)
import rhevmtests.virt.helper as helper
import pytest
import config


@pytest.fixture(scope="module")
def virtio_data_plane_setup(request):
    """
    Base setup for virtio data plane test.
    Create a vm for the test.
    """

    vm_name = config.VM_VIRTIO_DATA_PLANE_NAME

    def fin():
        """
        Base teardown for virtio data plane test
        Remove the specific vm.
        """
        testflow.teardown("Remove VM %s", vm_name)
        ll_vms.safely_remove_vms(vms=[vm_name])

    request.addfinalizer(fin)
    testflow.setup("Create VM %s with 4 disks", vm_name)
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO
    master_domain = (
        ll_sd.get_master_storage_domain_name(datacenter_name=config.DC_NAME[0])
    )
    assert helper.create_vm_from_template(vm_name=vm_name)
    first_disk_id = ll_disks.getObjDisks(name=vm_name, get_href=False)[0].id
    assert ll_disks.updateDisk(
        positive=True,
        vmName=vm_name,
        id=first_disk_id,
        bootable=True
    )
    for disk_id in range(1, 4):
        assert ll_vms.addDisk(
            positive=True,
            vm=vm_name,
            provisioned_size=config.GB,
            storagedomain=master_domain,
            interface=disk_interfaces,
            format=cow_disk,
            alias="".join((config.DISK_NAME, str(disk_id)))
        )


@pytest.fixture()
def hotplug_disk_to_vm(request):
    """
    Add disk to running vm
    """
    vm_name = config.VM_VIRTIO_DATA_PLANE_NAME
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO
    master_domain = (
        ll_sd.get_master_storage_domain_name(datacenter_name=config.DC_NAME[0])
    )

    def fin():
        """
        Remove hot plug disk
        """
        testflow.teardown("Remove hot plug disk")
        assert ll_vms.stop_vms_safely([vm_name])
        assert hl_disks.delete_disks(disks_names=[config.HOTPLUG_DISK_NAME])

    request.addfinalizer(fin)
    testflow.setup("Hot plug disk to VM %s", vm_name)
    assert ll_vms.addDisk(
        positive=True,
        vm=vm_name,
        provisioned_size=config.GB,
        storagedomain=master_domain,
        interface=disk_interfaces,
        format=cow_disk,
        alias=config.HOTPLUG_DISK_NAME,
        active=True
    )


@pytest.fixture()
def update_io_threads(request):
    """
    Update io thread on vm and reboot
    """
    args = request.node.get_marker("per_condition").kwargs
    new_number_of_threads = args['number_of_threads']

    def fin():
        """
        restore threads number to 0
        """
        testflow.teardown(
            "Restore io threads number to 0, (disable io threads)."
        )
        update_io_threads_action(number_of_threads=0)

    request.addfinalizer(fin)
    testflow.setup("Update io threads to: %s", new_number_of_threads)
    update_io_threads_action(number_of_threads=new_number_of_threads)


def update_io_threads_action(number_of_threads):
    """
    Update io thread on vm and reboot

    Args:
        number_of_threads (init): number of threads
    """
    vm_name = config.VM_VIRTIO_DATA_PLANE_NAME

    assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    assert ll_vms.updateVm(
        positive=True,
        vm=vm_name,
        io_threads=number_of_threads
    )
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP
    )
