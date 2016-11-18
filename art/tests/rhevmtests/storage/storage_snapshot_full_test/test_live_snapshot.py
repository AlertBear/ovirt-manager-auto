"""
Storage live snapshot sanity tests - full test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Snapshot
"""
import logging
import os
import shlex
import pytest

from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import config
from art.test_handler.tools import bz, polarion
from art.unittest_lib import StorageTest as TestCase, attr, testflow
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
)
from utilities.machine import Machine, LINUX

from rhevmtests.storage.fixtures import (
    create_vm, initialize_storage_domains, undo_snapshot, add_disk,
    create_template, start_vm, attach_disk, poweroff_vm, remove_vms,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa

from fixtures import (
    initialize_prepare_environment, add_disks_different_sd,
    add_two_vms_from_template,
)
logger = logging.getLogger(__name__)

LIVE_SNAPSHOT_DESC = 'test_live_snapshot'
MAX_DESC_LENGTH = 4000
SPECIAL_CHAR_DESC = '!@#$\% ^&*/\\'


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_prepare_environment.__name__,
    undo_snapshot.__name__,
)
class BasicEnvironmentSetUp(TestCase):
    """
    This class implements setup, teardowns and common functions
    """
    __test__ = False
    file_name = 'test_file'
    mount_path = '/root'
    cmd_create = 'echo "test_txt" > test_file'
    cm_del = 'rm -f test_file'

    def _perform_snapshot_operation(
            self, vm_name, disks=None, wait=True, live=False):
        if not live:
            if not ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
                ll_vms.shutdownVm(True, vm_name)
                ll_vms.waitForVMState(vm_name, config.VM_DOWN)
        if disks:
            is_disks = "disks: %s" % disks
        else:
            is_disks = "all disks"
        testflow.step(
            "Adding new snapshot to VM %s with %s", self.vm_name, is_disks
        )
        status = ll_vms.addSnapshot(
            True, vm_name, self.snapshot_description, disks_lst=disks,
            wait=wait
        )
        assert status, (
            "Failed to create snapshot %s" % self.snapshot_description
        )
        if wait:
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
            ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    def check_file_existence_operation(self, vm_name, should_exist=True):

        ll_vms.start_vms([vm_name], 1, wait_for_ip=False)
        ll_vms.waitForVMState(vm_name)
        full_path = os.path.join(self.mount_path, self.file_name)
        logger.info("Checking full path %s", full_path)
        result = self.vm.isFileExists(full_path)
        logger.info("File %s", "exists" if result else "does not exist")

        if should_exist != result:
            return False
        return True


@attr(tier=2)
class TestCase11660(BasicEnvironmentSetUp):
    """
    Full flow Live snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11660

    Create live snapshot
    Add file to the VM
    Stop VM
    Preview and commit snapshot

    Expected Results:
    Snapshot should be successfully created
    Verify that a new data is written on new volumes
    Verify that the file no longer exists both after preview and after commit
    """
    __test__ = True

    def _test_Live_snapshot(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        ll_vms.startVms([vm_name])
        ll_vms.waitForVMState(vm_name)
        vm_ip = hl_vms.get_vm_ip(vm_name, start_vm=False)
        self.vm = Machine(
            vm_ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        ).util(LINUX)
        testflow.step("Creating snapshot on a running VM %s", vm_name)
        self._perform_snapshot_operation(vm_name, live=True)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        testflow.step("Writing files to VM's %s disk", vm_name)
        cmd = self.cmd_create
        status, out = self.vm.runCmd(shlex.split(cmd))
        assert status, "Unable to write to VM %s: %s" % (vm_name, out)
        assert self.check_file_existence_operation(vm_name, True), (
            "Writing operation failed"
        )
        ll_vms.shutdownVm(True, vm_name, 'false')
        testflow.step(
            "Previewing snapshot %s on VM %s", self.snapshot_description,
            vm_name
        )
        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_description,
            ensure_vm_down=True
        )
        assert self.previewed, "Failed to preview snapshot %s" % (
            self.snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_ip=True
        )
        testflow.step("Checking that files no longer exist after preview")
        # PPC's IP doesn't seems to be static
        vm_ip = hl_vms.get_vm_ip(vm_name, start_vm=False)
        self.vm = Machine(
            vm_ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        ).util(LINUX)
        assert self.check_file_existence_operation(vm_name, False), (
            "Snapshot operation failed"
        )

        testflow.step(
            "Committing snapshot %s on VM %s", self.snapshot_description,
            vm_name
        )
        assert ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True
        ), "Failed to commit snapshot %s" % self.snapshot_description
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        testflow.step("Checking that files no longer exist after commit")
        assert self.check_file_existence_operation(vm_name, False), (
            "Snapshot operation failed"
        )

    @polarion("RHEVM3-11660")
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running
        """
        self._test_Live_snapshot(self.vm_name)


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_prepare_environment.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
@attr(tier=2)
class TestCase11679(BasicEnvironmentSetUp):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11679

    Add a disk to the VMs
    Create live snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    mount_path = '/new_fs_%s'
    cmd_create = 'echo "test_txt" > %s/test_file'

    def _prepare_fs_on_devs(self):
        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True), (
            "Failed to start VM %s" % self.vm_name
        )
        # PPC's IP doesn't seems to be static
        vm_ip = hl_vms.get_vm_ip(self.vm_name, start_vm=False)
        self.vm = Machine(
            vm_ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        ).util(LINUX)
        vm_devices = self.vm.get_storage_devices()
        assert vm_devices,  "No devices found in VM %s" % self.vm_name
        logger.info("Devices found: %s", vm_devices)
        self.devices = [d for d in vm_devices if d != 'vda']
        self.devices.sort()
        for dev in self.devices:
            dev_size = self.vm.get_storage_device_size(dev)
            dev_path = os.path.join('/dev', dev)
            logger.info("Creating partition for dev: %s", dev_path)
            dev_number = self.vm.createPartition(
                dev_path, (dev_size * config.GB) - 100 * config.MB
            )
            logger.info("Creating file system for dev: %s", dev + dev_number)
            self.vm.createFileSystem(
                dev_path, dev_number, 'ext4', (self.mount_path % dev)
            )

            self.mounted_paths.append(self.mount_path % dev)

    def check_file_existence_operation(
            self, should_exist=True, operation='snapshot'
    ):
        ll_vms.start_vms([self.vm_name], 1, config.VM_UP, wait_for_ip=True)
        # PPC's IP doesn't seems to be static
        vm_ip = hl_vms.get_vm_ip(self.vm_name, start_vm=False)
        self.vm = Machine(
            vm_ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        ).util(LINUX)
        lst = []
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s", "exist" if result else "not exist")
            lst.append(result)

        assert should_exist in lst, "%s operation failed" % operation

    def _test_Live_snapshot(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        logger.info("Make sure VM %s is up", vm_name)
        if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
            ll_vms.startVms([vm_name], config.VM_UP, wait_for_ip=True)
            # PPC's IP doesn't seems to be static
            vm_ip = hl_vms.get_vm_ip(vm_name, start_vm=False)
            self.vm = Machine(
                vm_ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW
            ).util(LINUX)
        testflow.step("Creating live snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        vm_devices = self.vm.get_storage_devices()
        assert vm_devices, "No devices found"
        logger.info("Devices found: %s", vm_devices)
        self.devices = [d for d in vm_devices if d != 'vda']
        self.devices.sort()
        for dev in self.devices:
            logger.info("writing file to disk")
            mount_path = self.mount_path % dev
            cmd = self.cmd_create % mount_path
            status, _ = self.vm.runCmd(shlex.split(cmd))

            assert status
            self.check_file_existence_operation(True, 'writing')
        ll_vms.stop_vms_safely([vm_name])

        testflow.step(
            "Previewing snapshot %s on VM %s",
            self.snapshot_description, vm_name
        )

        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_description,
            ensure_vm_down=True)
        assert self.previewed, "Failed to preview snapshot %s" % (
            self.snapshot_description
        )
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        )

        testflow.step("Checking that files no longer exist after preview")
        self.check_file_existence_operation(False)

        testflow.step("Commit snapshot")
        self.check_file_existence_operation(False)
        assert ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True), (
                "Failed to commit snapshot %s" % self.snapshot_description
            )
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        testflow.step("Checking that files no longer exist after commit")
        self.check_file_existence_operation(False)

    @polarion("RHEVM3-11679")
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running
        """
        self._prepare_fs_on_devs()
        self._test_Live_snapshot(self.vm_name)


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
)
@attr(tier=3)
class TestCase11676(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11676

    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = True

    def _test_snapshot_desc_length(self, positive, length, vm_name):
        """
        Tries to create snapshot with given length description
        Parameters:
            * length - how many 'a' chars should description contain
        """
        assert ll_vms.startVm(True, vm_name), "Failed to start VM %s" % vm_name
        description = length * 'a'
        testflow.step(
            "Trying to create snapshot on VM %s with description "
            "containing %d 'a' letters", vm_name, length
        )
        assert ll_vms.addSnapshot(
            positive, vm=vm_name, description=description
        )

    @polarion("RHEVM3-11676")
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        self._test_snapshot_desc_length(
            True, MAX_DESC_LENGTH, self.vm_name
        )

    @polarion("RHEVM3-11676")
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        testflow.step(
            "Trying to create snapshot with description %s",
            SPECIAL_CHAR_DESC
        )
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=SPECIAL_CHAR_DESC
        ), "Failed to add snapshot %s to VM %s" % (
            SPECIAL_CHAR_DESC, self.vm_name
        )


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_storage_domains.__name__,
    add_disks_different_sd.__name__,
    start_vm.__name__,
)
@attr(tier=3)
class TestCase11665(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11665

    Create 2 additional disks on a VM, each on a different storage domain
    Add snapshot

    Expected Results:
    You should be able to create a snapshot
    """
    __test__ = True
    disks_count = 2

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_CREATE_SNAPSHOT])
    @polarion("RHEVM3-11665")
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on VM that has disks on multiple
        storage domains
        """
        testflow.step(
            "Create a snapshot on VM %s that contains multiple disks on "
            "different domains", self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
)
@attr(tier=3)
class TestCase11680(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11680

    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = True

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MIGRATE_VM])
    @polarion("RHEVM3-11680")
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        assert ll_vms.startVm(True, self.vm_name), "Failed to start VM %s" % (
            self.vm_name
        )
        testflow.step("Migrate VM %s", self.vm_name)
        assert ll_vms.migrateVm(True, self.vm_name, wait=False)
        testflow.step("Take snapshot while the VM is migrating")
        assert ll_vms.addSnapshot(
            False, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_storage_domains.__name__,
    add_disks_different_sd.__name__,
    start_vm.__name__,
)
@attr(tier=2)
class TestCase11674(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11674/

    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = True
    disks_count = 1

    @polarion("RHEVM3-11674")
    def test_snapshot_with_multiple_disks(self):
        """
        Checks that created snapshot appears only once although VM has more
        disks
        """
        snap_descs = set([config.ACTIVE_SNAPSHOT, LIVE_SNAPSHOT_DESC])
        testflow.step("Create snapshot on VM %s", self.vm_name)
        assert ll_vms.addSnapshot(
            True, vm=self.vm_name, description=LIVE_SNAPSHOT_DESC
        )
        testflow.step(
            "Ensure only one snapshot appears even if the VM has multiple "
            "disks attached"
        )
        snapshots = ll_vms._getVmSnapshots(self.vm_name, False)
        current_snap_descs = set([snap.description for snap in snapshots])
        assert snap_descs == current_snap_descs


@bz({'1396960': {}})
@pytest.mark.usefixtures(
    create_vm.__name__,
    create_template.__name__,
    add_two_vms_from_template.__name__,
    remove_vms.__name__,
)
@attr(tier=3)
class TestCase11684(TestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11684

    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add snapshot for both thin and cloned VMs

    Expected Results:

    Live snapshots should be created for both cases
    """
    __test__ = True

    @polarion("RHEVM3-11684")
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        testflow.step("Create a snapshot on a thinly provisioned vm")
        assert ll_vms.addSnapshot(
            True, vm=self.vm_thin, description=LIVE_SNAPSHOT_DESC
        )

    @polarion("RHEVM3-11684")
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        testflow.step("Create a snapshot on a cloned vm")
        assert ll_vms.addSnapshot(
            True, vm=self.vm_clone, description=LIVE_SNAPSHOT_DESC
        )
