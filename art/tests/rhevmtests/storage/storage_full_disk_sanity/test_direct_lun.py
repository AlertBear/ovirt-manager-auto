"""
Test Direct Lun Sanity

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Storage/
3_1_Storage_Direct_Lun_General
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level.hosts import getHostIP
from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib.common import StorageTest as TestCase
from art.unittest_lib import attr
from utilities.machine import Machine, LINUX

from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, attachDisk, detachDisk, deleteDisk, get_other_storage_domain,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, getVmDisks, startVm, suspendVm,
    runVmOnce, addSnapshot, updateVm, removeSnapshot,
    get_snapshot_disks, moveVm, removeVm, getVmHost,
    get_vms_disks_storage_domain_name, wait_for_vm_snapshots,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
import rhevmtests.storage.helpers as helpers

from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

BASE_KWARGS = {
    "interface": config.VIRTIO_SCSI,
    "alias": "direct_lun_disk",
    "format": config.COW_DISK,
    "size": config.DISK_SIZE,
    "bootable": False,
    "type_": config.STORAGE_TYPE,
}
ISCSI = config.STORAGE_TYPE_ISCSI
ENUMS = config.ENUMS


def setup_module():
    """Set up the proper BASE args"""
    if hasattr(config, 'EXTEND_LUN_ADDRESS'):
        BASE_KWARGS.update({
            "lun_address": config.EXTEND_LUN_ADDRESS[0],
            "lun_target": config.EXTEND_LUN_TARGET[0],
            "lun_id": config.EXTEND_LUN[0],
        })


class DirectLunAttachTestCase(TestCase):
    """
    Base class for Direct Lun tests
    """
    # This tests are only desing to run on ISCSI
    # TODO: Enable for FC when our environment is stable
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    vm_name = None
    polarion_test_case = ""
    bz = {'1220824': {'engine': None, 'version': ['3.6']}}

    def setUp(self):
        """
        Build disk's parameters
        """
        self.vm_name = config.VM1_NAME % self.storage
        BASE_KWARGS.update({'type_': self.storage})
        self.disk_alias = "direct_lun_%s" % self.polarion_test_case

        self.storage_domains = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)

        self.vm_storage_domain = get_vms_disks_storage_domain_name(
            self.vm_name)
        self.lun_kwargs = BASE_KWARGS.copy()
        self.lun_kwargs["alias"] = self.disk_alias

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

    def attach_disk_to_vm(self):
        """
        Attach the lun to the VM
        """
        logger.info("Adding new disk (direct lun) %s", self.disk_alias)
        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

        logger.info("Attaching disk %s to vm %s", self.disk_alias,
                    self.vm_name)
        status = attachDisk(True, self.disk_alias, self.vm_name,
                            active=True)
        self.assertTrue(status, "Failed to attach direct lun to vm")
        assert self.disk_alias in (
            [d.get_alias() for d in getVmDisks(self.vm_name)]
        )

    def detach_and_delete_disk_from_vm(self, disk_alias):
        logger.info("Wait in case an disks are not ready")

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

        logger.info("Detaching disk %s from vm %s", disk_alias,
                    self.vm_name)
        try:
            detachDisk(True, disk_alias, self.vm_name)
        except EntityNotFound:
            logger.error("Disk %s was not found attached to %s", disk_alias,
                         self.vm_name)

        logger.info("Deleting disk %s", disk_alias)
        assert deleteDisk(True, disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])

    def tearDown(self):
        """
        Removed disks
        """
        self.detach_and_delete_disk_from_vm(self.disk_alias)


@attr(tier=2)
class TestCase5927(DirectLunAttachTestCase):
    """
    Attach a lun when vm is running
    """
    polarion_test_case = "5927"

    def setUp(self):
        """
        Start the vm
        """
        super(TestCase5927, self).setUp()
        assert startVm(True, self.vm_name, config.VM_UP)

    @polarion("RHEVM3-5927")
    def test_attach_lun_vm_running(self):
        """
        Attach the lun when vm is up
        """
        self.attach_disk_to_vm()


@attr(tier=2)
class TestCase5920(DirectLunAttachTestCase):
    """
    Suspend vm with direct lun attached
    """
    polarion_test_case = "5920"

    @polarion("RHEVM3-5920")
    def test_suspend_vm(self):
        """
        attach direct lun and suspend vm
        """
        self.attach_disk_to_vm()
        startVm(True, self.vm_name, config.VM_UP)
        assert suspendVm(True, self.vm_name)

    def tearDown(self):
        """
        Remove disk
        """
        assert startVm(True, self.vm_name)
        waitForVMState(self.vm_name)
        super(TestCase5920, self).tearDown()


@attr(tier=2)
class TestCase5930(DirectLunAttachTestCase):
    """
    Add more then one direct lun to the same vm
    """
    polarion_test_case = "5930"
    disk_to_add = 'disk_%s'

    def setUp(self):
        super(TestCase5930, self).setUp()
        self.disk_to_add = 'disk_2_%s' % self.polarion_test_case

    @polarion("RHEVM3-5930")
    def test_more_then_one_direct_lun(self):
        """
        Adds and attach two different direct luns to the same vm
        """
        self.attach_disk_to_vm()

        disk_alias = self.disk_alias
        self.disk_alias = self.disk_to_add

        self.lun_kwargs['alias'] = self.disk_to_add
        self.lun_kwargs['lun_address'] = config.EXTEND_LUN_ADDRESS[1]
        self.lun_kwargs['lun_target'] = config.EXTEND_LUN_TARGET[1]
        self.lun_kwargs['lun_id'] = config.EXTEND_LUN[1]

        self.attach_disk_to_vm()
        self.disk_alias = disk_alias

    def tearDown(self):
        """
        Remove disks
        """
        super(TestCase5930, self).tearDown()
        self.detach_and_delete_disk_from_vm(self.disk_to_add)


@attr(tier=2)
class TestCase5931(DirectLunAttachTestCase):
    """
    Attach lun vm, create a template and verify the direct lun will not be
    part of the template
    """
    # TODO: verify template's disks
    polarion_test_case = "5931"
    template_name = "template_%s" % polarion_test_case
    temp_created = False

    @polarion("RHEVM3-5931")
    def test_create_template_from_vm_with_lun(self):
        """
        Create template from vm with direct lun attached
        """
        self.attach_disk_to_vm()
        self.temp_created = createTemplate(True, vm=self.vm_name,
                                           name=self.template_name,
                                           cluster=config.CLUSTER_NAME)

        assert self.temp_created

    def tearDown(self):
        if self.temp_created:
            stop_vms_safely([self.vm_name])
            waitForVMState(self.vm_name, config.VM_DOWN)
            logger.info("Removing template %s", self.template_name)
            assert removeTemplate(True, self.template_name)
            wait_for_jobs([ENUMS['job_remove_vm_template']])
        super(TestCase5931, self).tearDown()


@attr(tier=2)
class TestCase5932(DirectLunAttachTestCase):
    """
    attach lun to vm, run vm as stateless and create snapshot.
    snapshot should not be created
    """
    polarion_test_case = "5932"
    snap_desc = "snapshot_name_%s" % polarion_test_case
    snap_added = False

    @polarion("RHEVM3-5932")
    def test_create_snapshot_from_stateless_vm(self):
        """
        """
        self.attach_disk_to_vm()
        assert runVmOnce(True, self.vm_name, stateless=True)
        waitForVMState(self.vm_name)
        self.snap_added = addSnapshot(False, self.vm_name, self.snap_desc)
        assert self.snap_added

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        if not waitForVMState(self.vm_name, config.VM_DOWN):
            raise exceptions.VMException(
                "Failed to stop vm %s" % self.vm_name
            )

        # after stopping vm that runs in stateless mode a temporary snapshot
        # is deleted and the ACTIVE_VM volume is locked for few seconds
        wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_OK, [self.snap_desc],
        )
        if not self.snap_added:
            logger.info("Removing snapshot %s", self.snap_desc)
            assert removeSnapshot(True, self.vm_name, self.snap_desc)

        super(TestCase5932, self).tearDown()


@attr(tier=2)
class TestCase5933(DirectLunAttachTestCase):
    """
    Attach lun to vm and verify the direct lun will not be
    part of the snapshot
    """
    polarion_test_case = "5933"
    snap_desc = "snapshot_name_%s" % polarion_test_case
    snap_added = False

    @polarion("RHEVM3-5933")
    def test_create_snapshot_from_vm_with_lun(self):
        """
        Create snapshot with direct lun
        """
        self.attach_disk_to_vm()

        logger.info("Create new snapshot %s", self.snap_desc)
        self.snap_added = addSnapshot(True, self.vm_name, self.snap_desc)
        assert self.snap_added
        wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_OK, [self.snap_desc],
        )

        snap_disks = get_snapshot_disks(self.vm_name, self.snap_desc)

        if self.disk_alias in snap_disks:
            raise exceptions.SnapshotException(
                "direct lun %s is part of thr snapshot %s"
                % (self.disk_alias, self.snap_desc))

    def tearDown(self):
        if self.snap_added:
            stop_vms_safely([self.vm_name])
            waitForVMState(self.vm_name, config.VM_DOWN)
            logger.info("Removing snapshot %s", self.snap_desc)
            assert removeSnapshot(True, self.vm_name, self.snap_desc)
        super(TestCase5933, self).tearDown()


@attr(tier=4)
class TestCase5934(DirectLunAttachTestCase):
    """
    HA vm with direct lun
    """
    polarion_test_case = "5934"

    @polarion("RHEVM3-5934")
    def test_ha_vm_with_direct_lun(self):
        """
        * Run vm with direct lun in HA mode
        * kill qemu precess
        """
        self.attach_disk_to_vm()
        assert updateVm(True, self.vm_name, highly_available='true')
        startVm(True, self.vm_name)

        _, host = getVmHost(self.vm_name)
        host_ip = getHostIP(host['vmHoster'])
        host_machine = Machine(
            host_ip, config.HOSTS_USER, config.HOSTS_PW).util(LINUX)

        assert host_machine.kill_qemu_process(self.vm_name)

        assert waitForVMState(self.vm_name)

    def tearDown(self):
        waitForVMState(self.vm_name)
        assert updateVm(True, self.vm_name, highly_available='false')
        super(TestCase5934, self).tearDown()


@attr(tier=2)
class TestCase5937(DirectLunAttachTestCase):
    """
    direct lun and disk interface
    """
    # TODO: Why? IDE disk cannot be hot plugged - fix whole test
    __test__ = False
    polarion_test_case = "5937"

    @polarion("RHEVM3-5937")
    def test_direct_lun_interface_ide(self):
        """
        Create direct lun - interface ide
        """
        self.lun_kwargs['interface'] = config.INTERFACE_IDE

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    @polarion("RHEVM3-5937")
    def test_direct_lun_interface_virtio(self):
        """
        Create direct lun - interface virtio
        """
        self.lun_kwargs['interface'] = config.INTERFACE_VIRTIO

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    @polarion("RHEVM3-5937")
    def test_direct_lun_interface_virtio_scsi(self):
        """
        Create direct lun - interface virtio-scsi
        """
        self.lun_kwargs['interface'] = config.INTERFACE_VIRTIO_SCSI

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])


@attr(tier=2)
class TestCase5938(DirectLunAttachTestCase):
    """
    direct lun as bootable disk
    """
    polarion_test_case = '5938'

    def setUp(self):
        """
        Create direct lun as bootable disk
        """
        super(TestCase5938, self).setUp()
        self.lun_kwargs["bootable"] = True

    @polarion("RHEVM3-5938")
    def test_bootable_disk(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    def tearDown(self):
        self.lun_kwargs["bootable"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])


@attr(tier=2)
class TestCase5939(DirectLunAttachTestCase):
    """
    shared disk from direct lun
    """
    polarion_test_case = '5939'

    def setUp(self):
        """
        Create a direct lun as shared disk
        """
        super(TestCase5939, self).setUp()
        self.lun_kwargs["shareable"] = True

    @polarion("RHEVM3-5939")
    def test_shared_direct_lun(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    def tearDown(self):
        self.lun_kwargs["shareable"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])


@attr(tier=2)
class TestCase5940(DirectLunAttachTestCase):
    """
    move vm with direct lun
    """
    polarion_test_case = "5940"
    target_domain = None

    @polarion("RHEVM3-5940")
    def test_migrate_vm_direct_lun(self):
        """
        Attache a direct lun to vm and move it to other domain
        """
        self.target_sd, self.vm_moved = None, None
        self.attach_disk_to_vm()
        vm_disk = filter(lambda w: w.get_alias() != self.disk_alias,
                         getVmDisks(self.vm_name))[0]
        self.original_sd = get_vms_disks_storage_domain_name(
            self.vm_name, vm_disk.get_alias())
        self.target_sd = get_other_storage_domain(
            vm_disk.get_alias(), self.vm_name, storage_type=self.storage)

        assert self.target_sd
        self.vm_moved = moveVm(True, self.vm_name, self.target_sd)
        self.assertTrue(self.vm_moved, "Failed to move vm %s" % self.vm_name)

    def tearDown(self):
        """Move the vm back to the original storage domain"""
        waitForVMState(self.vm_name)
        if self.target_sd and self.vm_moved:
            moveVm(True, self.vm_name, self.original_sd)
        waitForVMState(self.vm_name)
        super(TestCase5940, self).tearDown()


@attr(tier=1)
class TestCase5924(DirectLunAttachTestCase):
    """
    Full flow direct lun
    """
    polarion_test_case = "5924"

    @polarion("RHEVM3-5924")
    def test_remove_direct_lun(self):
        """
        * Create direct lun and attach it to vm.
        * Detach it and remove it
        """
        stop_vms_safely([self.vm_name])
        self.attach_disk_to_vm()
        # TODO: Verify write operation to direct lun

        logger.info("Detaching direct lun %s", self.disk_alias)
        assert detachDisk(True, self.disk_alias, self.vm_name)
        logger.info("Removing direct lun %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])

    def tearDown(self):
        pass


@attr(tier=2)
class TestCase5911(DirectLunAttachTestCase):
    """
    remove a vm with a direct lun
    """
    polarion_test_case = "5911"

    @polarion("RHEVM3-5911")
    def test_remove_vm_with_direct_lun(self):
        """
        Remove vm with direct lun attached
        """
        self.vm_removed = False
        self.attach_disk_to_vm()

        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        self.vm_removed = removeVm(True, self.vm_name)
        self.assertTrue(self.vm_removed,
                        "Failed to remove vm %s" % self.vm_name)

    def tearDown(self):
        if self.vm_removed:
            # Adding back vm since the test removes it
            assert helpers.create_vm(
                self.vm_name, config.VIRTIO_BLK,
                storage_domain=self.vm_storage_domain
            )
            wait_for_jobs([ENUMS['job_add_vm']])
        else:
            super(TestCase5911, self).tearDown()


@attr(tier=2)
class TestCase5913(DirectLunAttachTestCase):
    """
    Direct lun - wipe after delete
    """
    polarion_test_case = '5913'

    def setUp(self):
        """
        Create a direct lun with wipe after delete
        """
        super(TestCase5913, self).setUp()
        self.lun_kwargs["wipe_after_delete"] = True

    @polarion("RHEVM3-5913")
    def test_wipe_after_delete_with_direct_lun(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs([ENUMS['job_add_disk']])

    def tearDown(self):
        self.lun_kwargs["wipe_after_delete"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs([ENUMS['job_remove_disk']])
