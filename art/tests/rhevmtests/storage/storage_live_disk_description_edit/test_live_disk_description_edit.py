"""
3.5 Live Disk Description Edit
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Allow_Online_Vdisk_Editing
"""
import logging
import pytest
from rhevmtests.storage import config
import helpers
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    jobs as ll_jobs,
)
from rhevmtests.storage.fixtures import (
    create_vm, delete_disks,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from rhevmtests.storage.storage_live_disk_description_edit.fixtures import (
    add_disks_permutation, create_second_vm, poweroff_vms,
)
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import attr, StorageTest as BaseTestCase

logger = logging.getLogger(__name__)

VM_INITIAL_DESCRIPTION = "disk_description_initial_state"
VM_POWERED_ON_DESCRIPTION = "vm_powered_on_disk_description"
VM_SUSPENDED_DESCRIPTION = "vm_suspended_on_disk_description"

ALIAS = "alias"
DESCRIPTION = "description"
GLUSTERFS = config.STORAGE_TYPE_GLUSTER
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
CEPH = config.STORAGE_TYPE_CEPH
NFS = config.STORAGE_TYPE_NFS


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks_permutation.__name__,
    delete_disks.__name__
)
class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False


class BaseClassEditDescription(BasicEnvironment):
    """
    Base class to be used by test cases 11500 and 11501
    """
    __test__ = False

    updated_descriptions = dict()
    original_descriptions = dict()

    def basic_positive_flow(self):
        """
        Basic flow used by the majority of test cases in this plan
        """
        for disk_alias in self.disk_names:
            disk_object = ll_disks.get_disk_obj(disk_alias)
            testflow.step(
                "Attaching disk '%s' to VM: %s", disk_alias, self.vm_name
            )
            ll_disks.attachDisk(True, disk_alias, self.vm_name)
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, disk_object.get_description()
            )
            self.original_descriptions.update(
                {disk_alias: disk_object.get_description()}
            )
            self.updated_descriptions.update(
                {disk_alias: "update"}
            )
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                self.updated_descriptions.get(disk_alias)
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.updated_descriptions[disk_alias],
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias,
                self.updated_descriptions[disk_alias]
            )
        testflow.step("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP)
        for disk_alias in self.disk_names:
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias,
                self.updated_descriptions[disk_alias]
            )
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
        testflow.step("Stop VM %s", self.vm_name)
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        for disk_alias in self.disk_names:
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            testflow.step("Update disk %s to original description", disk_alias)
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=self.vm_name
            )
            ll_disks.detachDisk(True, disk_alias, self.vm_name)


class TestCase11500(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = ISCSI in opts['storages'] or FCP in opts['storages']
    polarion_test_case = '11500'
    storages = set([ISCSI, FCP])
    # Bugzilla history
    # 1211314: CLI auto complete option description is missing for add disk

    @polarion("RHEVM3-11500")
    @attr(tier=3)
    def test_edit_description_on_block_or_file_domain(self):
        """
        1. Add VM with a block based disk, add a description and run the VM,
        verify description
        2. Edit description while the VM is up
        3. Power off the VM, run the VM and verify that the description
        hasn't changed
        4. Suspend the VM, edit description, power off the VM and verify the
        description
        """
        self.basic_positive_flow()


class TestCase11501(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a file domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = (
        NFS in opts['storages'] or GLUSTERFS in opts['storages'] or
        CEPH in opts['storages']
    )
    polarion_test_case = '11501'
    storages = set([NFS, GLUSTERFS, CEPH])
    # Bugzilla history
    # 1211314: CLI auto complete option description is missing for add disk

    @polarion("RHEVM3-11501")
    @attr(tier=3)
    def test_edit_description_on_block_or_file_domain(self):
        """
        1. Add VM with a file based disk, add a description and run the VM,
        verify description
        2. Edit description while the VM is up
        3. Power off the VM, run the VM and verify that the description
        hasn't changed
        4. Suspend the VM, edit description, power off the VM and verify the
        description
        """
        self.basic_positive_flow()


@pytest.mark.usefixtures(
    create_second_vm.__name__,
    poweroff_vms.__name__,
)
class TestCase11503(BasicEnvironment):
    """
    Hot plug disk from one running VM to another, ensuring that the
    description does not change
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = True
    polarion_test_case = '11503'
    original_descriptions = dict()

    @polarion("RHEVM3-11503")
    @attr(tier=3)
    def test_verify_disk_description_edit_works_across_hot_plug(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Remove the Disk
        3. Hot plug the disk into a new VM, verify that the description is
        still valid
        """
        disks_to_hotplug = {}
        self.vms_to_poweroff = [self.vm_name, self.vm_name_2]
        for disk_alias in self.disk_names:
            disk_object = ll_disks.get_disk_obj(disk_alias)
            if disk_object.get_interface() != config.INTERFACE_SPAPR_VSCSI:
                # SPAPR VSCSI does not support hotplug
                disks_to_hotplug[disk_alias] = disk_object

        for disk_alias, disk_object in disks_to_hotplug.iteritems():
            testflow.step("Attach disk %s to VM %s", disk_alias, self.vm_name)
            ll_disks.attachDisk(True, disk_alias, self.vm_name)
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, disk_object.get_description()
            )
            self.original_descriptions.update(
                {disk_alias: disk_object.get_description()}
            )
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                VM_INITIAL_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_INITIAL_DESCRIPTION,
                vmName=self.vm_name
            )
        testflow.step("Start VMs %s and %s",  self.vm_name,  self.vm_name_2)
        ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        ll_vms.startVm(True, self.vm_name_2, wait_for_ip=True)
        assert ll_vms.waitForVmsStates(True, [self.vm_name, self.vm_name_2])

        for disk_alias in disks_to_hotplug:
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_INITIAL_DESCRIPTION
            )
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            testflow.step("Detach disk %s", disk_alias)
            ll_disks.detachDisk(True, disk_alias, self.vm_name)
            testflow.step("Attach disk %s and verify description", disk_alias)
            ll_disks.attachDisk(True, disk_alias, self.vm_name_2)
            assert helpers.verify_vm_disk_description(
                self.vm_name_2, disk_alias, VM_POWERED_ON_DESCRIPTION
            )

        # Detach disk that was attached into the 2nd VM from the 1st
        testflow.step("Stop VMs %s", [self.vm_name, self.vm_name_2])
        ll_vms.stop_vms_safely([self.vm_name, self.vm_name_2])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.waitForVMState(self.vm_name_2, config.VM_DOWN)
        for disk_alias in disks_to_hotplug:
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                self.original_descriptions.get(disk_alias)
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=self.vm_name_2
            )
            ll_disks.detachDisk(True, disk_alias, self.vm_name_2)


@pytest.mark.usefixtures(
    poweroff_vms.__name__
)
class TestCase11504(BasicEnvironment):
    """
    Attempt to edit a disk's description on a running VM while running a
    Live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = True
    polarion_test_case = '11504'

    @polarion("RHEVM3-11504")
    @attr(tier=3)
    def test_ensure_disk_description_is_locked_during_lsm(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Start a Live Storage migration, and ensure that the disk
        description cannot happen while this operation is running
        """
        for disk_alias in self.disk_names:
            testflow.step("Attach disk %s to VM %s", disk_alias, self.vm_name)
            ll_disks.attachDisk(True, disk_alias, self.vm_name)

        for disk_alias in self.disk_names:
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
        # Find a storage domain of the same type to migrate the disk into
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_names[0], self.vm_name, self.storage
        )
        ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_status=config.VM_UP
        )
        self.vms_to_poweroff.append(self.vm_name)
        for disk_alias in self.disk_names:
            testflow.step(
                "Migrate disk %s to storage-domain %s", disk_alias, target_sd
            )
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk_alias, target_sd, wait=False
            )
            ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
            disk_description_expected_to_fail = (
                "LSM_disk_description_will_not_work_at_all"
            )
            logger.info(
                "Waiting until disk is locked, this is expected to be the "
                "case when the Snapshot operation commences"
            )
            assert ll_disks.wait_for_disks_status(
                disk_alias, status=config.DISK_LOCKED
            )
            testflow.step(
                "Update disk %s description to %s", disk_alias,
                disk_description_expected_to_fail
            )
            assert ll_disks.updateDisk(
                False, alias=disk_alias,
                description=disk_description_expected_to_fail,
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            assert ll_vms.wait_for_snapshot_gone(
                vm_name=self.vm_name, snapshot=config.LIVE_SNAPSHOT_DESCRIPTION
            ), "Failed to remove snapshot %s" % (
                config.LIVE_SNAPSHOT_DESCRIPTION
            )
            assert ll_disks.wait_for_disks_status(disk_alias)
            ll_vms.wait_for_vm_snapshots(
                vm_name=self.vm_name, states=[config.SNAPSHOT_OK]
            )
