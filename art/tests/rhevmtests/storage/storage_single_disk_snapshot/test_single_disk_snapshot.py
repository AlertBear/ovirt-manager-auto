"""
3.4 Single disk snapshot
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Single_Snapshot
"""
import os
import pytest
import logging
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
)
from art.rhevm_api.utils import test_utils
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from art.test_handler.tools import polarion

from rhevmtests.storage import config
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    create_vm, poweroff_vm, unblock_connectivity_storage_domain_teardown,
    remove_vms, poweroff_vm_setup, start_vm, undo_snapshot, add_nic,
    initialize_variables_block_domain,
)

from rhevmtests.storage.fixtures import remove_vm  # noqa
from fixtures import add_disks, initialize_test_variables

logger = logging.getLogger(__name__)

ACTIVE_VM = 'Active VM'


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    polarion_test_case = None
    snapshot_desc = None
    disk_count = 4
    vm_wait_for_ip = True
    file_name = 'test_file'
    cmd_create = 'echo "test_txt" > %s/test_file'
    cmd_del = 'rm -f %s/test_file'
    umount_cmd = 'umount %s'

    def check_file_existence_operation(self, should_exist=True,
                                       operation='snapshot'):

        testflow.step("Check if files exist on vm %s", self.vm_name)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        if should_exist:
            assert all(self.get_list_path_exist()), (
                "%s operation failed, files should exist" % operation
            )
        else:
            assert not any(self.get_list_path_exist()), (
                "%s operation failed, files should not exist" % operation
            )

    def get_list_path_exist(self):
        lst = []
        for path in self.mounted_paths:
            full_path = os.path.join(path, self.file_name)
            logger.info("Checking full path %s", full_path)
            result = storage_helpers.does_file_exist(
                self.vm_name, full_path, self.vm_executor
            )
            logger.info("File %s", 'exist' if result else 'not exist')
            lst.append(result)
        return lst

    def delete_operation(self):
        testflow.step("Execute delete operation of files")
        ll_vms.start_vms(
            [self.vm_name], 1, wait_for_status=config.VM_UP, wait_for_ip=True
        )
        for path in self.mounted_paths:
            assert storage_helpers._run_cmd_on_remote_machine(
                self.vm_name, self.cmd_del % path, self.vm_executor
            )
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, config.SYNC_CMD, self.vm_executor
        )
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to shutdown vm %s" % self.vm_name
        )

    def _perform_snapshot_operation(self, disks=None, wait=True, live=False):
        self.snapshot_desc = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        if not live:
            if not ll_vms.get_vm_state(self.vm_name) == config.VM_DOWN:
                assert storage_helpers._run_cmd_on_remote_machine(
                    self.vm_name, config.SYNC_CMD, self.vm_executor
                )
                assert ll_vms.stop_vms_safely([self.vm_name]), (
                    "Failed to shutdown vm %s" % self.vm_name
                )
        if disks:
            snapshot_disks = '%s disks: %s' % (len(disks), disks)
        elif disks is None:
            snapshot_disks = 'all disks'
        elif disks == []:
            snapshot_disks = 'only vm configuration'
        testflow.step(
            "Adding new snapshot to vm %s with %s",
            self.vm_name, snapshot_disks
        )
        status = ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_desc, disks_lst=disks, wait=wait
        )
        assert status, "Failed to create snapshot %s" % self.snapshot_desc
        if wait:
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )

    def _prepare_fs_on_devs(self):
        if not ll_vms.get_vm_state(self.vm_name) == config.VM_UP:
            ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        self.mounted_paths = []

        testflow.step("Creating files for testing on VM %s", self.vm_name)
        for disk_alias in self.disks_names:
            status, mount_path = storage_helpers.create_fs_on_disk(
                self.vm_name, disk_alias
            )
            assert status, "Unable to create fs on disk %s" % disk_alias
            self.mounted_paths.append(mount_path)
            assert storage_helpers._run_cmd_on_remote_machine(
                self.vm_name, self.cmd_create % mount_path, self.vm_executor
            )
        self.check_file_existence_operation(True, 'Writing')
        return True

    def _perform_snapshot_with_verification(self, disks_for_snap, live=False):
        disk_ids = ll_disks.get_disk_ids(disks_for_snap)
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("Before snapshot: %s volumes", initial_vol_count)

        self._perform_snapshot_operation(disks_for_snap, live=live)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("After snapshot: %s volumes", current_vol_count)

        testflow.step(
            "Verifying amount of volumes increased by %s", len(disk_ids)
        )
        assert current_vol_count == initial_vol_count + len(disk_ids), (
            "Current volumes should be %s, not %s" % (
                initial_vol_count + len(disk_ids), current_vol_count
            )
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    poweroff_vm_setup.__name__,
)
class TestCase6022(BasicEnvironment):
    """
    Create snapshot of first disk out of 4 and verify that the
    snapshot was created successfully
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6022'

    @polarion("RHEVM3-6022")
    @tier2
    def test_create_snapshot_of_first_disk(self):
        """
        - Create VM with 4 disks
        - Create snapshot to the VM and pick only one disk from the list of
        disks
        """
        self._perform_snapshot_with_verification(self.disks_names[0:2])


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
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
    cmd_del = 'rm -f %s' % file_name

    @polarion("RHEVM3-6023")
    @tier2
    def test_preview_snapshot(self):
        """
        - Write file on the first disk
        - Create snapshot to all disks
        - Delete the file from the disk
        - Preview the snapshot of the first disk
        """
        testflow.step("Creating files for testing on VM %s", self.vm_name)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, self.cmd_create, self.vm_executor
        ), "Failed to create files for VM %s" % self.vm_name
        self._perform_snapshot_operation()
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, self.cmd_del, self.vm_executor
        ), "Failed to delete files from VM %s" % self.vm_name

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        testflow.step("Custom preview with disks %s", disks_to_preview)

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True,
            disks_lst=disks_to_preview
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )

        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        testflow.step(
            "Check that the file exist after previewing the snapshot"
        )
        assert storage_helpers.does_file_exist(
            self.vm_name, self.file_name, self.vm_executor
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class TestCase6024(BasicEnvironment):
    """
    Preview snapshot of 2 disks out of 4 and verify that the
    snapshot being presented is the correct one
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6024'

    @polarion("RHEVM3-6024")
    @tier3
    def test_create_snapshot_of_first_disk(self):
        """
        - Write some files on first and fourth disks
        - Create snapshot from the first and fourth disks
        - Delete the files that you have written from the first
          and fourth disks
        - Preview the first and fourth snapshots
        """
        assert self._prepare_fs_on_devs()
        disks_for_snap = [self.disks_names[0],
                          self.disks_names[3]]
        testflow.step("Creating snapshot for disks: %s", disks_for_snap)
        self._perform_snapshot_operation(
            disks=disks_for_snap
        )
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], self.snapshot_desc)]

        testflow.step("Previewing the snapshot %s", self.snapshot_desc)
        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True,
            disks_lst=disks_to_preview
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )

        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )

        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        lst = self.get_list_path_exist()
        results = [d for d in lst if d is True]
        assert len(results) == len(disks_for_snap)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class TestCase6026(BasicEnvironment):
    """
    Create snapshot of all vm's disks, preview it and undo the snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6026'

    @polarion("RHEVM3-6026")
    @tier3
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
        assert self._prepare_fs_on_devs()
        self._perform_snapshot_operation()
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        self.delete_operation()

        testflow.step("Previewing the snapshot %s", self.snapshot_desc)
        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )

        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )

        self.check_file_existence_operation(True, 'snapshot')

        testflow.step("Undo the snapshot %s", self.snapshot_desc)
        assert ll_vms.undo_snapshot_preview(
            True, self.vm_name, ensure_vm_down=True
        ), "Failure to undo snapshot on VM %s" % self.vm_name
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )
        self.check_file_existence_operation(False, 'undo')


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class TestCase6007(BasicEnvironment):
    """
    Create snapshot of first disk out of 4, preview it and undo the snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6007'
    file_name = '/root/test_file'
    cmd_create = 'echo "test_txt" > %s' % file_name
    cmd_del = 'rm -f %s' % file_name

    @polarion("RHEVM3-6007")
    @tier3
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
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, self.cmd_create, self.vm_executor
        ), "Files were not deleted"
        disks_for_snap = [self.boot_disk]
        self._perform_snapshot_operation(disks_for_snap)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        ll_vms.start_vms([self.vm_name], 1, config.VM_UP, wait_for_ip=True)
        assert storage_helpers._run_cmd_on_remote_machine(
            self.vm_name, self.cmd_del, self.vm_executor
        )

        disks_to_preview = [(self.boot_disk, self.snapshot_desc),
                            (self.disks_names[0], ACTIVE_VM),
                            (self.disks_names[1], ACTIVE_VM),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True,
            disks_lst=disks_to_preview
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        assert storage_helpers.does_file_exist(
            self.vm_name, self.file_name, self.vm_executor
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    remove_vms.__name__,
)
class TestCase6013(BasicEnvironment):
    """
    Check that the new cloned VM was created only with 1 disk and the
    configuration file of the original VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    # TODO: This case is False until RFE/bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1115440 is solved
    # This has been not tested since we need to integrate the RFE in our code
    __test__ = False
    polarion_test_case = '6013'
    disk_count = 2

    @polarion("RHEVM3-6013")
    @tier2
    def test_clone_vm_from_snapshot(self):
        """
        - Create a VM with 3 disks attached
        - Create a snapshot to the VM, pick only one disk and configuration
        file
        - Clone VM from the snapshot
        """
        assert self._prepare_fs_on_devs()
        self.new_vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self._perform_snapshot_operation(disks=[self.boot_disk])
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        ll_vms.cloneVmFromSnapshot(
            True, self.new_vm_name, config.CLUSTER_NAME, self.vm_name,
            self.snapshot_desc
        )
        self.vm_names.append(self.new_vm_name)
        ll_jobs.wait_for_jobs([config.JOB_CLONE_VM_FROM_SNAPSHOT])


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class TestCase6010(BasicEnvironment):
    """
    Custom preview of vm configuration and 2 disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6010'
    disks_for_custom_preview = 2

    @polarion("RHEVM3-6010")
    @tier2
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
        assert self._prepare_fs_on_devs()
        self._perform_snapshot_operation()

        self.delete_operation()

        disks_to_preview = [(self.boot_disk, ACTIVE_VM),
                            (self.disks_names[0], self.snapshot_desc),
                            (self.disks_names[1], self.snapshot_desc),
                            (self.disks_names[2], ACTIVE_VM),
                            (self.disks_names[3], ACTIVE_VM)]

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True,
            disks_lst=disks_to_preview
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )

        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        lst = self.get_list_path_exist()
        results = [d for d in lst if d is True]
        assert len(results) == self.disks_for_custom_preview


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    poweroff_vm_setup.__name__,
)
class TestCase6014(BasicEnvironment):
    """
    Restart vdsm during snapshot creation, check that snapshot creation
    fails nicely, rollback should be done and the leftover volumes should be
    deleted
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6014'

    @polarion("RHEVM3-6014")
    @tier4
    def test_restart_VDSM_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart vdsm during snapshot creation
        """
        self._perform_snapshot_operation(wait=False)
        self.host = ll_hosts.get_spm_host(config.HOSTS)
        self.host_ip = ll_hosts.get_host_ip(self.host)
        testflow.step("Restarting vdsm on host %s", self.host)
        assert test_utils.restartVdsmd(self.host_ip, config.HOSTS_PW), (
            "Failure to restart vdsm service on host %s" % self.host
        )
        ll_hosts.wait_for_spm(config.DATA_CENTER_NAME, 600, 30)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    poweroff_vm_setup.__name__,
)
class TestCase6006(BasicEnvironment):
    """
    Restart ovirt-engine service during snapshot creation, check that
    snapshot creation fails nicely, rollback should be done and the leftover
    volumes should be deleted
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '6006'

    @polarion("RHEVM3-6006")
    @tier4
    def test_restart_engine_during_snapshot_creation(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Restart ovirt-engine service during snapshot creation
        """
        self._perform_snapshot_operation(wait=False)
        testflow.step("Restarting ovirt-engine")
        test_utils.restart_engine(config.ENGINE, 5, 30)
        hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    add_nic.__name__,
    undo_snapshot.__name__,
    poweroff_vm.__name__,
)
class TestCase16779(BasicEnvironment):
    """
    Create snapshot only from VM configuration.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '16779'
    commit = False

    @polarion("RHEVM-16779")
    @tier2
    def test_create_snapshot_from_vm_configuration(self):
        """
        - Create VM with a disk and 2 NICs
        - Create files on the disk
        - Create snapshot only from VM configuration
        - Delete one of the VM's NICs
        - Restore the snapshot (which includes only the OVF - conf file)
        """
        assert self._prepare_fs_on_devs()
        self._perform_snapshot_operation(disks=[])

        self.delete_operation()
        disks_to_preview = []

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_desc, ensure_vm_down=True,
            disks_lst=disks_to_preview
        ), "Failure to preview snapshot %s from VM %s" % (
            self.snapshot_desc, self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], self.snapshot_desc
        )

        assert ll_vms.commit_snapshot(True, self.vm_name), (
            "Failure to commit VM's %s snapshot" % self.vm_name
        )
        self.commit = True

        assert ll_vms.removeNic(True, self.vm_name, self.nic), (
            "Failure to remove VM's %s nic %s" % (
                self.vm_name, self.nic
            )
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
)
class TestCase14399(BasicEnvironment):
    """
    Create 3 snapshot and delete the second
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_Single_Snapshot
    """
    __test__ = True
    polarion_test_case = '14399'
    snap_1 = 'snapshot_1'
    snap_2 = 'snapshot_2'
    snap_3 = 'snapshot_3'
    snaps = [snap_1, snap_2, snap_3]

    @polarion("RHEVM3-14399")
    @tier3
    def test_delete_second_snapshot_out_of_three(self):
        """
        - Create VM with 4 disks
        - Write file A on disk #2
        - Create snapshot from disk #2
        - Write more files on disk #2 (file B) and create second snapshot
        - Write more files on disk #2 (file C) and create third snapshot
        - Now you have 3 snapshots from disk #2. Delete snapshot #2
        """
        assert self._prepare_fs_on_devs()
        self.cmd_create = 'echo "test_txt" > %s/test_file_%s'
        for index, snap_desc in enumerate(self.snaps):
            testflow.step(
                "Start vm %s and create snapshot %s", self.vm_name, snap_desc
            )
            ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
            for path in self.mounted_paths:
                assert storage_helpers._run_cmd_on_remote_machine(
                    self.vm_name, self.cmd_create % (path, index),
                    self.vm_executor
                )
            assert storage_helpers._run_cmd_on_remote_machine(
                self.vm_name, config.SYNC_CMD, self.vm_executor
            )
            ll_vms.stop_vms_safely([self.vm_name])
            ll_vms.addSnapshot(
                True, self.vm_name, snap_desc,
                disks_lst=[self.disks_names[0]], wait=True
            )

        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        disk_ids = ll_disks.get_disk_ids(self.disks_names)
        initial_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info("The number of volumes is: %s", initial_vol_count)

        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.removeSnapshot(True, self.vm_name, self.snap_1)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        current_vol_count = storage_helpers.get_disks_volume_count(
            disk_ids
        )
        logger.info(
            "The number of volumes after removing one snapshot is: %s",
            current_vol_count
        )

        assert current_vol_count == initial_vol_count - 1, (
            "Current volumes should be %s, not %s" % (
                initial_vol_count - 1, current_vol_count
            )
        )

        self.check_file_existence_operation(True, 'snapshot')


@pytest.mark.usefixtures(
    create_vm.__name__,
    add_disks.__name__,
    start_vm.__name__,
    initialize_test_variables.__name__,
    initialize_variables_block_domain.__name__,
    poweroff_vm_setup.__name__,
    unblock_connectivity_storage_domain_teardown.__name__,
)
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

    @polarion("RHEVM3-6015")
    @tier4
    def test_block_connectivity_to_storage(self):
        """
        - Create a VM with 4 disks and OS installed
        - Create a snapshot to the VM, pick only 2 disks
        - Block connectivity to storage server during snapshot creation
        """
        self._perform_snapshot_operation(self.disks_names[0:2], wait=False)
        assert storage_helpers.setup_iptables(
            self.host_ip, self.storage_domain_ip, block=True
        ), "Failed to block connections from %s to %s" % (
            self.host_ip, self.storage_domain_ip
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        # TODO: cmestreg: doesn't this test needs to check the rollback and
        #                 that the volumes are gone?
