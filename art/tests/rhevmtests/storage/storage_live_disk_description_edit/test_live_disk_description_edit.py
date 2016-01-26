"""
3.5 Live Disk Description Edit
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Allow_Online_Vdisk_Editing
"""
import logging

import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as BaseTestCase
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)

VM1_NAME = config.VM_NAME[0]
VM2_NAME = config.VM_NAME[1]

VM_INITIAL_DESCRIPTION = "disk_description_initial_state"
VM_POWERED_ON_DESCRIPTION = "vm_powered_on_disk_description"
VM_SUSPENDED_DESCRIPTION = "vm_suspended_on_disk_description"

ALIAS = "alias"
DESCRIPTION = "description"
GLUSTERFS = config.STORAGE_TYPE_GLUSTER
ISCSI = config.STORAGE_TYPE_ISCSI
NFS = config.STORAGE_TYPE_NFS
VMS_WITH_VIRTIO_SCSI_FALSE = list()
DISK_STATUS_OK_TIMEOUT = 900


def setup_module():
    """
    Create one VM for use with all tests, create a list of VMs with
    VirtIO-SCSI disabled (and enable VirtIO-SCSI on these)
    """
    for vm_name in [VM1_NAME, VM2_NAME]:
        if not ll_vms.does_vm_exist(vm_name):
            raise exceptions.VMException(
                "VM '%s' does not exist, aborting test" % vm_name
            )

    for vm_name in [VM1_NAME, VM2_NAME]:
        logger.info(
            "Return VM object for current VM which will be checked for "
            "VirtIO-SCSI Enabled configuration"
        )
        vm = ll_vms.get_vm_obj(vm_name, all_content=True)
        is_virtio_scsi_enabled = vm.get_virtio_scsi().get_enabled()
        if not is_virtio_scsi_enabled:
            # Update global list, appending VM that had its VirtIO-SCSI
            # Enabled set to False, this will be reverted in the teardown
            VMS_WITH_VIRTIO_SCSI_FALSE.append(vm_name)
            ll_vms.updateVm(True, vm_name, virtio_scsi=True)


def teardown_module():
    """
    Stop VM used by all tests, restore VirtIO-SCSI Enabled option where this
    was updated
    """
    ll_vms.waitForVmsDisks(VM1_NAME)
    logger.info("Stop VM '%s'", VM1_NAME)
    ll_vms.stop_vms_safely([VM1_NAME])
    ll_vms.waitForVMState(VM1_NAME, config.VM_DOWN)

    logger.info(
        "Restore configuration to any VM that had its VirtIO-SCSI Enabled "
        "set to False before the start of the test run"
    )
    for vm_name in VMS_WITH_VIRTIO_SCSI_FALSE:
        ll_vms.updateVm(True, vm_name, virtio_scsi=False)


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    polarion_test_case = None

    def setup_with_disks(
            self, disk_interfaces=(config.VIRTIO, config.VIRTIO_SCSI)
    ):
        """
        Creates a set of disks to be used with all the Live disk
        description edit tests, and saves a dictionary with the aliases
        and descriptions of the created disks
        """
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        if config.PPC_ARCH:
            disk_interfaces += (config.INTERFACE_SPAPR_VSCSI,)
        self.disk_aliases = (
            storage_helpers.create_disks_from_requested_permutations(
                self.storage_domain, disk_interfaces, config.DISK_SIZE,
                test_name=self.polarion_test_case
            )
        )

    def tearDown(self):
        """
        Remove the disks created as part of the initial setup, this is to
        ensure no conflict between runs including Rest API and SDK
        """
        for disk in self.disk_aliases:
            if not ll_disks.deleteDisk(True, disk):
                logger.error("Failed to delete disk '%s'", disk)
                BaseTestCase.test_failed = True

        self.teardown_exception()


class BaseClassEditDescription(BasicEnvironment):
    """
    Base class to be used by test cases 11500 and 11501
    """
    __test__ = False

    def setUp(self):
        """
        Pass in all disk interfaces for the 2 basic sanity cases
        """
        self.setup_with_disks()
        self.original_descriptions = dict()
        self.updated_descriptions = dict()

    def basic_positive_flow(self):
        """
        Basic flow used by the majority of test cases in this plan
        """
        for disk_alias in self.disk_aliases:
            disk_object = ll_disks.get_disk_obj(disk_alias)
            logger.info("Attaching disk '%s' to VM", disk_alias)
            ll_disks.attachDisk(True, disk_alias, VM1_NAME)
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, disk_object.get_description()
            )

            self.original_descriptions.update(
                {disk_alias: disk_object.get_description()}
            )
            self.updated_descriptions.update(
                {disk_alias: disk_object.get_description() + "_update"}
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.updated_descriptions[disk_alias],
                vmName=VM1_NAME
            )
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, self.updated_descriptions[disk_alias]
            )
        logger.info("Starting VM")
        assert ll_vms.startVm(True, VM1_NAME, config.VM_UP)
        for disk_alias in self.disk_aliases:
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, self.updated_descriptions[disk_alias]
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=VM1_NAME
            )
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
        logger.info("Stopping VM safely")
        ll_vms.stop_vms_safely([VM1_NAME])
        ll_vms.waitForVMState(VM1_NAME, config.VM_DOWN)
        for disk_alias in self.disk_aliases:
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=VM1_NAME
            )
            ll_disks.detachDisk(True, disk_alias, VM1_NAME)


@attr(tier=1)
class TestCase11500(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '11500'
    # Bugzilla history
    # 1211314: CLI auto complete option description is missing for add disk

    @polarion("RHEVM3-11500")
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


@attr(tier=1)
class TestCase11501(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a file domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = NFS in opts['storages'] or GLUSTERFS in opts['storages']
    storages = set([NFS, GLUSTERFS])
    polarion_test_case = '11501'
    # Bugzilla history
    # 1211314: CLI auto complete option description is missing for add disk

    @polarion("RHEVM3-11501")
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


@attr(tier=2)
class TestCase11503(BasicEnvironment):
    """
    Hot plug disk from one running VM to another, ensuring that the
    description does not change
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = True
    polarion_test_case = '11503'

    def setUp(self):
        """ Setup disks for this test case """
        self.original_descriptions = dict()
        self.setup_with_disks()

    def tearDown(self):
        """ Remove disks and power off VM for this test case """
        super(TestCase11503, self).tearDown()
        ll_vms.stop_vms_safely([VM2_NAME])
        ll_vms.waitForVMState(VM2_NAME, config.VM_DOWN)

    @polarion("RHEVM3-11503")
    def test_verify_disk_description_edit_works_across_hot_plug(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Remove the Disk
        3. Hot plug the disk into a new VM, verify that the description is
        still valid
        """
        disks_to_hotplug = {}
        for disk_alias in self.disk_aliases:
            disk_object = ll_disks.get_disk_obj(disk_alias)
            if disk_object.get_interface() != config.INTERFACE_SPAPR_VSCSI:
                # SPAPR VSCSI does not support hotplug
                disks_to_hotplug[disk_alias] = disk_object

        for disk_alias, disk_object in disks_to_hotplug.iteritems():
            ll_disks.attachDisk(True, disk_alias, VM1_NAME)
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, disk_object.get_description()
            )
            self.original_descriptions.update(
                {disk_alias: disk_object.get_description()}
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_INITIAL_DESCRIPTION,
                vmName=VM1_NAME
            )

        ll_vms.startVm(True, VM1_NAME)
        ll_vms.startVm(True, VM2_NAME)
        assert ll_vms.waitForVmsStates(True, [VM1_NAME, VM2_NAME])

        for disk_alias in disks_to_hotplug:
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, VM_INITIAL_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=VM1_NAME
            )
            assert helpers.verify_vm_disk_description(
                VM1_NAME, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            ll_disks.detachDisk(True, disk_alias, VM1_NAME)
            ll_disks.attachDisk(True, disk_alias, VM2_NAME)
            assert helpers.verify_vm_disk_description(
                VM2_NAME, disk_alias, VM_POWERED_ON_DESCRIPTION
            )

        # Detach disk that was attached into the 2nd VM from the 1st
        ll_vms.stop_vms_safely([VM1_NAME, VM2_NAME])
        ll_vms.waitForVMState(VM1_NAME, config.VM_DOWN)
        ll_vms.waitForVMState(VM2_NAME, config.VM_DOWN)
        for disk_alias in disks_to_hotplug:
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=VM2_NAME
            )
            ll_disks.detachDisk(True, disk_alias, VM2_NAME)


@attr(tier=2)
class TestCase11504(BasicEnvironment):
    """
    Attempt to edit a disk's description on a running VM while running a
    Live storage migration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = True
    polarion_test_case = '11504'
    vm_name = polarion_test_case + "_Test_VM"
    bz = {'1289538': {'engine': None, 'version': ['3.6']}}
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785:  Error 'Unable to find org.ovirt.engine.core.common.job.Step
    # with id' after live migrate a Virtio RAW disk, job stays in status
    # STARTED

    def setUp(self):
        """ Setup disks for this test case """
        self.setup_with_disks()
        storage_helpers.create_vm_or_clone(
            True, self.vm_name, storageDomainName=self.storage_domain
        )

    @polarion("RHEVM3-11504")
    def test_ensure_disk_description_is_locked_during_lsm(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Start a Live Storage migration, and ensure that the disk
        description cannot happen while this operation is running
        """
        for disk_alias in self.disk_aliases:
            ll_disks.attachDisk(True, disk_alias, self.vm_name)

        for disk_alias in self.disk_aliases:
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=VM_POWERED_ON_DESCRIPTION, vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
        # Find a storage domain of the same type to migrate the disk into
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_aliases[0], self.vm_name, self.storage
        )
        for disk_alias in self.disk_aliases:
            ll_vms.live_migrate_vm_disk(
                self.vm_name, disk_alias, target_sd, wait=False
            )
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
            assert ll_disks.updateDisk(
                False, alias=disk_alias,
                description=disk_description_expected_to_fail,
                vmName=self.vm_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.wait_for_disks_status(disk_alias)

    def tearDown(self):
        """
        Ensure that the snapshot created is removed and all disks are detached
        """
        # Power off VM, remove snapshot created during Live storage
        # migration and then delete each disk
        logger.info(
            "Wait until all the disks are no longer locked, this will be the "
            "case once Live storage migration has completed"
        )
        ll_jobs.wait_for_jobs([config.ENUMS['job_live_migrate_disk']])
        assert ll_disks.wait_for_disks_status(
            self.disk_aliases, timeout=DISK_STATUS_OK_TIMEOUT
        )

        ll_vms.stop_vms_safely([self.vm_name])
        super(TestCase11504, self).tearDown()
        ll_vms.removeVm(True, self.vm_name)
