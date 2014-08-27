"""
Test Direct Lun Sanity - TCMS plan 5426
"""
import logging
from art.rhevm_api.tests_lib.low_level.hosts import getHostIP
from art.unittest_lib.common import StorageTest as TestCase
from utilities.machine import Machine, LINUX

import config
from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, attachDisk, detachDisk, deleteDisk,
    waitForDisksState,
)

from art.rhevm_api.tests_lib.low_level.storagedomains import (
    findMasterStorageDomain,
    findNonMasterStorageDomains,
)

from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)

from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, getVmDisks, startVm, suspendVm,
    runVmOnce, addSnapshot, updateVm, removeSnapshot,
    get_snapshot_disks, migrateVm, moveVm, removeVm,
    getVmHost, deactivateVmDisk,
)

from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
import common

from art.test_handler import exceptions
from art.test_handler.tools import tcms  # pylint: disable=E0611

logger = logging.getLogger(__name__)

TCMS_PLAN_ID = "5426"

BASE_KWARGS = {
    "interface": config.VIRTIO_SCSI,
    "alias": "direct_lun_disk",
    "format": config.COW_DISK,
    "size": config.DISK_SIZE,
    "bootable": False,
    "lun_address": config.EXTEND_LUN_ADDRESS[0],
    "lun_target": config.EXTEND_LUN_TARGET[0],
    "lun_id": config.EXTEND_LUN[0],
    "type_": config.STORAGE_TYPE,
}


class DirectLunAttachTestCase(TestCase):
    """
    Base class for Direct Lun tests
    """
    __test__ = False
    tcms_test_case = ""

    def setUp(self):
        """
        Build disk's parameters
        """
        self.disk_alias = "direct_lun_%s" % self.tcms_test_case

        status, masterDomain = findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = masterDomain['masterDomain']

        self.lun_kwargs = BASE_KWARGS.copy()
        self.lun_kwargs["alias"] = self.disk_alias
        self.lun_kwargs["storagedomain"] = self.master_domain

        stop_vms_safely([config.VM1_NAME])
        waitForVMState(config.VM1_NAME, config.VM_DOWN)

    def attach_disk_to_vm(self):
        """
        Attach the lun to the VM
        """
        logger.info("Adding new disk (direct lun) %s", self.disk_alias)
        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

        logger.info("Attaching disk %s to vm %s", self.disk_alias,
                    config.VM1_NAME)
        status = attachDisk(True, self.disk_alias, config.VM1_NAME,
                            active=True)
        wait_for_jobs()
        self.assertTrue(status, "Failed to attach direct lun to vm")
        assert self.disk_alias in (
            [d.get_alias() for d in getVmDisks(config.VM1_NAME)]
        )

    def detach_and_delete_disk_from_vm(self, disk_alias):
        logger.info("Wait in case an disks are not ready")
        wait_for_jobs()

        stop_vms_safely([config.VM1_NAME])
        waitForVMState(config.VM1_NAME, config.VM_DOWN)

        logger.info("Detaching disk %s from vm %s", disk_alias,
                    config.VM1_NAME)
        assert detachDisk(True, disk_alias, config.VM1_NAME)
        wait_for_jobs()

        logger.info("Deleting disk %s", disk_alias)
        assert deleteDisk(True, disk_alias)
        wait_for_jobs()

    def tearDown(self):
        """
        Removed disks
        """
        self.detach_and_delete_disk_from_vm(self.disk_alias)


class TestCase138744(DirectLunAttachTestCase):
    """
    Verify that a lun can be created
    """
    __test__ = True
    tcms_test_case = "138744"

    def test_add_lun(self):
        """
        create direct lun disk
        """
        logger.info("Adding new disk (direct lun) %s", self.disk_alias)
        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()


class TestCase138745(DirectLunAttachTestCase):
    """
    Attach a lun when vm is down.
    """
    __test__ = True
    tcms_test_case = "138745"

    def setUp(self):
        super(TestCase138745, self).setUp()
        stop_vms_safely([config.VM1_NAME], config.VM_DOWN)
        waitForVMState(config.VM1_NAME, config.VM_DOWN)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_attach_lun_vm_down(self):
        """
        Attach the lun
        """
        self.attach_disk_to_vm()


class TestCase138746(DirectLunAttachTestCase):
    """
    Attach a lun when vm is running
    """
    __test__ = True
    tcms_test_case = "138746"

    def setUp(self):
        """
        Start the vm
        """
        super(TestCase138746, self).setUp()
        assert startVm(True, config.VM1_NAME, config.VM_UP)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_attach_lun_vm_running(self):
        """
        Attach the lun when vm is up
        """
        self.attach_disk_to_vm()


class TestCase138749(DirectLunAttachTestCase):
    """
    Attach the lun to the vm and run it.
    """
    __test__ = True
    tcms_test_case = "138749"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_attach_vm_and_run(self):
        """
        Attach the lun to the vm and run it.
        """
        self.attach_disk_to_vm()
        assert startVm(True, config.VM1_NAME, config.VM_UP)


class TestCase231815(DirectLunAttachTestCase):
    """
    Suspend vm with direct lun attached
    """
    __test__ = True
    tcms_test_case = "231815"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_suspend_vm(self):
        """
        attach direct lun and suspend vm
        """
        self.attach_disk_to_vm()
        wait_for_jobs()
        startVm(True, config.VM1_NAME, config.VM_UP)
        assert suspendVm(True, config.VM1_NAME)

    def tearDown(self):
        """
        Remove disk
        """
        assert startVm(True, config.VM1_NAME)
        waitForVMState(config.VM1_NAME)
        super(TestCase231815, self).tearDown()


class TestCase138755(DirectLunAttachTestCase):
    """
    Add more then one direct lun to the same vm
    """
    __test__ = True
    tcms_test_case = "138755"
    disk_to_add = 'disk_%s'

    def setUp(self):
        super(TestCase138755, self).setUp()
        self.disk_to_add = 'disk_2_%s' % self.tcms_test_case

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_more_then_one_direct_lun(self):
        """
        Adds and attach two different direct luns to the same vm
        """
        self.attach_disk_to_vm()
        wait_for_jobs()

        disk_alias = self.disk_alias
        self.disk_alias = self.disk_to_add

        self.lun_kwargs['alias'] = self.disk_to_add
        self.lun_kwargs['lun_address'] = config.EXTEND_LUN_ADDRESS[1]
        self.lun_kwargs['lun_target'] = config.EXTEND_LUN_TARGET[1]
        self.lun_kwargs['lun_id'] = config.EXTEND_LUN[1]

        self.attach_disk_to_vm()
        wait_for_jobs()

        self.disk_alias = disk_alias

    def tearDown(self):
        """
        Remove disks
        """
        super(TestCase138755, self).tearDown()

        self.detach_and_delete_disk_from_vm(self.disk_to_add)


class TestCase138756(DirectLunAttachTestCase):
    """
    Attach lun vm, create a template and verify the direct lun will not be
    part of the template
    """
    # TODO: verify template's disks
    __test__ = True
    tcms_test_case = "138756"
    template_name = "template_%s" % tcms_test_case
    temp_created = False

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_template_from_vm_with_lun(self):
        """
        Create template from vm with direct lun attached
        """
        self.attach_disk_to_vm()
        self.temp_created = createTemplate(True, vm=config.VM1_NAME,
                                           name=self.template_name,
                                           cluster=config.CLUSTER_NAME)

        assert self.temp_created

    def tearDown(self):
        if self.temp_created:
            stop_vms_safely([config.VM1_NAME])
            waitForVMState(config.VM1_NAME, config.VM_DOWN)
            logger.info("Removing template %s", self.template_name)
            assert removeTemplate(True, self.template_name)
            wait_for_jobs()
        super(TestCase138756, self).tearDown()


class TestCase138757(DirectLunAttachTestCase):
    """
    attach lun to vm, run vm as stateless and create snapshot.
    snapshot should not be created
    """
    __test__ = True
    tcms_test_case = "138757"
    snap_desc = "snapshot_name_%s" % tcms_test_case
    snap_added = False

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_snapshot_from_stateless_vm(self):
        """
        """
        self.attach_disk_to_vm()
        assert runVmOnce(True, config.VM1_NAME, stateless=True)
        waitForVMState(config.VM1_NAME)
        self.snap_added = addSnapshot(False, config.VM1_NAME, self.snap_desc)
        assert self.snap_added

    def tearDown(self):
        stop_vms_safely([config.VM1_NAME])
        assert waitForVMState(config.VM1_NAME, config.VM_DOWN)

        if not self.snap_added:
            logger.info("Removing snapshot %s", self.snap_desc)
            assert removeSnapshot(True, config.VM1_NAME, self.snap_desc)
            wait_for_jobs()

        super(TestCase138757, self).tearDown()


class TestCase138758(DirectLunAttachTestCase):
    """
    Attach lun to vm and verify the direct lun will not be
    part of the snapshot
    """
    __test__ = True
    tcms_test_case = "138758"
    snap_desc = "snapshot_name_%s" % tcms_test_case
    snap_added = False

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_create_snapshot_from_vm_with_lun(self):
        """
        Create snapshot with direct lun
        """
        self.attach_disk_to_vm()
        wait_for_jobs()

        logger.info("Create new snapshot %s", self.snap_desc)
        self.snap_added = addSnapshot(True, config.VM1_NAME, self.snap_desc)
        assert self.snap_added
        wait_for_jobs()

        snap_disks = get_snapshot_disks(config.VM1_NAME, self.snap_desc)

        if self.disk_alias in snap_disks:
            raise exceptions.SnapshotException(
                "direct lun %s is part of thr snapshot %s"
                % (self.disk_alias, self.snap_desc))

    def tearDown(self):
        if self.snap_added:
            stop_vms_safely([config.VM1_NAME])
            waitForVMState(config.VM1_NAME, config.VM_DOWN)
            logger.info("Removing snapshot %s", self.snap_desc)
            assert removeSnapshot(True, config.VM1_NAME, self.snap_desc)
            wait_for_jobs()
        super(TestCase138758, self).tearDown()


class TestCase138760(DirectLunAttachTestCase):
    """
    HA vm with direct lun
    """
    __test__ = True
    tcms_test_case = "138760"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_ha_vm_with_direct_lun(self):
        """
        * Run vm with direct lun in HA mode
        * kill qemu precess
        """
        self.attach_disk_to_vm()
        assert updateVm(True, config.VM1_NAME, highly_available='true')
        startVm(True, config.VM1_NAME)

        _, host = getVmHost(config.VM1_NAME)
        host_ip = getHostIP(host['vmHoster'])
        host_machine = Machine(
            host_ip, config.HOSTS_USER, config.HOSTS_PW).util(LINUX)

        assert host_machine.kill_qemu_process(config.VM1_NAME)

        assert waitForVMState(config.VM1_NAME)
        wait_for_jobs()

    def tearDown(self):
        wait_for_jobs()
        assert updateVm(True, config.VM1_NAME, highly_available='false')
        super(TestCase138760, self).tearDown()


class TestCase138761(DirectLunAttachTestCase):
    """
    migrate a non-migrate vm with direct lun

    Bug: https://bugzilla.redhat.com/show_bug.cgi?id=1144810
    """
    __test__ = False
    tcms_test_case = "138761"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_migrate_vm_direct_lun(self):
        """
        Select a specific host for vm, with direct lun, and try to migrate it
        """
        self.attach_disk_to_vm()
        assert updateVm(True, config.VM1_NAME, placement_host=config.HOSTS[0])
        startVm(True, config.VM1_NAME)

        assert migrateVm(False, config.VM1_NAME)
        wait_for_jobs()

        assert waitForVMState(config.VM1_NAME)

    def tearDown(self):
        assert updateVm(True, config.VM1_NAME, placement_host=None)
        super(TestCase138761, self).tearDown()


class TestCase138763(DirectLunAttachTestCase):
    """
    direct lun and disk interface
    """
    __test__ = False
    tcms_test_case = "138763"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_direct_lun_interface_ide(self):
        """
        Create direct lun - interface ide
        """
        self.lun_kwargs['interface'] = config.INTERFACE_IDE

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_direct_lun_interface_virtio(self):
        """
        Create direct lun - interface virtio
        """
        self.lun_kwargs['interface'] = config.INTERFACE_VIRTIO

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()


class TestCase138764(DirectLunAttachTestCase):
    """
    direct lun as bootable disk
    """
    __test__ = True
    tcms_test_case = '138764'

    def setUp(self):
        """
        Create direct lun as bootable disk
        """
        super(TestCase138764, self).setUp()
        self.lun_kwargs["bootable"] = True

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_bootable_disk(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    def tearDown(self):
        self.lun_kwargs["bootable"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()


class TestCase138765(DirectLunAttachTestCase):
    """
    shared disk from direct lun
    """
    __test__ = True
    tcms_test_case = '138765'

    def setUp(self):
        """
        Create a direct lun as shared disk
        """
        super(TestCase138765, self).setUp()
        self.lun_kwargs["shareable"] = True

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_shared_direct_lun(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    def tearDown(self):
        self.lun_kwargs["shareable"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()


class TestCase138766(DirectLunAttachTestCase):
    """
    move vm with direct lun
    """
    __test__ = True
    tcms_test_case = "138766"
    target_domain = None

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_migrate_vm_direct_lun(self):
        """
        Attache a direct lun to vm and move it to other domain
        """
        self.attach_disk_to_vm()
        _, non_master_domain = findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        self.target_domain = non_master_domain['nonMasterDomains'][0]

        assert moveVm(True, config.VM1_NAME, self.target_domain)
        wait_for_jobs()

    def tearDown(self):
        moveVm(True, config.VM1_NAME, self.master_domain)
        wait_for_jobs()
        super(TestCase138766, self).tearDown()


class TestCase138768(DirectLunAttachTestCase):
    """
    detach a direct lun
    """
    __test__ = True
    tcms_test_case = "138768"
    detached = False

    def detach_disk_from_vm(self, vm_name, disk_alias):
        logger.info("Detaching direct lun %s", disk_alias)
        deactivateVmDisk(True, vm_name, diskAlias=disk_alias)
        self.detached = detachDisk(True, disk_alias, vm_name)
        assert self.detached
        wait_for_jobs()

    #  Not working!
    # @tcms(TCMS_PLAN_ID, tcms_test_case)
    # def test_live_detach_direct_lun(self):
    #     """
    #     Live detach direct lun from vm
    #     """
    #     self.attach_disk_to_vm()
    #
    #     startVm(True, config.VM1_NAME)
    #     waitForVMState(config.VM1_NAME)
    #     self.detach_disk_from_vm(config.VM1_NAME, self.disk_alias)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_cold_detach_direct_lun(self):
        """
        Detach direct lun from vm
        """
        self.attach_disk_to_vm()

        stop_vms_safely([config.VM1_NAME])
        waitForVMState(config.VM1_NAME, config.VM_DOWN)

        self.detach_disk_from_vm(config.VM1_NAME, self.disk_alias)

    def tearDown(self):
        if self.detached:
            assert deleteDisk(True, self.disk_alias)

        else:
            detachDisk(True, self.disk_alias, config.VM1_NAME)
            waitForDisksState(self.disk_alias)
            assert deleteDisk(True, self.disk_alias)

        wait_for_jobs()


class TestCase138769(DirectLunAttachTestCase):
    """
    remove direct lun
    """
    __test__ = True
    tcms_test_case = "138769"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_remove_direct_lun(self):
        """
        * Create direct lun and attach it to vm.
        * Detach it and remove it
        """
        self.attach_disk_to_vm()

        logger.info("Detaching direct lun %s", self.disk_alias)
        assert detachDisk(True, self.disk_alias, config.VM1_NAME)
        wait_for_jobs()
        logger.info("Removing direct lun %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()

    def tearDown(self):
        pass


class TestCase138770(DirectLunAttachTestCase):
    """
    remove a vm with a direct lun
    """
    __test__ = True
    tcms_test_case = "138770"

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_remove_vm_with_direct_lun(self):
        """
        Remove vm with direct lun attached
        """
        self.attach_disk_to_vm()

        stop_vms_safely([config.VM1_NAME])
        waitForVMState(config.VM1_NAME, config.VM_DOWN)
        assert removeVm(True, config.VM1_NAME)

    def tearDown(self):
        assert common._create_vm(config.VM1_NAME, config.VIRTIO_BLK)
        wait_for_jobs()


class TestCase138773(DirectLunAttachTestCase):
    """
    Direct lun - wipe after delete
    """
    __test__ = True
    tcms_test_case = '138773'

    def setUp(self):
        """
        Create a direct lun with wipe after delete
        """
        super(TestCase138773, self).setUp()
        self.lun_kwargs["wipe_after_delete"] = True

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_wipe_after_delete_with_direct_lun(self):

        assert addDisk(True, **self.lun_kwargs)
        wait_for_jobs()

    def tearDown(self):
        self.lun_kwargs["wipe_after_delete"] = False
        logger.info("Deleting disk %s", self.disk_alias)
        assert deleteDisk(True, self.disk_alias)
        wait_for_jobs()
