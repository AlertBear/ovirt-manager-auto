"""
Storage live snapshot sanity tests - full test
https://tcms.engineering.redhat.com/plan/5588/
"""
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler import exceptions
import helpers
import shlex
import config
import logging
import os
from rhevmtests.storage import helpers as storage_helpers

from concurrent.futures import ThreadPoolExecutor

from art.unittest_lib import StorageTest as TestCase, attr
from art.test_handler.tools import tcms  # pylint: disable=E0611

from art.rhevm_api.tests_lib.high_level.vms import restore_snapshot

from art.rhevm_api.tests_lib.low_level import hosts, templates, vms
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType)

from art.rhevm_api.utils.test_utils import (
    get_api, raise_if_exception, wait_for_tasks,
)
from rhevmtests.storage.helpers import remove_all_vm_snapshots
from utilities.machine import Machine, LINUX


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
VM_API = get_api('vm', 'vms')


BASE_SNAP = "base_snap"  # Base snapshot description
SNAP_1 = 'spm_snapshot1'
ACTIVE_SNAP = 'Active VM'
VM_ON_SPM = 'vm_on_spm_%s'
VM_ON_HSM = 'vm_on_hsm-%s'
ACTIVE_VM = 'Active VM'

SPM = None
HSM = None

vm_args = {
    'positive': True,
    'vmName': "",
    'vmDescription': "",
    'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK,
    'cluster': config.CLUSTER_NAME,
    'installation': True,
    'size': config.DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'image': config.COBBLER_PROFILE,
    'useAgent': True,
    'os_type': config.ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD
}

VM_LIST = []


def setup_module():
    """
    Prepares VMs for testing, sets HSM and SPM hosts
    """
    global SPM
    global HSM
    assert hosts.waitForSPM(config.DATA_CENTER_NAME, timeout=100, sleep=10)
    SPM = hosts.returnSPMHost(config.HOSTS)[1]['spmHost']
    HSM = hosts.getAnyNonSPMHost(config.HOSTS, [config.HOST_UP],
                                 config.CLUSTER_NAME)[1]['hsmHost']
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]

        args = vm_args.copy()
        args['storageDomainName'] = storage_domain
        for host, vm_name in [(SPM, VM_ON_SPM), (HSM, VM_ON_HSM)]:
            args['vmName'] = vm_name % storage_type
            args['vmDescription'] = vm_name % storage_type
            helpers.prepare_vm(**args)

            VM_LIST.append(args['vmName'])


def teardown():
    """
    Removes vms
    """
    vms.stop_vms_safely(VM_LIST)
    vms.removeVms(True, VM_LIST)


class BasicEnvironmentSetUp(TestCase):
    """
    This class implements setup, teardowns and common functions
    """
    __test__ = False
    vm_on_hsm = VM_ON_HSM % TestCase.storage
    vm_on_spm = VM_ON_SPM % TestCase.storage
    tcms_plan_id = '5588'
    vm_name = ''
    file_name = 'test_file'
    mount_path = '/root'
    cmd_create = 'echo "test_txt" > test_file'
    cm_del = 'rm -f test_file'

    def setUp(self):
        """
        Prepare environment
        """
        self.disk_name = 'test_disk_%s' % self.tcms_test_case
        self.snapshot_desc = 'snapshot_%s' % self.tcms_test_case
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        if not vms.waitForVMState(self.vm_name):
            raise exceptions.VMException(
                "Timeout when waiting for vm %s and state up" % self.vm_name)
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.vm = Machine(vm_ip, config.VM_USER,
                          config.VM_PASSWORD).util(LINUX)
        self.mounted_paths = []
        self.boot_disk = vms.get_vm_bootable_disk(self.vm_name)
        logger.info("The boot disk is: %s", self.boot_disk)

    def tearDown(self):
        remove_all_vm_snapshots(self.vm_name, self.snapshot_desc)
        if not vms.start_vms([self.vm_name]):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name)
        if not vms.waitForVMState(self.vm_name):
            raise exceptions.VMException(
                "Timeout when waiting for vm %s to start" % self.vm_name)
        if self.check_file_existence_operation(self.vm_name, True):
            status, _ = self.vm.runCmd(shlex.split(self.cm_del))
            if not status:
                raise exceptions.DiskException(
                    "File deletion from disk failed"
                )

    def _perform_snapshot_operation(
            self, vm_name, disks=None, wait=True, live=False):
        if not live:
            if not vms.get_vm_state(vm_name) == config.VM_DOWN:
                vms.shutdownVm(True, vm_name)
                vms.waitForVMState(vm_name, config.VM_DOWN)
        if disks:
            is_disks = 'disks: %s' % disks
        else:
            is_disks = 'all disks'
        logger.info("Adding new snapshot to vm %s with %s",
                    self.vm_name, is_disks)
        status = vms.addSnapshot(
            True, vm_name, self.snapshot_desc, disks_lst=disks, wait=wait)
        self.assertTrue(status, "Failed to create snapshot %s" %
                                self.snapshot_desc)
        if wait:
            vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
            wait_for_jobs()

    def check_file_existence_operation(self, vm_name, should_exist=True):

        vms.start_vms([vm_name], 1, wait_for_ip=False)
        vms.waitForVMState(vm_name)
        full_path = os.path.join(self.mount_path, self.file_name)
        logger.info("Checking full path %s", full_path)
        result = self.vm.isFileExists(full_path)
        logger.info("File %s", 'exists' if result else 'does not exist')

        if should_exist != result:
            return False
        return True


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_plan_id = '5588'
    vm_on_hsm = VM_ON_HSM % TestCase.storage
    vm_on_spm = VM_ON_SPM % TestCase.storage

    @classmethod
    def setup_class(cls):
        """
        Start machines
        """
        cls.vm_list = [cls.vm_on_spm, cls.vm_on_hsm]
        vms.start_vms(cls.vm_list, config.MAX_WORKERS)

    @classmethod
    def teardown_class(cls):
        """
        Returns VM to the base snapshot and cleans out all other snapshots
        """
        results = list()
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for vm_name in cls.vm_list:
                results.append(
                    executor.submit(restore_snapshot, vm_name, BASE_SNAP))
        raise_if_exception(results)


@attr(tier=0)
class TestCase141612(BasicEnvironmentSetUp):
    """
    Full flow Live snapshot - Test case 141612
    https://tcms.engineering.redhat.com/case/141612

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
    tcms_test_case = '141612'
    bz = {'1211588': {'engine': ['cli'], 'version': ['3.5', '3.6']}}

    def setUp(self):
        self.previewed = False
        self.vm_name = VM_ON_SPM % TestCase.storage
        super(TestCase141612, self).setUp()

    def _test_Live_snapshot(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        logger.info("Make sure vm %s is up", vm_name)
        if vms.get_vm_state(vm_name) == config.VM_DOWN:
            vms.startVms([vm_name])
            vms.waitForVMState(vm_name)
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        wait_for_jobs()

        logger.info("writing file to disk")
        cmd = self.cmd_create
        status, _ = self.vm.runCmd(shlex.split(cmd))
        assert status
        if not self.check_file_existence_operation(vm_name, True):
            raise exceptions.DiskException(
                "Writing operation failed"
            )

        vms.shutdownVm(True, vm_name)
        vms.waitForVMState(vm_name, state=config.VM_DOWN)

        logger.info("Previewing snapshot %s on vm %s",
                    self.snapshot_desc, vm_name)

        self.previewed = vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_desc,
            ensure_vm_down=True)
        self.assertTrue(self.previewed,
                        "Failed to preview snapshot %s" % self.snapshot_desc)
        wait_for_jobs()

        assert vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP)
        assert vms.waitForIP(vm=vm_name)
        logger.info("Checking that files no longer exist after preview")
        if not self.check_file_existence_operation(vm_name, False):
            raise exceptions.SnapshotException(
                "Snapshot operation failed"
            )

        self.assertTrue(vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True),
            "Failed to commit snapshot %s" % self.snapshot_desc)
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        if not self.check_file_existence_operation(vm_name, False):
            raise exceptions.SnapshotException(
                "Snapshot operation failed"
            )

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running on SPM host
        """
        self._test_Live_snapshot(self.vm_name)

    def tearDown(self):
        if self.previewed:
            if not vms.undo_snapshot_preview(
                    True, self.vm_name, ensure_vm_down=True):
                raise exceptions.SnapshotException(
                    "Failed to undo snapshot for vm %s" % self.vm_name)


@attr(tier=1)
class TestCase141646(BasicEnvironmentSetUp):
    """
    https://tcms.engineering.redhat.com/case/141646/

    Add a disk to the VMs
    Create live snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    tcms_test_case = '141646'
    mount_path = '/new_fs_%s'
    cmd_create = 'echo "test_txt" > %s/test_file'

    def setUp(self):
        self.previewed = False
        self.vm_name = VM_ON_SPM % TestCase.storage
        super(TestCase141646, self).setUp()
        logger.info("Adding disk to vm %s", self.vm_name)
        assert vms.addDisk(
            True, vm=self.vm_name, size=3 * config.GB, wait='True',
            storagedomain=self.storage_domain,
            type=ENUMS['disk_type_data'], interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, sparse='true'
        )
        self._prepare_fs_on_devs()

    def _prepare_fs_on_devs(self):
        vm_devices = self.vm.get_storage_devices()
        if not vm_devices:
            logger.error("No devices found in vm %s", self.vm_name)
            return False
        logger.info("Devices found: %s", vm_devices)
        devices = [d for d in vm_devices if d != 'vda']
        devices.sort()
        for dev in devices:
            dev_size = self.vm.get_storage_device_size(dev)
            dev_path = os.path.join('/dev', dev)
            logger.info("Creating partition for dev: %s", dev_path)
            dev_number = self.vm.createPartition(
                dev_path, ((dev_size / 2) * config.GB)
            )
            logger.info("Creating file system for dev: %s", dev + dev_number)
            self.vm.createFileSystem(
                dev_path, dev_number, 'ext4', (self.mount_path % dev)
            )

            self.mounted_paths.append(self.mount_path % dev)

    def check_file_existence_operation(
            self, should_exist=True, operation='snapshot'
    ):

        vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        vms.waitForVMState(self.vm_name)
        lst = []
        state = not should_exist
        for dev in self.devices:
            full_path = os.path.join((self.mount_path % dev), self.file_name)
            logger.info("Checking full path %s", full_path)
            result = self.vm.isFileExists(full_path)
            logger.info("File %s", 'exist' if result else 'not exist')
            lst.append(result)

        if state in lst:
            raise exceptions.SnapshotException(
                "%s operation failed" % operation
            )

    def _test_Live_snapshot(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        logger.info("Make sure vm %s is up", vm_name)
        if vms.get_vm_state(vm_name) == config.VM_DOWN:
            vms.startVms([vm_name])
            vms.waitForVMState(vm_name)
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        wait_for_jobs()

        vm_devices = self.vm.get_storage_devices()
        if not vm_devices:
            raise exceptions.VMException("No devices found")
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

        vms.stop_vms_safely([vm_name])

        logger.info("Previewing snapshot %s on vm %s",
                    self.snapshot_desc, vm_name)

        self.previewed = vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_desc,
            ensure_vm_down=True)
        self.assertTrue(self.previewed,
                        "Failed to preview snapshot %s" % self.snapshot_desc)
        logger.info("Wait for all jobs to complete")
        wait_for_jobs()

        assert vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP)
        assert vms.waitForIP(vm=vm_name)

        logger.info("Checking that files no longer exist after preview")
        self.check_file_existence_operation(False)

        self.assertTrue(vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True),
            "Failed to commit snapshot %s" % self.snapshot_desc)
        logger.info("Wait for all jobs to complete")
        wait_for_jobs()
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        self.check_file_existence_operation(False)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running on SPM host
        """
        self._test_Live_snapshot(self.vm_name)

    def tearDown(self):
        if self.previewed:
            if not vms.undo_snapshot_preview(
                    True, self.vm_name, ensure_vm_down=True
            ):
                raise exceptions.SnapshotException(
                    "Failed to undo snapshot for vm %s" % self.vm_name
                )


@attr(tier=1)
class TestCase141636(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141636

    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = True
    tcms_test_case = '141636'

    def _test_snapshot_desc_length(self, positive, length, vm_name):
        """
        Tries to create snapshot with given length description
        Parameters:
            * length - how many 'a' chars should description contain
        """
        description = length * 'a'
        logger.info("Trying to create snapshot on vm %s with description "
                    "containing %d 'a' letters", vm_name, length)
        self.assertTrue(
            vms.addSnapshot(positive, vm=vm_name, description=description))

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        self._test_snapshot_desc_length(True, config.MAX_DESC_LENGTH,
                                        self.vm_on_hsm)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        logger.info("Trying to create snapshot with description %s",
                    config.SPECIAL_CHAR_DESC)
        assert vms.addSnapshot(True, vm=self.vm_on_hsm,
                               description=config.SPECIAL_CHAR_DESC)


@attr(tier=1)
class TestCase147751(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/147751

    Create 2 additional disks in a different storage domain
    to the VM on HSM
    Add snapshot

    Expected Results:

    You should be able to create a snapshot
    """
    __test__ = True
    tcms_test_case = '147751'

    @classmethod
    def setup_class(cls):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        cls.vm_list = [cls.vm_on_spm, cls.vm_on_hsm]
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[1]
        for _ in range(2):
            logger.info("Adding disk to vm %s", cls.vm_on_hsm)
            assert vms.addDisk(
                True, vm=cls.vm_on_hsm, size=3 * config.GB, wait='True',
                storagedomain=storage_domain, type=ENUMS['disk_type_data'],
                interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
                sparse='true')
        super(TestCase147751, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Removes the second disk of vm vm_on_spm
        """
        super(TestCase147751, cls).teardown_class()
        for disk_index in [2, 3]:
            disk_name = "%s_Disk%d" % (cls.vm_on_hsm, disk_index)
            logger.info("Removing disk %s of vm %s", disk_name, cls.vm_on_hsm)
            assert vms.removeDisk(True, cls.vm_on_hsm, disk_name)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on vm that has disks on multiple
        storage domains
        """
        self.assertTrue(
            vms.addSnapshot(True, vm=self.vm_on_hsm, description=SNAP_1))


@attr(tier=1)
class TestCase141738(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141738

    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = True
    tcms_test_case = '141738'

    @classmethod
    def teardown_class(cls):
        """
        Waits until migration finishes
        """
        vms.waitForVMState(cls.vm_on_hsm)
        super(TestCase141738, cls).teardown_class()

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        assert vms.migrateVm(True, self.vm_on_hsm, wait=False)
        self.assertTrue(
            vms.addSnapshot(False, vm=self.vm_on_hsm, description=SNAP_1))


@attr(tier=1)
class TestCase141614(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141614/

    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = True
    tcms_test_case = '141614'

    @classmethod
    def setup_class(cls):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[1]
        logger.info("Adding disk to vm %s", cls.vm_on_spm)
        assert vms.addDisk(
            True, vm=cls.vm_on_spm, size=3 * config.GB, wait='True',
            storagedomain=storage_domain, type=ENUMS['disk_type_data'],
            interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
            sparse='true')
        super(TestCase141614, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Removes the second disk of vm vm_on_spm
        """
        super(TestCase141614, cls).teardown_class()
        disk_name = "%s_Disk2" % cls.vm_on_spm
        logger.info("Removing disk %s of vm %s", disk_name, cls.vm_on_spm)
        assert vms.removeDisk(True, cls.vm_on_spm, disk_name)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_with_multiple_disks(self):
        """
        Checks that created snapshot appears only once although vm has more
        disks
        """
        snap_descs = set([SNAP_1, BASE_SNAP, ACTIVE_SNAP])
        self.assertTrue(
            vms.addSnapshot(True, vm=self.vm_on_spm, description=SNAP_1))
        snapshots = vms._getVmSnapshots(self.vm_on_spm, False)
        current_snap_descs = set([snap.description for snap in snapshots])
        self.assertTrue(snap_descs == current_snap_descs)


@attr(tier=1)
class TestCase286330(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/286330

    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add snapshot for both thin and cloned VMs

    Expected Results:

    Live snapshots should be created for both cases
    """
    __test__ = True
    tcms_test_case = '286330'

    @classmethod
    def setup_class(cls):
        """
        Prepares template and two VMs based on this template: one clone and one
        thinly provisioned
        """
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        assert templates.createTemplate(
            True, vm=cls.vm_on_spm, name='template_test',
            cluster=config.CLUSTER_NAME)
        assert vms.addVm(
            True, name='vm_thin', description='', cluster=config.CLUSTER_NAME,
            storagedomain=storage_domain, template='template_test')
        assert vms.addVm(
            True, name='vm_clone', description='', cluster=config.CLUSTER_NAME,
            storagedomain=storage_domain, template='template_test',
            disk_clone='True')
        vms.start_vms(['vm_thin', 'vm_clone'], config.MAX_WORKERS)

    @classmethod
    def teardown_class(cls):
        """
        Removes cloned, thinly provisioned vm and template
        """
        assert vms.removeVm(True, 'vm_thin', stopVM='true')
        assert vms.removeVm(True, 'vm_clone', stopVM='true')
        assert templates.removeTemplate(True, template='template_test')
        wait_for_tasks(
            vdc=config.PARAMETERS['host'],
            vdc_password=config.PARAMETERS['vdc_root_password'],
            datacenter=config.DATA_CENTER_NAME)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_thin', description=SNAP_1))

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_clone', description=SNAP_1))
