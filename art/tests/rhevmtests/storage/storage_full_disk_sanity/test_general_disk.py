"""
Storage Disk sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage_3_6/3_6_Storage_Disk_General
"""
import logging
import pytest
import config
from art.unittest_lib import (
    StorageTest as TestCase,
    tier2,
    tier3,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    templates as ll_template,
)
from art.test_handler.tools import bz, polarion
import rhevmtests.helpers as helpers
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    add_disk, attach_disk, create_snapshot, create_vm, create_template,
    deactivate_domain, delete_disks, initialize_storage_domains, poweroff_vm,
    preview_snapshot, undo_snapshot, delete_disk,
)

from rhevmtests.storage.fixtures import remove_vm # noqa

from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    create_second_vm, poweroff_vm_and_wait_for_stateless_to_remove
)

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    create_vm.__name__,
    delete_disks.__name__,
)
class NegativeAttachDetach(TestCase):
    """
    * Attach a locked disk to VM
    * Detach disk from vm in powering up state
    """
    __test__ = True
    disk_size = 20 * config.GB
    installation = False

    @polarion("RHEVM-16776")
    @tier2
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

    @polarion("RHEVM-16775")
    @tier2
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

    @polarion("RHEVM-16736")
    @tier2
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

    @polarion("RHEVM-16739")
    @tier2
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


@pytest.mark.usefixtures(create_vm.__name__)
class TestCase16737(TestCase):
    """
    Attach OVF store disk to VM - should fail
    """
    __test__ = True
    installation = False
    storage_domain = None

    @polarion("RHEVM-16737")
    @tier3
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


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
    preview_snapshot.__name__,
    add_disk.__name__,
    undo_snapshot.__name__,
    delete_disk.__name__,
)
class TestCase16738(TestCase):
    """
    Attach disk to VM in preview - should fail
    """
    __test__ = True
    installation = False

    @polarion("RHEVM-16738")
    @tier3
    def test_attach_disk_to_vm_in_preview(self):
        """
        Attach disk to VM in preview of snapshot
        """
        assert ll_disks.attachDisk(False, self.disk_name, self.vm_name), (
            "Succeeded to attach disk %s to VM %s in preview" %
            (self.disk_name, self.vm_name)
        )


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

    @polarion("RHEVM-16741")
    @tier3
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

    @polarion("RHEVM-16743")
    @tier3
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


class TestCase16774(TestCase):
    """
    Remove OVF store disk - should fail
    """
    __test__ = True

    @polarion("RHEVM-16774")
    @tier3
    def test_remove_ovf_disk(self):
        """
        Remove OVF disk - should fail
        """
        ovf_disk = None
        all_disks = ll_disks.get_all_disks()
        for disk in all_disks:
            if disk.get_alias() == config.OVF_DISK_ALIAS:
                ovf_disk = disk
                break

        assert ll_disks.deleteDisk(False, disk_id=ovf_disk.get_id()), (
            "Succeeded to delete OVF disk %s" % (ovf_disk.get_alias())
        )


@pytest.mark.usefixtures(
    add_disk.__name__,
    delete_disk.__name__,
)
class TestCase16777(TestCase):
    """
    Remove locked disk - should fail
    """
    __test__ = True

    @polarion("RHEVM-16777")
    @tier3
    @helpers.wait_for_jobs_deco([config.JOB_MOVE_COPY_DISK])
    def test_remove_locked_disk(self):
        """
        Try to remove locked disk - should fail
        """
        target_sd = ll_disks.get_other_storage_domain(self.disk_name)
        assert ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=target_sd, wait=False
        ), (
            "Failed move disk %s to storage domain %s" %
            (self.disk_name, target_sd)
        )
        assert ll_disks.deleteDisk(False, self.disk_name), (
            "Succeeded to delete locked disk %s" % self.disk_name
        )


@bz({'1370075': {}})
@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_template.__name__,
)
class TestCase16780(TestCase):
    """
    Remove template's disk of locked template - should fail
    """
    __test__ = True

    @polarion("RHEVM-16780")
    @tier3
    def test_delete_disk_of_locked_template(self):
        """
        Try Remove template's disk of locked template - should fail
        """
        template_disk = ll_template.getTemplateDisks(self.template_name)[0]
        ll_template.copy_template_disks(
            self.template_name, [self.storage_domain_1], False
        )
        assert ll_template.remove_template_disk_from_storagedomain(
            False, self.template_name, self.storage_domain,
            disk_id=template_disk.get_id(),
        ), (
            "Succeeded to delete disk %s of locked template %s" % (
                template_disk.get_alias(), self.template_name
            )
        )
        # wait for template copy disk to end so teardown will succeed
        ll_disks.wait_for_disks_status(
            template_disk.get_alias(), timeout=config.DEFAULT_DISK_TIMEOUT
        )


@bz({'1370075': {}})
@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_template.__name__,
)
class TestCase16782(TestCase):
    """
    Remove template's disk
    """
    __test__ = True

    @polarion("RHEVM-16782")
    @tier2
    def test_delete_disk_of_template(self):
        """
        Remove template's disk
        """
        template_disk = ll_template.getTemplateDisks(self.template_name)[0]
        ll_template.copy_template_disks(
            self.template_name, [self.storage_domain_1]
        )
        assert ll_template.remove_template_disk_from_storagedomain(
            False, self.template_name, self.storage_domain_1,
            disk_id=template_disk.get_id(),
        ), ("Failed to delete disk %s of template %s from storage domain %s"
            % (template_disk.get_alias(), self.template_name,
               self.storage_domain))


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__
)
class TestCase16784(TestCase):
    """
    Update disk size of read only disk - should fail
    """
    __test__ = True
    installation = False
    update_attach_params = {
        'read_only': True,
    }

    @polarion("RHEVM-16784")
    @tier3
    def test_update_disk_size_of_RO_disk(self):
        """
        Update disk size of read only disk
        """
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name,
            provisioned_size=2 * config.GB
        ), "Failed to update disk size of read-only disk"


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_snapshot.__name__,
)
class TestCase16785(TestCase):
    """
    Update snapshot's disk size
    """
    __test__ = True
    installation = False

    @polarion("RHEVM-16785")
    @tier3
    def test_resize_snapshot_disk(self):
        """
        Resize a snapshot's disk
        """
        snapshot_disk = ll_vms.get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )[0]
        assert ll_vms.updateDisk(
            True, vmName=self.vm_name, alias=snapshot_disk.get_alias(),
            provisioned_size=10 * config.GB
        ), "Failed to update snapshot's disk size of VM" % self.vm_name
        ll_vms.waitForDisksStat(self.vm_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
)
class TestCase16786(TestCase):
    """
    Update disk size to smaller size (6GB -> 1 GB)
    """
    __test__ = True
    installation = False

    @polarion("RHEVM-16786")
    @tier2
    def test_update_disk_size_to_smaller_size(self):
        """
        Update disk size to smaller size - should fail
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=vm_disk,
            provisioned_size=1 * config.GB
        ), "Succeeded to update disk size from 6G to 1GB"


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_vm.__name__,
    deactivate_domain.__name__,
)
class TestCase16787(TestCase):
    """
    Update disk size of disk on inactive storage domain
    """
    __test__ = True
    installation = False
    sd_to_deactivate_index = 0

    @polarion("RHEVM-16787")
    @tier3
    def test_update_disk_size_to_smaller_size(self):
        """
        Update disk size of disk on inactive storage domain - should fail
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=vm_disk,
            provisioned_size=10 * config.GB
        ), "Succeeded to update disk size on storage domain in maintenance"
