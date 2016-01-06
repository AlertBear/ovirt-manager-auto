"""
3.5 Live merge
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Live_Merge
"""
import config
import logging
import os
import shlex
from threading import Thread
import time
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.utils.test_utils import restartVdsmd, restart_engine
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.tests_lib.low_level import disks, hosts, storagedomains, vms
from art.unittest_lib import StorageTest as BaseTestCase
from rhevmtests.storage import helpers as storage_helpers
from art.unittest_lib import attr
from rhevmtests.storage.storage_live_merge import helpers
from utilities.machine import LINUX, Machine
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler import exceptions
from socket import timeout as TimeoutError

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

VM_NAMES = dict()
CMD_CREATE_FILE = 'touch %s/test_file_%s'
CMD_DELETE_FILE = 'rm -f %s/test_file_%s'
VM_TEMPLATE = 'template_live_merge'
TEST_FILE_TEMPLATE = 'test_file_%s'
SNAPSHOT_DESCRIPTION_TEMPLATE = 'snapshot_%s_%s_%s'
REGEX = "All Live Merge child commands have completed, status 'SUCCEEDED'"
# Live snapshot removal required long timeout
REMOVE_SNAPSHOT_TIMEOUT = 2400
POLL_TIMEOUT = 20

vmArgs = {
    'positive': True,
    'vmDescription': config.VM_NAME % "description",
    'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK,
    'cluster': config.CLUSTER_NAME,
    'storageDomainName': None,
    'installation': True,
    'size': config.VM_DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'useAgent': True, 'os_type': config.ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
    'image': config.COBBLER_PROFILE,
}

disk_args = {
    'positive': True,
    'provisioned_size': config.DISK_SIZE,
    'bootable': False,
    'interface': config.VIRTIO,
    'sparse': True,
    'format': config.COW_DISK,
}


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    test_case = None

    def setUp(self):
        """
        Prepare the environment for testing
        """
        self.vm_name = config.VM_NAME % self.storage
        self.snapshot_list = list()
        VM_NAMES[self.storage] = list()
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.spm = hosts.getSPMHost(config.HOSTS)
        host_ip = hosts.getHostIP(self.spm)
        self.host = Machine(host_ip, config.HOSTS_USER,
                            config.HOSTS_PW).util(LINUX)
        logger.info("Creating VM %s", self.vm_name)
        vmArgs['storageDomainName'] = self.storage_domain
        vmArgs['vmName'] = self.vm_name

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name)
        VM_NAMES[self.storage].append(self.vm_name)
        helpers.prepare_disks_with_fs_for_vm(
            self.storage_domain, self.storage, self.vm_name
        )

        disk_objects = vms.getVmDisks(self.vm_name)
        for disk in disk_objects:
            new_vm_disk_name = (
                "%s_%s" % (disk.get_name(), self.test_case)
            )
            disks.updateDisk(
                True, vmName=self.vm_name, id=disk.get_id(),
                alias=new_vm_disk_name
            )
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.vm_machine = Machine(
            host=vm_ip, user=config.VM_USER, password=config.VM_PASSWORD
        ).util(LINUX)

    def tearDown(self):
        """
        Clean the environment - remove vm created during setup
        """
        logger.info('Deleting VM %s', self.vm_name)
        if not vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            self.test_failed = True

        for disk_name in helpers.DISK_NAMES.iteritems():
            if disks.checkDiskExists(True, disk_name):
                if not disks.deleteDisk(True, disk_name):
                    logger.error("Failed to delete disk %s", self.disk_name)
                    self.test_failed = True
        self.teardown_exception()

    def create_files_on_vm_disks(self, vm_name, iteration_number):
        """
        Files will be created on vm's disks with name:
        'test_file_<iteration_number>'
        """
        if vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            assert vms.startVm(
                True, self.vm_name, config.VM_UP, wait_for_ip=True
            )
        for idx, mount_dir in enumerate(helpers.MOUNT_POINTS[self.storage]):
            logger.info("Creating file in %s", mount_dir)
            status, output = self.vm_machine.runCmd(
                shlex.split(CMD_CREATE_FILE % (mount_dir, iteration_number))
            )
            if not status:
                logger.error(
                    "Failed to create file test_file_%s under %s on vm %s. "
                    "output:  %s",
                    iteration_number, mount_dir, vm_name, output
                )
                return False
        return True

    def perform_snapshot_operation(
            self, snapshot_description, wait=True, live=False
    ):
        if not live:
            if not vms.get_vm_state(self.vm_name) == config.VM_DOWN:
                vms.shutdownVm(True, self.vm_name)
                vms.waitForVMState(self.vm_name, config.VM_DOWN)

        logger.info(
            "Adding new %s snapshot to vm %s",
            'live' if live else '', self.vm_name
        )
        status = vms.addSnapshot(
            True, self.vm_name, snapshot_description, wait=wait
        )
        self.assertTrue(
            status, "Failed to create snapshot %s" % snapshot_description
        )
        if wait:
            vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], [snapshot_description]
            )
        self.snapshot_list.append(snapshot_description)
        if not live:
            if vms.get_vm_state(self.vm_name) == config.VM_DOWN:
                vms.startVm(True, self.vm_name, config.VM_UP)

    def perform_snapshot_with_verification(
            self, snap_description, disks_for_snap
    ):
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disks_for_snap
        )
        logger.info("Before snapshot: %s volumes", initial_vol_count)

        self.perform_snapshot_operation(snap_description)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disks_for_snap
        )
        logger.info("After snapshot: %s volumes", current_vol_count)

        self.assertEqual(current_vol_count,
                         initial_vol_count + len(disks_for_snap))

    def check_files_existence(self, files, should_exist=True):
        """
        Verifies whether files exist
        """
        vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        result_list = []
        state = not should_exist
        # For each mount point, check if the corresponding file exists
        for mount_dir in helpers.MOUNT_POINTS[self.storage]:
            for file_name in files:
                full_path = os.path.join(mount_dir, file_name)
                try:
                    logger.info("Checking if file %s exists", full_path)
                    result = self.vm_machine.isFileExists(full_path)
                except TimeoutError, ex:
                    logger.error("%s", ex)
                logger.info(
                    "File %s", 'exists' if result else 'does not exist'
                )
                result_list.append(result)

        if state in result_list:
            return False
        return True

    def verify_snapshot_files(self, snapshot_description, files):
        """
        Verifies whether files exist in snapshot using Preview for the
        verification
        """
        logger.info("Previewing snapshot %s", snapshot_description)
        if not vms.preview_snapshot(
                True, self.vm_name, snapshot_description, True
        ):
            raise exceptions.SnapshotException(
                "Failed to preview snapshot %s. Can't verify files",
                snapshot_description
            )
        wait_for_jobs([ENUMS['job_preview_snapshot']])
        # TODO: workaround for bug:
        # https://bugzilla.redhat.com/show_bug.cgi?id=1270583
        logger.info("Plugging in the vm's nic as workaround for bug #1270583")
        if not vms.updateNic(
                True, self.vm_name, config.NIC_NAME[0], plugged=True
        ):
            raise exceptions.NetworkException(
                "Failed to plug vm nic as workaround for bug "
                "https://bugzilla.redhat.com/show_bug.cgi?id=1270583"
            )
        try:
            logger.info(
                "Verifying files %s on snapshot %s",
                files, snapshot_description
            )
            if not self.check_files_existence(files):
                raise exceptions.SnapshotException(
                    "Snapshot verification failed"
                )

        # Make sure to undo the previewed snapshot if the file
        # verification failed
        finally:
            logger.info("Undoing snapshot preview")
            self.assertTrue(
                vms.undo_snapshot_preview(True, self.vm_name, True),
                "Undo snapshot failed"
            )
            logger.info(
                "Plugging in the vm's nic as workaround for bug #1270583"
            )
            # TODO: workaround for bug:
            # https://bugzilla.redhat.com/show_bug.cgi?id=1270583
            if not vms.updateNic(
                True, self.vm_name, config.NIC_NAME[0], plugged=True
            ):
                logger.error(
                    "Failed to plug vm nic as workaround for bug "
                    "https://bugzilla.redhat.com/show_bug.cgi?id=1270583"
                )

    def live_delete_snapshot_with_verification(
            self, vm_name, snapshot_description
    ):
        if vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            vms.startVm(True, self.vm_name, config.VM_UP)
        t = Thread(target=watch_logs, args=(
            config.ENGINE_LOG, REGEX, '', None,
            config.VDC, 'root', config.VDC_ROOT_PASSWORD)
        )
        t.start()
        time.sleep(5)

        logger.info("Removing snapshot %s", snapshot_description)
        status = vms.removeSnapshot(True, vm_name, snapshot_description)
        t.join()
        self.assertTrue(
            status, "Failed to remove snapshot %s" % snapshot_description
        )
        logger.info("Snapshot %s removed", snapshot_description)

    def basic_flow(self, snapshot_count=3):
        vm_disks = vms.getVmDisks(self.vm_name)
        disk_names = [disk.get_alias() for disk in vm_disks]
        for idx in xrange(snapshot_count):
            # Create files on all vm's disks before snapshot operation.
            # Files will be named: 'test_file_<idx>'
            if not self.create_files_on_vm_disks(self.vm_name, idx):
                raise exceptions.VMException("Failed to create file")
            snap_description = SNAPSHOT_DESCRIPTION_TEMPLATE % (
                self.test_case, self.storage, idx
            )
            self.perform_snapshot_with_verification(
                snap_description, disk_names
            )


@attr(tier=1)
class TestCase6038(BasicEnvironment):
    """
    Basic live delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6038
    """
    __test__ = True
    test_case = '6038'

    @polarion("RHEVM3-6038")
    def test_basic_live_deletion(self):
        self.basic_flow()

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


@attr(tier=2)
class TestCase12215(BasicEnvironment):
    """
    Deleting all snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-12215
    """
    __test__ = True
    test_case = '12215'

    @polarion("RHEVM3-12215")
    def test_live_deletion_of_all_snapshots(self):
        self.basic_flow()

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[0], [TEST_FILE_TEMPLATE % '0']
        )


@attr(tier=2)
class TestCase6044(BasicEnvironment):
    """
    Live delete and merge after deleting the base snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6044
    """
    __test__ = True
    test_case = '6044'

    @polarion("RHEVM3-6044")
    def test_live_deletion_base_snapshot(self):
        self.basic_flow()

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[0]
        )
        self.verify_snapshot_files(
            self.snapshot_list[1], [TEST_FILE_TEMPLATE % i for i in xrange(2)]
        )
        assert vms.startVm(True, self.vm_name, config.VM_UP, wait_for_ip=True)


@attr(tier=4)
class TestCase6045(BasicEnvironment):
    """
    Live snapshot delete and merge with restart of vdsm

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6045
    """
    __test__ = True
    test_case = '6045'

    @polarion("RHEVM3-6045")
    def test_live_deletion_during_vdsm_restart(self):
        self.basic_flow()

        logger.info("Removing snapshot %s", self.snapshot_list[1])
        # timeout=-1 means no wait
        assert vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )

        logger.info("Restarting VDSM")
        assert restartVdsmd(self.spm, config.HOSTS_PW)
        logger.info("VDSM restarted")

        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


@attr(tier=2)
class TestCase6043(BasicEnvironment):
    """
    Live delete and merge after deleting the last created snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6043
    """
    __test__ = True
    test_case = '6043'

    @polarion("RHEVM3-6043")
    def test_basic_live_deletion(self):
        self.basic_flow()

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[1], [TEST_FILE_TEMPLATE % i for i in xrange(2)]
        )
        assert vms.startVm(True, self.vm_name, config.VM_UP)


@attr(tier=4)
class TestCase6046(BasicEnvironment):
    """
    Live delete and merge of snapshot while stopping the engine

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6046
    """
    __test__ = True
    test_case = '6046'

    @polarion("RHEVM3-6046")
    def test_live_deletion_during_engine_restart(self):
        self.basic_flow()

        logger.info("Removing snapshot %s", self.snapshot_list[1])
        assert vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        logger.info("Restarting ovirt-engine")
        restart_engine(config.ENGINE, 10, 75)
        logger.info("ovirt-engine restarted")

        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


@attr(tier=2)
class TestCase6048(BasicEnvironment):
    """
    Consecutive delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6048
    """
    __test__ = True
    test_case = '6048'

    @polarion("RHEVM3-6048")
    def test_consecutive_live_deletion_of_snapshots(self):
        self.basic_flow(5)

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[3], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[3]
        )
        self.verify_snapshot_files(
            self.snapshot_list[4], [TEST_FILE_TEMPLATE % i for i in xrange(5)]
        )


@attr(tier=2)
class TestCase6050(BasicEnvironment):
    """
    Delete a 2nd live snapshot during a delete and merge of another
    snapshot within the same VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6050
    """
    __test__ = True
    test_case = '6050'

    @polarion("RHEVM3-6050")
    def test_live_merge_during_live_merge(self):
        self.basic_flow()

        logger.info("Removing snapshot %s", self.snapshot_list[1])
        assert vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        assert vms.removeSnapshot(
            False, self.vm_name, self.snapshot_list[2], timeout=-1
        )
        assert vms.wait_for_snapshot_gone(self.vm_name, self.snapshot_list[1])


@attr(tier=2)
class TestCase6057(BasicEnvironment):
    """
    Live delete and merge of snapshot after disk Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6057
    """
    __test__ = True
    test_case = '6057'

    @polarion("RHEVM3-6057")
    def test_live_deletion_after_disk_migration(self):
        self.basic_flow()
        vms.live_migrate_vm(self.vm_name)

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


@attr(tier=2)
class TestCase6058(BasicEnvironment):
    """
    Live delete and merge of snapshot while crashing the VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6058
    """
    __test__ = True
    test_case = '6058'
    bz = {'1275836': {'engine': None, 'version': ['3.6']}}

    @polarion("RHEVM3-6058")
    def test_live_merge_with_stop_vm(self):
        self.basic_flow()
        # Creation of 4th disk
        for mount_dir in helpers.MOUNT_POINTS[self.storage]:
            logger.info("Creating file in %s", mount_dir)
            status, output = self.vm_machine.runCmd(
                shlex.split(CMD_CREATE_FILE % (mount_dir, 3))
            )
            if not status:
                logger.error(
                    "Failed to create file test_file_%s under %s on vm %s. "
                    "output:  %s",
                    3, mount_dir, self.vm_name, output
                )

        logger.info("Removing snapshot %s", self.snapshot_list[1])
        assert vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        assert vms.stopVm(True, self.vm_name)
        assert vms.waitForVMState(self.vm_name, config.VM_DOWN)
        assert vms.startVm(True, self.vm_name, wait_for_ip=True)
        snapshot = vms._getVmSnapshot(self.vm_name, self.snapshot_list[1])
        if snapshot is None:
            raise exceptions.SnapshotException("Live merge was expected to "
                                               "fail")
        self.verify_snapshot_files(
            self.snapshot_list[1], [TEST_FILE_TEMPLATE % i for i in xrange(2)]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.check_files_existence([TEST_FILE_TEMPLATE % i for i in xrange(4)])


@attr(tier=2)
class TestCase6062(BasicEnvironment):
    """
    Live delete and merge of snapshot during Live Storage Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6062
    """
    __test__ = True
    test_case = '6062'

    @polarion("RHEVM3-6062")
    def test_live_merge_during_lsm(self):
        self.basic_flow()
        vm_disks = vms.getVmDisks(self.vm_name)
        vm_disk_aliases = [
            disk.get_alias() for disk in vm_disks if not disk.get_bootable()
        ]

        target_sd = disks.get_other_storage_domain(
            vm_disk_aliases[0],  self.vm_name
        )
        vms.live_migrate_vm_disk(
            self.vm_name, vm_disk_aliases[0], target_sd, wait=False
        )

        self.assertTrue(vms.removeSnapshot(
            False, self.vm_name, self.snapshot_list[1], wait=False
        ), "Live merge should fail")
        vms.waitForVmsDisks(self.vm_name)


@attr(tier=2)
class TestCase12216(BasicEnvironment):
    """
    Basic live merge after disk with snapshot is extended

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=12216
    """
    __test__ = True
    test_case = '12216'

    # Bugzilla history:
    # 1232481: Live merge fails after a disk containing a snapshot has
    # been extended
    bz = {'1232481': {'engine': None, 'version': ['3.6']}}

    @polarion("RHEVM3-12216")
    def test_basic_live_merge_after_disk_resize(self):
        self.basic_flow(1)
        vm_disks = vms.getVmDisks(self.vm_name)

        for disk in vm_disks:
            logger.info("Resizing disk %s", disk)
            size_before = disk.get_size()
            new_size = size_before + (1 * config.GB)
            status = vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk.get_alias(),
                provisioned_size=new_size
            )
            self.assertTrue(status, "Failed to resize disk %s to size %s"
                                    % (disk.get_alias(), new_size))
            assert disks.wait_for_disks_status(disk.get_alias())
            disk_obj = disks.getVmDisk(self.vm_name, disk.get_alias())
            assert disk_obj.get_size() == new_size

        self.live_delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[0]
        )
        assert self.check_files_existence([TEST_FILE_TEMPLATE % '0'])
