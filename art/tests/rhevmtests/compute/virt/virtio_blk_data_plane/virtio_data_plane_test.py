#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt test - virtio data plan
Test plan:
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Compute/Virtio-blk%20Data%20Plane
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import helpers
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier2,
)
from fixtures import (
    reactivate_vm_disks,
    remove_disk_from_vm,
    start_vm,
    virtio_data_plane_setup,
    update_vm_io_threads
)


@pytest.mark.usefixtures(
    virtio_data_plane_setup.__name__,
    update_vm_io_threads.__name__,
    reactivate_vm_disks.__name__,
    start_vm.__name__
)
class TestBasicVirtioDataPlane(VirtTest):
    """
    Virtio data plane test
    """

    @tier2
    @pytest.mark.parametrize(
        ("iothreads", "vm_name"),
        [
            polarion("RHEVM-17132")([4, config.VM_IOTHREAD_VIRTIO]),
            polarion("RHEVM-17133")([2, config.VM_IOTHREAD_VIRTIO]),
            polarion("RHEVM-17134")([6, config.VM_IOTHREAD_VIRTIO]),
            polarion("RHEVM-21892")([4, config.VM_IOTHREAD_SCSI_VIRTIO]),
            polarion("RHEVM-21893")([2, config.VM_IOTHREAD_SCSI_VIRTIO]),
            polarion("RHEVM-21894")([6, config.VM_IOTHREAD_SCSI_VIRTIO]),
            polarion("RHEVM-21895")([4, config.VM_IOTHREAD_MIXED]),
            polarion("RHEVM-21896")([2, config.VM_IOTHREAD_MIXED]),
            polarion("RHEVM-21897")([6, config.VM_IOTHREAD_MIXED])
        ],
        ids=[
            "Number_of_iothreads_equals_to_number_of_disks_Virtio",
            "Number_of_iothreads_less_than_number_of_disks_Virtio",
            "Number_of_iothreads_greater_than_number_of_disks_Virtio",
            "Number_of_iothreads_equals_to_number_of_disks_SCSI_Virtio",
            "Number_of_iothreads_less_than_number_of_disks_SCSI_Virtio",
            "Number_of_iothreads_greater_than_number_of_disks_SCSI_Virtio",
            "Number_of_iothreads_equals_to_number_of_disks_Mixed",
            "Number_of_iothreads_less_than_number_of_disks_Mixed",
            "Number_of_iothreads_greater_than_number_of_disks_Mixed"
        ]
    )
    def test_iothreads(self, iothreads, vm_name):
        """
        Check iothreads allocation to disks
        """
        helpers.check_iothreads(vm_name=vm_name, number_of_iothreads=iothreads)


@pytest.mark.usefixtures(
    virtio_data_plane_setup.__name__,
    update_vm_io_threads.__name__,
    remove_disk_from_vm.__name__,
    start_vm.__name__,
)
class TestHotplugVirtioDataPlane(VirtTest):
    """
    Verify IO threads for test cases with disk hotplug
    """

    @tier2
    @pytest.mark.parametrize(
        ("iothreads", "vm_name"),
        [
            polarion("RHEVM-17135")([5, config.VM_IOTHREAD_VIRTIO]),
            polarion("RHEVM-17136")([4, config.VM_IOTHREAD_VIRTIO])
        ],
        ids=[
            "Hotplug_new_disk_when_number_of_iothreads_greater_Virtio",
            "Hotplug_new_disk_when_number_of_iothreads_lesser_Virtio"
        ]
    )
    def test_iothreads_with_disk_hotplug(self, iothreads, vm_name):
        """
        Hot plug new disk and check IO thread allocation
        """
        testflow.step("Hotplug disk %s to VM %s", config.HOTPLUG_DISK, vm_name)
        assert ll_vms.addDisk(
            positive=True,
            wait=False,
            vm=vm_name,
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[0],
            interface=config.VMS_IOTHREADS_NAMES[vm_name].keys()[0],
            format=config.DISK_FORMAT_COW,
            alias=config.HOTPLUG_DISK,
        )
        helpers.check_iothreads(vm_name=vm_name, number_of_iothreads=iothreads)


@pytest.mark.usefixtures(
    virtio_data_plane_setup.__name__,
    update_vm_io_threads.__name__,
    reactivate_vm_disks.__name__,
    start_vm.__name__
)
class TestMigrationVirtioDataPlane(VirtTest):
    """
    Verify that migration preserve on VM IO threads
    """

    @tier2
    @pytest.mark.parametrize(
        ("iothreads", "vm_name"),
        [
            polarion("RHEVM-21898")([4, config.VM_IOTHREAD_VIRTIO]),
            polarion("RHEVM-21899")([4, config.VM_IOTHREAD_SCSI_VIRTIO])
        ],
        ids=[
            "Migrate_VM_with_iothreads_Virtio",
            "Migrate_VM_with_iothreads_SCSI_Virtio"
        ]
    )
    def test_iothreads_with_migration(self, iothreads, vm_name):
        """
        Migrate the VM and check VM IO threads
        """
        testflow.step("Migrate VM %s", vm_name)
        ll_vms.migrateVm(positive=True, vm=vm_name)
        helpers.check_iothreads(vm_name=vm_name, number_of_iothreads=iothreads)
