"""
Test Direct Lun Sanity
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Storage/
3_1_Storage_Direct_Lun_General
"""
import pytest
import config
import logging
from art.unittest_lib.common import StorageTest as TestCase, testflow
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    templates as ll_templates,
    vms as ll_vms,
    hosts as ll_hosts
)
from rhevmtests.storage.fixtures import (
    create_vm, remove_template, start_vm,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
from rhevmtests.storage.storage_full_disk_sanity.fixtures import (
    initialize_direct_lun_params, delete_direct_lun_disk,
    poweroff_vm_and_wait_for_stateless_to_remove,
)
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from rhevmtests import helpers as rhevm_helpers
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion, bz
import rhevmtests.storage.helpers as storage_helpers


logger = logging.getLogger(__name__)

ISCSI = config.STORAGE_TYPE_ISCSI
ENUMS = config.ENUMS
STATELESS_SNAPSHOT_DESCRIPTION = 'stateless snapshot'


@pytest.fixture(scope='module', autouse=True)
def set_up_proper_base_args(request):
    """
    Prepares direct lun base arguments
    """
    if hasattr(config, 'EXTEND_LUN_ADDRESS'):
        config.BASE_KWARGS.update({
            "lun_address": config.EXTEND_LUN_ADDRESS[0],
            "lun_target": config.EXTEND_LUN_TARGET[0],
            "lun_id": config.EXTEND_LUN[0],
        })


@pytest.mark.usefixtures(
    create_vm.__name__,
    initialize_direct_lun_params.__name__,
)
class DirectLunAttachTestCase(TestCase):
    """
    Base class for Direct Lun tests ,
    This class implements setup and teardowns of each test case ,
    Also defines multi used arguments .
    """
    # This tests are only designed to run on ISCSI
    # TODO: Enable for FC when our environment is stable
    __test__ = ISCSI in ART_CONFIG['RUN']['storages']
    storages = set([ISCSI])
    vm_name = None
    polarion_test_case = ""
    # Bugzilla history:
    # 1220824: Adding a disk to a VM fails with NullPointerException if not
    # disk.storage_domains is provided (even for direct lun disks)

    def attach_disk_to_vm(self, bootable=False):
        """
        Add a new direct lun disk and attach lun to the VM
        """
        testflow.step("Adding new disk (direct lun) %s", self.disk_alias)
        assert ll_disks.addDisk(True, **self.lun_kwargs), (
            "Failed to add direct LUN %s" % self.lun_kwargs['alias']
        )
        ll_jobs.wait_for_jobs([config.JOB_ADD_DISK])
        testflow.step(
            "Attaching disk %s to VM %s", self.disk_alias, self.vm_name
        )
        assert ll_disks.attachDisk(
            True, alias=self.disk_alias, vm_name=self.vm_name, active=True,
            interface=config.VIRTIO_SCSI, bootable=bootable
        ), (
            "Failed to attach direct lun disk %s to VM %s" % (
                self.disk_alias, self.vm_name
            )
        )

        assert self.disk_alias in (
            [d.get_alias() for d in ll_vms.getVmDisks(self.vm_name)]
        ), (
            "Direct LUN %s wasn't attached to VM %s" % (
                self.disk_alias, self.vm_name
            )
        )


@pytest.mark.usefixtures(
    start_vm.__name__,
)
class TestCase5927(DirectLunAttachTestCase):
    """
    Attach a LUN when VM is running
    """
    polarion_test_case = "5927"

    @polarion("RHEVM3-5927")
    @tier2
    def test_attach_lun_vm_running(self):
        """
        1) Attach a LUN to running VM
        """
        self.attach_disk_to_vm()


class TestCase5920(DirectLunAttachTestCase):
    """
    Suspend VM with direct LUN attached
    """
    polarion_test_case = "5920"

    @polarion("RHEVM3-5920")
    @tier3
    def test_suspend_vm(self):
        """
        1) attach direct LUN
        2) suspend VM
        """
        self.attach_disk_to_vm()
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP), (
            "Failed to start VM %s" % self.vm_name
        )
        assert ll_vms.suspendVm(True, self.vm_name), (
            "Failed to suspend VM %s" % self.vm_name
        )


class TestCase5930(DirectLunAttachTestCase):
    """
    Add more then one direct LUN to the same VM
    """
    polarion_test_case = "5930"

    @polarion("RHEVM3-5930")
    @tier2
    def test_more_then_one_direct_lun(self):
        """
        1) Add and attach first LUN to VM
        2) Add and attach second LUN to the same VM
        """
        self.attach_disk_to_vm()
        self.disk_to_add = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DIRECT_LUN
        )
        disk_alias = self.disk_alias
        self.disk_alias = self.disk_to_add
        self.lun_kwargs['alias'] = self.disk_to_add
        self.lun_kwargs['lun_address'] = config.EXTEND_LUN_ADDRESS[1]
        self.lun_kwargs['lun_target'] = config.EXTEND_LUN_TARGET[1]
        self.lun_kwargs['lun_id'] = config.EXTEND_LUN[1]
        self.attach_disk_to_vm()
        self.disk_alias = disk_alias


@pytest.mark.usefixtures(
    remove_template.__name__,
)
class TestCase5931(DirectLunAttachTestCase):
    """
    Attach LUN VM, create a template and verify the direct LUN will not be
    part of the template
    """
    polarion_test_case = "5931"

    @polarion("RHEVM3-5931")
    @tier3
    def test_create_template_from_vm_with_lun(self):
        """
        1) Attach direct LUN to VM
        2) Create template from the VM
        3) Verify direct LUN disk is not part of the template disks
        """
        self.attach_disk_to_vm()
        template_created = ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME
        )
        assert template_created, (
            "Failed to create template %s" % self.template_name
        )
        template_d_obj_list = ll_templates.getTemplateDisks(self.template_name)
        template_disks = [
            temp_obj.get_alias() for temp_obj in template_d_obj_list
        ]
        assert self.disk_alias not in template_disks, (
            "Unexpected disk %s found in template %s disks list" % (
                self.disk_alias, self.template_name
            )
        )


@pytest.mark.usefixtures(
    poweroff_vm_and_wait_for_stateless_to_remove.__name__,
)
@bz({'1415407': {}})
class TestCase5932(DirectLunAttachTestCase):
    """
    1) Attach LUN to VM
    2) Run VM as stateless
    3) Create snapshot
    """
    polarion_test_case = "5932"
    snap_desc = "snapshot_name_%s" % polarion_test_case
    snap_added = False

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_REMOVE_SNAPSHOT])
    @polarion("RHEVM3-5932")
    @tier3
    def test_create_snapshot_from_stateless_vm(self):
        """
        1) Attach direct LUN to VM
        2) Run VM in stateless mode
        3) Create snapshot from stateless VM (should fail)
        """
        self.attach_disk_to_vm()
        assert ll_vms.runVmOnce(
            True, self.vm_name, stateless=True, wait_for_state=config.VM_UP
        ), "Failed to run vm %s in stateless mode" % self.vm_name
        self.snap_added = ll_vms.addSnapshot(
            False, self.vm_name, self.snap_desc
        )
        assert self.snap_added, (
            "Succeeded to create snapshot from stateless VM with direct LUN "
            "attached"
        )


class TestCase5933(DirectLunAttachTestCase):
    """
    Attach LUN to VM and verify the direct LUN will not be
    part of the snapshot
    """
    polarion_test_case = "5933"
    snap_desc = "snapshot_name_%s" % polarion_test_case

    @polarion("RHEVM3-5933")
    @tier3
    def test_create_snapshot_from_vm_with_lun(self):
        """
        1) Attach direct LUN to VM
        2) Create snapshot
        """
        self.attach_disk_to_vm()
        testflow.step("Create new snapshot %s", self.snap_desc)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snap_desc
        ), "Failed to create snapshot %s to vm %s" % (
            self.snap_desc, self.vm_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_OK, [self.snap_desc],
        )
        snap_d_object_list = ll_vms.get_snapshot_disks(
            self.vm_name, self.snap_desc
        )
        snap_disks = [snap_obj.get_alias() for snap_obj in snap_d_object_list]

        assert self.disk_alias not in snap_disks, (
            "direct lun %s is part of the snapshot %s" % (
                self.disk_alias, self.snap_desc
            )
        )


class TestCase5934(DirectLunAttachTestCase):
    """
    HA VM with direct LUN
    """
    polarion_test_case = "5934"

    @polarion("RHEVM3-5934")
    @tier4
    def test_ha_vm_with_direct_lun(self):
        """
        1) Run VM with direct LUN in HA mode
        2) Kill qemu precess
        """
        self.attach_disk_to_vm()
        assert ll_vms.updateVm(
            True, self.vm_name, highly_available='true'
        ), "Failed to update vm %s HA attribute to 'true" % self.vm_name
        ll_vms.startVm(True, self.vm_name)
        host = ll_vms.get_vm_host(vm_name=self.vm_name)
        assert host, "Failed to get VM: %s hoster" % self.vm_name
        host_resource = rhevm_helpers.get_host_resource_by_name(host_name=host)
        status = ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=self.vm_name
        )
        assert status, "Failed to kill qemu process"
        assert ll_vms.waitForVMState(self.vm_name), (
            "VM state is not up after killing QEMU process and setting HA "
            "attribute to 'true"
        )


class TestCase5938(DirectLunAttachTestCase):
    """
    Direct LUN as bootable disk
    """
    polarion_test_case = '5938'
    # parameters needed to create_VM fixture to create a VM without disks
    installation = False
    storage_domain = None

    @polarion("RHEVM3-5938")
    @tier2
    def test_bootable_disk(self):
        """
        1) Add direct LUN as bootable to a VM without prior bootable disk
        2) Start VM
        """
        self.lun_kwargs["bootable"] = True
        self.attach_disk_to_vm(bootable=True), (
            "Failed to add direct LUN with bootable attribute set to 'true'"
        )
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP), (
            "Failed to start VM %s" % self.vm_name
        )


@pytest.mark.usefixtures(
    delete_direct_lun_disk.__name__,
)
class TestCase5939(DirectLunAttachTestCase):
    """
    Shared disk from direct LUN
    """
    polarion_test_case = '5939'

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_ADD_DISK])
    @polarion("RHEVM3-5939")
    @tier2
    def test_shared_direct_lun(self):
        """
        1) Add direct LUN as shareable
        """
        self.lun_kwargs["shareable"] = True
        assert ll_disks.addDisk(
            True, **self.lun_kwargs
        ), "Failed to add direct LUN with shareable attribute set to 'true'"
        self.disks_to_remove.append(self.disk_alias)


class TestCase5940(DirectLunAttachTestCase):
    """
    Move VM with direct LUN
    """
    polarion_test_case = "5940"
    target_domain = None

    @polarion("RHEVM3-5940")
    @tier3
    def test_migrate_vm_direct_lun(self):
        """
        1) Attach a direct LUN to VM
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


class TestCase5924(DirectLunAttachTestCase):
    """
    Full flow direct LUN
    """
    polarion_test_case = "5924"

    def full_flow_direct_lun(self):
        """
        1) Create a direct LUN and attach it to the VM
        2) Detach the LUN from the VM and remove it
        """
        testflow.step(
            "Attach direct LUN %s to VM %s", self.disk_alias, self.vm_name
        )
        self.attach_disk_to_vm()
        # TODO: verify write operation to direct LUN when bug:
        # https://bugzilla.redhat.com/show_bug.cgi?id=957788 will fix

        testflow.step(
            "Detaching direct LUN %s from VM %s", self.disk_alias, self.vm_name
        )
        assert ll_disks.detachDisk(
            True, self.disk_alias, self.vm_name
        ), "Failed to detach direct LUN from VM %s" % self.vm_name
        testflow.step("Removing direct LUN %s", self.disk_alias)
        assert ll_disks.deleteDisk(
            True, self.disk_alias
        ), "Failed to delete direct LUN"
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])

    @polarion("RHEVM3-5924")
    @tier1
    def test_full_flow_direct_lun(self):
        """
        Execute full flow
        """
        self.full_flow_direct_lun()

    @polarion("RHEVM3-5924")
    @tier1
    def test_full_flow_direct_lun_passthrough(self):
        """
        Execute full flow
        """
        # Setting pass-through sgio = 'unfiltered'
        self.lun_kwargs['sgio'] = 'unfiltered'
        self.full_flow_direct_lun()


class TestCase5911(DirectLunAttachTestCase):
    """
    Remove a VM with a direct LUN
    """
    polarion_test_case = "5911"

    @polarion("RHEVM3-5911")
    @tier2
    def test_remove_vm_with_direct_lun(self):
        """
        Remove VM with direct LUN attached
        """
        self.vm_removed = False
        self.attach_disk_to_vm()

        ll_vms.stop_vms_safely([self.vm_name])
        self.vm_removed = ll_vms.removeVm(True, self.vm_name)
        assert self.vm_removed, "Failed to remove VM %s" % self.vm_name


@pytest.mark.usefixtures(
    delete_direct_lun_disk.__name__,
)
@bz({'1394564': {}})
class TestCase5913(DirectLunAttachTestCase):
    """
    Direct LUN - wipe after delete
    """
    polarion_test_case = '5913'

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_ADD_DISK])
    @polarion("RHEVM3-5913")
    @tier3
    def test_wipe_after_delete_with_direct_lun(self):
        self.lun_kwargs["wipe_after_delete"] = True
        assert ll_disks.addDisk(
            True, **self.lun_kwargs
        ), ("Failed to add direct LUN with wipe after delete attribute "
            "set to 'true'")
        self.disks_to_remove.append(self.disk_alias)


@pytest.mark.usefixtures(
    delete_direct_lun_disk.__name__,
)
class TestCase5918(DirectLunAttachTestCase):
    """
    Update a direct LUN attached to VM
    """
    polarion_test_case = "5918"
    new_alias = 'new_direct_lun_%s' % polarion_test_case

    @polarion("RHEVM3-5918")
    @tier2
    def test_update_direct_lun(self):
        """
        Update direct LUN attached to VM
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
        self.disks_to_remove.append(self.new_alias)


class TestCase24944(DirectLunAttachTestCase):
    """
    Migrate VM with direct LUN attached
    """
    polarion_test_case = "24944"

    @polarion("RHEVM-24944")
    @tier2
    def test_migrate_vm_with_direct_lun(self):
        """
        1) Attach direct LUN
        2) Migrate VM
        """
        self.attach_disk_to_vm()
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP), (
            "Failed to start VM %s" % self.vm_name
        )
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_name
        ), "Failed to migrate VM %s" % self.vm_name
