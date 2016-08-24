"""
Storage Disk sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage_3_6/3_6_Storage_Disk_General
"""
import logging
import pytest
import config
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
)
from art.test_handler.tools import polarion
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    add_disk, create_snapshot, create_vm, delete_disks,
    poweroff_vm, preview_snapshot, undo_snapshot
)
from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    create_second_vm, poweroff_vm_and_wait_for_stateless_to_remove
)

logger = logging.getLogger(__name__)


@attr(tier=2)
@pytest.mark.usefixtures(create_vm.__name__, delete_disks.__name__)
class NegativeAttachDetach(TestCase):
    """
    * Attach a locked disk to VM
    * Detach disk from vm in powering up state
    """
    __test__ = True
    disk_size = 20 * config.GB
    installation = False

    @polarion("RHEVM3-16713")
    def test_attach_locked_disk_to_vm(self):
        """
        Attach disk to VM when the disk is in locked state
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=self.disk_size,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO_SCSI, format=config.RAW_DISK,
            sparse=False
        )
        assert ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        )
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s" %
            (self.disk_name, self.vm_name)
        )
        self.disks_to_remove.append(self.disk_name)

    @polarion("RHEVM3-16714")
    @pytest.mark.usefixtures(poweroff_vm.__name__)
    def test_detach_disk_from_powering_up_vm(self):
        """
        Detach a disk from a VM in powering up state
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0]
        ll_vms.startVm(True, self.vm_name, None)
        assert ll_disks.detachDisk(False, vm_disk.get_alias(), self.vm_name), (
            "Succeeded to detach disk %s from VM %s" %
            (self.disk_name, self.vm_name)
        )
        ll_vms.wait_for_vm_states(self.vm_name)

    @polarion("RHEVM3-16736")
    @pytest.mark.usefixtures(poweroff_vm.__name__)
    def test_attach_disk_to_vm_in_powering_up_state(self):
        """
        Attach disk to VM in powering up state
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=config.DISK_SIZE,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO, format=config.COW_DISK, sparse=True
        )
        assert ll_disks.wait_for_disks_status([self.disk_name])
        ll_vms.startVm(True, self.vm_name, None)
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s in powering up state" % (
                self.disk_name, self.vm_name
            )
        )
        ll_vms.wait_for_vm_states(self.vm_name)
        self.disks_to_remove.append(self.disk_name)

    @polarion("RHEVM3-16739")
    def test_attach_disk_to_vm_as_bootable(self):
        """
        Attach disk to VM as second bootable disk - should fail
        """
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DISK
        )
        ll_disks.addDisk(
            True, provisioned_size=config.DISK_SIZE,
            storagedomain=self.storage_domain, alias=self.disk_name,
            interface=config.VIRTIO, format=config.COW_DISK, sparse=True
        )
        assert ll_disks.wait_for_disks_status([self.disk_name])
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, bootable=True), (
            "Succeeded to attach disk %s to VM %s as second bootable disk" %
            (self.disk_name, self.vm_name)
        )

        self.disks_to_remove.append(self.disk_name)


@attr(tier=2)
@pytest.mark.usefixtures(create_vm.__name__)
class TestCase16737(TestCase):
    """
    Attach OVF store disk to VM - should fail
    """
    __test__ = True
    installation = False
    storage_domain = None

    @polarion("RHEVM3-16737")
    def test_attach_ovf_disk_to_vm(self):
        """
        Attach OVF disk to VM
        """
        ovf_disk = None
        all_disks = ll_disks.get_all_disks()
        for disk in all_disks:
            if disk.get_alias() == config.OVF_DISK_ALIAS:
                ovf_disk = disk
                break

        assert ll_disks.attachDisk(
            False, ovf_disk.get_alias(), self.vm_name,
            disk_id=ovf_disk.get_id()
        ), "Succeeded to attach disk %s to VM %s" % (
            ovf_disk.get_alias(), self.vm_name
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    preview_snapshot.__name__,
    add_disk.__name__,
    undo_snapshot.__name__
)
class TestCase16738(TestCase):
    """
    Attach disk to VM in preview - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16738")
    def test_attach_disk_to_vm_in_preview(self):
        """
        Attach disk to VM in preview of snapshot
        """
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s in preview" %
            (self.disk_name, self.vm_name)
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    poweroff_vm_and_wait_for_stateless_to_remove.__name__
)
class TestCase16741(TestCase):
    """
    Attach stateless snapshot's disk to VM - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16741")
    def test_attach_disk_of_stateless_snapshot_to_vm(self):
        """
        Attach stateless snapshot's disk to VM
        """
        assert ll_vms.runVmOnce(
            True, self.vm_name, config.VM_UP, stateless=True
        ), "Failed to run VM %s in stateless" % self.vm_name
        stateless_snapshot_disk = ll_vms.get_snapshot_disks(
            self.vm_name, config.STATELESS_SNAPSHOT
        )[0]
        assert not ll_vms.attach_snapshot_disk_to_vm(
            stateless_snapshot_disk, config.VM_NAME[0]
        ), "Succeeded to attach a stateless snapshot's disk to vm"


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
)
class TestCase16742(TestCase):
    """
    Attach read only disk to VM with IDE interface - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16742")
    def test_attach_read_only_disk_with_ide(self):
        """
        Attach read only disk to VM with IDE interface
        """
        assert ll_disks.attachDisk(
            False, self.disk_name, self.vm_name, read_only=True,
            interface=config.IDE
        ), (
            "Succeeded to attach disk %s to VM %s in preview" %
            (self.disk_name, self.vm_name)
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    create_second_vm.__name__
)
class TestCase16743(TestCase):
    """
    Detach snapshot's disk from VM
    """
    __test__ = True
    installation = False

    @polarion("RHEVM3-16743")
    def test_detach_snapshot_disk_to_vm(self):
        """
        Detach snapshot's disk from VM
        """
        snapshot_disk = ll_vms.get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )[0]
        assert ll_vms.attach_snapshot_disk_to_vm(
            snapshot_disk, self.second_vm_name
        ), (
            "Failed to attach snapshot's disk %s to VM %s" %
            (snapshot_disk.get_alias(), self.second_vm_name)
        )
        assert ll_disks.detachDisk(
            False, snapshot_disk.get_alias(), self.vm_name
        ), (
            "Succeeded to detach snapshot's disk %s from VM %s" %
            (snapshot_disk.get_alias(), self.vm_name)
        )
