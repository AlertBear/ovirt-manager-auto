#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module default virtio scsi test
"""
import pytest

from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks
)
from art.unittest_lib import testflow
from rhevmtests.compute.virt import config


@pytest.fixture(scope='class')
def create_vm_for_virtio_scsi(request):
    """
    Create VM from 'Blank' template
    """
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Remove VM created from 'Blank' template
        """
        testflow.teardown("Remove VM %s", vm_name)
        assert ll_vms.safely_remove_vms([vm_name])
    request.addfinalizer(fin)

    testflow.setup("Create VM %s from 'Blank' template", vm_name)
    assert ll_vms.createVm(
        True, vm_name, template="Blank",
        cluster=config.CLUSTER_NAME[0]
    )


@pytest.fixture()
def create_disk(request):
    """
    Create Disk for virtio scsi VM
    """
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Remove Disk from VM
        """
        testflow.teardown("Remove Disk From VM")
        disk_id = ll_disks.getObjDisks(name=vm_name, get_href=False)[0].id
        assert ll_vms.removeDisk(True, vm_name, disk_id=disk_id)
    request.addfinalizer(fin)

    testflow.setup("add disk to VM %s" % vm_name)
    assert ll_vms.addDisk(
        True, vm=vm_name, provisioned_size=config.GB,
        storagedomain=config.STORAGE_NAME[0]
    )


@pytest.fixture()
def disable_virtio_scsi(request):
    """
    Disable Virtio scsi on VM
    """
    vm_name = request.node.cls.vm_name
    testflow.setup("Disable virtio scsi on VM %s", vm_name)
    assert ll_vms.updateVm(True, vm_name, virtio_scsi=False)
