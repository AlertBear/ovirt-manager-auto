#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virtio default scsi test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Compute/4_1_VIRT_virtio-scsi_default_interface
"""
import pytest
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, VirtTest, testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    templates as ll_templates,
    disks as ll_disks
)
from fixtures import (
    create_vm_for_virtio_scsi, create_disk, disable_virtio_scsi
)
from rhevmtests.virt import config  # flake8:  noqa


@attr(tier=2)
@pytest.mark.usefixtures(create_vm_for_virtio_scsi.__name__)
class TestVirtioScsiDefaultInterface(VirtTest):
    """
    Virt virtio scsi default interface
    """
    vm_name = "virt_virtio_scsi"
    disk_name = "%s_Disk1" % vm_name

    @polarion("RHEVM-18327")
    def test_if_virtio_scsi_is_enabled_by_default_in_blank_template(self):
        """
        Check the Virtio-scsi is enabled by default in the blank template
        """
        testflow.step(
            "Check Virtio-scsi is enabled by default in blank template"
        )
        template_obj = ll_templates.get_template_obj("Blank", all_content=True)
        assert template_obj.virtio_scsi.enabled, (
            "The vitio-scsi is disabeled in the blank tempalte"
        )

    @polarion("RHEVM-18327")
    def test_if_virtio_scsi_is_enabled_by_default_in_new_vm(self):
        """
        Check the Virtio-scsi is enabled by default in every new vm creation
        """
        testflow.step(
            "Check Virtio-scsi is enabled by default in every new vm creation"
        )
        vm_obj = ll_vms.get_vm_obj(self.vm_name, all_content=True)
        assert vm_obj.virtio_scsi.enabled, (
            "The vitio-scsi is disabeled in %s" % self.vm_name
        )

    @pytest.mark.usefixtures(create_disk.__name__)
    @polarion("RHEVM-18329")
    @bz({'1435976': {}})
    def test_default_disk_interface_is_iscsi(self):
        """
        Check that the Default disk interface is iscsi
        """
        disk = ll_vms.get_disk_attachment(
            name=self.vm_name, disk=self.disk_name, attr="name"
        )
        testflow.step(
            "Test if VM %s has %s interface",
            self.vm_name, config.INTERFACE_VIRTIO_SCSI
        )
        assert config.INTERFACE_VIRTIO_SCSI == disk.get_interface(), (
            "Disk %s should have interface %s instead of interface %s"
            % (self.disk_name, config.INTERFACE_VIRTIO_SCSI,
               disk.get_interface()
               )
        )

    @polarion("RHEVM-19662")
    @pytest.mark.usefixtures(
        disable_virtio_scsi.__name__, create_disk.__name__
    )
    def test_negative_virtio_scsi_interface_not_available(self):
        """
        Negative:
        Check that that virtio scsi is not available when
        disabling virtio scsi on VM
        """
        testflow.step(
            "Negative: try to set VM %s interface to %s",
            self.vm_name, config.INTERFACE_VIRTIO_SCSI
        )
        disk_id = ll_disks.getObjDisks(name=self.vm_name, get_href=False)[0].id
        assert not ll_disks.updateDisk(
            positive=True, vmName=self.vm_name,
            interface=config.INTERFACE_VIRTIO_SCSI, id=disk_id
        )
