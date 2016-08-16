"""
3.4 Feature: Read only (RO) disk
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_RO_Disks
"""
import logging
import config
import helpers
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.networking.helper import seal_vm
from rhevmtests.storage import helpers as storage_helpers


logger = logging.getLogger(__name__)

DISK_TIMEOUT = 600
REMOVE_SNAPSHOT_TIMEOUT = 900
TEMPLATE_TIMEOUT = 360
DISK_NAMES = helpers.DISK_NAMES
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'

ISCSI = config.STORAGE_TYPE_ISCSI
NFS = config.STORAGE_TYPE_NFS


def not_bootable(vm_name):
    """
    Get the vm's disks except the bootable disk

    :param vm_name: Name of vm
    :type vm_name: str
    :return: List of disk objects
    :rtype: list
    """
    return [
        disk for disk in ll_vms.getVmDisks(vm_name) if not
        ll_vms.is_bootable_disk(vm_name, disk.get_id()) and
        ll_vms.is_active_disk(vm_name, disk.get_id())
    ]


class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    __test__ = False
    deep_copy = False

    def setUp(self):
        global DISK_NAMES
        self.vm_name = config.VM_NAME % self.storage
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['deep_copy'] = self.deep_copy

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        DISK_NAMES[self.storage] = list()

    def prepare_disks_for_vm(self, read_only, vm_name=None):
        """Attach read-only disks to the vm"""
        vm_name = self.vm_name if not vm_name else vm_name
        return storage_helpers.prepare_disks_for_vm(
            vm_name, DISK_NAMES[self.storage], read_only=read_only
        )

    def set_persistent_network(self, vm_name=None):
        """Set persistent network to vm"""
        vm_name = self.vm_name if not vm_name else vm_name
        ll_vms.start_vms([vm_name], max_workers=1, wait_for_ip=True)
        assert ll_vms.waitForVMState(vm_name)
        vm_ip = storage_helpers.get_vm_ip(vm_name)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        ll_vms.stop_vms_safely([vm_name])
        assert ll_vms.waitForVMState(vm_name, config.VM_DOWN)

    def verify_snapshot_disks_are_ro(self, vm_name, snapshot):
        """
        Verifies that the snapshot's disks are read-only

        :param vm_name: The vm that contains the snapshot to verify
        :type vm_name: str
        :param snapshot: Snapshot that contains the disks to verify
        :type snapshot: str
        :raises: DiskException
        """
        snap_disks = ll_vms.get_snapshot_disks(vm_name, snapshot)
        ro_vm_disks = not_bootable(vm_name)
        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that read-only disk %s is part of the snapshot",
                ro_disk.get_alias()
            )
            is_part_of_disks = ro_disk.get_id() in [
                d.get_id() for d in snap_disks
            ]

            if not is_part_of_disks:
                raise exceptions.DiskException(
                    "read-only disk %s is not part of the snapshot that "
                    "was taken" % ro_disk.get_alias()
                )

    def tearDown(self):
        """
        Clean environment
        """
        ll_vms.waitForVmsDisks(self.vm_name)
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to stop and remove vm %s" % self.vm_name)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


class DefaultEnvironment(BaseTestCase):
    """
    A class with common setup and teardown methods
    """
    spm = None
    shared = False
    polarion_test_case = None

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        global DISK_NAMES
        super(DefaultEnvironment, self).setUp()
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        DISK_NAMES[self.storage] = (
            storage_helpers.create_disks_from_requested_permutations(
                domain_to_use=self.storage_domains[0],  size=config.DISK_SIZE,
                shared=self.shared, test_name=self.polarion_test_case
            )
        )
        assert ll_disks.wait_for_disks_status(
            DISK_NAMES[self.storage], timeout=DISK_TIMEOUT
        )


class DefaultSnapshotEnvironment(DefaultEnvironment):
    """
    A class with common setup and teardown methods
    """

    __test__ = False

    spm = None
    snapshot_description = 'test_snap'

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        super(DefaultSnapshotEnvironment, self).setUp()
        self.prepare_disks_for_vm(read_only=True)

        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        )


@attr(tier=2)
class TestCase4906(DefaultEnvironment):
    """
    Attach a read-only disk to vm and try to write to the disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4906'

    @polarion("RHEVM3-4906")
    def test_attach_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk
        """
        self.prepare_disks_for_vm(read_only=True)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=2)
class TestCase4907(BaseTestCase):
    """
    Attach a read-only direct LUN disk to vm and try to write to the disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4907'
    # Bugzilla history:
    # 1220824:[REST] Adding a disk to a vm fails with NullPointerException if
    # not disk.storage_domains is provided

    @polarion("RHEVM3-4907")
    @bz({'957788': {}})
    def test_attach_RO_direct_LUN_disk(self):
        """
        - VM with OS
        - Attach a second read-only direct LUN disk to the VM
        - Activate the disk
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk:
        """
        for i, interface in enumerate([config.VIRTIO, config.VIRTIO_SCSI]):
            disk_alias = "direct_lun_disk_%s" % interface
            direct_lun_args = {
                'wipe_after_delete': True,
                'bootable': False,
                'shareable': False,
                'active': True,
                'format': config.COW_DISK,
                'interface': interface,
                'alias': disk_alias,
                'lun_address': config.DIRECT_LUN_ADDRESSES[i],
                'lun_target': config.DIRECT_LUN_TARGETS[i],
                'lun_id': config.DIRECT_LUNS[i],
                "type_": self.storage}

            logger.info("Creating disk %s", disk_alias)
            assert ll_disks.addDisk(True, **direct_lun_args)
            DISK_NAMES[self.storage].append(disk_alias)

            logger.info("Attaching disk %s as read-only disk to vm %s",
                        disk_alias, self.vm_name)
            status = ll_disks.attachDisk(
                True, disk_alias, self.vm_name, active=True,
                read_only=True
            )
            self.assertTrue(status, "Failed to attach direct lun as read-only")
            ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
            helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=2)
class TestCase4908(DefaultEnvironment):
    """
    Attach a read-only shared disk to vm and try to write to the disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # Gluster doesn't support shareable disks
    __test__ = ISCSI in opts['storages'] or NFS in opts['storages']
    storages = set([ISCSI, NFS])
    polarion_test_case = '4908'
    test_vm_name = ''

    def setUp(self):
        self.shared = True
        super(TestCase4908, self).setUp()
        self.prepare_disks_for_vm(read_only=False)

        self.test_vm_name = 'test_%s' % self.polarion_test_case
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.test_vm_name
        vm_args['storageDomainName'] = self.storage_domains[0]

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.test_vm_name
            )

    @polarion("RHEVM3-4908")
    def test_shared_RO_disk(self):
        """
        - 2 VMs with OS
        - Add a second disk to VM1 as shared disk
        - Attach VM1 shared disk to VM2 as read-only disk and activate it
        - On VM2, Verify that it's impossible to write to the read-only disk
        """
        self.prepare_disks_for_vm(read_only=True, vm_name=self.test_vm_name)

        ll_vms.start_vms([self.test_vm_name], 1, wait_for_ip=True)
        for disk in DISK_NAMES[self.storage]:
            logger.info("Trying to write to read-only disk %s", disk)
            state, out = storage_helpers.perform_dd_to_disk(
                self.test_vm_name, disk
            )
            status = (not state) and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")

    def tearDown(self):
        if not ll_vms.safely_remove_vms([self.test_vm_name]):
            logger.error(
                "Failed to stop and remove vm %s" % self.test_vm_name
            )
            BaseTestCase.test_failed = True
        super(TestCase4908, self).tearDown()
        for disk in DISK_NAMES[self.storage]:
            if not ll_disks.deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)
                BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4909(DefaultEnvironment):
    """
    Verifies that read-only shared disk is persistent after snapshot is
    taken to a shared disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # Gluster doesn't support shareable disks
    __test__ = ISCSI in opts['storages'] or NFS in opts['storages']
    storages = set([ISCSI, NFS])
    polarion_test_case = '4909'
    snapshot_description = 'test_snap'
    test_vm_name = ''

    def setUp(self):
        self.shared = True
        super(TestCase4909, self).setUp()

        self.prepare_disks_for_vm(read_only=False)

        self.test_vm_name = 'test_%s' % self.polarion_test_case
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.test_vm_name
        vm_args['storageDomainName'] = self.storage_domains[0]

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)

    @polarion("RHEVM3-4909")
    def test_RO_persistent_after_snapshot_creation_to_a_shared_disk(self):
        """
        - 2 VMs with OS
        - On one of the VM, create a second shared disk
        - Attach the shared disk also to the second vm as read-only
        - Check that the disk is actually read-only for the second VM
        - Create a snapshot to the first VM that sees the disk as RW
        - Check that the disk is still read-only for the second VM
        """
        self.prepare_disks_for_vm(read_only=True, vm_name=self.test_vm_name)
        ro_vm_disks = not_bootable(self.test_vm_name)
        rw_vm_disks = not_bootable(self.vm_name)

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info(
                'check if disk %s is visible as read-only to vm %s'
                % (ro_disk.get_alias(), self.test_vm_name)
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as read-only disk"
                % (ro_disk.get_alias(), self.test_vm_name)
            )
        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        )
        ro_vm_disks = not_bootable(self.test_vm_name)
        rw_vm_disks = not_bootable(self.vm_name)

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info(
                'check if disk %s is still visible as read-only to vm %s'
                ' after snapshot was taken', ro_disk.get_alias(),
                self.test_vm_name
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as read-only disk"
                % (ro_disk.get_alias(), self.test_vm_name)
            )

    def tearDown(self):
        if not ll_vms.safely_remove_vms([self.test_vm_name]):
            logger.error(
                "Failed to stop and remove vm %s" % self.test_vm_name
            )
            BaseTestCase.test_failed = True
        super(TestCase4909, self).tearDown()
        for disk in DISK_NAMES[self.storage]:
            if not ll_disks.deleteDisk(True, disk):
                logger.error("Failed to remove disk %s", disk)
                BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4910(BaseTestCase):
    """
    Checks that changing disk's write policy from RW to read-only will fails
    when the disk is active
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4910'

    @polarion("RHEVM3-4910")
    def test_change_disk_from_RW_to_RO(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Try to change the permissions to read-only. It should fail
          because the disk is active
        - Deactivate the disk and change the VM permissions on the disk
          to read-only
        - Activate the disk
        """
        DISK_NAMES[self.storage] = (
            storage_helpers.create_disks_from_requested_permutations(
                domain_to_use=self.storage_domain,
                test_name=self.polarion_test_case
            )
        )
        ll_vms.start_vms(
            [self.vm_name], 1, wait_for_status=config.VM_UP, wait_for_ip=False
        )
        self.prepare_disks_for_vm(read_only=False)

        vm_disks = ll_vms.getVmDisks(self.vm_name)
        for disk in [vm_disk.get_alias() for vm_disk in vm_disks]:
            status = ll_vms.updateDisk(
                False, vmName=self.vm_name, alias=disk, read_only=True
            )
            self.assertTrue(
                status, "Succeeded to change RW disk %s to read-only" % disk
            )
            assert ll_vms.deactivateVmDisk(True, self.vm_name, disk)

            status = ll_vms.updateDisk(
                True, vmName=self.vm_name, alias=disk, read_only=True
            )
            self.assertTrue(
                status, "Failed to change RW disk %s to read-only" % disk
            )


@attr(tier=2)
class TestCase4912(BaseTestCase):
    """
    Check that booting from read-only disk should be impossible
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4912'

    @polarion("RHEVM3-4912")
    def test_boot_from_RO_disk(self):
        """
        - VM with OS
        - Detach the disk from the VM
        - Edit the disk and change it to be read-only to the VM
        - Start the VM, boot it from its hard disk which is supposed to
          be read-only
        """


@attr(tier=4)
class TestCase4913(DefaultEnvironment):
    """
    Block connectivity from vdsm to the storage domain
    where the VM read-only disk is located
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4913'
    blocked = False
    storage_domain_ip = ''
    # BZ history:
    # 1138144: Failed to autorecover storage domain after unblocking connection
    # with host

    @polarion("RHEVM3-4913")
    def test_RO_persistent_after_block_connectivity_to_storage(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Write to the disk from the guest, it shouldn't be allowed
        - Block connectivity from vdsm to the storage domain
          where the VM disk is located
        - VM should enter to 'paused' state
        - Resume connectivity to the storage and wait for the
          VM to start again
        - Write to the disk from the guest, it shouldn't be allowed
        """
        self.prepare_disks_for_vm(read_only=True)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)

        for disk in DISK_NAMES[self.storage]:
            logger.info("Trying to write to read-only disk %s", disk)
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk
            )
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")

        storage_domain_name = (
            ll_vms.get_vms_disks_storage_domain_name(self.vm_name)
        )
        found, self.storage_domain_ip = ll_sd.getDomainAddress(
            True, storage_domain_name
        )
        assert found
        logger.info(
            "Found IP %s for storage domain %s",
            self.storage_domain_ip, storage_domain_name
        )
        self.host_ip = ll_hosts.getHostIP(
            ll_hosts.getVmHost(self.vm_name)[1]['vmHoster']
        )
        logger.info("Blocking connection from vdsm to storage domain")
        status = blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        )
        self.assertTrue(
            status, "Blocking connection from %s to %s failed"
            % (self.host_ip, self.storage_domain_ip)
        )
        if status:
            self.blocked = True

        assert ll_vms.waitForVMState(self.vm_name, state=config.VM_PAUSED)

        logger.info("Unblocking connection from vdsm to storage domain")
        status = unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        )
        if status:
            self.blocked = False

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        for disk in DISK_NAMES[self.storage]:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk
            )
            logger.info("Trying to write to read-only disk...")
            status = (not state) and ((READ_ONLY in out) or
                                      (NOT_PERMITTED in out))
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")

    def tearDown(self):
        """
        Unblocking connection in case test fails
        """
        if self.blocked:
            logger.info(
                "Unblocking connectivity from host %s to storage domain %s",
                self.host_ip, self.storage_domains[0]
            )

            logger.info("Unblocking connection from vdsm to storage domain")
            status = unblockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
                self.storage_domain_ip
            )

            if not status:
                logger.error(
                    "Failed to unblock connectivity from host %s to "
                    "storage domain %s", (self.host, self.storage_domain_ip)
                )
                BaseTestCase.test_failed = True
        super(TestCase4913, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4914(DefaultEnvironment):
    """
    Migrate a vm with read-only disk, and check the disk is still
    visible as read-only
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4914'
    is_migrated = False

    @polarion("RHEVM3-4914")
    def test_migrate_vm_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - migrate the VM to another host
        - Check that disk is visible to the VM
        - Check that engine still reports the VM disk as read-only
        - Verify that it's impossible to write to the disk
        """
        self.prepare_disks_for_vm(read_only=True)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        assert ll_vms.waitForVMState(self.vm_name)
        vm_disks = not_bootable(self.vm_name)
        for ro_disk in vm_disks:
            logger.info(
                'check if disk %s is visible as read-only to vm %s'
                % (ro_disk.get_alias(), self.vm_name)
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as read-only disk"
                % (ro_disk.get_alias(), self.vm_name)
            )
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        assert ll_vms.waitForVMState(self.vm_name)
        self.is_migrated = ll_vms.migrateVm(True, self.vm_name)
        vm_disks = not_bootable(self.vm_name)
        for ro_disk in vm_disks:
            logger.info(
                'check if disk %s is still visible as read-only to vm %s'
                'after migration', ro_disk.get_alias(), self.vm_name
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only, "Disk %s is not visible to vm %s as Read "
                "Only disk" % (ro_disk.get_alias(), self.vm_name)
            )


@attr(tier=2)
class TestCase4915(DefaultEnvironment):
    """
    Checks that suspending a vm with read-only disk shouldn't
    change disk configuration
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4915'

    @polarion("RHEVM3-4915")
    def test_RO_disk_persistent_after_suspend_the_vm(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Suspend the VM
        - Re-activate the VM
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk
        """
        self.prepare_disks_for_vm(read_only=True)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        assert ll_vms.waitForVMState(self.vm_name)
        logger.info("Suspending vm %s", self.vm_name)
        ll_vms.suspendVm(True, self.vm_name)
        logger.info("Re activating vm %s", self.vm_name)
        ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=2)
class TestCase4917(DefaultEnvironment):
    """
    Import more than once VM with read-only disk, and verify that it's
    impossible to write to the disk for both the original and the imported VMs
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4917'
    imported_vm_1 = 'imported_vm_1'
    imported_vm_2 = 'imported_vm_2'
    export_domain = ''
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot
    # Same issue happens after the vm is imported

    def setUp(self):
        self.deep_copy = True
        super(TestCase4917, self).setUp()

    @polarion("RHEVM3-4917")
    @bz({'1309788': {}})
    def test_import_more_than_once_VM_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Export the VM to an export domain
        - Import the same VM twice
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk:
        """
        self.vm_exported = False
        self.prepare_disks_for_vm(read_only=True)

        logger.info("Setting persistent network configuration")
        seal_vm(self.vm_name, config.VM_PASSWORD)

        self.export_domain = ll_sd.findExportStorageDomains(
            config.DATA_CENTER_NAME
        )[0]

        logger.info("Exporting vm %s", self.vm_name)
        self.vm_exported = ll_vms.exportVm(
            True, self.vm_name, self.export_domain
        )
        self.assertTrue(
            self.vm_exported, "Couldn't export vm %s" % self.vm_name
        )
        logger.info(
            "Importing vm %s as %s", self.vm_name, self.imported_vm_1
        )
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domains[0],
            config.CLUSTER_NAME, name=self.imported_vm_1
        )
        ll_vms.start_vms(
            [self.imported_vm_1], max_workers=1, wait_for_ip=False
        )
        assert ll_vms.waitForVMState(self.imported_vm_1)

        logger.info(
            "Importing vm %s as %s", self.vm_name, self.imported_vm_2
        )
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domains[0],
            config.CLUSTER_NAME, name=self.imported_vm_2
        )
        ll_vms.start_vms(
            [self.imported_vm_2], max_workers=1, wait_for_ip=True
        )
        helpers.write_on_vms_ro_disks(
            self.imported_vm_1, self.storage, imported_vm=True
        )
        helpers.write_on_vms_ro_disks(
            self.imported_vm_2, self.storage, imported_vm=True
        )

    def tearDown(self):
        vm_list = filter(
            ll_vms.does_vm_exist, [self.imported_vm_1, self.imported_vm_2]
        )
        if not ll_vms.safely_remove_vms(vm_list):
            logger.error("Failed to stop and remove vms %s" % vm_list)
            BaseTestCase.test_failed = True
        if self.vm_exported and not ll_vms.remove_vm_from_export_domain(
                True, vm=self.vm_name, datacenter=config.DATA_CENTER_NAME,
                export_storagedomain=self.export_domain
        ):
            logger.error(
                "Failed to remove vm %s from export domain %s",
                self.imported_vm, self.export_domain
            )
            BaseTestCase.test_failed = True
        super(TestCase4917, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4918(DefaultSnapshotEnvironment):
    """
    Check that the read-only disk is part of vm snapshot, and also
    after preview
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4918'
    snapshot_description = 'test_snap'
    create_snapshot = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @rhevm_helpers.wait_for_jobs_deco(
        [config.JOB_CREATE_SNAPSHOT, config.JOB_PREVIEW_SNAPSHOT]
    )
    @polarion("RHEVM3-4918")
    def test_preview_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the read-only disk is part of the snapshot
        - Shutdown the VM and preview the snapshot. Start the VM
          and try to write to the read-only disk
        """
        self.verify_snapshot_disks_are_ro(
            self.vm_name, self.snapshot_description
        )
        logger.info("Previewing snapshot %s", self.snapshot_description)
        self.create_snapshot = ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )

        assert self.create_snapshot
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not ll_vms.undo_snapshot_preview(True, self.vm_name):
                logger.error("Error undoing snapshot snapshot preview for %s",
                             self.vm_name)
                BaseTestCase.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )

        super(TestCase4918, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4919(DefaultSnapshotEnvironment):
    """
    Check that the read-only disk is part of vm snapshot, and the disk
    should be remain read-only for the VM after undoing the snapshot.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4919'
    snapshot_description = 'test_snap'
    create_snapshot = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-4919")
    def test_preview_and_undo_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the read-only disk is part of the snapshot
        - Shutdown the VM, preview and undo the snapshot.
        - Start the VM and try to write to the read-only disk
        """
        self.verify_snapshot_disks_are_ro(
            self.vm_name, self.snapshot_description
        )
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )
        self.create_snapshot = status

        self.assertTrue(
            status, "Failed to preview snapshot %s" % self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )
        logger.info("Undoing snapshot %s", self.snapshot_description)
        status = ll_vms.undo_snapshot_preview(True, self.vm_name)
        self.assertTrue(
            status, "Failed to undo vm's snapshot %s" %
            self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK]
        )
        self.create_snapshot = not status
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        if not ll_vms.stop_vms_safely([self.vm_name]):
            logger.error("Failed to stop vm %s", self.vm_name)
            BaseTestCase.test_failed = True
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not ll_vms.undo_snapshot_preview(True, self.vm_name):
                logger.error("Error undoing snapshot for %s", self.vm_name)
                BaseTestCase.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )
        super(TestCase4919, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4920(DefaultSnapshotEnvironment):
    """
    Check that the read-only disk is part of vm snapshot, and the disk
    should be remain read-only for the VM after committing the snapshot.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4920'
    snapshot_description = 'test_snap'
    create_snapshot = False
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-4920")
    def test_preview_and_commit_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the read-only disk is part of the snapshot
        - Shutdown the VM, preview and commit the snapshot.
        - Start the VM and try to write to the read-only disk
        """
        self.verify_snapshot_disks_are_ro(
            self.vm_name, self.snapshot_description
        )
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )
        self.create_snapshot = True
        assert status
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )

        logger.info("Committing snapshot %s", self.snapshot_description)
        status = ll_vms.commit_snapshot(True, self.vm_name)
        assert status
        self.create_snapshot = not status
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not ll_vms.undo_snapshot_preview(True, self.vm_name):
                logger.error("Error undoing snapshot for %s", self.vm_name)
                BaseTestCase.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )
        super(TestCase4920, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4921(DefaultSnapshotEnvironment):
    """
    Checks that deleting a snapshot with read-only disk shouldn't effect
    the read-only disk
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4921'
    snapshot_description = 'test_snap'
    snapshot_removed = False

    @polarion("RHEVM3-4921")
    def test_delete_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the read-only disk is part of the snapshot
        - Shutdown the VM and delete the snapshot.
        - Start the VM and try to write to the read-only disk
        """
        self.verify_snapshot_disks_are_ro(
            self.vm_name, self.snapshot_description
        )
        logger.info("Removing snapshot %s", self.snapshot_description)
        status = ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_description,
            timeout=REMOVE_SNAPSHOT_TIMEOUT,
        )
        self.snapshot_removed = status
        self.assertTrue(
            status, "Failed to remove snapshot %s from vm %s"
            % (self.snapshot_description, self.vm_name)
        )
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=2)
class TestCase4922(DefaultEnvironment):
    """
    Checks that a cloned vm from a snapshot with read-only disk shouldn't
    be able to write to the read-only disk as well
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4922'
    snapshot_description = 'test_snap'
    cloned = False
    cloned_vm_name = 'cloned_vm'

    @polarion("RHEVM3-4922")
    @bz({'1201268': {}})
    def test_clone_vm_from_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the read-only disk is part of the snapshot
        - Clone a new VM from the snapshot
        - Try to write to the read-only disk of the cloned VM
        """
        self.prepare_disks_for_vm(read_only=True)
        seal_vm(self.vm_name, config.VM_PASSWORD)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], [self.snapshot_description],
        )
        self.verify_snapshot_disks_are_ro(
            self.vm_name, self.snapshot_description
        )
        status = ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm_name, snapshot=self.snapshot_description,
            cluster=config.CLUSTER_NAME, vm=self.vm_name
        )
        if status:
            self.cloned = True

        self.assertTrue(status, "Failed to clone vm from snapshot")
        ll_vms.start_vms([self.cloned_vm_name], 1, wait_for_ip=True)
        ro_vm_disks = not_bootable(self.vm_name)
        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.cloned_vm_name, disk.get_alias(),
            )
            logger.info("Trying to write to read-only disk %s", disk)
            status = (not state) and ((READ_ONLY in out) or
                                      (NOT_PERMITTED in out))
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")

    def tearDown(self):
        if self.cloned:
            if not ll_vms.removeVm(
                    True, self.cloned_vm_name, stopVM='true', wait=True
            ):
                logger.error(
                    "Failed to remove cloned vms %s", self.cloned_vm_name
                )
                BaseTestCase.test_failed = True
        super(TestCase4922, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4923(DefaultEnvironment):
    """
    Create 2 VMs from a template with read-only disk in 2 provisioning methods:
    the first cloned from template and the second as thin copy.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4923'
    template_name = 'test_template'
    cloned_vm_name = 'cloned_vm'
    thin_cloned_vm_name = 'thin_cloned_vm'
    cloned_vms = [cloned_vm_name, thin_cloned_vm_name]
    cloned = False

    @polarion("RHEVM3-4923")
    def test_create_vms_from_template_with_RO_disk(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Create a template from the VM
        - Create 2 VMs from the template in 2 provisioning methods:
            * the first cloned from template
            * the second as thin copy
        - Check that for the second disk of the new VMs, engine reports
          that its read-only
        - Try to write to that disk from both the VMs
        """
        self.prepare_disks_for_vm(read_only=True)
        logger.info("Setting persistent network configuration")
        seal_vm(self.vm_name, config.VM_PASSWORD)

        logger.info("creating template %s", self.template_name)
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domains[0]
        )
        logger.info("Cloning vm from template")
        self.cloned = ll_vms.cloneVmFromTemplate(
            True, self.cloned_vm_name, self.template_name, config.CLUSTER_NAME,
            storagedomain=self.storage_domains[0]
        )
        self.assertTrue(self.cloned, "Failed to clone vm from template")

        logger.info("Cloning vm from template as Thin copy")
        self.cloned = ll_vms.cloneVmFromTemplate(
            True, self.thin_cloned_vm_name, self.template_name,
            config.CLUSTER_NAME, clone=False
        )
        self.assertTrue(self.cloned, "Failed to clone vm from template")
        ll_vms.start_vms(self.cloned_vms, 2, wait_for_ip=True)
        for vm in self.cloned_vms:
            cloned_vm_disks = ll_vms.getVmDisks(vm)
            cloned_vm_disks = [
                disk for disk in cloned_vm_disks if not
                ll_vms.is_bootable_disk(vm, disk.get_id())
            ]

            for disk in cloned_vm_disks:
                logger.info(
                    'check if disk %s is visible as read-only to vm %s',
                    disk.get_alias(), vm
                )
                is_read_only = disk.get_read_only()
                self.assertTrue(
                    is_read_only,
                    "Disk %s is not visible to vm %s as read-only disk"
                    % (disk.get_alias(), vm)
                )

                logger.info("Trying to write to read-only disk %s", disk)
                state, out = storage_helpers.perform_dd_to_disk(
                    vm, disk.get_alias(),
                )
                status = (not state) and ((READ_ONLY in out) or
                                          (NOT_PERMITTED in out))
                self.assertTrue(
                    status, "Write operation to read-only disk succeeded"
                )
                logger.info("Failed to write to read-only disk")

    def tearDown(self):
        if self.cloned:
            if not ll_vms.removeVms(True, self.cloned_vms, stop='true'):
                logger.error("Failed to remove cloned vms")
                BaseTestCase.test_failed = True
        ll_templates.waitForTemplatesStates(self.template_name)

        if not ll_templates.removeTemplate(
                True, self.template_name, timeout=TEMPLATE_TIMEOUT
        ):
            logger.error(
                "Failed to remove template %s", self.template_name
            )
            BaseTestCase.test_failed = True
        super(TestCase4923, self).tearDown()
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase4924(DefaultEnvironment):
    """
    Checks that moving read-only disk to a second storage domain will
    cause that the disk should remain read-only for the VM after the move
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4924'
    # Bugzilla history:
    # 1196049, 1176673: After live storage migration on block storage vdsm
    # extends migrated drive using all free space in the vg

    @polarion("RHEVM3-4924")
    def test_moving_RO_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
          and plug it to the VM
        - Try to write to the disk, it should not be allowed
        - Unplug the disk from the VM
        - Try to move the disk to the second storage domain
          while disk is unplugged and read-only
        """
        self.prepare_disks_for_vm(read_only=True)
        ro_vm_disks = not_bootable(self.vm_name)
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk.get_alias(),
            )
            logger.info(
                "Trying to write to read-only disk %s...", disk.get_alias(),
            )
            status = (not state) and (READ_ONLY in out) or (NOT_PERMITTED
                                                            in out)
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")

        for index, disk in enumerate(ro_vm_disks):
            logger.info("Unplugging vm disk %s", disk.get_alias())
            assert ll_vms.deactivateVmDisk(
                True, self.vm_name, disk.get_alias()
            )
            ll_vms.move_vm_disk(
                self.vm_name, disk.get_alias(), self.storage_domains[1]
            )
            ll_disks.wait_for_disks_status(disk.get_alias())
            logger.info("disk %s moved", disk.get_alias())
            vm_disk = ll_disks.getVmDisk(self.vm_name, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(
                is_disk_ro,
                "Disk %s is not read-only after move "
                "to different storage domain" % vm_disk.get_alias()
            )
            logger.info(
                "Disk %s is read-only after move to different storage domain"
                % vm_disk.get_alias()
            )


@attr(tier=2)
class TestCase4925(DefaultEnvironment):
    """
    Checks that Live Storage Migration of read-only disk should be possible
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: This case is blocked for Block and File because of
    # performance bug: https://bugzilla.redhat.com/show_bug.cgi?id=1246114
    # There are 5 snapshots created and it can take over 40 minutes to
    # delete them across all storage types
    __test__ = True
    polarion_test_case = '4925'
    # Bugzilla history:
    # 1196049, 1176673: After live storage migration on block storage vdsm
    # extends migrated drive using all free space in the vg

    @polarion("RHEVM3-4925")
    @bz({'1246114': {}})
    def test_live_migrate_RO_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the disk (LSM) to the second storage domain
        """
        assert self.prepare_disks_for_vm(read_only=True)

        ro_vm_disks = not_bootable(self.vm_name)
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        assert ll_vms.waitForVMState(self.vm_name)

        for index, disk in enumerate(ro_vm_disks):
            ll_vms.move_vm_disk(
                self.vm_name, disk.get_alias(), self.storage_domains[1]
            )

            logger.info("disk %s moved", disk.get_alias())
            vm_disk = ll_disks.getVmDisk(self.vm_name, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(
                is_disk_ro,
                "Disk %s is not read-only after move "
                "to different storage domain" % vm_disk.get_alias()
            )
            logger.info(
                "Disk %s is read-only after move to different storage domain"
                % vm_disk.get_alias()
            )


@attr(tier=2)
class TestCase4927(BaseTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently __test__ = False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4927'

    @polarion("RHEVM3-4927")
    def test_copy_template_RO_disk_to_second_SD(self):
        """
        - 2 storage domains
        - VM with OS (with disk on SD1)
        - Change the VM permissions on its bootable disk to read-only
        - Create a template from the VM
        - Copy the template read-only disk to SD2
        - Create a VM from the template and place its disk on SD2
        - Check that engine reports the VM disk as read-only
        - Try to write from the new VM to its disk
        """
        pass


@attr(tier=2)
class TestCase4926(DefaultEnvironment):
    """
    Checks that Live Storage Migration of RW disk should be possible, even
    when a read-only disk is attached to vm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4926'
    # Bugzilla history:
    # 1196049, 1176673: After live storage migration on block storage vdsm
    # extends migrated drive using all free space in the vg

    @polarion("RHEVM3-4926")
    def test_live_migrate_RW_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the first RW to the second storage domain

        """
        bootable = ll_vms.get_vm_bootable_disk(self.vm_name)
        assert self.prepare_disks_for_vm(read_only=True)

        vm_disks = ll_vms.getVmDisks(self.vm_name)
        ro_vm_disks = [
            disk for disk in vm_disks if not
            ll_vms.is_bootable_disk(self.vm_name, disk.get_id())
        ]

        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        assert ll_vms.waitForVMState(self.vm_name)

        ll_vms.move_vm_disk(self.vm_name, bootable, self.storage_domains[1])


@attr(tier=4)
class TestCase4930(DefaultEnvironment):
    """
    Check that the VM sees its second disk as read-only,
    after killing qemu process
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    __test__ = True
    polarion_test_case = '4930'

    @polarion("RHEVM3-4930")
    def test_kill_qemu_of_vm_with_RO_disk_attached(self):
        """
        - VM with OS
        - Attaching read-only disks to the VM (all possible permutations)
          and hotplug it
        - Kill qemu process of the VM
        - Start the VM again
        """
        self.prepare_disks_for_vm(read_only=True)
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=False)
        logger.info("Killing qemu process")
        self.host = ll_hosts.getVmHost(self.vm_name)[1]['vmHoster']
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=self.host
        )
        status = ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=self.vm_name
        )
        self.assertTrue(status, "Failed to kill qemu process")
        logger.info("qemu process killed")
        ll_vms.start_vms([self.vm_name], 1, wait_for_ip=True)
        ro_vm_disks = ll_vms.getVmDisks(self.vm_name)
        ro_vm_disks = [
            d for d in ro_vm_disks if not ll_vms.is_bootable_disk(
                self.vm_name, d.get_id()
            )
        ]
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])
        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk.get_alias(),
            )
            logger.info("Trying to write to read-only disk...")
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(
                status, "Write operation to read-only disk succeeded"
            )
            logger.info("Failed to write to read-only disk")


@attr(tier=4)
class TestCase4931(BaseTestCase):
    """
    Restart vdsm during read-only disk activation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4931'

    @polarion("RHEVM3-4931")
    def test_restart_vdsm_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change disk from RW to read-only
        - Activate the disk and restart vdsm service right after
        """


@attr(tier=4)
class TestCase4932(BaseTestCase):
    """
    Restart ovirt-engine during read-only disk activation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4932'

    @polarion("RHEVM3-4932")
    def test_restart_ovirt_engine_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change disk from RW to read-only
        - Activate the disk and restart ovirt-engine service right after
        """


@attr(tier=4)
class TestCase4933(BaseTestCase):
    """
    Restart libvirt during read-only disk activation
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4933'

    @polarion("RHEVM3-4933")
    def test_restart_libvirt_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change the VM permissions on the disk to read-only
        - Hotplug the disk and restart libvirtd service
          right after (initctl restart libvirtd)
        - Activate the disk when vdsm comes up
        """


@attr(tier=2)
class TestCase4934(BaseTestCase):
    """
    Changing RW disk to read-only while disk is plugged to a running VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_4_Storage_RO_Disks
    """
    # TODO: Currently False because update operation is needed:
    # https://bugzilla.redhat.com/show_bug.cgi?id=854932
    __test__ = False
    polarion_test_case = '4934'

    @polarion("RHEVM3-4934")
    def test_change_RW_disk_to_RO_while_disk_is_plugged_to_running_vm(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Try to change the disk to read-only without unplugging the disk
        """
