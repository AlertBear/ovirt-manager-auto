"""
Storage live snapshot sanity tests - full test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Snapshot
"""
import config
import logging
import os
import shlex
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.networking.helper import seal_vm
from rhevmtests.storage import helpers as storage_helpers
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    storagedomains as ll_sds,
    templates as ll_templates,
    vms as ll_vms,
)
from utilities.machine import Machine, LINUX


logger = logging.getLogger(__name__)


class BaseTestCase(TestCase):
    """
    This class implements the common setUp and tearDown functions
    """
    __test__ = False
    polarion_test_case = None
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status

    def setUp(self):
        """
        Create a VM to be used with each test
        """
        self.storage_domains = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.vm_name = config.VM_NAME % (self.storage, self.polarion_test_case)
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domains[0]
        vm_args['vmName'] = self.vm_name
        vm_args['vmDescription'] = self.vm_name
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm_name
            )

    def tearDown(self):
        """
        Removes the VM created
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            TestCase.test_failed = True
        TestCase.teardown_exception()


class BasicEnvironmentSetUp(BaseTestCase):
    """
    This class implements setup, teardowns and common functions
    """
    __test__ = False
    file_name = 'test_file'
    mount_path = '/root'
    cmd_create = 'echo "test_txt" > test_file'
    cm_del = 'rm -f test_file'

    def setUp(self):
        """
        Prepare environment
        """
        super(BasicEnvironmentSetUp, self).setUp()
        if not seal_vm(self.vm_name, config.VM_PASSWORD):
            raise exceptions.VMException(
                "Failed to seal vm %s" % self.vm_name
            )
        self.disk_name = 'test_disk_%s' % self.polarion_test_case
        self.snapshot_desc = 'snapshot_%s' % self.polarion_test_case
        self.mounted_paths = []
        self.boot_disk = ll_vms.get_vm_bootable_disk(self.vm_name)
        logger.info("The boot disk is: %s", self.boot_disk)
        if not ll_vms.startVm(True, self.vm_name, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to power on vm %s" % self.vm_name
            )
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.vm = Machine(
            vm_ip, config.VM_USER, config.VM_PASSWORD
        ).util(LINUX)
        if not ll_vms.stop_vms_safely([self.vm_name]):
            raise exceptions.VMException(
                "Failed to power off vm %s" % self.vm_name
            )

    def _perform_snapshot_operation(
            self, vm_name, disks=None, wait=True, live=False):
        if not live:
            if not ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
                ll_vms.shutdownVm(True, vm_name)
                ll_vms.waitForVMState(vm_name, config.VM_DOWN)
        if disks:
            is_disks = 'disks: %s' % disks
        else:
            is_disks = 'all disks'
        logger.info("Adding new snapshot to vm %s with %s",
                    self.vm_name, is_disks)
        status = ll_vms.addSnapshot(
            True, vm_name, self.snapshot_desc, disks_lst=disks, wait=wait)
        self.assertTrue(
            status, "Failed to create snapshot %s" % self.snapshot_desc
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
        logger.info("File %s", 'exists' if result else 'does not exist')

        if should_exist != result:
            return False
        return True


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
        super(TestCase11660, self).setUp()

    def _test_Live_snapshot(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        logger.info("Make sure vm %s is up", vm_name)
        if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
            ll_vms.startVms([vm_name])
            ll_vms.waitForVMState(vm_name)
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        logger.info("writing file to disk")
        cmd = self.cmd_create
        status, _ = self.vm.runCmd(shlex.split(cmd))
        assert status
        if not self.check_file_existence_operation(vm_name, True):
            raise exceptions.DiskException(
                "Writing operation failed"
            )
        ll_vms.shutdownVm(True, vm_name, 'false')
        logger.info(
            "Previewing snapshot %s on vm %s", self.snapshot_desc, vm_name
        )
        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_desc,
            ensure_vm_down=True
        )
        self.assertTrue(
            self.previewed,
            "Failed to preview snapshot %s" % self.snapshot_desc
        )
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_ip=True
        )
        logger.info("Checking that files no longer exist after preview")
        if not self.check_file_existence_operation(vm_name, False):
            raise exceptions.SnapshotException(
                "Snapshot operation failed"
            )

        self.assertTrue(ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True
        ),
            "Failed to commit snapshot %s" % self.snapshot_desc)
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        if not self.check_file_existence_operation(vm_name, False):
            raise exceptions.SnapshotException(
                "Snapshot operation failed"
            )

    @polarion("RHEVM3-11660")
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running
        """
        self._test_Live_snapshot(self.vm_name)

    def tearDown(self):
        if self.previewed:
            if not ll_vms.undo_snapshot_preview(
                    True, self.vm_name, ensure_vm_down=True):
                logger.error(
                    "Failed to undo snapshot for vm %s", self.vm_name
                )
                TestCase.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )
        super(TestCase11660, self).tearDown()


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
        super(TestCase11679, self).setUp()
        logger.info("Adding disk to vm %s", self.vm_name)
        if not ll_vms.addDisk(
            True, vm=self.vm_name, provisioned_size=3 * config.GB,
            wait='True', storagedomain=self.storage_domains[0],
            type=config.DISK_TYPE_DATA, interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW, sparse='true'
        ):
            raise exceptions.DiskException(
                "Failed to add new disk to vm %s" % self.vm_name
            )
        self._prepare_fs_on_devs()

    def _prepare_fs_on_devs(self):
        if not ll_vms.startVm(True, self.vm_name, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )
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
        ll_vms.start_vms([self.vm_name], 1, config.VM_UP)
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
        if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
            ll_vms.startVms([vm_name], config.VM_UP)
        logger.info("Creating snapshot")
        self._perform_snapshot_operation(vm_name, live=True)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

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
        ll_vms.stop_vms_safely([vm_name])

        logger.info("Previewing snapshot %s on vm %s",
                    self.snapshot_desc, vm_name)

        self.previewed = ll_vms.preview_snapshot(
            True, vm=vm_name, description=self.snapshot_desc,
            ensure_vm_down=True)
        self.assertTrue(
            self.previewed,
            "Failed to preview snapshot %s" % self.snapshot_desc
        )
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        assert ll_vms.startVm(
            True, vm=vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        )

        logger.info("Checking that files no longer exist after preview")
        self.check_file_existence_operation(False)

        self.assertTrue(ll_vms.commit_snapshot(
            True, vm=vm_name, ensure_vm_down=True),
            "Failed to commit snapshot %s" % self.snapshot_desc)
        logger.info("Wait for all jobs to complete")
        ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
        self.previewed = False
        logger.info("Checking that files no longer exist after commit")
        self.check_file_existence_operation(False)

    @polarion("RHEVM3-11679")
    def test_live_snapshot(self):
        """
        Create a snapshot while VM is running
        """
        self._test_Live_snapshot(self.vm_name)

    def tearDown(self):
        if self.previewed:
            if not ll_vms.undo_snapshot_preview(
                    True, self.vm_name, ensure_vm_down=True
            ):
                raise exceptions.SnapshotException(
                    "Failed to undo snapshot for vm %s" % self.vm_name
                )
        super(TestCase11679, self).tearDown()


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
        self.assertTrue(
            ll_vms.startVm(True, vm_name), "Failed to start vm %s" % vm_name
        )
        description = length * 'a'
        logger.info("Trying to create snapshot on vm %s with description "
                    "containing %d 'a' letters", vm_name, length)
        self.assertTrue(
            ll_vms.addSnapshot(positive, vm=vm_name, description=description)
        )

    @polarion("RHEVM3-11676")
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        self._test_snapshot_desc_length(
            True, config.MAX_DESC_LENGTH, self.vm_name
        )

    @polarion("RHEVM3-11676")
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        logger.info(
            "Trying to create snapshot with description %s",
            config.SPECIAL_CHAR_DESC
        )
        self.assertTrue(ll_vms.addSnapshot(
            True, vm=self.vm_name, description=config.SPECIAL_CHAR_DESC
        ), "Failed to add snapshot %s to vm %s" %
           (config.SPECIAL_CHAR_DESC, self.vm_name))


@attr(tier=2)
class TestCase11665(BaseTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Live_Snapshot?selection=RHEVM3-11665

    Create 2 additional disks on a VM, each on a different storage domain
    Add snapshot

    Expected Results:
    You should be able to create a snapshot
    """
    __test__ = True
    polarion_test_case = '11665'
    snapshot_description = (
        config.LIVE_SNAPSHOT % polarion_test_case
    )

    def setUp(self):
        """
        Adds disk to vm that will be on second domain
        """
        super(TestCase11665, self).setUp()
        for index in range(2):
            alias = "disk_%s_%d" % (self.polarion_test_case, index)
            logger.info("Adding disk %s to vm %s", alias, self.vm_name)
            assert ll_vms.addDisk(
                True, vm=self.vm_name, provisioned_size=3 * config.GB,
                wait='True', storagedomain=self.storage_domains[1],
                type=config.DISK_TYPE_DATA,
                interface=config.VIRTIO, format=config.COW_DISK,
                sparse='true', alias=alias
            )
        if not ll_vms.startVm(True, self.vm_name):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_CREATE_SNAPSHOT])
    @polarion("RHEVM3-11665")
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on vm that has disks on multiple
        storage domains
        """
        self.assertTrue(
            ll_vms.addSnapshot(
                True, vm=self.vm_name, description=self.snapshot_description
            )
        )


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
    snapshot_description = (
        config.LIVE_SNAPSHOT % polarion_test_case
    )

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MIGRATE_VM])
    @polarion("RHEVM3-11680")
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        self.assertTrue(
            ll_vms.startVm(True, self.vm_name),
            "Failed to start vm %s" % self.vm_name
        )
        assert ll_vms.migrateVm(True, self.vm_name, wait=False)
        self.assertTrue(
            ll_vms.addSnapshot(
                False, vm=self.vm_name, description=self.snapshot_description
            )
        )


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
    snapshot_description = (
        config.LIVE_SNAPSHOT % polarion_test_case
    )

    def setUp(self):
        """
        Adds disk to vm that will be on second domain
        """
        super(TestCase11674, self).setUp()
        self.disk_name = "disk_%s" % self.polarion_test_case
        logger.info("Adding disk %s to vm %s", self.disk_name, self.vm_name)
        if not ll_vms.addDisk(
            True, vm=self.vm_name, provisioned_size=3 * config.GB, wait=True,
            storagedomain=self.storage_domains[0], type=config.DISK_TYPE_DATA,
            interface=config.VIRTIO, format=config.COW_DISK,
            sparse='true', alias=self.disk_name
        ):
            raise exceptions.DiskException(
                "Failed to add new disk to vm %s" % self.vm_name
            )
        if not ll_vms.startVm(True, self.vm_name):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )

    @polarion("RHEVM3-11674")
    def test_snapshot_with_multiple_disks(self):
        """
        Checks that created snapshot appears only once although vm has more
        disks
        """
        snap_descs = set([config.ACTIVE_SNAPSHOT, self.snapshot_description])
        self.assertTrue(
            ll_vms.addSnapshot(
                True, vm=self.vm_name, description=self.snapshot_description
            )
        )
        snapshots = ll_vms._getVmSnapshots(self.vm_name, False)
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
    snapshot_description = (
        config.LIVE_SNAPSHOT % polarion_test_case
    )

    def setUp(self):
        """
        Prepares template and two VMs based on this template: one clone and one
        thinly provisioned
        """
        self.template_name = 'template_test_%s' % self.polarion_test_case
        self.vm_thin = 'vm_thin_%s' % self.polarion_test_case
        self.vm_clone = 'vm_clone_%s' % self.polarion_test_case
        super(TestCase11684, self).setUp()
        if not ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME
        ):
            raise exceptions.TemplateException(
                "Failed to create template %s from vm %s" %
                (self.template_name, self.vm_name)
            )
        if not ll_vms.addVm(
            True, name=self.vm_thin, description='',
            cluster=config.CLUSTER_NAME,
            storagedomain=self.storage_domains[0], template=self.template_name
        ):
            raise exceptions.VMException(
                "Failed to create new vm %s from template %s as thin copy" %
                (self.vm_thin, self.template_name)
            )
        if not ll_vms.addVm(
            True, name=self.vm_clone, description='',
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domains[0],
            template=self.template_name, disk_clone='True'
        ):
            raise exceptions.VMException(
                "Failed to create new vm %s from template %s as deep copy" %
                (self.vm_clone, self.template_name)
            )
        ll_vms.start_vms([self.vm_thin, self.vm_clone], config.MAX_WORKERS)

    def tearDown(self):
        """
        Removes cloned, thinly provisioned vm and template
        """
        if not ll_vms.safely_remove_vms([self.vm_thin, self.vm_clone]):
            logger.error(
                "Failed to remove vms %s", [self.vm_thin, self.vm_clone]
            )
            BaseTestCase.test_failed = True
        if not ll_templates.removeTemplate(True, template=self.template_name):
            logger.error(
                "Failed to remove template %s", self.template_name
            )
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs(
            [config.JOB_REMOVE_VM, config.JOB_REMOVE_TEMPLATE]
        )
        super(TestCase11684, self).tearDown()

    @polarion("RHEVM3-11684")
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        self.assertTrue(
            ll_vms.addSnapshot(
                True, vm=self.vm_thin, description=self.snapshot_description
            )
        )

    @polarion("RHEVM3-11684")
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        self.assertTrue(
            ll_vms.addSnapshot(
                True, vm=self.vm_clone, description=self.snapshot_description
            )
        )
