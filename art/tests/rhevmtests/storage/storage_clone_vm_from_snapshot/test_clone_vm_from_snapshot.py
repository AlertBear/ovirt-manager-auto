"""
Clone Vm From Snapshot
"""
import config
import logging
import pytest
from art.unittest_lib.common import attr, StorageTest as TestCase, testflow
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions
import rhevmtests.storage.helpers as helpers
from rhevmtests.storage.fixtures import (
    initialize_storage_domains, remove_vms, delete_disks
)
from rhevmtests.storage.storage_clone_vm_from_snapshot.fixtures import (
    initialize_vm, remove_additional_nic, remove_additional_snapshot,
    create_server_vm_with_snapshot, remove_cloned_vm
)


logger = logging.getLogger(__name__)

# DON'T REMOVE THIS, larger disk size are needed when cloning multiple
# disks since new snapshots will be bigger than the minimum size
DISK_SIZE = 3 * config.GB
SNAPSHOT_NAME = None


@pytest.fixture(scope='module', autouse=True)
def create_vm_with_snapshot(request):
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    global VM_NAMES, SNAPSHOT_NAME

    def finalizer_module():
        ll_vms.safely_remove_vms(VM_NAMES.values())

    request.addfinalizer(finalizer_module)
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = "base_vm_%s" % storage_type
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['vmDescription'] = vm_name

        if not helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        VM_NAMES[storage_type] = vm_name
        SNAPSHOT_NAME = helpers.create_unique_object_name(
            "base_%s" % storage_type, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.setup("Creating snapshot of for VM %s", vm_name)
        assert ll_vms.addSnapshot(True, vm_name, SNAPSHOT_NAME)


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    initialize_vm.__name__,
    remove_vms.__name__,
)
class BaseTestCase(TestCase):
    """
    Base Test Case for clone snapshot
    """
    snapshot = "snapshot_%s"
    __test__ = False
    # Disable cli, check ticket RHEVM-2238
    jira = {'RHEVM-2238': None}

    def add_disk(self, disk_alias):
        """
        Add disk with alias 'disk_alias' to vm
        """
        assert ll_disks.addDisk(
            True, alias=disk_alias, provisioned_size=DISK_SIZE,
            storagedomain=self.storage_domain,
            sparse=True, interface=config.VIRTIO_SCSI,
            format=config.COW_DISK
        )

        assert ll_disks.wait_for_disks_status(disks=[disk_alias])
        assert ll_disks.attachDisk(True, disk_alias, self.vm_name)
        assert ll_disks.wait_for_disks_status(disks=[disk_alias])
        assert ll_vms.wait_for_vm_disk_active_status(
            self.vm_name, True, diskAlias=disk_alias, sleep=1
        )

    def clone_vm_from_snapshot(
        self, cloned_vm_name, snapshot, sparse=True, vol_format=config.COW_DISK
    ):
        testflow.step(
            "Cloning vm %s from snapshot %s", cloned_vm_name, snapshot
        )
        assert ll_vms.cloneVmFromSnapshot(
            True, name=cloned_vm_name, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=snapshot,
            storagedomain=self.storage_domain_1, vol_format=vol_format,
            sparse=sparse, compare=False
        )
        assert ll_vms.waitForVMState(cloned_vm_name, state=config.VM_DOWN), (
            "VM %s is not in status down" % cloned_vm_name
        )
        self.vm_names.append(cloned_vm_name)


@attr(tier=2)
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

    @polarion("RHEVM3-6103")
    def test_clone_vm_from_snapshot(self):
        """
        Test that Clone from a vm snapshot works.
        """
        self.cloned_vm = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(self.cloned_vm, SNAPSHOT_NAME)
        testflow.step("Starting VM %s and waiting for IP", self.cloned_vm)
        assert ll_vms.startVm(True, self.cloned_vm, wait_for_ip=True), (
            "Starting VM %s encounter issues" % self.cloned_vm
        )


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

    @polarion("RHEVM3-6119")
    def test_clone_vm_from_snapshot_select_storage(self):
        """
        Test the sd, type and format can be selected
        """
        self.cloned_vm = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(
            self.cloned_vm, SNAPSHOT_NAME, sparse=False,
            vol_format=config.RAW_DISK
        )


@attr(tier=3)
class TestCase6120(BaseTestCase):
    """
    Create VM from snapshot while original VM is Down ->  Success
    Create VM from snapshot while original VM is Up   ->  Success

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
        self.cloned_vm_down = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(self.cloned_vm_down, SNAPSHOT_NAME)

        assert ll_vms.startVm(True, self.vm_name, wait_for_status=config.VM_UP)

        self.cloned_vm_up = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(self.cloned_vm_up, SNAPSHOT_NAME)


@attr(tier=3)
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

    @polarion("RHEVM3-6122")
    def test_clone_vm_name_validation(self):
        """
        Test for vm name property and duplicity
        """
        self.cloned_vm = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(self.cloned_vm, SNAPSHOT_NAME)
        assert ll_vms.searchForVm(True, 'name', self.cloned_vm, 'name')

        testflow.step("Trying to clone a vm's snapshot with the same name")

        assert ll_vms.cloneVmFromSnapshot(
            False, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False
        )

        testflow.step(
            "Trying to clone a vm's snapshot with invalid characters"
        )
        illegal_characters = "* are not allowed"

        assert ll_vms.cloneVmFromSnapshot(
            False, name=illegal_characters, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False
        )


@attr(tier=3)
@pytest.mark.usefixtures(
    remove_additional_nic.__name__,
    remove_additional_snapshot.__name__,
)
class TestCase6108(BaseTestCase):
    """
    Clone a vm with multiple nics.
    Verify the clone is successful and all nics are cloned.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6108"
    snapshot_to_remove = "snapshot_with_two_nics"

    @polarion("RHEVM3-6108")
    def test_clone_vm_multiple_nics(self):
        """
        Add a new nic to the self.vm_name, make a snapshot and clone it.
        """
        testflow.step("Adding nic to %s", self.vm_name)
        assert ll_vms.addNic(
            True, self.vm_name, name="nic2", network=config.MGMT_BRIDGE,
            interface=config.NIC_TYPE_VIRTIO
        )
        assert len(
            ll_vms.get_vm_nics_obj(self.vm_name)
        ) == 2, "VM %s should have 2 nics" % self.vm_name
        testflow.step(
            "Taking a snapshot %s from VM %s",
            self.snapshot_to_remove, self.vm_name
        )
        assert ll_vms.addSnapshot(True, self.vm_name, self.snapshot_to_remove)
        self.cloned_vm = helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.clone_vm_from_snapshot(self.cloned_vm, self.snapshot_to_remove)
        assert len(ll_vms.get_vm_nics_obj(self.cloned_vm)) == 2


@attr(tier=2)
@pytest.mark.usefixtures(
    remove_additional_snapshot.__name__,
    delete_disks.__name__,
    remove_cloned_vm.__name__,
)
class TestCase6109(BaseTestCase):
    """
    Clone a vm with multiple disks.
    Verify the clone is successful and all disks are cloned.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6109"
    snapshot_to_remove = "snapshot_%s" % polarion_case_id
    disk_alias = "second_disk_%s" % polarion_case_id

    @polarion("RHEVM3-6109")
    def test_clone_vm_multiple_disks(self):
        """
        Verify the cloned vm contains multiple disks
        """
        testflow.step("Adding disk to vm %s", self.vm_name)
        assert 1 == len(ll_vms.getVmDisks(self.vm_name))
        self.add_disk(self.disk_alias)
        self.disks_to_remove.append(self.disk_alias)

        testflow.step(
            "Taking a snapshot %s from VM %s",
            self.snapshot_to_remove, self.vm_name
        )
        assert ll_vms.addSnapshot(True, self.vm_name, self.snapshot_to_remove)
        self.clone_vm_from_snapshot(self.cloned_vm, self.snapshot_to_remove)

        assert len(ll_vms.getVmDisks(self.cloned_vm)) == 2


@attr(tier=3)
@pytest.mark.usefixtures(
    create_server_vm_with_snapshot.__name__,
)
class TestCase6111(BaseTestCase):
    """
    Clone a desktop and a server VM.
    Verify that clone is successful and is the proper type.

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Clone_VM_From_Snapshot
    """
    __test__ = True
    polarion_case_id = "6111"
    cloned_vm_desktop = "cloned_desktop_%s" % polarion_case_id
    vm_server = "vm_server_%s" % polarion_case_id
    snapshot_server = "snapshot_server_%s" % polarion_case_id
    cloned_vm_server = "cloned_server_%s" % polarion_case_id

    @polarion("RHEVM3-6111")
    def test_clone_vm_type_desktop_server(self):
        """
        Verify that desktop and server types are preserved after cloning
        """
        # Base vm should be type desktop
        assert config.VM_TYPE_DESKTOP == ll_vms.get_vm(self.vm_name).get_type()
        testflow.step("Cloning vm %s", self.vm_name)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_desktop, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=SNAPSHOT_NAME,
            storagedomain=self.storage_domain_1, compare=False
        )
        self.vm_names.append(self.cloned_vm_desktop)

        assert config.VM_TYPE_DESKTOP == ll_vms.get_vm(
            self.cloned_vm_desktop
        ).get_type()

        assert config.VM_TYPE_SERVER == ll_vms.get_vm(
            self.vm_server
        ).get_type()
        testflow.step("Cloning vm %s", self.vm_server)

        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_server, cluster=config.CLUSTER_NAME,
            vm=self.vm_server, snapshot=self.snapshot_server,
            storagedomain=self.storage_domain_1, compare=False)
        self.vm_names.append(self.cloned_vm_server)
        assert config.VM_TYPE_SERVER == ll_vms.get_vm(
            self.cloned_vm_server
        ).get_type()


@attr(tier=3)
@pytest.mark.usefixtures(
    remove_additional_snapshot.__name__,
    delete_disks.__name__,
    remove_cloned_vm.__name__,
)
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
    cloned_vm = "cloned_vm_%s" % polarion_case_id
    disk_alias = "second_disk_%s" % polarion_case_id
    disk_alias2 = "third_disk_%s" % polarion_case_id
    snapshot_to_remove = "snapshot_multiple_disks_%s" % polarion_case_id

    @polarion("RHEVM3-6112")
    def test_clone_vm_after_deleting_disk(self):
        """
        Test only existing disks are cloned even if it were snapshoted.
        """
        assert 1 == len(ll_vms.getVmDisks(self.vm_name))
        testflow.step("Adding 2 disks to VM %s", self.vm_name)
        self.add_disk(self.disk_alias)
        self.disks_to_remove.append(self.disk_alias)
        self.add_disk(self.disk_alias2)
        self.disks_to_remove.append(self.disk_alias2)
        assert 3 == len(ll_vms.getVmDisks(self.vm_name))
        self.disk_obj = ll_disks.get_disk_obj(self.disk_alias)
        self.disk_obj_2 = ll_disks.get_disk_obj(self.disk_alias2)

        testflow.step(
            "Taking a snapshot %s from VM %s",
            self.snapshot_to_remove, self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_to_remove
        )
        testflow.step("Removing disk %s", self.disk_alias)
        ll_vms.delete_snapshot_disks(
            self.vm_name, self.snapshot_to_remove, self.disk_obj.get_id()
        )
        ll_jobs.wait_for_jobs([config.ENUMS['job_remove_snapshots_disk']])

        testflow.step("Cloning VM %s", self.vm_name)
        self.clone_vm_from_snapshot(
            self.cloned_vm, self.snapshot_to_remove
        )
        cloned_disks = ll_vms.getVmDisks(self.cloned_vm)
        disks = [disk.name for disk in cloned_disks]
        assert len(disks) == 2
        assert self.disk_alias2 in disks
        assert not (self.disk_alias in disks)
