"""
Test Direct Lun Sanity
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Storage/
3_1_Storage_Direct_Lun_General
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level.hosts import getHostIP
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sds,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz
from utilities.machine import Machine, LINUX

logger = logging.getLogger(__name__)

ISCSI = config.STORAGE_TYPE_ISCSI
ENUMS = config.ENUMS
VM_NAME = 'direct_lun_vm_%s_%s'
STATELESS_SNAPSHOT_DESCRIPTION = 'stateless snapshot'
BASE_KWARGS = {
    "interface": config.VIRTIO_SCSI,
    "alias": "direct_lun_disk",
    "format": config.COW_DISK,
    "provisioned_size": config.DISK_SIZE,
    "bootable": False,
    "type_": ISCSI,
}


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
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    vm_name = None
    polarion_test_case = ""
    # Bugzilla history:
    # 1220824: Adding a disk to a vm fails with NullPointerException if not
    # disk.storage_domains is provided (even for direct lun disks)

    def setUp(self):
        """
        Build disk's parameters
        """
        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        self.vm_name = VM_NAME % (self.storage, self.polarion_test_case)
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['installation'] = False
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm_name
            )
        BASE_KWARGS.update({'type_': self.storage})
        self.disk_alias = "direct_lun_%s" % self.polarion_test_case
        self.lun_kwargs = BASE_KWARGS.copy()
        self.lun_kwargs["alias"] = self.disk_alias

    def attach_disk_to_vm(self):
        """
        Attach the lun to the VM
        """
        logger.info("Adding new disk (direct lun) %s", self.disk_alias)
        if not ll_disks.addDisk(True, **self.lun_kwargs):
            raise exceptions.DiskException(
                "Failed to add direct LUN %s" % self.lun_kwargs['alias']
            )
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])
        logger.info(
            "Attaching disk %s to vm %s", self.disk_alias, self.vm_name
        )
        status = ll_disks.attachDisk(
            True, self.disk_alias, self.vm_name, active=True
        )
        if not status:
            raise exceptions.VMException(
                "Failed to attach direct lun to vm %s" % self.vm_name
            )
        if self.disk_alias not in (
            [d.get_alias() for d in ll_vms.getVmDisks(self.vm_name)]
        ):
            raise exceptions.DiskException(
                "Direct LUN wasn't attached to vm %s" % self.vm_name)

    def tearDown(self):
        """
        Remove VM
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            TestCase.test_failed = True


@attr(tier=2)
@bz({'1394564': {}})
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
        if not ll_vms.startVm(True, self.vm_name, config.VM_UP):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )

    @polarion("RHEVM3-5927")
    def test_attach_lun_vm_running(self):
        """
        1) Attach a lun to running vm
        """
        self.attach_disk_to_vm()

    def tearDown(self):
        super(TestCase5927, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1394564': {}})
class TestCase5920(DirectLunAttachTestCase):
    """
    Suspend vm with direct lun attached
    """
    polarion_test_case = "5920"

    @polarion("RHEVM3-5920")
    def test_suspend_vm(self):
        """
        1) attach direct lun
        2) suspend vm
        """
        self.attach_disk_to_vm()
        if not ll_vms.startVm(True, self.vm_name, config.VM_UP):
            raise exceptions.VMException(
                "Failed to start vm %s" % self.vm_name
            )
        if not ll_vms.suspendVm(True, self.vm_name):
            raise exceptions.VMException(
                "Failed to change vm %s state to suspend" % self.vm_name
            )

    def tearDown(self):
        """
        Resume vm after suspend and remove it
        """
        if not ll_vms.startVm(True, self.vm_name, config.VM_UP):
            logger.error("Failed to start vm %s" % self.vm_name)
            TestCase.test_failed = True
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            TestCase.test_failed = True
        TestCase.teardown_exception()


@attr(tier=2)
@bz({'1394564': {}})
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
        1) Add and attach first LUN to vm
        2) Add and attach second LUN to the same vm
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
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1394564': {}})
class TestCase5931(DirectLunAttachTestCase):
    """
    Attach lun vm, create a template and verify the direct lun will not be
    part of the template
    """
    # TODO: verify template's disks
    polarion_test_case = "5931"
    template_name = "template_%s" % polarion_test_case
    template_created = False

    @polarion("RHEVM3-5931")
    def test_create_template_from_vm_with_lun(self):
        """
        1) Attach direct LUN to vm
        2) Create template from the vm
        """
        self.attach_disk_to_vm()
        self.template_created = ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME
        )
        assert self.template_created, (
            "Failed to create template %s" % self.template_name
        )

    def tearDown(self):
        if self.template_created:
            logger.info("Removing template %s", self.template_name)
            if not ll_templates.removeTemplate(True, self.template_name):
                logger.error(
                    "Failed to remove template %s", self.template_name
                )
                TestCase.test_failed = True
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_TEMPLATE])
        super(TestCase5931, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1245630': {}})
class TestCase5932(DirectLunAttachTestCase):
    """
    attach lun to vm, run vm as stateless and create snapshot.
    snapshot should not be created
    """
    polarion_test_case = "5932"
    snap_desc = "snapshot_name_%s" % polarion_test_case
    snap_added = False

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_REMOVE_SNAPSHOT])
    @polarion("RHEVM3-5932")
    def test_create_snapshot_from_stateless_vm(self):
        """
        1) Attach direct LUN to vm
        2) Run vm in stateless mode
        3) Create snapshot from stateless vm (should fail)
        """
        self.attach_disk_to_vm()
        if not ll_vms.runVmOnce(
            True, self.vm_name, stateless=True, wait_for_state=config.VM_UP
        ):
            raise exceptions.VMException(
                "Failed to run vm %s in stateless mode" % self.vm_name
            )
        self.snap_added = ll_vms.addSnapshot(
            False, self.vm_name, self.snap_desc
        )
        assert self.snap_added, (
            "Succeeded to create snapshot from stateless vm with direct LUN "
            "attached"
        )

    def tearDown(self):
        if not ll_vms.stop_vms_safely([self.vm_name]):
            logger.error("Failed to power off vm %s", self.vm_name)
            TestCase.test_failed = True
        ll_vms.wait_for_snapshot_gone(
            self.vm_name, STATELESS_SNAPSHOT_DESCRIPTION
        )
        super(TestCase5932, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1394564': {}})
class TestCase5933(DirectLunAttachTestCase):
    """
    Attach lun to vm and verify the direct lun will not be
    part of the snapshot
    """
    polarion_test_case = "5933"
    snap_desc = "snapshot_name_%s" % polarion_test_case

    @polarion("RHEVM3-5933")
    def test_create_snapshot_from_vm_with_lun(self):
        """
        1) Attach direct LUN to vm
        2) Create snapshot
        """
        self.attach_disk_to_vm()
        logger.info("Create new snapshot %s", self.snap_desc)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snap_desc
        ), "Failed to create snapshot %s to vm %s" % (
            self.snap_desc, self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_OK, [self.snap_desc],
        )
        snap_disks = ll_vms.get_snapshot_disks(self.vm_name, self.snap_desc)

        if self.disk_alias in snap_disks:
            raise exceptions.SnapshotException(
                "direct lun %s is part of thr snapshot %s"
                % (self.disk_alias, self.snap_desc))

    def tearDown(self):
        super(TestCase5933, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=4)
@bz({'1394564': {}})
class TestCase5934(DirectLunAttachTestCase):
    """
    HA vm with direct lun
    """
    polarion_test_case = "5934"

    @polarion("RHEVM3-5934")
    def test_ha_vm_with_direct_lun(self):
        """
        1) Run vm with direct lun in HA mode
        2) kill qemu precess
        """
        self.attach_disk_to_vm()
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true'
        ), "Failed to update vm %s HA attribute to 'true" % self.vm_name
        ll_vms.startVm(True, self.vm_name)
        _, host = ll_vms.getVmHost(self.vm_name)
        host_ip = getHostIP(host['vmHoster'])
        host_machine = Machine(
            host_ip, config.HOSTS_USER, config.HOSTS_PW).util(LINUX)
        assert host_machine.kill_qemu_process(
            self.vm_name
        ), "Failed to kill the QEMU process"
        assert ll_vms.waitForVMState(self.vm_name), (
            "VM state is not up after killing QEMU process and setting HA "
            "attribute to 'true"
        )

    def tearDown(self):
        super(TestCase5934, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=2)
@bz({'1394564': {}})
class TestCase5938(DirectLunAttachTestCase):
    """
    direct lun as bootable disk
    """
    polarion_test_case = '5938'

    def setUp(self):
        """
        Create direct lun as bootable disk
        """
        self.disk_alias = "direct_lun_%s" % self.polarion_test_case
        self.kwargs = BASE_KWARGS.copy()
        self.kwargs["alias"] = self.disk_alias
        self.kwargs["bootable"] = True

    @polarion("RHEVM3-5938")
    def test_bootable_disk(self):
        """
        1) Add direct LUN as bootable
        """
        assert ll_disks.addDisk(
            True, **self.kwargs
        ), "Failed to add direct LUN with bootable attribute set to 'true'"
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Failed to remove disk %s", self.disk_alias)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        TestCase.teardown_exception()


@attr(tier=2)
@bz({'1394564': {}})
class TestCase5939(DirectLunAttachTestCase):
    """
    shared disk from direct lun
    """
    polarion_test_case = '5939'

    def setUp(self):
        """
        Create a direct lun as shared disk
        """
        self.disk_alias = "direct_lun_%s" % self.polarion_test_case
        self.kwargs = BASE_KWARGS.copy()
        self.kwargs["alias"] = self.disk_alias
        self.kwargs["shareable"] = True

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_ADD_DISK])
    @polarion("RHEVM3-5939")
    def test_shared_direct_lun(self):
        """
        1) Add direct LUN as shareable
        """
        assert ll_disks.addDisk(
            True, **self.kwargs
        ), "Failed to add direct LUN with shareable attribute set to 'true'"

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Failed to remove disk %s", self.disk_alias)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1394564': {}})
class TestCase5940(DirectLunAttachTestCase):
    """
    move vm with direct lun
    """
    polarion_test_case = "5940"
    target_domain = None

    @polarion("RHEVM3-5940")
    def test_migrate_vm_direct_lun(self):
        """
        1) Attach a direct LUN to vm
        2) Move the disk to another domain
        """
        self.target_sd, self.vm_moved = None, None
        self.attach_disk_to_vm()
        vm_disk = filter(
            lambda w: w.get_alias() != self.disk_alias,
            ll_vms.getVmDisks(self.vm_name)
        )[0]
        self.original_sd = ll_vms.get_vms_disks_storage_domain_name(
            self.vm_name, vm_disk.get_alias()
        )
        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disk.get_alias(), self.vm_name, storage_type=self.storage
        )

        assert self.target_sd, "Target SD %s wasn't found" % self.target_sd
        hl_vms.move_vm_disks(self.vm_name, self.target_sd)

    def tearDown(self):
        """
        Remove vm
        """
        super(TestCase5940, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=1)
@bz({'1394564': {}})
class TestCase5924(DirectLunAttachTestCase):
    """
    Full flow direct lun
    """
    polarion_test_case = "5924"

    def full_flow_direct_lun(self):
        """
        1) Create a direct LUN and attach it to the vm
        2) Detach the LUN from the vm and remove it
        """
        testflow.step(
            "Attach direct lun %s to vm %s", self.disk_alias, self.vm_name
        )
        self.attach_disk_to_vm()
        # TODO: verify write operation to direct LUN when bug:
        # https://bugzilla.redhat.com/show_bug.cgi?id=957788 will fix

        testflow.step(
            "Detaching direct lun %s from vm %s", self.disk_alias, self.vm_name
        )
        assert ll_disks.detachDisk(
            True, self.disk_alias, self.vm_name
        ), "Failed to detach direct lun from vm %s" % self.vm_name
        logger.info("Removing direct lun %s", self.disk_alias)
        assert ll_disks.deleteDisk(
            True, self.disk_alias
        ), "Failed to delete direct lun"
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])

    @polarion("RHEVM3-5924")
    def test_full_flow_direct_lun(self):
        """
        Execute full flow
        """
        self.full_flow_direct_lun()

    @polarion("RHEVM3-5924")
    def test_full_flow_direct_lun_passthrough(self):
        """
        Execute full flow
        """
        # Setting pass-through sgio = 'unfiltered'
        self.lun_kwargs['sgio'] = 'unfiltered'
        self.full_flow_direct_lun()

    def tearDown(self):
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove vm %s", self.vm_name)
            TestCase.test_failed = True
        TestCase.teardown_exception()


@attr(tier=2)
@bz({'1394564': {}})
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

        ll_vms.stop_vms_safely([self.vm_name])
        self.vm_removed = ll_vms.removeVm(True, self.vm_name)
        assert self.vm_removed, "Failed to remove vm %s" % self.vm_name

    def tearDown(self):
        if not self.vm_removed:
            super(TestCase5911, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=3)
@bz({'1394564': {}})
class TestCase5913(DirectLunAttachTestCase):
    """
    Direct lun - wipe after delete
    """
    polarion_test_case = '5913'

    def setUp(self):
        """
        Create a direct lun with wipe after delete
        """
        self.disk_alias = "direct_lun_%s" % self.polarion_test_case
        self.kwargs = BASE_KWARGS.copy()
        self.kwargs["alias"] = self.disk_alias
        self.kwargs["wipe_after_delete"] = True

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_ADD_DISK])
    @polarion("RHEVM3-5913")
    def test_wipe_after_delete_with_direct_lun(self):

        assert ll_disks.addDisk(
            True, **self.kwargs
        ), "Failed to add direct LUN with shareable attribute set to 'true'"

    def tearDown(self):
        logger.info("Deleting disk %s", self.disk_alias)
        if not ll_disks.deleteDisk(True, self.disk_alias):
            logger.error("Failed to remove disk %s", self.disk_alias)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        TestCase.teardown_exception()


@attr(tier=2)
@bz({'1394564': {}})
class TestCase5918(DirectLunAttachTestCase):
    """
    Update a direct lun attached to vm
    """
    polarion_test_case = "5918"
    new_alias = 'new_direct_lun'

    @polarion("RHEVM3-5918")
    def test_update_direct_lun(self):
        """
        Update direct lun attached to vm
        """
        self.attach_disk_to_vm()
        lun_id = ll_vms.getVmDisk(self.vm_name, self.disk_alias).get_id()
        update_kwars = {
            'id': lun_id,
            'alias': self.new_alias,
            'interface': config.VIRTIO_SCSI,
            'shareable': True,
        }
        assert ll_vms.updateDisk(
            True, vmName=self.vm_name, **update_kwars
        ), "Failed to update direct LUN"
        lun_disk = ll_vms.getVmDisk(self.vm_name, self.new_alias)
        lun_attachment = ll_vms.get_disk_attachment(
            self.vm_name, lun_disk.get_id(),
        )
        status = (
            update_kwars['alias'] == lun_disk.get_alias() and
            update_kwars['shareable'] == lun_disk.get_shareable() and
            update_kwars['interface'] == lun_attachment.get_interface()
        )
        assert status, "Direct LUN disk's parameters are not updated"

    def tearDown(self):
        logger.info("Deleting disk %s", self.new_alias)
        if not ll_disks.deleteDisk(True, self.new_alias):
            logger.error("Failed to remove disk %s", self.new_alias)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
        super(TestCase5918, self).tearDown()
        TestCase.teardown_exception()
