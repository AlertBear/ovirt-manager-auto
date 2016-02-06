"""
3.4 Single disk snapshot
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Single_Snapshot
"""
import logging
import shlex
import os
import re
from art.rhevm_api.tests_lib.low_level.disks import (
    deleteDisk, addDisk, wait_for_disks_status, get_disk_ids,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    waitForHostsStates, getSPMHost, getHostIP,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType, getDomainAddress,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, stop_vms_safely, preview_snapshot, start_vms,
    waitForVMState, startVm, commit_snapshot,
    get_vm_bootable_disk, undo_snapshot_preview, cloneVmFromSnapshot, addNic,
    removeNic, shutdownVm, removeSnapshot,
    wait_for_vm_snapshots, get_vm_state, safely_remove_vms,
    get_vms_disks_storage_domain_name,
)
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.rhevm_api.utils.test_utils import restartVdsmd, restart_engine
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.storage_single_disk_snapshot import config, helpers
from art.unittest_lib import StorageTest as BaseTestCase
from art.unittest_lib import attr
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from utilities.machine import Machine, LINUX

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

ACTIVE_VM = 'Active VM'
VM_NAMES = []
ISCSI = config.STORAGE_TYPE_ISCSI

vmArgs = {
    'positive': True,
    'vmDescription': config.VM_NAME % "description",
    'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK,
    'cluster': config.CLUSTER_NAME,
    'storageDomainName': None,
    'installation': True,
    'size': config.DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'useAgent': True,
    'os_type': config.OS_TYPE,
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
    'image': config.COBBLER_PROFILE,
}


def setup_module():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    for storage_type in config.STORAGE_SELECTOR:
        vm_name = config.VM_NAME % storage_type
        logger.info("Creating VM %s", vm_name)
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]
        vmArgs['storageDomainName'] = storage_domain
        vmArgs['vmName'] = vm_name

        logger.info('Creating vm and installing OS on it')

        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name)

        VM_NAMES.append(vm_name)

    logger.info('Shutting down vms %s', VM_NAMES)
    stop_vms_safely(VM_NAMES)


def teardown_module():
    """
    Clean datacenter
    """
    if config.GOLDEN_ENV:
        safely_remove_vms(VM_NAMES)
    else:
        logger.info('Cleaning datacenter')
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    polarion_test_case = None
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
        self.vm_name = config.VM_NAME % self.storage
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        start_vms([self.vm_name], 1, wait_for_ip=True)
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.vm = Machine(
            vm_ip, config.VM_USER, config.VM_PASSWORD).util(LINUX)
        self.boot_disk = get_vm_bootable_disk(self.vm_name)
        self.mounted_paths = []
        spm = getSPMHost(config.HOSTS)
        host_ip = getHostIP(spm)
        self.host = Machine(host_ip, config.HOSTS_USER,
                            config.HOSTS_PW).util(LINUX)

        self.disks_names = ['disk_%s_%s' % (d, self.polarion_test_case)
                            for d in range(self.disk_count)]
        logger.info("DISKS: %s", self.disks_names)
        for disk_name in self.disks_names:
            addDisk(
                True, alias=disk_name, size=config.GB,
                storagedomain=self.storage_domain, format=config.COW_DISK,
                interface=config.INTERFACE_VIRTIO, sparse=True,
            )
        wait_for_disks_status(self.disks_names)
        storage_helpers.prepare_disks_for_vm(self.vm_name, self.disks_names)
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

    def check_file_existence_operation(self, should_exist=True,
                                       operation='snapshot'):

        start_vms([self.vm_name], 1, wait_for_ip=True)
        lst = []
        state = not should_exist
        self._get_non_bootable_devices()
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
        start_vms(
            [self.vm_name], 1, wait_for_status=config.VM_UP, wait_for_ip=True
        )
        waitForVMState(self.vm_name)
        for dev in self.devices:
            mount_path = self.mount_path % dev
            cmd = self.cm_del % mount_path
            status, output = self.vm.runCmd(shlex.split(cmd))
            logger.info("File %s", 'deleted' if status else 'not deleted')
            if not status:
                raise exceptions.VMException(
                    "Failed to delete file(s) from vm %s, Output: %s"
                    % (self.vm_name, output)
                )

        shutdownVm(True, self.vm_name)
        waitForVMState(self.vm_name, config.VM_DOWN)

    def _perform_snapshot_operation(self, disks=None, wait=True, live=False):
        if not live:
            if not get_vm_state(self.vm_name) == config.VM_DOWN:
                shutdownVm(True, self.vm_name)
                waitForVMState(self.vm_name, config.VM_DOWN)
        if disks:
            is_disks = 'disks: %s' % disks
        else:
            is_disks = 'all disks'
        logger.info("Adding new snapshot to vm %s with %s", self.vm_name,
                    is_disks)
        status = addSnapshot(True, self.vm_name, self.snapshot_desc,
                             disks_lst=disks, wait=wait)
        self.assertTrue(status, "Failed to create snapshot %s" %
                                self.snapshot_desc)
        if wait:
            wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], [self.snapshot_desc],
            )

    def _get_non_bootable_devices(self):
        vm_devices = self.vm.get_storage_devices()
        if not vm_devices:
            logger.error("No devices found in vm %s", self.vm_name)
            raise exceptions.VMException(
                "No devices found in vm %s" % self.vm_name
            )
        logger.info("Devices found: %s", vm_devices)
        boot_disk_output = self.vm.get_boot_storage_device()
        boot_disk = re.search(
            storage_helpers.REGEX_DEVICE_NAME, boot_disk_output
        ).group()
        boot_device = boot_disk.split('/')[-1]
        logger.info("Boot disk device is: %s", boot_device)
        self.devices = [d for d in vm_devices if d != boot_device]
        self.devices.sort()
        logger.info("Devices (excluding boot disk): %s", self.devices)

    def _prepare_fs_on_devs(self):
        start_vms([self.vm_name], 1, wait_for_ip=True)

        self._get_non_bootable_devices()

        for dev in self.devices:
            dev_path = os.path.join('/dev', dev)
            rc, out = self.vm.runCmd(
                (storage_helpers.CREATE_DISK_LABEL % dev_path).split()
            )
            logger.info(out)
            assert rc
            rc, out = self.vm.runCmd(
                (storage_helpers.CREATE_DISK_PARTITION % dev_path).split()
            )
            logger.info(out)
            assert rc
            # Create the partition as number 1
            dev_number = '1'
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

    def _perform_snapshot_with_verification(self, disks_for_snap, live=False):
        disk_ids = get_disk_ids(disks_for_snap)
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("Before snapshot: %s volumes", initial_vol_count)

        self._perform_snapshot_operation(disks_for_snap, live=live)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("After snapshot: %s volumes", current_vol_count)

        self.assertEqual(current_vol_count,
                         initial_vol_count + len(disk_ids))

    def _prepare_environment(self):
        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.vm = Machine(vm_ip, config.VM_USER,
                          config.VM_PASSWORD).util(LINUX)

        self.vm.runCmd(shlex.split(self.cmd_create))
        shutdownVm(True, self.vm_name)
        waitForVMState(self.vm_name, config.VM_DOWN)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        for disk in self.disks_names:
            assert deleteDisk(True, disk)
        helpers.remove_all_vm_snapshots(self.vm_name,
                                        self.snapshot_desc)


@attr(tier=1)
class TestCase6022(BasicEnvironment):
    """
    Create snapshot of first disk out of 4 and verify that the
    snapshot was created successfully
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6022'

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6022, self).setUp()

    @polarion("RHEVM3-6022")
    def test_create_snapshot_of_first_disk(self):
        """
        - Create VM with 4 disks
        - Create snapshot to the VM and pick only one disk from the list of
        disks
        """
        self._perform_snapshot_with_verification(self.disks_names[0:2])


@attr(tier=2)
class TestCase6023(BasicEnvironment):
    """
    Preview snapshot of first disk out of 4 and verify
    that the snapshot being presented is the correct one
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6023'
    file_name = '/root/test_file'
    cmd_create = 'echo "test_txt" > %s' % file_name
    cm_del = 'rm -f %s' % file_name
    previewed = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        """
        Prepares the environment
        """
        super(TestCase6023, self).setUp()
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        self._prepare_environment()

    @polarion("RHEVM3-6023")
    def test_preview_snapshot(self):
        """
        - Write file on the first disk
        - Create snapshot to all disks
        - Delete the file from the disk
        - Preview the snapshot of the first disk
        """
        self._perform_snapshot_operation()
        start_vms([self.vm_name], 1, wait_for_ip=True)
        status, output = self.vm.runCmd(shlex.split(self.cm_del))
        self.assertTrue(status, "Files were not deleted {0}".format(output))

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        logger.info("Custom preview with disks %s", disks_to_preview)

        self.previewed = preview_snapshot(True, self.vm_name,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)

        assert self.previewed
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], [self.snapshot_desc],
        )
        start_vms([self.vm_name], 1, wait_for_ip=True)

        logger.info("Check that the file exist after previewing the snapshot")
        assert self.vm.isFileExists(self.file_name)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, self.vm_name)
            wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK],
                [self.snapshot_desc],
            )
        wait_for_jobs([ENUMS['job_preview_snapshot']])
        super(TestCase6023, self).tearDown()


@attr(tier=2)
class TestCase6024(BasicEnvironment):
    """
    Preview snapshot of 2 disks out of 4 and verify that the
    snapshot being presented is the correct one
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6024'
    previewed = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6024, self).setUp()
        assert self._prepare_fs_on_devs()

    @polarion("RHEVM3-6024")
    def test_create_snapshot_of_first_disk(self):
        """
        - Write some files on first and fourth disks
        - Create snapshot from the first and fourth disks
        - Delete the files that you have written from the first
          and fourth disks
        - Preview the first and fourth snapshots
        """
        disks_for_snap = [self.disks_names[0],
                          self.disks_names[3]]
        logger.info("Snapshot with disks: %s", disks_for_snap)
        self._perform_snapshot_operation(
            disks=disks_for_snap)
        start_vms([self.vm_name], 1, wait_for_ip=True)

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], self.snapshot_desc)]

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        self.previewed = preview_snapshot(True, self.vm_name,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)

        assert self.previewed
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], [self.snapshot_desc],
        )

        assert startVm(True, self.vm_name, wait_for_ip=True)
        lst = []
        self._get_non_bootable_devices()
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

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, self.vm_name)

        super(TestCase6024, self).tearDown()


@attr(tier=2)
class TestCase6026(BasicEnvironment):
    """
    Create snapshot of all vm's disks, preview it and undo the snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6026'
    previewed = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6026, self).setUp()
        assert self._prepare_fs_on_devs()

    @polarion("RHEVM3-6026")
    def test_flow_create_preview_and_undo_snapshot_of_all_disks(self):
        """
        - Create VM with 4 disks
        - Write file A to all disks
        - Create snapshot from the whole VM (all disks)
        - Delete files from all disks
        - Preview snapshot
        - Start VM
        - Stop VM
        - Undo previewed snapshot
        - Start VM
        """
        logger.info("Creating snapshot")
        self._perform_snapshot_operation()
        wait_for_jobs([ENUMS['job_create_snapshot']])

        self.delete_operation()

        logger.info("Previewing the snapshot %s", self.snapshot_desc)
        self.previewed = preview_snapshot(True, self.vm_name,
                                          self.snapshot_desc,
                                          ensure_vm_down=True)
        assert self.previewed

        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_desc],
        )

        self.check_file_existence_operation(True, 'snapshot')

        if self.previewed:
            logger.info("Undo the snapshot %s", self.snapshot_desc)
            assert undo_snapshot_preview(True, self.vm_name,
                                         ensure_vm_down=True)
            self.previewed = False
            wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK],
                [self.snapshot_desc],
            )

        self.check_file_existence_operation(False, 'undo')

    def tearDown(self):
        if self.previewed:
            logger.info("Undo the snapshot %s", self.snapshot_desc)
            assert undo_snapshot_preview(True, self.vm_name,
                                         ensure_vm_down=True)

            wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK],
                [self.snapshot_desc],
            )
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        super(TestCase6026, self).tearDown()


@attr(tier=2)
class TestCase6027(BasicEnvironment):
    """
    Create snapshot of first disk out of 4, preview it and undo the snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6027'
    file_name = '/root/test_file'
    cmd_create = 'echo "test_txt" > %s' % file_name
    cm_del = 'rm -f %s' % file_name
    previewed = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        """
        Prepares the environment
        """
        super(TestCase6027, self).setUp()
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        self._prepare_environment()

    @polarion("RHEVM3-6027")
    def test_preview_snapshot(self):
        """
        - Create VM with 4 disks
        - Write file to first disk
        - Create snapshot from first disk
        - delete the file
        - Preview snapshot
        - Start VM, check that the file exists under the first VM disk
        - Stop VM
        - Undo previewed snapshot
        - Start VM
        """
        disks_for_snap = [self.boot_disk]
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(disks_for_snap)
        wait_for_jobs([ENUMS['job_create_snapshot']])
        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)
        self.vm.runCmd(shlex.split(self.cm_del))

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        self.previewed = preview_snapshot(True, self.vm_name,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)
        assert self.previewed
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_desc],
        )

        start_vms([self.vm_name], 1, wait_for_ip=True)

        assert self.vm.isFileExists(self.file_name)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, self.vm_name)

        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_desc
        )
        super(TestCase6027, self).tearDown()


@attr(tier=2)
class TestCase6013(BasicEnvironment):
    """
    Check that the new cloned VM was created only with 1 disk and the
    configuration file of the original VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    # TODO: This case is False until RFE/bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1115440 is solved
    __test__ = False
    polarion_test_case = '6013'
    new_vm_name = 'new_vm_%s' % polarion_test_case

    def setUp(self):
        self.disk_count = 2
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6013, self).setUp()
        assert self._prepare_fs_on_devs()

    @polarion("RHEVM3-6013")
    def test_clone_vm_from_snapshot(self):
        """
        - Create a VM with 3 disks attached
        - Create a snapshot to the VM, pick only one disk and configuration
        file
        - Clone VM from the snapshot
        """
        self._perform_snapshot_operation(disks=[self.boot_disk])
        wait_for_jobs([ENUMS['job_create_snapshot']])

        self._get_non_bootable_devices()
        for dev in self.devices:
            mount_path = self.mount_path % dev
            cmd = self.cm_del % mount_path
            status, _ = self.vm.runCmd(shlex.split(cmd))
            logger.info("File %s", 'deleted' if status else 'not deleted')

        cloneVmFromSnapshot(True, self.new_vm_name, config.CLUSTER_NAME,
                            self.vm_name, self.snapshot_desc, )
        wait_for_jobs([ENUMS['job_add_vm_from_snapshot']])

        start_vms([self.vm_name], 1, wait_for_ip=False)
        waitForVMState(self.vm_name)

    def tearDown(self):
        for path in self.mounted_paths:
            self.vm.runCmd(shlex.split(self.umount_cmd % path))

        super(TestCase6013, self).tearDown()


@attr(tier=2)
class TestCase6030(BasicEnvironment):
    """
    Custom preview of vm configuration and 2 disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6030'
    disks_for_custom_preview = 2
    previewed = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6030, self).setUp()
        assert self._prepare_fs_on_devs()

    @polarion("RHEVM3-6030")
    def test_custom_preview_with_configuration_and_two_disks(self):
        """
        - Create a Vm with 4 disks (file system on all of them)
        - Create files on all the VM's disks
        - Create snapshot to all of the VM's disks
        - Delete all new files created on step 2
        - Go to custom preview
        - Choose VM's configuration and snapshot only from 2 of the disks
        - Preview snapshots
        - Start VM
        """
        self._perform_snapshot_operation()

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], self.snapshot_desc),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        self.previewed = preview_snapshot(True, self.vm_name,
                                          self.snapshot_desc,
                                          ensure_vm_down=True,
                                          disks_lst=disks_to_preview)
        assert self.previewed

        wait_for_jobs([ENUMS['job_preview_snapshot']])

        start_vms([self.vm_name], 1, wait_for_ip=True)

        lst = []
        self._get_non_bootable_devices()
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s", 'exist' if result else 'not exist')
            lst.append(result)

        results = [d for d in lst if d is True]
        self.assertEqual(len(results), self.disks_for_custom_preview)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.previewed:
            assert undo_snapshot_preview(True, self.vm_name)
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_desc
        )
        super(TestCase6030, self).tearDown()


@attr(tier=4)
class TestCase6014(BasicEnvironment):
    """
    Restart vdsm during snapshot creation, check that snapshot creation
    fails nicely, rollback should be done and the leftover volumes should be
    deleted
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot

    """
    # TODO: fix after https://bugzilla.redhat.com/show_bug.cgi?id=1119203
    __test__ = False
    polarion_test_case = '6014'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6014, self).setUp()

    @polarion("RHEVM3-6014")
    def test_restart_VDSM_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart vdsm during snapshot creation
        """
        self._perform_snapshot_operation(wait=False)
        self.host = getSPMHost(config.HOSTS)
        self.host_ip = getHostIP(self.host)
        assert restartVdsmd(self.host_ip, config.HOSTS_PW)
        waitForHostsStates(True, self.host)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        super(TestCase6014, self).tearDown()


@attr(tier=4)
class TestCase6006(BasicEnvironment):
    """
    Restart ovirt-engine service during snapshot creation, check that
    snapshot creation fails nicely, rollback should be done and the leftover
    volumes should be deleted
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    # TODO: fix after https://bugzilla.redhat.com/show_bug.cgi?id=1119203
    __test__ = False
    polarion_test_case = '6006'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6006, self).setUp()

    @polarion("RHEVM3-6006")
    def test_restart_engine_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart ovirt-engine service during snapshot creation
        """
        self._perform_snapshot_operation(wait=False)
        logger.info("Restarting ovirt-engine...")
        restart_engine(config.ENGINE, 5, 30)
        waitForHostsStates(True, config.HOSTS[0])

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        super(TestCase6006, self).tearDown()


@attr(tier=2)
class TestCase6032(BasicEnvironment):
    """
    Create snapshot only from VM configuration.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6032'
    nic = 'nic_%s' % polarion_test_case
    commit = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        """
        Prepares the environment
        """
        super(TestCase6032, self).setUp()
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        profile = vmArgs['network']
        if not addNic(True, vm=self.vm_name, name=self.nic,
                      mac_address=None,
                      network=vmArgs['network'],
                      vnic_profile=profile, plugged='true', linked='true'):
            raise exceptions.NetworkException("Can't add nic %s" % self.nic)

        assert self._prepare_fs_on_devs()

    @polarion("RHEVM3-6032")
    def test_create_snapshot_from_vm_configuration(self):
        """
        - Create VM with a disk and 2 NICs
        - Create files on the disk
        - Create snapshot only from VM configuration
        - Delete one of the VM's NICs
        - Restore the snapshot (which includes only the OVF - conf file)
        """
        self._perform_snapshot_operation(disks=[])

        self.delete_operation()
        disks_to_preview = []

        assert preview_snapshot(True, self.vm_name, self.snapshot_desc,
                                ensure_vm_down=True,
                                disks_lst=disks_to_preview)
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )

        assert commit_snapshot(True, self.vm_name)
        self.commit = True

        assert removeNic(True, self.vm_name, self.nic)
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_desc
        )

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

        if not self.commit:
            assert undo_snapshot_preview(True, self.vm_name)
            wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], self.snapshot_desc
            )
        super(TestCase6032, self).tearDown()


@attr(tier=2)
class TestCase6033(BasicEnvironment):
    """
    Create 3 snapshot and delete the second
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6033'
    snap_1 = 'snapshot_1'
    snap_2 = 'snapshot_2'
    snap_3 = 'snapshot_3'

    def setUp(self):
        """
        Prepares the environment
        """
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        self.snaps = [self.snap_1, self.snap_2, self.snap_3]
        super(TestCase6033, self).setUp()
        assert self._prepare_fs_on_devs()
        self.cmd_create = 'echo "test_txt" > %s/test_file_%s'

    @polarion("RHEVM3-6033")
    def test_delete_second_snapshot_out_of_three(self):
        """
        - Create VM with 4 disks
        - Write file A on disk #2
        - Create snapshot from disk #2
        - Write more files on disk #2 (file B) and create second snapshot
        - Write more files on disk #2 (file C) and create third snapshot
        - Now you have 3 snapshots from disk #2. Delete snapshot #2
        """
        for index, snap_desc in enumerate(self.snaps):
            start_vms([self.vm_name], 1, wait_for_ip=True)
            self._get_non_bootable_devices()
            for dev in self.devices:
                logger.info("writing file to disk %s", dev)
                self.vm.runCmd(shlex.split(self.cmd_create
                                           % ((self.mount_path % dev), index)))

            shutdownVm(True, self.vm_name)
            waitForVMState(self.vm_name, config.VM_DOWN)

            addSnapshot(True, self.vm_name, snap_desc,
                        disks_lst=[self.disks_names[0]], wait=True)

        wait_for_jobs([ENUMS['job_create_snapshot']])
        start_vms([self.vm_name], 1, wait_for_ip=True)

        disk_ids = get_disk_ids(self.disks_names)
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("The number of volumes is: %s", initial_vol_count)

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        removeSnapshot(True, self.vm_name, self.snap_1,
                       helpers.SNAPSHOT_TIMEOUT)
        wait_for_jobs([ENUMS['job_remove_snapshot']])

        start_vms([self.vm_name], 1, wait_for_ip=True)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("The number of volumes after removing one snapshot is: "
                    "%s", current_vol_count)

        self.assertEqual(current_vol_count, initial_vol_count - 1)

        self.check_file_existence_operation(True, 'snapshot')


@attr(tier=4)
class TestCase6015(BasicEnvironment):
    """
    Block connectivity to storage server during snapshot creation, Check that
    snapshot creation fails nicely, rollback should be done and the leftover
    volumes should be deleted
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6015'

    def setUp(self):
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        super(TestCase6015, self).setUp()
        self.host = getSPMHost(config.HOSTS)
        self.host_ip = getHostIP(self.host)
        self.sd = get_vms_disks_storage_domain_name(self.vm_name)
        found, address = getDomainAddress(True, self.sd)
        self.assertTrue(found, "IP for storage domain %s not found" % self.sd)
        self.sd_ip = address['address']

    @polarion("RHEVM3-6015")
    def test_block_connectivity_to_storage(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Block connectivity to storage server during snapshot creation
        """

        self._perform_snapshot_operation(self.disks_names[0:2], wait=False)
        blockOutgoingConnection(self.host_ip, config.HOSTS_USER,
                                config.HOSTS_PW, self.sd_ip)
        wait_for_jobs([ENUMS['job_create_snapshot']])
        # TODO: cmestreg: doesn't this test needs to check the rollback and
        #                 that the volumes are gone?

    def tearDown(self):
        try:
            unblockOutgoingConnection(self.host_ip, config.HOSTS_USER,
                                      config.HOSTS_PW, self.sd_ip)
        except AttributeError, err:
            logger.error(
                "AttributeError calling unblockOutgoingConnection: %s", err)
        super(TestCase6015, self).tearDown()
