"""
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Live_Merge
"""
import pytest
import logging
import os
import shlex
from multiprocessing import Process, Queue
from time import sleep
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    hosts as ll_hosts,
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import restart_engine
from rhevmtests.storage.fixtures import (
    create_vm, prepare_disks_with_fs_for_vm, delete_disks,
    wait_for_disks_and_snapshots, init_vm_executor, start_vm
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from rhevmtests.storage.storage_remove_snapshots.fixtures import (
    initialize_params,
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest, testflow
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)

CMD_CREATE_FILE = 'touch %s/test_file_%s'
TEST_FILE_TEMPLATE = 'test_file_%s'
SNAPSHOT_DESCRIPTION_TEMPLATE = 'snapshot_%s_%s_%s'
DD_SIZE = 900 * config.MB
ISCSI = config.STORAGE_TYPE_ISCSI


class BaseTestCase(StorageTest):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    test_case = None
    checksum_files = dict()
    live_merge = None
    vm_wait_for_ip = True

    def create_files_on_vm_disks(self, vm_name, iteration_number):
        """
        Files will be created on vm's disks with name:
        'test_file_<iteration_number>'
        """
        if ll_vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            assert ll_vms.startVm(
                True, self.vm_name, config.VM_UP, wait_for_ip=True
            )
        for idx, mount_dir in enumerate(config.MOUNT_POINTS):
            full_path = os.path.join(
                mount_dir, TEST_FILE_TEMPLATE % iteration_number
            )
            testflow.step("Creating file %s", full_path)

            rc = storage_helpers.create_file_on_vm(
                vm_name, TEST_FILE_TEMPLATE % iteration_number,
                mount_dir, vm_executor=self.vm_executor
            )
            if not rc:
                logger.error(
                    "Failed to create file test_file_%s under %s on vm %s",
                    mount_dir, vm_name
                )
                return False
            if not storage_helpers.write_content_to_file(
                vm_name, full_path, vm_executor=self.vm_executor
            ):
                logger.error(
                    "Failed to write content to file %s on vm %s",
                    full_path, vm_name
                )
            self.checksum_files[full_path] = storage_helpers.checksum_file(
                vm_name, full_path, vm_executor=self.vm_executor
            )
        rc, _, error = self.vm_executor.run_cmd(
            cmd=shlex.split(config.SYNC_CMD)
        )
        assert not rc, "Failed to `sync` after write %s" % error

        return True

    def perform_snapshot_operation(
        self, snapshot_description, wait=True, live=False
    ):
        if not live:
            ll_vms.stop_vms_safely([self.vm_name])
        testflow.step(
            "Adding new snapshot to vm %s", self.vm_name
        )
        status = ll_vms.addSnapshot(
            True, self.vm_name, snapshot_description, wait=wait
        )
        assert status, "Failed to create snapshot %s" % snapshot_description
        if wait:
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], [snapshot_description]
            )
            ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        self.snapshot_list.append(snapshot_description)
        if not live:
            ll_vms.start_vms([self.vm_name])

    def perform_snapshot_with_verification(
        self, snap_description, disks_for_snap
    ):
        cluster = getattr(self, 'cluster_name', config.CLUSTER_NAME)
        data_center = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
        disk_ids = ll_disks.get_disk_ids(disks_for_snap)
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids, cluster_name=cluster, datacenter_name=data_center
        )
        testflow.step("Before snapshot: %s volumes", initial_vol_count)

        self.perform_snapshot_operation(snap_description)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids, cluster_name=cluster, datacenter_name=data_center
        )
        testflow.step("After snapshot: %s volumes", current_vol_count)

        assert current_vol_count == (
            initial_vol_count + len(disk_ids)
        )

    def check_files_existence(self, files, should_exist=True):
        """
        Verifies whether files exist
        """
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        result_list = []
        state = not should_exist
        self.vm_executor = storage_helpers.get_vm_executor(self.vm_name)
        # For each mount point, check if the corresponding file exists
        for mount_dir in config.MOUNT_POINTS:
            for file_name in files:
                full_path = os.path.join(mount_dir, file_name)
                testflow.step("Checking if file %s exists", full_path)
                result = storage_helpers.does_file_exist(
                    self.vm_name, full_path, vm_executor=self.vm_executor
                )
                logger.info(
                    "File %s", 'exists' if result else 'does not exist'
                )
                if result:
                    checksum = storage_helpers.checksum_file(
                        self.vm_name, full_path, vm_executor=self.vm_executor
                    )
                    if checksum != self.checksum_files[full_path]:
                        logger.error(
                            "File exists but it's content changed since it's "
                            "creation!"
                        )
                        result = False
                result_list.append(result)

        if state in result_list:
            return False
        return True

    def verify_snapshot_files(self, snapshot_description, files):
        """
        Verifies whether files exist in snapshot using Preview for the
        verification
        """
        testflow.step(
            "Previewing snapshot %s to validate disk's content",
            snapshot_description
        )
        assert ll_vms.preview_snapshot(
            True, self.vm_name, snapshot_description, True
        ), (
            "Failed to preview snapshot %s. Can't verify files",
            snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
        try:
            logger.info(
                "Verifying files %s on snapshot %s",
                files, snapshot_description
            )
            assert self.check_files_existence(files), (
                "Snapshot verification failed"
            )

        # Make sure to undo the previewed snapshot even if the file
        # verification failed
        finally:
            testflow.step("Undoing snapshot preview")
            status = ll_vms.undo_snapshot_preview(True, self.vm_name, True)
            ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
            assert status, "Undo snapshot failed for VM '%s'" % self.vm_name

    def delete_snapshot_with_verification(
        self, vm_name, snapshot_description, running_io_op=False
    ):

        if self.live_merge and ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
            testflow.step("Starting vm %s", vm_name)
            ll_vms.startVm(True, vm_name, config.VM_UP, wait_for_ip=True)
        snapshot_disks = [
            disk.get_id() for disk in ll_vms.get_snapshot_disks(
                vm_name, snapshot_description
            )
        ]
        initial_vol_count = storage_helpers.get_disks_volume_count(
            snapshot_disks
        )
        testflow.step("Before live merge: %s volumes", initial_vol_count)

        disk_object = ll_vms.getVmDisk(
            vm_name, disk_id=self.disks_to_remove[0]
        )

        def f(q):
            q.put(
                storage_helpers.perform_dd_to_disk(
                    vm_name=vm_name, disk_alias=disk_object.get_alias(),
                    size=DD_SIZE
                )
            )
        if self.live_merge and running_io_op:
            q = Queue()
            p = Process(target=f, args=(q,))
            p.start()
            sleep(5)
        testflow.step(
            "Removing snapshot '%s' of vm %s", snapshot_description, vm_name
        )
        assert ll_vms.removeSnapshot(True, vm_name, snapshot_description), (
            "Failed to live delete snapshot %s" % snapshot_description
        )
        if running_io_op:
            p.join()
            rc, output = q.get()
            assert rc, "dd command failed: %s" % output

        current_vol_count = storage_helpers.get_disks_volume_count(
            snapshot_disks
        )
        testflow.step("After live merge: %s volumes", current_vol_count)

        assert current_vol_count == initial_vol_count - len(snapshot_disks), (
            "Live merge failed - before live merge: %s volumes, "
            "after live merge: %s volumes, snapshot contains %s disks" %
            (initial_vol_count, current_vol_count, len(snapshot_disks))
        )
        logger.info("Snapshot %s was removed", snapshot_description)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])

    def basic_flow(self, snapshot_count=3):
        vm_disks = ll_vms.getVmDisks(self.vm_name)
        disk_names = [disk.get_alias() for disk in vm_disks]
        for idx in xrange(snapshot_count):
            # Create files on all vm's disks before snapshot operation.
            # Files will be named: 'test_file_<idx>'
            testflow.step("Creating files on vm's '%s' disks", self.vm_name)
            assert self.create_files_on_vm_disks(self.vm_name, idx), (
                "Failed to create file"
            )
            snap_description = SNAPSHOT_DESCRIPTION_TEMPLATE % (
                self.test_case, self.storage, idx
            )
            testflow.step("Creating snapshot of vm %s", self.vm_name)
            self.perform_snapshot_with_verification(
                snap_description, disk_names
            )
            ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        if not self.live_merge:
            assert ll_vms.stop_vms_safely([self.vm_name]), (
                "Failed to poweroff VM %s" % self.vm_name
            )


@pytest.mark.usefixtures(
    delete_disks.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__,
    prepare_disks_with_fs_for_vm.__name__,
    initialize_params.__name__,
    wait_for_disks_and_snapshots.__name__,
)
class BasicEnvironment(BaseTestCase):
    __test__ = False


class TestCase6038(BasicEnvironment):
    """
    Basic delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6038
    """
    __test__ = False
    test_case = '6038'

    @polarion("RHEVM3-6038")
    @tier1
    def test_basic_snapshot_deletion(self):
        self.basic_flow()
        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


class TestCase6052(BasicEnvironment):
    """
    Basic delete and merge of snapshots with continuous I/O

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6052
    """
    __test__ = False
    test_case = '6052'

    @polarion("RHEVM3-6052")
    @tier1
    def test_basic_snapshot_deletion_with_io(self):
        self.basic_flow()
        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[0], running_io_op=True
        )


class TestCase16287(BasicEnvironment):
    """
    Basic delete and merge of a single snapshot's disk

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM/workitem?id=RHEVM3-16287
    """
    __test__ = False
    test_case = '16287'

    @polarion("RHEVM3-16287")
    @tier2
    def test_basic_snapshot_deletion_of_snapshots_disk(self):
        self.perform_snapshot_operation(self.snapshot_description)
        snapshot_disks_before = ll_vms.get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        disk_ids_before = [disk.get_id() for disk in snapshot_disks_before]
        vm_disk = ll_vms.getVmDisks(self.vm_name)[-1]
        assert vm_disk.get_id() in disk_ids_before, (
            "Disk %s is not part of the snapshot's disks" % vm_disk.get_alias()
        )
        if not self.live_merge:
            assert ll_vms.stop_vms_safely([self.vm_name])
        assert ll_vms.delete_snapshot_disks(
            self.vm_name, self.snapshot_description, vm_disk.get_id()
        ), "Failed to remove snapshots disk %s" % vm_disk.get_alias()
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        snapshot_disks_after = ll_vms.get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        disk_ids_after = [disk.get_id() for disk in snapshot_disks_after]
        assert vm_disk.get_id() not in disk_ids_after, (
            "Disk %s is part of the snapshot's disks" % vm_disk.get_alias()
        )


class TestCase12215(BasicEnvironment):
    """
    Deleting all snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-12215
    """
    __test__ = False
    test_case = '12215'

    @polarion("RHEVM3-12215")
    @tier3
    def test_snapshot_deletion_of_all_snapshots(self):
        self.basic_flow()

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[0], [TEST_FILE_TEMPLATE % '0']
        )


class TestCase6044(BasicEnvironment):
    """
    Snapshot delete and merge after deleting the base snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6044
    """
    __test__ = False
    test_case = '6044'

    @tier3
    @polarion("RHEVM3-6044")
    def test_snapshot_deletion_base_snapshot(self):
        self.basic_flow()

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[0]
        )
        self.verify_snapshot_files(
            self.snapshot_list[1], [TEST_FILE_TEMPLATE % i for i in xrange(2)]
        )
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        )


class TestCase6045(BasicEnvironment):
    """
    Snapshot snapshot delete and merge with restart of vdsm

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6045
    """
    __test__ = False
    test_case = '6045'

    @polarion("RHEVM3-6045")
    @tier4
    def test_snapshot_deletion_during_vdsm_restart(self):
        host = ll_hosts.get_spm_host(config.HOSTS)
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=host
        )
        self.basic_flow()

        if not self.live_merge:
            assert ll_vms.stop_vms_safely([self.vm_name])
        testflow.step("Removing snapshot %s", self.snapshot_list[1])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        testflow.step("Restarting VDSM")
        assert ll_hosts.kill_vdsmd(host_resource)

        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        )
        assert ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


class TestCase6043(BasicEnvironment):
    """
    Snapshot delete and merge after deleting the last created snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6043
    """
    __test__ = False
    test_case = '6043'

    @polarion("RHEVM3-6043")
    @tier3
    def test_basic_snapshot_deletion(self):
        self.basic_flow()

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[1], [TEST_FILE_TEMPLATE % i for i in xrange(2)]
        )
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        )


class TestCase6046(BasicEnvironment):
    """
    Snapshot delete and merge of snapshot while stopping the engine

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6046
    """
    __test__ = False
    test_case = '6046'

    @polarion("RHEVM3-6046")
    @tier4
    def test_live_deletion_during_engine_restart(self):
        self.basic_flow()

        if not self.live_merge:
            assert ll_vms.stop_vms_safely([self.vm_name])
        testflow.step("Removing snapshot %s", self.snapshot_list[1])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )

        testflow.step("Restarting ovirt-engine")
        restart_engine(config.ENGINE, 10, 75)
        logger.info("ovirt-engine restarted")
        assert ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


class TestCase6048(BasicEnvironment):
    """
    Consecutive delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6048
    """
    __test__ = False
    test_case = '6048'

    @polarion("RHEVM3-6048")
    @tier3
    def test_consecutive_snapshot_deletion_of_snapshots(self):
        self.basic_flow(5)

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[2]
        )
        self.verify_snapshot_files(
            self.snapshot_list[3], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )
        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[3]
        )
        self.verify_snapshot_files(
            self.snapshot_list[4], [TEST_FILE_TEMPLATE % i for i in xrange(5)]
        )


class TestCase6050(BasicEnvironment):
    """
    Delete a 2nd snapshot during a delete and merge of another
    snapshot within the same VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6050
    """
    __test__ = False
    test_case = '6050'

    @polarion("RHEVM3-6050")
    @tier3
    def test_snapshot_merge_during_snapshot_merge(self):
        self.basic_flow()

        if not self.live_merge:
            assert ll_vms.stop_vms_safely([self.vm_name])
        testflow.step("Removing snapshot %s", self.snapshot_list[1])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        assert ll_vms.removeSnapshot(
            False, self.vm_name, self.snapshot_list[2], timeout=-1
        )
        assert ll_vms.wait_for_snapshot_gone(
            self.vm_name, self.snapshot_list[1]
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


class TestCase6057(BasicEnvironment):
    """
    Live delete and merge of snapshot after disk Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6057
    """
    __test__ = False
    test_case = '6057'

    @polarion("RHEVM3-6057")
    @tier2
    def test_live_deletion_after_disk_migration(self):
        self.basic_flow()
        ll_vms.migrate_vm_disks(self.vm_name)

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[1]
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in xrange(3)]
        )


class TestCase6058(BasicEnvironment):
    """
    Live delete and merge of snapshot while crashing the VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6058
    """
    __test__ = False
    test_case = '6058'

    @polarion("RHEVM3-6058")
    @tier2
    def test_live_merge_with_stop_vm(self):
        self.basic_flow()
        # Creation of 4th disk
        for mount_dir in config.MOUNT_POINTS:
            testflow.step("Creating file in %s", mount_dir)
            status = storage_helpers.create_file_on_vm(
                self.vm_name, TEST_FILE_TEMPLATE % 3, mount_dir
            )
            if not status:
                logger.error(
                    "Failed to create file test_file_%s under %s on vm %s",
                    3, mount_dir, self.vm_name
                )

        testflow.step("Removing snapshot %s", self.snapshot_list[1])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        assert ll_vms.stopVm(positive=True, vm=self.vm_name, async='true')
        assert ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )
        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True)


class TestCase6062(BasicEnvironment):
    """
    Live delete and merge of snapshot during Live Storage Migration

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6062
    """
    __test__ = False
    test_case = '6062'
    disk_to_migrate = None

    @polarion("RHEVM3-6062")
    @tier3
    def test_live_merge_during_lsm(self):
        self.basic_flow()
        vm_disks = ll_vms.getVmDisks(self.vm_name)
        vm_disk_aliases = [
            disk.get_alias() for disk in vm_disks if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id())
        ]
        self.disk_to_migrate = vm_disk_aliases[0]
        target_sd = ll_disks.get_other_storage_domain(
            self.disk_to_migrate, self.vm_name
        )
        ll_vms.migrate_vm_disk(
            self.vm_name, self.disk_to_migrate, target_sd, wait=False
        )
        ll_disks.wait_for_disks_status(
            [self.disk_to_migrate], status=config.DISK_LOCKED
        )
        assert ll_vms.removeSnapshot(
            False, self.vm_name, self.snapshot_list[1], wait=False
        ), (
            "Removing snapshot '%s' during a live migration of disk %s was "
            "expected to fail" % (self.snapshot_list[1], self.disk_to_migrate)
        )


class TestCase12216(BasicEnvironment):
    """
    Basic snapshot merge after disk with snapshot is extended

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=12216
    """
    __test__ = False
    test_case = '12216'

    @polarion("RHEVM3-12216")
    @tier2
    def test_basic_snapshot_merge_after_disk_resize(self):
        self.basic_flow(1)
        vm_disks = ll_vms.getVmDisks(self.vm_name)

        for disk in vm_disks:
            testflow.step("Resizing disk %s", disk)
            size_before = disk.get_provisioned_size()
            new_size = size_before + (1 * config.GB)
            status = ll_vms.extend_vm_disk_size(
                True, self.vm_name, disk=disk.get_alias(),
                provisioned_size=new_size
            )
            assert status, "Failed to resize disk %s to size %s" % (
                disk.get_alias(), new_size
            )
            assert ll_disks.wait_for_disks_status(disk.get_alias())
            disk_obj = ll_disks.getVmDisk(self.vm_name, disk.get_alias())
            assert disk_obj.get_provisioned_size() == new_size

        self.delete_snapshot_with_verification(
            self.vm_name, self.snapshot_list[0]
        )
        assert self.check_files_existence([TEST_FILE_TEMPLATE % '0'])
