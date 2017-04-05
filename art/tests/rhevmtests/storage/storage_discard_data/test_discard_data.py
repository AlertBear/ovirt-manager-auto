"""
4.1 Feature: storage domain discard data
https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage_4_0/4_1_Storage_Discard_Data_Setting_In_SD
"""
import pytest
import config
import rhevmtests.helpers as rhevm_helpers
from art.test_handler.tools import polarion
from art.unittest_lib import attr
import helpers
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms
)
from rhevmtests.storage.fixtures import (
    create_storage_domain, copy_template_disk, create_lun_on_storage_server
)
from fixtures import (
    add_disks, create_vm_for_test, attach_disks, get_second_storage_domain,
    start_vm_for_test, init_storage_manager
)


@pytest.mark.usefixtures(
    init_storage_manager.__name__,
    create_lun_on_storage_server.__name__,
    create_storage_domain.__name__,
)
class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_FCP])
    index = None

    def perform_delete(self):
        """
        Perform the requested delete verb
        """
        if self.delete_verb == config.DELETE_DISK:
            helpers.delete_disk_flow(self.disk_name, self.vm_name)

        elif self.delete_verb == config.COLD_MOVE:
            helpers.cold_move_flow(
                self.vm_name, self.disk_name, self.second_storage_domain
            )

        elif self.delete_verb == config.LIVE_STORAGE_MIGRATION:
            helpers.live_storage_migration_flow(
                self.vm_name, self.disk_name, self.second_storage_domain
            )

        elif self.delete_verb == config.LIVE_MERGE:
            helpers.live_merge_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

        elif self.delete_verb == config.COLD_MERGE:
            helpers.cold_merge_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

        elif self.delete_verb == config.COLD_MERGE_WITH_MEMORY:
            helpers.cold_merge_with_memory_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

        elif self.delete_verb == config.RESTORE_SNAPSHOT:
            helpers.restore_snapshot_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

        elif self.delete_verb == config.PREVIEW_UNDO_SNAPSHOT:
            helpers.undo_previewed_snapshot_flow(
                self.vm_name, self.disk_name, self.storage_manager,
                self.new_lun_id
            )

        elif self.delete_verb == config.RESTORE_SNAPSHOT_WITH_MEMORY:
            helpers.restore_snapshot_with_memory_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

        elif self.delete_verb == config.REMOVE_SNAPSHOT_SINGLE_DISK:
            helpers.remove_snspshot_single_disk_flow(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )

    def discard_basic_flow(self):
        """
        Check discard data basic flow
        """
        testflow.step(
            "Checking discard with %s as the delete verb", self.delete_verb
        )

        # Starting the VM in case it's down
        if ll_vms.get_vm_state(self.vm_name) != config.VM_UP:
            testflow.setup("Starting VM %s", self.vm_name)
            assert ll_vms.startVm(True, self.vm_name, config.VM_UP), (
                "Failed to start VM %s" % self.vm_name
            )

        # Fill the disk with dd, won't be done here for snapshots flows
        if self.delete_verb not in config.SNAPSHOT_FLOWS:

            # Write to the disk and verify LUN used space is claimed
            helpers.write_to_disk_and_verify_size_claim(
                self.vm_name, self.disk_name, self.new_storage_domain,
                self.storage_manager, self.new_lun_id
            )
            config.USED_SIZE_BEFORE_DELETE = rhevm_helpers.get_lun_actual_size(
                self.storage_manager, self.new_lun_id
            )
            testflow.step(
                "LUN used size before delete operation is %s",
                config.USED_SIZE_BEFORE_DELETE
            )

        # Perform the specified delete verb
        self.perform_delete()
        ll_vms.wait_for_disks_status(self.disk_names)

        # Check storage domain's LUN used size after deletion
        lun_used_size_after_deletion = rhevm_helpers.get_lun_actual_size(
            self.storage_manager, self.new_lun_id
        )
        assert lun_used_size_after_deletion, (
            "Couldn't get storage domain %s volume used size" % (
                self.new_storage_domain
            )
        )
        testflow.step(
            "LUN used size after %s is %s", self.delete_verb,
            lun_used_size_after_deletion
        )
        assert lun_used_size_after_deletion < config.USED_SIZE_BEFORE_DELETE, (
            "SD LUN size hasn't been reclaimed upon %s" % self.delete_verb
        )
        config.USED_SIZE_BEFORE_DELETE = None


@pytest.mark.usefixtures(
    copy_template_disk.__name__,
    create_vm_for_test.__name__,
    start_vm_for_test.__name__,
    add_disks.__name__,
    attach_disks.__name__,
)
class BaseDelete(BaseTestCase):
    """
    Basic class for various delete verbs
    """
    __test__ = False
    create_domain_kwargs = {'discard_after_delete': True}
    template = config.TEMPLATE_NAME[0]
    delete_verb = None
    disk_name = None

    def discard_both_allocation_policies(self):
        self.disk_name = self.disk_names[0]
        self.discard_basic_flow()
        self.disk_name = self.disk_names[1]
        self.discard_basic_flow()

    def discard_snapshot_flows(self):
        self.disk_name = self.disk_names[0]
        self.discard_basic_flow()


class TestCase19569(BaseTestCase):
    """
    RHEVM-19569 Update storage domain with discard to true
    """
    __test__ = True

    @polarion("RHEVM3-19569")
    @attr(tier=1)
    def test_update_discard_flag_on_storage_domain(self):
        """
        Checking update discard_after_delete flag from false to true
        """
        # Verify that the domain discard_after_delete flag is set to False
        testflow.step(
            "Checking discard flag for domain %s", self.new_storage_domain
        )
        assert not ll_sd.get_discard_after_delete(self.new_storage_domain), (
            "Discard flag should be set to false if not specified in storage "
            "domain creation"
        )

        # Change discard_after_delete flag to true
        testflow.step(
            "Updating storage domain %s discard_after_delete to true",
            self.new_storage_domain
        )
        assert ll_sd.updateStorageDomain(
            True, self.new_storage_domain, discard_after_delete=True,
            storage_type=self.storage
        ), "Error editing storage domain %s" % self.new_storage_domain


@pytest.mark.usefixtures(
    get_second_storage_domain.__name__
)
class DiscardVariousDeleteVerbs(BaseDelete):
    """
    Test class contains several test cases of various delete verbs for discard
    after delete validation
    """
    # TODO:
    # Due storage server issues (XtremIO LUN mapping failures and Netapp not
    # reclaiming LUN used space upon deletion), all the cases in this class
    # won't be tested until issues are fixed
    __test__ = False

    @polarion("RHEVM3-17273")
    @attr(tier=1)
    def test_discard_data_after_delete_disk(self):
        """
        RHEVM-17273 Discard data after disk deletion
        Checking basic flow with delete disk as delete verb
        """
        self.delete_verb = config.DELETE_DISK
        self.discard_both_allocation_policies()

    @polarion("RHEVM3-17572")
    @attr(tier=1)
    def test_discard_data_after_live_merge(self):
        """
        RHEVM-17572 Discard data after live merge of snapshot
        Checking basic flow with live merge as delete verb
        """
        self.delete_verb = config.LIVE_MERGE
        self.discard_snapshot_flows()

    @polarion("RHEVM3-17573")
    @attr(tier=1)
    def test_discard_data_after_cold_merge(self):
        """
        RHEVM-17573 Discard data after cold merge of snapshot
        Checking basic flow with cold merge as delete verb
        """
        self.delete_verb = config.COLD_MERGE
        self.discard_snapshot_flows()

    @polarion("RHEVM3-17574")
    @attr(tier=1)
    def test_discard_data_after_merge_with_memory(self):
        """
        RHEVM-17574 Discard data after deletion of snapshot with memory
        Checking basic flow with snapshot merge with memory as delete verb
        """
        self.delete_verb = config.COLD_MERGE_WITH_MEMORY
        self.discard_snapshot_flows()

    @polarion("RHEVM3-17575")
    @attr(tier=1)
    def test_discard_data_after_restore_snapshot(self):
        """
        RHEVM-17575 Discard data after preview and commit of snapshot
        Checking basic flow with snapshot restore as delete verb
        """
        self.delete_verb = config.RESTORE_SNAPSHOT
        self.discard_snapshot_flows()

    @polarion("RHEVM3-17576")
    @attr(tier=1)
    def test_discard_data_after_snapshot_preview_and_undo(self):
        """
        Checking basic flow with snapshot preview and undo as delete verb
        RHEVM-17576 Discard data after preview and undo of snapshot
        """
        self.delete_verb = config.PREVIEW_UNDO_SNAPSHOT
        self.discard_snapshot_flows()

    @polarion("RHEVM3-19397")
    @attr(tier=1)
    def test_discard_data_after_restore_snapshot_with_memory(self):
        """
        Checking basic flow with restore snapshot with memory delete verb
        RHEVM-19397 Discard data after restore snapshot with memory
        """
        self.delete_verb = config.RESTORE_SNAPSHOT_WITH_MEMORY
        self.discard_snapshot_flows()

    @polarion("RHEVM3-19398")
    @attr(tier=1)
    def test_discard_data_after_remove_snapshot_single_disk(self):
        """
        Checking basic flow with remove snapshot single disk delete verb
        RHEVM-19398 Discard data after remove snapshot single disk
        """
        self.delete_verb = config.REMOVE_SNAPSHOT_SINGLE_DISK
        self.discard_snapshot_flows()

    @polarion("RHEVM3-17571")
    @attr(tier=1)
    def test_discard_data_after_cold_move(self):
        """
        RHEVM-17571 Discard data after move disk on VM that is down
        Checking basic flow with cold move as delete verb
        """
        self.delete_verb = config.COLD_MOVE
        self.discard_both_allocation_policies()

    @polarion("RHEVM3-19396")
    @attr(tier=1)
    def test_discard_data_after_live_storage_migration(self):
        """
        Checking basic flow with live storage migration delete verb
        RHEVM-19397 Discard data after live storage migration
        """
        self.delete_verb = config.LIVE_STORAGE_MIGRATION
        self.discard_both_allocation_policies()
