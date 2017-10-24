#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for virtio data plane test
"""
import pytest

import art.rhevm_api.tests_lib.high_level.disks as hl_disks
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
from art.unittest_lib import testflow


@pytest.fixture(scope="module")
def virtio_data_plane_setup(request):
    """
    Create VM's for IO threads test
    """
    def fin():
        """
        Remove all IO threads VM's
        """
        ll_disks.wait_for_disks_status(disks=disks)
        assert ll_vms.safely_remove_vms(vms=config.VMS_IOTHREADS_NAMES.keys())

    request.addfinalizer(fin)

    disks = []
    for vm_name, vm_disks in config.VMS_IOTHREADS_NAMES.iteritems():
        bootable = True
        assert ll_vms.addVm(
            positive=True,
            name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.BLANK_TEMPLATE
        )
        for disk_interface, num_of_disks in vm_disks.iteritems():
            for i in range(num_of_disks):
                disk_alias = "{0}_{1}_{2}".format(vm_name, "disk", i)
                assert ll_vms.addDisk(
                    positive=True,
                    wait=False,
                    vm=vm_name,
                    provisioned_size=config.GB,
                    storagedomain=config.STORAGE_NAME[0],
                    interface=disk_interface,
                    format=config.DISK_FORMAT_COW,
                    alias=disk_alias,
                    bootable=bootable
                )
                if bootable:
                    bootable = False
                disks.append(disk_alias)
    assert ll_disks.wait_for_disks_status(disks=disks)


@pytest.fixture()
def remove_disk_from_vm(request):
    """
    Remove hot plugged disk
    """
    def fin():
        """
        Remove hot plugged disk
        """
        testflow.teardown("Delete disk %s", config.HOTPLUG_DISK)
        assert hl_disks.delete_disks(disks_names=[config.HOTPLUG_DISK])
    request.addfinalizer(fin)


@pytest.fixture()
def update_vm_io_threads(request):
    """
    Update VM IO threads
    """
    vm_name = request.getfixturevalue("vm_name")
    iothreads = request.getfixturevalue("iothreads")

    def fin():
        """
        Update VM IO threads to default value
        """
        assert ll_vms.updateVm(positive=True, vm=vm_name, io_threads=0)
    request.addfinalizer(fin)

    assert ll_vms.updateVm(
        positive=True, vm=vm_name, io_threads=iothreads, virtio_scsi=True
    )


@pytest.fixture()
def start_vm(request):
    vm_name = request.getfixturevalue("vm_name")

    def fin():
        """
        restore threads number to 0
        """
        assert ll_vms.stop_vms_safely(vms_list=[vm_name])
    request.addfinalizer(fin)

    testflow.setup("Start VM %s", vm_name)
    assert ll_vms.startVm(positive=True, vm=vm_name)


@pytest.fixture()
def reactivate_vm_disks(request):
    """
    Reactivate disk it to apply IO threads parameters
    """
    vm_name = request.getfixturevalue("vm_name")
    if vm_name == config.VM_IOTHREAD_VIRTIO:
        return
    vm_disks = ll_vms.get_vm_disks_ids(vm=vm_name)
    for disk_id in vm_disks:
        testflow.setup("Deactivate VM %s disk %s", vm_name, disk_id)
        assert ll_vms.deactivateVmDisk(
            positive=True, vm=vm_name, diskId=disk_id
        )
        testflow.setup("Activate VM %s disk %s", vm_name, disk_id)
        assert ll_vms.activateVmDisk(positive=True, vm=vm_name, diskId=disk_id)
