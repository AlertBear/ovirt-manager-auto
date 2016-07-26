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
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, StorageTest as BaseTestCase
from rhevmtests.storage import helpers as storage_helpers

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
VMS_WITH_VIRTIO_SCSI_FALSE = list()
DISK_STATUS_OK_TIMEOUT = 900


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    polarion_test_case = None
    vm1_name = None
    vm2_name = None

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
        vm_names = storage_helpers.get_vms_for_storage(self.storage)
        self.vm1_name = vm_names[0]
        self.vm2_name = vm_names[1]
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
            ll_disks.attachDisk(True, disk_alias, self.vm1_name)
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, disk_object.get_description()
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
                vmName=self.vm1_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias,
                self.updated_descriptions[disk_alias]
            )
        logger.info("Starting VM")
        assert ll_vms.startVm(True, self.vm1_name, config.VM_UP)
        for disk_alias in self.disk_aliases:
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias,
                self.updated_descriptions[disk_alias]
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=self.vm1_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
        logger.info("Stopping VM safely")
        ll_vms.stop_vms_safely([self.vm1_name])
        ll_vms.waitForVMState(self.vm1_name, config.VM_DOWN)
        for disk_alias in self.disk_aliases:
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=self.vm1_name
            )
            ll_disks.detachDisk(True, disk_alias, self.vm1_name)


@attr(tier=2)
class TestCase11500(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Allow_Online_Vdisk_Editing
    """
    __test__ = ISCSI in opts['storages'] or FCP in opts['storages']
    storages = set([ISCSI, FCP])
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


@attr(tier=2)
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
    storages = set([NFS, GLUSTERFS, CEPH])
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
        ll_vms.stop_vms_safely([self.vm2_name])
        ll_vms.waitForVMState(self.vm2_name, config.VM_DOWN)

    @polarion("RHEVM3-11503")
    @bz({'1350708': {}})
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
            ll_disks.attachDisk(True, disk_alias, self.vm1_name)
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, disk_object.get_description()
            )
            self.original_descriptions.update(
                {disk_alias: disk_object.get_description()}
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_INITIAL_DESCRIPTION,
                vmName=self.vm1_name
            )

        ll_vms.startVm(True, self.vm1_name)
        ll_vms.startVm(True, self.vm2_name)
        assert ll_vms.waitForVmsStates(True, [self.vm1_name, self.vm2_name])

        for disk_alias in disks_to_hotplug:
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, VM_INITIAL_DESCRIPTION
            )
            assert ll_disks.updateDisk(
                True, alias=disk_alias, description=VM_POWERED_ON_DESCRIPTION,
                vmName=self.vm1_name
            )
            assert helpers.verify_vm_disk_description(
                self.vm1_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )
            ll_disks.detachDisk(True, disk_alias, self.vm1_name)
            ll_disks.attachDisk(True, disk_alias, self.vm2_name)
            assert helpers.verify_vm_disk_description(
                self.vm2_name, disk_alias, VM_POWERED_ON_DESCRIPTION
            )

        # Detach disk that was attached into the 2nd VM from the 1st
        ll_vms.stop_vms_safely([self.vm1_name, self.vm2_name])
        ll_vms.waitForVMState(self.vm1_name, config.VM_DOWN)
        ll_vms.waitForVMState(self.vm2_name, config.VM_DOWN)
        for disk_alias in disks_to_hotplug:
            assert ll_disks.updateDisk(
                True, alias=disk_alias,
                description=self.original_descriptions.get(disk_alias),
                vmName=self.vm2_name
            )
            ll_disks.detachDisk(True, disk_alias, self.vm2_name)


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
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785:  Error 'Unable to find org.ovirt.engine.core.common.job.Step
    # with id' after live migrate a Virtio RAW disk, job stays in status
    # STARTED

    def setUp(self):
        """ Setup disks for this test case """
        self.setup_with_disks()
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name)

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
