"""
Storage live snapshot sanity tests - full test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Snapshot
"""
import config
import helpers
import logging
import os
import shlex
from rhevmtests.storage import helpers as storage_helpers

from concurrent.futures import ThreadPoolExecutor

from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr

from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level import hosts, templates, vms
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType)

from art.rhevm_api.utils.test_utils import get_api, raise_if_exception
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
    'size': config.VM_DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'image': config.COBBLER_PROFILE,
    'useAgent': True,
    'os_type': config.OS_TYPE,
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
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


def teardown_module():
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
    vm_name = ''
    file_name = 'test_file'
    mount_path = '/root'
    cmd_create = 'echo "test_txt" > test_file'
    cm_del = 'rm -f test_file'

    def setUp(self):
        """
        Prepare environment
        """
        self.vm_on_hsm = VM_ON_HSM % self.storage
        self.vm_on_spm = VM_ON_SPM % self.storage
        self.disk_name = 'test_disk_%s' % self.polarion_test_case
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        if not vms.waitForVMState(self.vm_name):
            raise exceptions.VMException(
                "Timeout when waiting for vm %s and state up" % self.vm_name)
        self.mounted_paths = []
        self.boot_disk = vms.get_vm_bootable_disk(self.vm_name)
        logger.info("The boot disk is: %s", self.boot_disk)

    def set_vm_machine_object(self):
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        logger.debug("IP for vm %s is %s", self.vm_name, vm_ip)
        self.vm = Machine(vm_ip, config.VM_USER,
                          config.VM_PASSWORD).util(LINUX)

    def tearDown(self):
        remove_all_vm_snapshots(self.vm_name, self.snapshot_desc)
        if not vms.start_vms([self.vm_name]):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name)
        if not vms.waitForVMState(self.vm_name):
            raise exceptions.VMException(
                "Timeout when waiting for vm %s to start" % self.vm_name)
        self.set_vm_machine_object()
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
            wait_for_jobs([ENUMS['job_create_snapshot']])

    def check_file_existence_operation(self, vm_name, should_exist=True):

        vms.start_vms([vm_name], 1, wait_for_ip=False)
        vms.waitForVMState(vm_name)
        self.set_vm_machine_object()
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
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status

    def setUp(self):
        """
        Start machines
        """
        self.vm_on_hsm = VM_ON_HSM % self.storage
        self.vm_on_spm = VM_ON_SPM % self.storage
        self.vm_list = [self.vm_on_spm, self.vm_on_hsm]
        vms.start_vms(self.vm_list, config.MAX_WORKERS)

    def tearDown(self):
        """
        Returns VM to the base snapshot and cleans out all other snapshots
        """
        results = list()
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for vm_name in self.vm_list:
                results.append(
                    executor.submit(
                        vms.restore_snapshot, True, vm_name, BASE_SNAP, True
                    )
                )
        raise_if_exception(results)


@attr(tier=1)
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
    polarion_test_case = '11660'
    # Bugzilla history
    # 1211588: CLI auto complete options async and grace_period-expiry are
    # missing for preview_snapshot

    def setUp(self):
        self.previewed = False

        self.vm_name = VM_ON_SPM % self.storage
        super(TestCase11660, self).setUp()

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
        wait_for_jobs([ENUMS['job_create_snapshot']])
        self.set_vm_machine_object()

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
        wait_for_jobs([ENUMS['job_preview_snapshot']])

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
        wait_for_jobs([ENUMS['job_restore_vm_snapshot']])
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        if not self.check_file_existence_operation(vm_name, False):
            raise exceptions.SnapshotException(
                "Snapshot operation failed"
            )

    @polarion("RHEVM3-11660")
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
        remove_all_vm_snapshots(self.vm_name, self.snapshot_desc)


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
    polarion_test_case = '11679'
    mount_path = '/new_fs_%s'
    cmd_create = 'echo "test_txt" > %s/test_file'

    def setUp(self):
        self.previewed = False
        self.vm_name = VM_ON_SPM % self.storage
        super(TestCase11679, self).setUp()
        logger.info("Adding disk to vm %s", self.vm_name)
        assert vms.addDisk(
            True, vm=self.vm_name, size=3 * config.GB, wait='True',
            storagedomain=self.storage_domain,
            type=ENUMS['disk_type_data'], interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, sparse='true'
        )
        self._prepare_fs_on_devs()

    def _prepare_fs_on_devs(self):
        self.set_vm_machine_object()
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
        self.set_vm_machine_object()
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
        self.set_vm_machine_object()
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        wait_for_jobs([ENUMS['job_create_snapshot']])

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
        wait_for_jobs([ENUMS['job_preview_snapshot']])

        assert vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP)
        assert vms.waitForIP(vm=vm_name)

        logger.info("Checking that files no longer exist after preview")
        self.check_file_existence_operation(False)

        self.assertTrue(vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True),
            "Failed to commit snapshot %s" % self.snapshot_desc)
        logger.info("Wait for all jobs to complete")
        wait_for_jobs([ENUMS['job_restore_vm_snapshot']])
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        self.check_file_existence_operation(False)

    @polarion("RHEVM3-11679")
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


@attr(tier=2)
class TestCase11676(BaseTestCase):
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
    polarion_test_case = '11676'

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

    @polarion("RHEVM3-11676")
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        self._test_snapshot_desc_length(True, config.MAX_DESC_LENGTH,
                                        self.vm_on_hsm)

    @polarion("RHEVM3-11676")
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        logger.info("Trying to create snapshot with description %s",
                    config.SPECIAL_CHAR_DESC)
        assert vms.addSnapshot(True, vm=self.vm_on_hsm,
                               description=config.SPECIAL_CHAR_DESC)


@attr(tier=2)
class TestCase11665(BaseTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11665

    Create 2 additional disks in a different storage domain
    to the VM on HSM
    Add snapshot

    Expected Results:

    You should be able to create a snapshot
    """
    __test__ = True
    polarion_test_case = '11665'

    def setUp(self):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        self.disks_names = []
        self.vm_on_hsm = VM_ON_HSM % self.storage
        self.vm_on_spm = VM_ON_SPM % self.storage
        self.vm_list = [self.vm_on_spm, self.vm_on_hsm]
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        for index in range(2):
            alias = "disk_%s_%d" % (self.polarion_test_case, index)
            logger.info("Adding disk %s to vm %s", alias, self.vm_on_hsm)
            assert vms.addDisk(
                True, vm=self.vm_on_hsm, size=3 * config.GB, wait='True',
                storagedomain=storage_domain, type=ENUMS['disk_type_data'],
                interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
                sparse='true', alias=alias)
            self.disks_names.append(alias)
        super(TestCase11665, self).setUp()

    @polarion("RHEVM3-11665")
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on vm that has disks on multiple
        storage domains
        """
        self.assertTrue(
            vms.addSnapshot(True, vm=self.vm_on_hsm, description=SNAP_1))


@attr(tier=2)
class TestCase11680(BaseTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11680

    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = True
    polarion_test_case = '11680'

    def tearDown(self):
        """
        Waits until migration finishes
        """

        vms.waitForVMState(self.vm_on_hsm)
        super(TestCase11680, self).tearDown()

    @polarion("RHEVM3-11680")
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        assert vms.migrateVm(True, self.vm_on_hsm, wait=False)
        self.assertTrue(
            vms.addSnapshot(False, vm=self.vm_on_hsm, description=SNAP_1))


@attr(tier=2)
class TestCase11674(BaseTestCase):
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
    polarion_test_case = '11674'

    def setUp(self):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        self.vm_on_hsm = VM_ON_HSM % self.storage
        self.vm_on_spm = VM_ON_SPM % self.storage
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        self.disk_name = "disk_%s" % self.polarion_test_case
        logger.info("Adding disk %s to vm %s", self.disk_name, self.vm_on_spm)
        assert vms.addDisk(
            True, vm=self.vm_on_spm, size=3 * config.GB, wait='True',
            storagedomain=storage_domain, type=ENUMS['disk_type_data'],
            interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
            sparse='true', alias=self.disk_name
        )
        super(TestCase11674, self).setUp()

    @polarion("RHEVM3-11674")
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


@attr(tier=2)
class TestCase11684(BaseTestCase):
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
    polarion_test_case = '11684'

    def setUp(self):
        """
        Prepares template and two VMs based on this template: one clone and one
        thinly provisioned
        """
        self.vm_on_hsm = VM_ON_HSM % self.storage
        self.vm_on_spm = VM_ON_SPM % self.storage
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        assert templates.createTemplate(
            True, vm=self.vm_on_spm, name='template_test',
            cluster=config.CLUSTER_NAME)
        assert vms.addVm(
            True, name='vm_thin', description='', cluster=config.CLUSTER_NAME,
            storagedomain=storage_domain, template='template_test')
        assert vms.addVm(
            True, name='vm_clone', description='', cluster=config.CLUSTER_NAME,
            storagedomain=storage_domain, template='template_test',
            disk_clone='True')
        vms.start_vms(['vm_thin', 'vm_clone'], config.MAX_WORKERS)

    def tearDown(self):
        """
        Removes cloned, thinly provisioned vm and template
        """
        assert vms.removeVm(True, 'vm_thin', stopVM='true')
        assert vms.removeVm(True, 'vm_clone', stopVM='true')
        assert templates.removeTemplate(True, template='template_test')
        wait_for_jobs(
            [ENUMS['job_remove_vm'], ENUMS['job_remove_vm_template']]
        )

    @polarion("RHEVM3-11684")
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_thin', description=SNAP_1))

    @polarion("RHEVM3-11684")
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_clone', description=SNAP_1))
