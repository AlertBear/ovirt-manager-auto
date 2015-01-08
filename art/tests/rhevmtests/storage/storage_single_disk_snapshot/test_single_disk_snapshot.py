"""
3.4 Single disk snapshot
https://tcms.engineering.redhat.com/plan/12057
"""

import logging
import shlex
import os
from utilities.utils import getIpAddressByHostName
from art.rhevm_api.tests_lib.low_level.disks import deleteDisk
from art.rhevm_api.tests_lib.low_level.hosts import (
    waitForHostsStates,
    getSPMHost,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    findMasterStorageDomain,
    cleanDataCenter,
)
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection,
    unblockOutgoingConnection,
)

from art.rhevm_api.utils.test_utils import restartVdsmd, restartOvirtEngine
from rhevmtests.storage.helpers import get_vm_ip
from rhevmtests.storage.storage_single_disk_snapshot import helpers

from art.unittest_lib import StorageTest as BaseTestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, stop_vms_safely, preview_snapshot, createVm,
    start_vms, waitForVMState, suspendVm, startVm, commit_snapshot,
    get_vm_bootable_disk, undo_snapshot_preview, cloneVmFromSnapshot, addNic,
    removeNic, get_snapshot_disks, shutdownVm, removeSnapshot,
    wait_for_vm_snapshots, get_vm_state,
)

from art.unittest_lib import attr

from utilities.machine import Machine, LINUX

from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler import exceptions

from rhevmtests.storage.storage_single_disk_snapshot import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

TEST_PLAN_ID = '12057'
ACTIVE_VM = 'Active VM'

vmArgs = {
    'positive': True, 'vmName': config.VM_NAME,
    'vmDescription': config.VM_NAME, 'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK, 'cluster': config.CLUSTER_NAME,
    'storageDomainName': None, 'installation': True, 'size': config.DISK_SIZE,
    'nic': 'nic1', 'image': config.COBBLER_PROFILE, 'useAgent': True,
    'os_type': config.ENUMS['rhel6'], 'user': config.VM_USER,
    'password': config.VM_PASSWORD, 'network': config.MGMT_BRIDGE,
}


def setup_module():
    """
    Prepares environment
    """
    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TESTNAME)

    rc, masterSD = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
    if not rc:
        raise exceptions.StorageDomainException(
            "Could not find master storage domain for dc %s" %
            config.DATA_CENTER_NAME)

    vmArgs['storageDomainName'] = masterSD['masterDomain']

    logger.info('Creating vm and installing OS on it')

    if not createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    stop_vms_safely([config.VM_NAME])


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_test_case = None
    snapshot_desc = None
    disk_count = 4
    file_name = 'test_file'
    mount_path = '/new_fs_%s'
    cmd_create = 'echo "test_txt" > %s/test_file'
    cm_del = 'rm -f %s/test_file'
    umount_cmd = 'umount %s'

    def setUp(self):
        """
        Creating disks for case
        """
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        vm_ip = get_vm_ip(config.VM_NAME)
        self.vm = Machine(vm_ip, config.VM_USER,
                          config.VM_PASSWORD).util(LINUX)
        self.mounted_paths = []
        spm = getSPMHost(config.HOSTS)
        host_ip = getIpAddressByHostName(spm)
        self.host = Machine(host_ip, config.HOSTS_USER,
                            config.HOSTS_PW).util(LINUX)

        self.disks_names = ['disk_%s_%s' % (d, self.tcms_test_case) for d in
                            range(self.disk_count)]
        self.boot_disk = get_vm_bootable_disk(config.VM_NAME)
        logger.info("DISKS: %s", self.disks_names)
        helpers.prepare_disks_for_vm(config.VM_NAME, self.disks_names)
        wait_for_jobs()
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)

    def check_file_existence_operation(self, should_exist=True,
                                       operation='snapshot'):

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        lst = []
        state = not should_exist
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s", 'exist' if result else 'not exist')
            lst.append(result)

        if state in lst:
            raise exceptions.SnapshotException("%s operation failed"
                                               % operation)

    def delete_operation(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        for dev in self.devices:
            mount_path = self.mount_path % dev
            cmd = self.cm_del % mount_path
            status, _ = self.vm.runCmd(shlex.split(cmd))
            logger.info("File %s", 'deleted' if status else 'not deleted')

        logger.info("Shutting down vm %s", config.VM_NAME)

        shutdownVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME, config.VM_DOWN)

    def _perform_snapshot_operation(self, disks=None, wait=True, live=False):
        if not live:
            if not get_vm_state(config.VM_NAME) == config.VM_DOWN:
                shutdownVm(True, config.VM_NAME)
                waitForVMState(config.VM_NAME, config.VM_DOWN)
        if disks:
            is_disks = 'disks: %s' % disks
        else:
            is_disks = 'all disks'
        logger.info("Adding new snapshot to vm %s with %s", config.VM_NAME,
                    is_disks)
        status = addSnapshot(True, config.VM_NAME, self.snapshot_desc,
                             disks_lst=disks, wait=wait)
        self.assertTrue(status, "Failed to create snapshot %s" %
                                self.snapshot_desc)
        if wait:
            wait_for_vm_snapshots(config.VM_NAME, ENUMS['snapshot_state_ok'])
            wait_for_jobs()

    def _prepare_fs_on_devs(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        vm_devices = self.vm.get_storage_devices()
        if not vm_devices:
            logger.info("No devices found")
            return False
        logger.info("Devices found: %s", vm_devices)
        self.devices = [d for d in vm_devices if d != 'vda']
        self.devices.sort()
        for dev in self.devices:
            dev_size = self.vm.get_storage_device_size(dev)
            dev_path = os.path.join('/dev', dev)
            logger.info("Creating partition for dev: %s", dev_path)
            dev_number = self.vm.createPartition(dev_path,
                                                 ((dev_size / 2) * config.GB))
            logger.info("Creating file system for dev: %s", dev + dev_number)
            self.vm.createFileSystem(dev_path, dev_number, 'ext4',
                                     (self.mount_path % dev))

            self.mounted_paths.append(self.mount_path % dev)
            logger.info("writing file to disk")

            mount_path = self.mount_path % dev
            cmd = self.cmd_create % mount_path
            status, _ = self.vm.runCmd(shlex.split(cmd))

            assert status
        self.check_file_existence_operation(True, 'Writing')
        return True

    def _perform_snapshot_with_verification(self, disks_for_snap,
                                            live=False):

        vol_before = self.host.get_amount_of_volumes()
        logger.info("Before snapshot: %s volumes", vol_before)

        self._perform_snapshot_operation(disks_for_snap, live=live)

        vol_after = self.host.get_amount_of_volumes()
        logger.info("After snapshot: %s volumes", vol_after)

        self.assertEqual(vol_after, vol_before + len(disks_for_snap))

    def _prepare_environment(self):
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        vm_ip = get_vm_ip(config.VM_NAME)
        self.vm = Machine(vm_ip, config.VM_USER,
                          config.VM_PASSWORD).util(LINUX)

        self.vm.runCmd(shlex.split(self.cmd_create))
        shutdownVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME, config.VM_DOWN)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        for disk in self.disks_names:
            assert deleteDisk(True, disk)
        helpers.remove_all_vm_test_snapshots(config.VM_NAME,
                                             self.snapshot_desc)


@attr(tier=1)
class TestCase333023(BasicEnvironment):
    """
    Create snapshot of first disk out of 4 and verify that the
    snapshot was created successfully
    https://tcms.engineering.redhat.com/case/333023/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333023'

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase333023, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_snapshot_of_first_disk(self):
        """
        - Create VM with 4 disk.
        - Create snapshot to the VM and pick only one disk
          from the list of disks.
        """
        self._perform_snapshot_with_verification(self.disks_names[0:2])


@attr(tier=1)
class TestCase333028(BasicEnvironment):
    """
    Preview snapshot of first disk out of 4 and verify
    that the snapshot being presented is the correct one
    https://tcms.engineering.redhat.com/case/333028/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333028'
    file_name = '/root/test_file'
    cmd_create = 'echo "test_txt" > %s' % file_name
    cm_del = 'rm -f %s' % file_name
    previewed = False

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        self._prepare_environment()
        super(TestCase333028, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preview_snapshot(self):
        """
        - Write file on the first disk.
        - Create snapshot to all disks.
        - Delete the file from the disk.
        - Preview the snapshot of the first disk.
        """
        self._perform_snapshot_operation()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        self.vm.runCmd(shlex.split(self.cm_del))

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        logger.info("Custom preview with disks %s", disks_to_preview)

        self.previewed = preview_snapshot(True, config.VM_NAME,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)

        assert self.previewed

        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        assert self.vm.isFileExists(self.file_name)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, config.VM_NAME)

        wait_for_jobs()
        super(TestCase333028, self).tearDown()


@attr(tier=2)
class TestCase289572(BasicEnvironment):
    """
    Create a snapshot to the VM while it's suspended and pick only one disk
    and configuration file
    https://tcms.engineering.redhat.com/case/289572/?from_plan=12057

    __test__ = False -> https://bugzilla.redhat.com/show_bug.cgi?id=1120232
    """
    __test__ = False
    tcms_test_case = '289572'

    def setUp(self):
        self.disk_count = 2
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase289572, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_suspended_vm(self):
        """
        - Create a VM with 2 disks  (with file system on both disks)
        - Write files to both disks
        - Suspend the VM
        - Create a snapshot to the VM while it's suspended and pick only one
          disk and conf.
        - Resume the VM
        - Delete the files created in step 2
        - Shutdown the VM
        - Preview the snapshot created in step 4 and commit it
        - Start the VM
        """
        logger.info("Suspending vm %s", config.VM_NAME)
        assert suspendVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME, config.VM_SUSPENDED)
        disks_for_snap = [self.boot_disk, self.disks_names[0]]
        logger.info("Snapshot with disks: %s", disks_for_snap)
        self._perform_snapshot_operation(disks=disks_for_snap, live=True)
        wait_for_jobs()

        logger.info("Starting vm %s", config.VM_NAME)
        assert startVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME)

        disk_count = len(get_snapshot_disks(config.VM_NAME,
                                            self.snapshot_desc))
        status = disk_count == self.disk_count
        self.assertTrue(status, "Snapshot wasn't created properly")

        self.delete_operation()
        boot_disk = get_vm_bootable_disk(config.VM_NAME)
        disks_to_preview = [(boot_disk, self.snapshot_desc),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], ACTIVE_VM)]

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        assert preview_snapshot(True, config.VM_NAME, self.snapshot_desc,
                                ensure_vm_down=True,
                                disks_lst=disks_to_preview)

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        full_path = os.path.join((self.mount_path % self.devices[0]),
                                 self.file_name)
        logger.info("Checking full path %s", full_path)

        assert self.vm.isFileExists(full_path)

        logger.info("Committing the snapshot %s", self.snapshot_desc)
        assert commit_snapshot(True, config.VM_NAME)

        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        assert self.vm.isFileExists(full_path)

        self.disks_names = [disks_for_snap[1]]

    def tearDown(self):
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        super(TestCase289572, self).tearDown()


@attr(tier=2)
class TestCase333031(BasicEnvironment):
    """
    Preview snapshot of 2 disks out of 4 and verify that the
    snapshot being presented is the correct one
    https://tcms.engineering.redhat.com/case/333031/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333031'
    previewed = False

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase333031, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_snapshot_of_first_disk(self):
        """
        - Write some files on first and fourth disks.
        - Create snapshot from the first and fourth disks.
        - Delete the files that you have written from the first
          and fourth disks
        - Preview first and fourth snapshots.
        """
        disks_for_snap = [self.disks_names[0],
                          self.disks_names[3]]
        logger.info("Snapshot with disks: %s", disks_for_snap)
        self._perform_snapshot_operation(
            disks=disks_for_snap)
        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], self.snapshot_desc)]

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        self.previewed = preview_snapshot(True, config.VM_NAME,
                                          ACTIVE_VM,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)

        assert self.previewed

        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        lst = []
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s ", 'exist' if result else 'does not exist')
            lst.append(result)

        results = [d for d in lst if d is True]
        self.assertEqual(len(results), len(disks_for_snap))

    def tearDown(self):
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, config.VM_NAME)

        super(TestCase333031, self).tearDown()


@attr(tier=2)
class TestCase333049(BasicEnvironment):
    """
    Create snapshot of all vm's disks, preview it and undo the snapshot.
    https://tcms.engineering.redhat.com/case/333049/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333049'
    previewed = False

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase333049, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_flow_create_preview_and_undo_snapshot_of_all_disks(self):
        """
        - Create VM with 4 disks.
        - Write file A to all disks.
        - Create snapshot from the whole VM (all disks)
        - Delete files from all disks
        - Preview snapshot.
        - Start VM.
        - Stop Vm.
        - Undo previewed snapshot.
        - Start VM.
        """
        logger.info("Creating snapshot")
        self._perform_snapshot_operation()
        wait_for_jobs()

        self.delete_operation()

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        self.previewed = preview_snapshot(True, config.VM_NAME,
                                          self.snapshot_desc,
                                          ensure_vm_down=True)
        assert self.previewed

        wait_for_jobs()

        self.check_file_existence_operation(True, 'snapshot')

        if self.previewed:
            logger.info("Undo the snapshot %s", self.snapshot_desc)
            assert undo_snapshot_preview(True, config.VM_NAME,
                                         ensure_vm_down=True)
            self.previewed = False

        wait_for_jobs()

        self.check_file_existence_operation(False, 'undo')

    def tearDown(self):
        if self.previewed:
            logger.info("Undo the snapshot %s", self.snapshot_desc)
            assert undo_snapshot_preview(True, config.VM_NAME,
                                         ensure_vm_down=True)

        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        super(TestCase333049, self).tearDown()


@attr(tier=2)
class TestCase333050(BasicEnvironment):
    """
    Create snapshot of first disk out of 4, preview it and undo the snapshot.
    https://tcms.engineering.redhat.com/case/333050/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333050'
    file_name = '/root/test_file'
    cmd_create = 'echo "test_txt" > %s' % file_name
    cm_del = 'rm -f %s' % file_name
    previewed = False

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        self._prepare_environment()
        super(TestCase333050, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preview_snapshot(self):
        """
        - Create VM with 4 disks.
        - Write file to first disk.
        - Create snapshot from first disk
        - delete the file
        - Preview snapshot.
        - Start VM, check that the file exists under the first VM disk
        - Stop Vm.
        - Undo previewed snapshot.
        - Start VM.
        """
        disks_for_snap = [self.boot_disk]
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(disks_for_snap)
        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        self.vm.runCmd(shlex.split(self.cm_del))

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        self.previewed = preview_snapshot(True, config.VM_NAME,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)
        assert self.previewed

        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        assert self.vm.isFileExists(self.file_name)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, config.VM_NAME)

        wait_for_jobs()
        super(TestCase333050, self).tearDown()


@attr(tier=2)
class TestCase333058(BasicEnvironment):
    """
    Custom preview of vm configuration and all disks
    https://tcms.engineering.redhat.com/case/333058/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333058'
    commit = False

    def setUp(self):
        self.disk_count = 2
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase333058, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_custom_preview_with_configuration_and_all_disks(self):
        """
        - Create a VM with 2 disks (with file system on both)
        - Create files on both disks
        - Create snapshot to all VM's disks and conf.
        - Delete the files created as part of step 2
        - Preview snapshot of all VM's disks and conf.
        - Commit snapshot
        """
        self._perform_snapshot_operation()
        wait_for_jobs()

        self.delete_operation()

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        assert preview_snapshot(True, config.VM_NAME, self.snapshot_desc,
                                ensure_vm_down=True)
        wait_for_jobs()

        self.check_file_existence_operation(True, 'snapshot')

        logger.info("Committing the snapshot %s", self.snapshot_desc)
        assert commit_snapshot(True, config.VM_NAME, ensure_vm_down=True)

        self.commit = True

        wait_for_jobs()

        self.check_file_existence_operation(True, 'commit')

    def tearDown(self):
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        if not self.commit:
            assert undo_snapshot_preview(True, config.VM_NAME,
                                         ensure_vm_down=True)

        super(TestCase333058, self).tearDown()


@attr(tier=2)
class TestCase342783(BasicEnvironment):
    """
    Check that the new cloned VM was created only with 1 disk and the
    configuration file of the original VM
    https://tcms.engineering.redhat.com/case/342783/?from_plan=12057
    This case is False until
    RFE: https://bugzilla.redhat.com/show_bug.cgi?id=1115440 is solved
    """
    __test__ = False
    tcms_test_case = '342783'
    new_vm_name = 'new_vm_%s' % tcms_test_case

    def setUp(self):
        self.disk_count = 2
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase342783, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_clone_vm_from_snapshot(self):
        """
        - Create a VM with 3 disks attached
        - Create a snapshot to the VM, pick only one disk and
          configuration file.
        - Clone VM from the snapshot.
        """
        self._perform_snapshot_operation(disks=[self.boot_disk])
        wait_for_jobs()

        for dev in self.devices:
            mount_path = self.mount_path % dev
            cmd = self.cm_del % mount_path
            status, _ = self.vm.runCmd(shlex.split(cmd))
            logger.info("File %s", 'deleted' if status else 'not deleted')

        cloneVmFromSnapshot(True, self.new_vm_name, config.CLUSTER_NAME,
                            config.VM_NAME, self.snapshot_desc, )
        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

    def tearDown(self):
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        super(TestCase342783, self).tearDown()


@attr(tier=3)
class TestCase333055(BasicEnvironment):
    """
    Custom preview of vm configuration and 2 disks
    https://tcms.engineering.redhat.com/case/333055/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '333055'
    disks_for_custom_preview = 2
    previewed = False

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase333055, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_custom_preview_with_configuration_and_two_disks(self):
        """
        - Create a Vm with 4 disks  (file system on all of them).
        - Create files on all the VM's disks
        - Create snapshot to all of the VM's disks.
        - Delete all new files created on step 2
        - Go to custom preview
        - Choose VM's configuration and snapshot only from 2 of the disks
        - Preview snapshots.
        - Start VM.
        """
        self._perform_snapshot_operation()

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], self.snapshot_desc),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        self.previewed = preview_snapshot(True, config.VM_NAME,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)
        assert self.previewed

        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        lst = []
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s", 'exist' if result else 'not exist')
            lst.append(result)

        results = [d for d in lst if d is True]
        self.assertEqual(len(results), self.disks_for_custom_preview)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, config.VM_NAME)
        wait_for_jobs()
        super(TestCase333055, self).tearDown()


@attr(tier=3)
class TestCase343074(BasicEnvironment):
    """
    Restart vdsm during snapshot creation, check that snapshot creation
    fails nicely, rollback should be done and the leftover volumes should be
    deleted
    https://tcms.engineering.redhat.com/case/343074/?from_plan=12057

    __test__ = False :
       https://bugzilla.redhat.com/show_bug.cgi?id=1119203
    """
    __test__ = False
    tcms_test_case = '343074'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase343074, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_VDSM_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart vdsm during snapshot creation
        """
        self._perform_snapshot_operation(wait=False)
        assert restartVdsmd(config.HOSTS[0], config.HOSTS_PW)
        waitForHostsStates(True, config.HOSTS[0])

        wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        wait_for_jobs()
        super(TestCase343074, self).tearDown()


@attr(tier=3)
class TestCase343077(BasicEnvironment):
    """
    Restart ovirt-engine service during snapshot creation, check that
    snapshot creation fails nicely, rollback should be done and the leftover
    volumes should be deleted
    https://tcms.engineering.redhat.com/case/343077/?from_plan=12057

    __test__ = False :
       https://bugzilla.redhat.com/show_bug.cgi?id=1119203
    """
    __test__ = False
    tcms_test_case = '343077'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase343077, self).setUp()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_engine_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart ovirt-engine service during snapshot creation
        """
        engine = config.VDC
        engine_object = Machine(
            host=engine,
            user=config.VDC,
            password=config.VDC_ROOT_PASSWORD).util(LINUX)

        self._perform_snapshot_operation(wait=False)
        logger.info("Restarting ovirt-engine...")
        self.assertTrue(restartOvirtEngine(engine_object, 5, 30, 30),
                        "Failed restarting ovirt-engine")
        waitForHostsStates(True, config.HOSTS[0])

        wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        wait_for_jobs()
        super(TestCase343077, self).tearDown()


@attr(tier=2)
class TestCase336096(BasicEnvironment):
    """
    Create snapshot only from VM configuration.
    https://tcms.engineering.redhat.com/case/336096/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '336096'
    nic = 'nic_%s' % tcms_test_case
    commit = False

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        profile = vmArgs['network']
        if not addNic(True, vm=config.VM_NAME, name=self.nic,
                      mac_address=None,
                      network=vmArgs['network'],
                      vnic_profile=profile, plugged='true', linked='true'):
            raise exceptions.NetworkException("Can't add nic %s" % self.nic)

        super(TestCase336096, self).setUp()
        assert self._prepare_fs_on_devs()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_snapshot_from_vm_configuration(self):
        """
        - Create VM with a disk and 2 NICs.
        - Create files on the disk
        - Create snapshot only from VM configuration.
        - Delete one of the VM's NICs
        - Restore the snapshot (which includes only the OVF - conf file)
        """
        self._perform_snapshot_operation(disks=[])

        self.delete_operation()

        disks_to_preview = []

        assert preview_snapshot(True, config.VM_NAME, self.snapshot_desc,
                                ensure_vm_down=True,
                                disks_lst=disks_to_preview)

        assert commit_snapshot(True, config.VM_NAME)
        wait_for_jobs()
        self.commit = True

        assert removeNic(True, config.VM_NAME, self.nic)
        wait_for_jobs()

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)

        if not self.commit:
            assert undo_snapshot_preview(True, config.VM_NAME)
            wait_for_jobs()
        super(TestCase336096, self).tearDown()


@attr(tier=3)
class TestCase336105(BasicEnvironment):
    """
    Create 3 snapshot and delete the second.
    https://tcms.engineering.redhat.com/case/336105/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '336105'
    snap_1 = 'snapshot_1'
    snap_2 = 'snapshot_2'
    snap_3 = 'snapshot_3'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        self.snaps = [self.snap_1, self.snap_2, self.snap_3]
        super(TestCase336105, self).setUp()
        assert self._prepare_fs_on_devs()
        self.cmd_create = 'echo "test_txt" > %s/test_file_%s'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_delete_second_snapshot_out_of_three(self):
        """
        - Create VM with 4 disks.
        - Write file A on disk #2.
        - Create snapshot from disk #2.
        - Write more files on disk #2 (file B) and create second snapshot.
        - Write more files on disk #2 (file C) and create third snapshot.
        - Now you have 3 snapshots from disk #2. Delete snapshot #2.
        """
        for index, snap_desc in enumerate(self.snaps):
            start_vms([config.VM_NAME], 1, wait_for_ip=False)
            waitForVMState(config.VM_NAME)
            for dev in self.devices:

                logger.info("writing file to disk %s", dev)
                self.vm.runCmd(shlex.split(self.cmd_create
                                           % ((self.mount_path % dev), index)))

            shutdownVm(True, config.VM_NAME)
            waitForVMState(config.VM_NAME, config.VM_DOWN)

            addSnapshot(True, config.VM_NAME, snap_desc,
                        disks_lst=[self.disks_names[0]], wait=True)

        wait_for_jobs()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        vol_count = self.host.get_amount_of_volumes()

        stop_vms_safely([config.VM_NAME])
        waitForVMState(config.VM_NAME, config.VM_DOWN)
        removeSnapshot(True, config.VM_NAME, self.snap_1,
                       helpers.SNAPSHOT_TIMEOUT)
        wait_for_jobs()

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        self.assertEqual(self.host.get_amount_of_volumes(),
                         vol_count - 1)

        self.check_file_existence_operation(True, 'snapshot')


@attr(tier=3)
class TestCase343076(BasicEnvironment):
    """
    Block connectivity to storage server during snapshot creation, Check that
    snapshot creation fails nicely, rollback should be done and the leftover
    volumes should be deleted
    https://tcms.engineering.redhat.com/case/343076/?from_plan=12057
    """
    __test__ = True
    tcms_test_case = '343076'

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        super(TestCase343076, self).setUp()
        _, self.master_domain = findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        self.master_domain = self.master_domain['masterDomain']

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_block_connectivity_to_storage(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Block connectivity to storage server during snapshot creation
        """

        self._perform_snapshot_operation(self.disks_names[0:2], wait=False)
        blockOutgoingConnection(config.FIRST_HOST, config.HOSTS_USER,
                                config.HOSTS_PW, self.master_domain)
        wait_for_jobs()

    def tearDown(self):
        unblockOutgoingConnection(config.FIRST_HOST, config.HOSTS_USER,
                                  config.HOSTS_PW, self.master_domain)
        super(TestCase343076, self).tearDown()
