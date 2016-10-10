#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt test - virtio data plan
Test plan:
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Compute/Virtio-blk%20Data%20Plane
"""

import pytest
from art.unittest_lib import attr, VirtTest, testflow
from art.test_handler.tools import polarion
import rhevmtests.virt.helper as helper
from fixtures import (
    virtio_data_plane_setup,
    update_io_threads,
    hotplug_disk_to_vm
)
import config


@attr(tier=2)
class TestVirtioDataPlane(VirtTest):
    """
    Virtio data plane test
    """
    __test__ = True

    @polarion("RHEVM-17132")
    @pytest.mark.usefixtures(
        virtio_data_plane_setup.__name__,
        update_io_threads.__name__
    )
    @pytest.mark.per_condition(number_of_threads=4)
    def test_threads_number_same_as_disks_number(self):
        """
        Check that threads are allocated to all disks
        """
        testflow.step("Check that threads are allocate to all disks")
        assert helper.check_iothreads_of_vm(
            vm_name=config.VM_VIRTIO_DATA_PLANE_NAME,
            number_of_disks=4,
            number_of_threads=4
        )

    @polarion("RHEVM-17133")
    @pytest.mark.usefixtures(
        virtio_data_plane_setup.__name__,
        update_io_threads.__name__
    )
    @pytest.mark.per_condition(number_of_threads=2)
    def test_number_of_threads_smaller_than_disks_number(self):
        """
        Check that threads are allocated to all disks, reuse of threads
        """

        self.number_of_threads = 2
        testflow.step(
            "Check that threads are allocate to all disks, reuse of threads"
        )
        assert helper.check_iothreads_of_vm(
            vm_name=config.VM_VIRTIO_DATA_PLANE_NAME,
            number_of_disks=4,
            number_of_threads=2
        )

    @polarion("RHEVM-17134")
    @pytest.mark.usefixtures(
        virtio_data_plane_setup.__name__,
        update_io_threads.__name__
    )
    @pytest.mark.per_condition(number_of_threads=6)
    def test_number_of_threads_larger_than_disks_number(self):
        """
        Check that threads are allocated to all disks
        """
        testflow.step(
            "Check that threads are allocate to all disks"
        )
        assert helper.check_iothreads_of_vm(
            vm_name=config.VM_VIRTIO_DATA_PLANE_NAME,
            number_of_disks=4,
            number_of_threads=6
        )

    @polarion("RHEVM-17135")
    @pytest.mark.usefixtures(
        virtio_data_plane_setup.__name__,
        update_io_threads.__name__,
        hotplug_disk_to_vm.__name__
    )
    @pytest.mark.per_condition(number_of_threads=5)
    def test_hotplug_disk_allocate_new_thread(self):
        """
        Hot plug new disk and check that new thread is allocated to new disk
        """

        testflow.step(
            "Hot plug new disk and check that new thread is allocate "
            "to new disk"
        )

        assert helper.check_iothreads_of_vm(
            vm_name=config.VM_VIRTIO_DATA_PLANE_NAME,
            number_of_disks=5,
            number_of_threads=5
        )

    @polarion("RHEVM-17135")
    @pytest.mark.usefixtures(
        virtio_data_plane_setup.__name__,
        update_io_threads.__name__,
        hotplug_disk_to_vm.__name__
    )
    @pytest.mark.per_condition(number_of_threads=4)
    def test_hotplug_disk_reuse_thread(self):
        """
        Hot plug new disk and check that reuse of thread of new disk
        """
        testflow.step(
            "Hot plug new disk and check that reuse of thread of new disk"
        )
        assert helper.check_iothreads_of_vm(
            vm_name=config.VM_VIRTIO_DATA_PLANE_NAME,
            number_of_disks=5,
            number_of_threads=4
        )
