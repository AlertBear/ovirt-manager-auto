"""
Clone Vm From Snapshot
"""
import config
import logging
from art.unittest_lib.common import attr, StorageTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
import rhevmtests.storage.helpers as helpers

logger = logging.getLogger(__name__)

# DON'T REMOVE THIS, larger disk size are needed when cloning multiple
# disks since new snapshots will be bigger than the minimum size
DISK_SIZE = 3 * config.GB


# TODO: If the test fails with error = low level Image copy failed, code = 261
# re-open https://bugzilla.redhat.com/show_bug.cgi?id=1201268 and uncomment:
# @attr(config.DO_NOT_RUN)
class BaseTestCase(TestCase):
    """
    Base Test Case for clone snapshot
    """
    snapshot = "snapshot_%s"
    __test__ = False
    # Disable cli, check ticket RHEVM-2238
    jira = {'RHEVM-2238': None}

    def setUp(self):
        """
        Get all the storage domains available.
        """
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)
        self.storage_domain_0 = self.storage_domains[0]
        self.storage_domain_1 = self.storage_domains[1]
        self.vm = config.VM_NAME % self.storage

    def add_disk(self, disk_alias):
        """
        Add disk with alias 'disk_alias' to vm
        """
        assert ll_disks.addDisk(
            True, alias=disk_alias, provisioned_size=DISK_SIZE,
            storagedomain=self.storage_domain_0,
            sparse=False, interface=config.VIRTIO_SCSI,
            format=config.RAW_DISK
        )

        assert ll_disks.wait_for_disks_status(disks=[disk_alias])
        assert ll_disks.attachDisk(True, disk_alias, self.vm)
        assert ll_disks.wait_for_disks_status(disks=[disk_alias])
        assert ll_vms.waitForVmDiskStatus(
            self.vm, True, diskAlias=disk_alias, sleep=1)

    def tearDown(self):
        """
        Remove the cloned vm
        """
        ll_vms.safely_remove_vms([self.cloned_vm])


@attr(tier=1)
class TestCase6103(BaseTestCase):
    """
    Clone a vm from snapshot.
    verify: 1. VM is successfully created
            2. VM's info is cloned from original VM.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6103"
    cloned_vm = "vm_%s" % polarion_case_id

    @polarion("RHEVM3-6103")
    def test_clone_vm_from_snapshot(self):
        """
        Test that Clone from a vm snapshot works.
        """
        logger.info("Creating vm %s from snapshot %s", self.cloned_vm,
                    config.SNAPSHOT_NAME)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm, state=config.VM_DOWN)


@attr(tier=2)
class TestCase6119(BaseTestCase):
    """
    Create a VM from snapshot for a DC with multiple storage domains
    verify: storage domain destination can be selected.
            volume type can be selected
            format can be selected
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6119"
    cloned_vm = "vm_%s" % polarion_case_id

    @polarion("RHEVM3-6119")
    def test_clone_vm_from_snapshot_select_storage(self):
        """
        Test the sd, type and format can be selected
        """
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, sparse=False,
            vol_format=config.RAW_DISK, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm, state=config.VM_DOWN)


@attr(tier=2)
class TestCase6120(BaseTestCase):
    """
    Create VM from snapshot while original VM is Down    ->  Success
    Create VM from snapshot while original VM is Up      ->  Success

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    polarion_case_id = "6120"
    cloned_vm_up = "vm_up_%s" % polarion_case_id
    cloned_vm_down = "vm_down_%s" % polarion_case_id
    temp_name = 'test_template'
    __test__ = True

    @polarion("RHEVM3-6120")
    def test_clone_vm_from_snapshot_vm_status(self):
        """
        Try to clone vm's snapshot from different states
        """
        ll_vms.stop_vms_safely([self.vm])
        assert ll_vms.waitForVMState(self.vm, config.VM_DOWN)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_down, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm_down, state=config.VM_DOWN)

        assert ll_vms.startVm(True, self.vm)
        ll_vms.waitForVMState(self.vm)
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_up, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm_up, state=config.VM_DOWN)

        assert ll_vms.stopVm(True, self.vm)
        ll_vms.waitForVMState(self.vm, config.VM_DOWN)

    def tearDown(self):
        """
        Remove created vms and make sure the original vm is unlocked
        """
        ll_vms.safely_remove_vms([self.cloned_vm_down, self.cloned_vm_up])


@attr(tier=2)
class TestCase6122(BaseTestCase):
    """
    Clone vm from snapshot:
    Verify that name can be chosen, that no illegal characters can be entered,
    and that duplicate name can't be entered.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6122"
    cloned_vm = "vm_%s" % polarion_case_id

    @polarion("RHEVM3-6122")
    def test_clone_vm_name_validation(self):
        """
        Test for vm name property and duplicity
        """
        assert ll_vms.searchForVm(False, 'name', self.cloned_vm, 'name')

        logger.info("Creating vm %s from snapshot %s", self.cloned_vm,
                    self.snapshot)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.searchForVm(True, 'name', self.cloned_vm, 'name')

        logger.info("Trying to clone a vm's snapshot with the same name")

        assert ll_vms.cloneVmFromSnapshot(
            False, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        logger.info("Trying to clone a vm's snapshot with invalid characters")
        illegal_characters = "* are not allowed"

        assert ll_vms.cloneVmFromSnapshot(
            False, name=illegal_characters, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)


@attr(tier=2)
class TestCase6108(BaseTestCase):
    """
    Clone a vm with multiple nics.
    Verify the clone is successful and all nics are cloned.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6108"
    cloned_vm = "vm_%s" % polarion_case_id
    snapshot_two_nics = "snapshot with two nics"

    @polarion("RHEVM3-6108")
    def test_clone_vm_multiple_nics(self):
        """
        Add a new nic to the self.vm, make a snapshot and clone it.
        """
        logger.info("Adding nic to %s", self.vm)
        assert ll_vms.addNic(
            True, self.vm, name="nic2", network=config.MGMT_BRIDGE,
            interface=config.NIC_TYPE_VIRTIO
        )

        self.assertEqual(
            len(ll_vms.get_vm_nics_obj(self.vm)), 2,
            "VM %s should have 2 nics" % self.vm
        )

        logger.info("Making a snapshot %s from %s",
                    self.snapshot_two_nics, self.vm)

        assert ll_vms.addSnapshot(True, self.vm, self.snapshot_two_nics)

        logger.info("Cloning vm %s", self.vm)
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=self.snapshot_two_nics,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm, state=config.VM_DOWN)

        self.assertEqual(len(ll_vms.get_vm_nics_obj(self.cloned_vm)), 2)

    def tearDown(self):
        """
        * Removing created nic and the cloned vm
        """
        ll_vms.stop_vms_safely([self.cloned_vm, self.vm])
        ll_vms.removeNic(True, self.vm, "nic2")
        ll_vms.removeSnapshot(True, self.vm, self.snapshot_two_nics)
        super(TestCase6108, self).tearDown()


@attr(tier=2)
class TestCase6109(BaseTestCase):
    """
    Clone a vm with multiple disks.
    Verify the clone is successful and all disks are cloned.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6109"
    cloned_vm = "cloned_vm_%s" % polarion_case_id
    snapshot_two_disks = "snapshot_%s" % polarion_case_id
    disk_alias = "second_disk_%s" % polarion_case_id

    @polarion("RHEVM3-6109")
    def test_clone_vm_multiple_disks(self):
        """
        Verify the cloned vm contains multiple disks
        """
        logger.info("Adding disk to vm %s", self.vm)
        assert 1 == len(ll_vms.getVmDisks(self.vm))
        self.add_disk(self.disk_alias)

        logger.info("Making a snapshot %s from %s",
                    self.snapshot_two_disks, self.vm)

        assert ll_vms.addSnapshot(True, self.vm, self.snapshot_two_disks)

        logger.info("Cloning vm %s", self.vm)
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=self.snapshot_two_disks,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm, state=config.VM_DOWN)
        self.assertEqual(len(ll_vms.getVmDisks(self.cloned_vm)), 2)

    def tearDown(self):
        """
        Remove created disk and cloned vm
        """
        ll_vms.stop_vms_safely([self.vm])
        ll_vms.removeSnapshot(True, self.vm, self.snapshot_two_disks)
        ll_vms.wait_for_vm_snapshots(self.vm, [config.SNAPSHOT_OK])
        ll_vms.removeDisk(True, self.vm, self.disk_alias)
        ll_jobs.wait_for_jobs([config.ENUMS['job_remove_disk']])
        super(TestCase6109, self).tearDown()


@attr(tier=2)
class TestCase6111(BaseTestCase):
    """
    Clone a desktop and a server VM.
    Verify that clone is successful and is the proper type.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    polarion_case_id = "6111"
    __test__ = True
    cloned_vm_desktop = "cloned_desktop_%s" % polarion_case_id

    vm_server = "vm_server_%s" % polarion_case_id
    snapshot_server = "snapshot_server_%s" % polarion_case_id
    cloned_vm_server = "cloned_server_%s" % polarion_case_id

    def setUp(self):
        """
        Create a server type vm
        """
        super(TestCase6111, self).setUp()
        helpers.create_vm_or_clone(
            True, self.vm_server, diskInterface=config.VIRTIO_SCSI,
            type=config.VM_TYPE_SERVER, installation=False
        )
        ll_vms.addSnapshot(True, self.vm_server, self.snapshot_server)

    @polarion("RHEVM3-6111")
    def test_clone_vm_type_desktop_server(self):
        """
        Verify that desktop and server types are preserved after cloning
       """
        # Base vm should be type desktop
        assert config.VM_TYPE_DESKTOP == ll_vms.get_vm(self.vm).get_type()
        logger.info("Cloning vm %s", self.vm)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_desktop, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=config.SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False)

        assert config.VM_TYPE_DESKTOP == \
            ll_vms.get_vm(self.cloned_vm_desktop).get_type()

        assert config.VM_TYPE_SERVER == ll_vms.get_vm(
            self.vm_server
        ).get_type()
        logger.info("Cloning vm %s", self.vm_server)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_server, cluster=config.CLUSTER_NAME,
            vm=self.vm_server, snapshot=self.snapshot_server,
            storagedomain=self.storage_domain_1, compare=False)

        assert config.VM_TYPE_SERVER == \
            ll_vms.get_vm(self.cloned_vm_server).get_type()

    def tearDown(self):
        """
        Remove created vms
        """
        ll_vms.safely_remove_vms(
            [self.cloned_vm_desktop, self.cloned_vm_server, self.vm_server]
        )


@attr(tier=2)
class TestCase6112(BaseTestCase):
    """
    Make a snapshot of a vm with three disks.
    Remove one of the disks.
    Verify the snapshot clone success, and only has 2 disk.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6112"

    def setUp(self):
        super(TestCase6112, self).setUp()
        self.cloned_vm = "cloned_vm_%s_%s" % (
            self.polarion_case_id, self.storage
        )
        self.disk_alias = "second_disk_%s_%s" % (
            self.polarion_case_id, self.storage
        )
        self.disk_alias2 = "third_disk_%s_%s" % (
            self.polarion_case_id, self.storage
        )
        self.snapshot_multiple_disks = "snapshot_%s" % self.polarion_case_id

    @polarion("RHEVM3-6112")
    def test_clone_vm_after_deleting_disk(self):
        """
        Test only existing disks are cloned even if it were snapshoted.
        """
        assert 1 == len(ll_vms.getVmDisks(self.vm))
        self.add_disk(self.disk_alias)
        self.add_disk(self.disk_alias2)
        assert 3 == len(ll_vms.getVmDisks(self.vm))
        self.disk_obj = ll_disks.get_disk_obj(self.disk_alias)
        self.disk_obj_2 = ll_disks.get_disk_obj(self.disk_alias2)

        logger.info("Making a snapshot %s from %s",
                    self.snapshot_multiple_disks, self.vm)
        assert ll_vms.addSnapshot(True, self.vm, self.snapshot_multiple_disks)
        logger.info("Removing disk %s", self.disk_alias)
        ll_vms.delete_snapshot_disks(
            self.vm, self.snapshot_multiple_disks, self.disk_obj.get_id()
        )
        ll_jobs.wait_for_jobs([config.ENUMS['job_remove_snapshots_disk']])

        logger.info("Cloning vm %s", self.vm)
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm, snapshot=self.snapshot_multiple_disks,
            storagedomain=self.storage_domain_1, compare=False)

        assert ll_vms.waitForVMState(self.cloned_vm, state=config.VM_DOWN)

        cloned_disks = ll_vms.getVmDisks(self.cloned_vm)
        disks = [disk.name for disk in cloned_disks]
        self.assertEqual(len(disks), 2)
        self.assertTrue(self.disk_alias2 in disks)
        self.assertFalse(self.disk_alias in disks)

    def tearDown(self):
        """
        Remove vm, disk and snapshot
        """
        if not ll_vms.safely_remove_vms([self.cloned_vm]):
            logger.error(
                "Failed to power off and remove vm %s", self.cloned_vm
            )
            BaseTestCase.test_failed = True
        if not ll_vms.delete_snapshot_disks(
            self.vm, self.snapshot_multiple_disks, self.disk_obj.get_id()
        ):
            logger.error(
                "Failed to remove snapshot's disk %s belonging to vm %s",
                self.disk_obj.get_id(), self.vm
            )
            BaseTestCase.test_failed = True
        if not ll_vms.delete_snapshot_disks(
            self.vm, self.snapshot_multiple_disks, self.disk_obj_2.get_id()
        ):
            logger.error(
                "Failed to remove snapshot's disk %s belonging to vm %s",
                self.disk_obj_2.get_id(), self.vm
            )
            BaseTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOTS_DISK])
        if not ll_vms.removeSnapshot(
            True, self.vm, self.snapshot_multiple_disks
        ):
            logger.error(
                "Failed to remove snapshot %s belonging to vm %s",
                self.snapshot_multiple_disks, self.cloned_vm
            )
            BaseTestCase.test_failed = True
        ll_vms.wait_for_vm_snapshots(self.vm, config.SNAPSHOT_OK)
        if not ll_vms.removeDisk(True, self.vm, self.disk_alias):
            logger.error(
                "Failed to remove disk %s", self.disk_alias
            )
            BaseTestCase.test_failed = True
        if not ll_vms.removeDisk(True, self.vm, self.disk_alias2):
            logger.error(
                "Failed to remove disk %s", self.disk_alias2
            )
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()
