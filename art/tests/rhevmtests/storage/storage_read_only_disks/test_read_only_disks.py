"""
3.4 Feature: Read only (RO) disk - 12049
https://tcms.engineering.redhat.com/plan/12049
"""
import config
import helpers
import logging
from art.rhevm_api.tests_lib.low_level.hosts import (
    kill_qemu_process, getHostIP, getVmHost,
)
from art.rhevm_api.tests_lib.low_level.disks import (
    updateDisk, getVmDisk, wait_for_disks_status, addDisk, attachDisk,
    checkDiskExists, deleteDisk,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getDomainAddress, findExportStorageDomains,
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    removeTemplate, createTemplate, waitForTemplatesStates,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import (
    addSnapshot, getVmDisks, removeDisk, start_vms, deactivateVmDisk,
    waitForVMState, removeSnapshot, migrateVm, suspendVm, startVm, exportVm,
    importVm, get_snapshot_disks, cloneVmFromSnapshot, removeVm,
    cloneVmFromTemplate, stop_vms_safely, removeVms, move_vm_disk,
    waitForVmsStates, preview_snapshot, undo_snapshot_preview, commit_snapshot,
    removeVmFromExportDomain, does_vm_exist, DiskNotFound,
    get_vms_disks_storage_domain_name, waitForDisksStat,
    safely_remove_vms, get_vm_bootable_disk, remove_all_vm_lsm_snapshots,
    wait_for_vm_snapshots,
)
from art.rhevm_api.tests_lib.high_level.datacenters import (
    build_setup,
    clean_datacenter,
)
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler import exceptions
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 600
REMOVE_SNAPSHOT_TIMEOUT = 900
TEMPLATE_TIMOUT = 360

TEST_PLAN_ID = '12049'
ENUMS = config.ENUMS
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'

vmArgs = {'positive': True,
          'vmDescription': config.TEST_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.FORMAT_COW,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.VM_DISK_SIZE,
          'nic': config.NIC_NAME[0],
          'image': config.COBBLER_PROFILE,
          'useAgent': True,
          'os_type': config.ENUMS['rhel6'],
          'user': config.VM_USER,
          'password': config.VM_PASSWORD,
          'network': config.MGMT_BRIDGE
          }

not_bootable = lambda d: (not d.get_bootable()) and (d.get_active())


def setup_module():
    """
    Create datacenter with 2 host, 2 storage domains and 1 export domain
    Create vm and install OS on it

    for this TCMS plan we need 3 SD but only two of them should be created on
    setup. the other SD will be created manually in the test case 334923.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only two lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    if not config.GOLDEN_ENV:
        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)

        if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
            domain_path = config.PATH
            config.PARAMETERS['data_domain_path'] = domain_path[0:2]
        else:
            luns = config.LUNS
            config.PARAMETERS['lun'] = luns[0:2]

        build_setup(config=config.PARAMETERS,
                    storage=config.PARAMETERS,
                    storage_type=config.STORAGE_TYPE)

        if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
            config.PARAMETERS['data_domain_path'] = domain_path
        else:
            config.PARAMETERS['lun'] = luns

    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]

        vm_name = config.VM_NAME % storage_type

        vmArgs['storageDomainName'] = storage_domain
        vmArgs['vmName'] = vm_name

        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )

        logger.info('Shutting down VM %s', vm_name)
        stop_vms_safely([vm_name])


def teardown_module():
    """
    Clean datacenter
    """
    if config.GOLDEN_ENV:
        for storage_type in config.STORAGE_SELECTOR:
            vm_name = config.VM_NAME % storage_type
            stop_vms_safely([vm_name])
            removeVm(True, vm_name)
    else:
        logger.info('Cleaning datacenter')
        clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """

    __test__ = False
    vm_name = config.VM_NAME % TestCase.storage

    def setUp(self):
        """Initialize DISKS_NAMES variable"""
        helpers.DISKS_NAMES[self.storage] = list()

    def prepare_disks_for_vm(self, read_only, vm_name=None):
        """Attach read only disks to the vm"""
        vm_name = self.vm_name if not vm_name else vm_name
        return helpers.prepare_disks_for_vm(
            vm_name, helpers.DISKS_NAMES[self.storage], read_only=read_only
        )

    def set_persistent_network(self, vm_name=None):
        """Set persistent network to vm"""
        vm_name = self.vm_name if not vm_name else vm_name
        start_vms([vm_name], max_workers=1, wait_for_ip=True)
        assert waitForVMState(vm_name)
        vm_ip = storage_helpers.get_vm_ip(vm_name)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        stop_vms_safely([vm_name])
        assert waitForVMState(vm_name, config.VM_DOWN)


class DefaultEnvironment(BaseTestCase):
    """
    A class with common setup and teardown methods
    """

    spm = None
    shared = False

    def ensure_vm_exists(self):
        """If vm does not exist, create it"""
        if not does_vm_exist(self.vm_name):
            # The storage domain will be accesible at class level
            vmArgs['storageDomainName'] = self.storage_domains[0]
            logger.info('Creating vm and installing OS on it')
            if not storage_helpers.create_vm_or_clone(**vmArgs):
                raise exceptions.VMException(
                    'Unable to create vm %s for test' % self.vm_name
                )

            logger.info('Shutting down VM %s', self.vm_name)
        stop_vms_safely([self.vm_name])

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        self.storage_domains = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.ensure_vm_exists()
        helpers.start_creating_disks_for_test(
            self.storage_domains[0], self.storage, shared=self.shared
        )
        assert wait_for_disks_status(
            helpers.DISKS_NAMES[self.storage],
            timeout=DISK_TIMEOUT,
        )
        stop_vms_safely([self.vm_name])
        assert waitForVMState(vm=self.vm_name, state=config.VM_DOWN)

    def tearDown(self):
        """
        Clean environment
        """
        wait_for_jobs()
        stop_vms_safely([self.vm_name])
        logger.info("Removing all disks")
        for disk in helpers.DISKS_NAMES[self.storage]:
            try:
                deactivateVmDisk(True, self.vm_name, disk)
                if not removeDisk(True, self.vm_name, disk):
                    logger.error("Failed to remove disk %s", disk)
                logger.info("Disk %s removed successfully", disk)
            except DiskNotFound, e:
                logger.error("Error DiskNotFound: %s", e)
                if checkDiskExists(True, disk):
                    if not deleteDisk(True, disk):
                        logger.error("Error trying to remove disk %s", disk)


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

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert addSnapshot(
            True, self.vm_name, self.snapshot_description
        )

    def tearDown(self):
        """
        Clean environment
        """
        super(DefaultSnapshotEnvironment, self).tearDown()


@attr(tier=0)
class TestCase332472(DefaultEnvironment):
    """
    Attach a RO disk to vm and try to write to the disk
    https://tcms.engineering.redhat.com/case/332472/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332472'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk
        """
        self.prepare_disks_for_vm(read_only=True)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=1)
class TestCase332473(BaseTestCase):
    """
    Attach a RO direct LUN disk to vm and try to write to the disk
    https://tcms.engineering.redhat.com/case/332473/?from_plan=12049
    """
    __test__ = BaseTestCase.storage in config.BLOCK_TYPES
    tcms_test_case = '332473'
    bz = {'1194695': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_attach_RO_direct_LUN_disk(self):
        """
        - VM with OS
        - Attach a second RO direct LUN disk to the VM
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
                'format': config.FORMAT_COW,
                'interface': interface,
                'alias': disk_alias,
                'lun_address': config.DIRECT_LUN_ADDRESSES[i],
                'lun_target': config.DIRECT_LUN_TARGETS[i],
                'lun_id': config.DIRECT_LUNS[i],
                "type_": self.storage}

            logger.info("Creating disk %s", disk_alias)
            assert addDisk(True, **direct_lun_args)
            helpers.DISKS_NAMES[self.storage].append(disk_alias)

            logger.info("Attaching disk %s as RO disk to vm %s",
                        disk_alias, self.vm_name)
            status = attachDisk(
                True, disk_alias, self.vm_name, active=True,
                read_only=True
            )

            self.assertTrue(status, "Failed to attach direct lun as read only")

            start_vms([self.vm_name], 1, wait_for_ip=True)
            assert waitForVMState(self.vm_name)

            helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        disks_aliases = [disk.get_alias() for disk in getVmDisks(self.vm_name)]
        for disk_alias in helpers.DISKS_NAMES[self.storage]:
            if disk_alias in disks_aliases:
                remove_func = lambda w: removeDisk(True, self.vm_name, w)
            else:
                remove_func = lambda w: deleteDisk(True, w)

            if not remove_func(disk_alias):
                logger.info("Failed to remove disk %s", self.disk_alias)


@attr(tier=1)
class TestCase332474(DefaultEnvironment):
    """
    Attach a RO shared disk to vm and try to write to the disk
    https://tcms.engineering.redhat.com/case/332474/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332474'
    test_vm_name = ''

    def setUp(self):
        self.shared = True
        super(TestCase332474, self).setUp()

        self.prepare_disks_for_vm(read_only=False)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        self.test_vm_name = 'test_%s' % self.tcms_test_case
        vmArgs['vmName'] = self.test_vm_name
        vmArgs['storageDomainName'] = self.storage_domains[0]

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.test_vm_name
            )
        assert waitForVMState(self.test_vm_name)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_shared_RO_disk(self):
        """
        - 2 VMs with OS
        - Add a second disk to VM1 as shared disk
        - Attach VM1 shared disk to VM2 as RO disk and activate it
        - On VM2, Verify that it's impossible to write to the RO disk
        """
        self.prepare_disks_for_vm(read_only=True, vm_name=self.test_vm_name)

        for disk in helpers.DISKS_NAMES[self.storage]:
            state, out = storage_helpers.perform_dd_to_disk(
                self.test_vm_name, disk
            )
            logger.info("Trying to write to read only disk %s", disk)
            status = (not state) and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

    def tearDown(self):
        safely_remove_vms([self.test_vm_name])
        super(TestCase332474, self).tearDown()


@attr(tier=1)
class TestCase337630(DefaultEnvironment):
    """
    Verifies that RO shared disk is persistent after snapshot is taken to a
    shared disk
    https://tcms.engineering.redhat.com/case/337630/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '337630'
    snapshot_description = 'test_snap'
    test_vm_name = ''

    def setUp(self):
        self.shared = True
        super(TestCase337630, self).setUp()

        self.prepare_disks_for_vm(read_only=False)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        self.test_vm_name = 'test_%s' % self.tcms_test_case
        vmArgs['vmName'] = self.test_vm_name
        vmArgs['storageDomainName'] = self.storage_domains[0]

        logger.info('Creating vm and installing OS on it')
        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)
        assert waitForVMState(self.test_vm_name)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_RO_persistent_after_snapshot_creation_to_a_shared_disk(self):
        """
        - 2 VMs with OS
        - On one of the VM, create a second shared disk
        - Attach the shared disk also to the second vm as RO
        - Check that the disk is actually RO for the second VM
        - Create a snapshot to the first VM that sees the disk as RW
        - Check that the disk is still RO for the second VM
        """
        self.prepare_disks_for_vm(read_only=True, vm_name=self.test_vm_name)
        ro_vm_disks = filter(not_bootable, getVmDisks(self.test_vm_name))

        rw_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info(
                'check if disk %s is visible as RO to vm %s'
                % (ro_disk.get_alias(), self.test_vm_name)
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as Read Only disk"
                % (ro_disk.get_alias(), self.test_vm_name)
            )
        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert addSnapshot(
            True, self.vm_name, self.snapshot_description
        )

        ro_vm_disks = filter(not_bootable, getVmDisks(self.test_vm_name))

        rw_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info(
                'check if disk %s is still visible as RO to vm %s'
                ' after snapshot was taken', ro_disk.get_alias(),
                self.test_vm_name
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as Read Only disk"
                % (ro_disk.get_alias(), self.test_vm_name)
            )

    def tearDown(self):
        safely_remove_vms([self.test_vm_name])
        stop_vms_safely([self.vm_name])
        super(TestCase337630, self).tearDown()

        if not removeSnapshot(
                True, self.vm_name, self.snapshot_description,
                timeout=REMOVE_SNAPSHOT_TIMEOUT
        ):
            logger.error(
                "Failed to remove snapshot %s", self.snapshot_description)
        wait_for_jobs()


@attr(tier=1)
class TestCase332475(BaseTestCase):
    """
    Checks that changing disk's write policy from RW to RO will fails
    when the disk is active
    https://tcms.engineering.redhat.com/case/332475/?from_plan=12049

    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332475'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_change_disk_from_RW_to_RO(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Try to change the permissions to RO. It should fail
          because the disk is active
        - Deactivate the disk and change the VM permissions on the disk to RO
        - Activate the disk
        """
        helpers.start_creating_disks_for_test(self.storage_domains[0],
                                              self.storage)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        self.prepare_disks_for_vm(read_only=False)

        vm_disks = getVmDisks(self.vm_name)
        for disk in [vm_disk.get_alias() for vm_disk in vm_disks]:
            status = updateDisk(True, alias=disk, read_only=True)
            self.assertFalse(status, "Succeeded to change RW disk %s to RO" %
                             disk)
            assert deactivateVmDisk(True, self.vm_name, disk)

            status = updateDisk(True, alias=disk, read_only=True)
            self.assertTrue(status, "Failed to change RW disk %s to RO" % disk)


@attr(tier=1)
class TestCase337936(BaseTestCase):
    """
    Check that booting from RO disk should be impossible
    https://tcms.engineering.redhat.com/case/337936/?from_plan=12049

    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '337936'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_boot_from_RO_disk(self):
        """
        - VM with OS
        - Detach the disk from the VM
        - Edit the disk and change it to be RO to the VM
        - Start the VM, boot it from its hard disk which is supposed to be RO
        """


@attr(tier=3)
class TestCase332489(DefaultEnvironment):
    """
    Block connectivity from vdsm to the storage domain
    where the VM RO disk is located
    https://tcms.engineering.redhat.com/case/332489/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332489'
    blocked = False
    storage_domain_ip = ''
    bz = {'1138144': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_RO_persistent_after_block_connectivity_to_storage(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
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
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        for disk in helpers.DISKS_NAMES[self.storage]:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk
            )
            logger.info("Trying to write to read only disk...")
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

        storage_domain_name = get_vms_disks_storage_domain_name(self.vm_name)
        found, self.storage_domain_ip = getDomainAddress(
            True, storage_domain_name)
        assert found
        logger.info(
            "Found IP %s for storage domain %s",
            self.storage_domain_ip, storage_domain_name
        )

        self.host_ip = getHostIP(getVmHost(self.vm_name)[1]['vmHoster'])
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

        assert waitForVMState(self.vm_name, state=config.VM_PAUSED)

        logger.info("Unblocking connection from vdsm to storage domain")
        status = unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        )
        if status:
            self.blocked = False

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        for disk in helpers.DISKS_NAMES[self.storage]:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk
            )
            logger.info("Trying to write to read only disk...")
            status = (not state) and ((READ_ONLY in out) or
                                      (NOT_PERMITTED in out))
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

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
                raise exceptions.HostException(
                    "Failed to unblock connectivity from host %s to "
                    "storage domain %s" % (self.host, self.storage_domain_ip)
                )
        super(TestCase332489, self).tearDown()


@attr(tier=1)
class TestCase332484(DefaultEnvironment):
    """
    Migrate a vm with RO disk, and check the disk is still visible as RO
    https://tcms.engineering.redhat.com/case/332484/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332484'
    is_migrated = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_migrate_vm_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - migrate the VM to another host
        - Check that disk is visible to the VM
        - Check that engine still reports the VM disk as RO
        - Verify that it's impossible to write to the disk
        """
        self.prepare_disks_for_vm(read_only=True)

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk in vm_disks:
            logger.info(
                'check if disk %s is visible as RO to vm %s'
                % (ro_disk.get_alias(), self.vm_name)
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only,
                "Disk %s is not visible to vm %s as Read Only disk"
                % (ro_disk.get_alias(), self.vm_name)
            )

        self.is_migrated = migrateVm(True, self.vm_name)

        for ro_disk in vm_disks:
            logger.info(
                'check if disk %s is still visible as RO to vm %s'
                'after migration', ro_disk.get_alias(), self.vm_name
            )
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(
                is_read_only, "Disk %s is not visible to vm %s as Read "
                              "Only disk" % (ro_disk.get_alias(), self.vm_name)
            )

    def tearDown(self):
        if self.is_migrated:
            if not migrateVm(True, self.vm_name):
                logger.error("Failed to migrate vm %s", self.vm_name)
        super(TestCase332484, self).tearDown()


@attr(tier=1)
class TestCase332476(DefaultEnvironment):
    """
    Checks that suspending a vm with RO disk shouldn't
    change disk configuration
    https://tcms.engineering.redhat.com/case/332476/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332476'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_RO_disk_persistent_after_suspend_the_vm(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Suspend the VM
        - Re-activate the VM
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk
        """
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        self.prepare_disks_for_vm(read_only=True)

        logger.info("Suspending vm %s", self.vm_name)
        suspendVm(True, self.vm_name)
        logger.info("Re activating vm %s", self.vm_name)
        startVm(True, self.vm_name)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)


@attr(tier=1)
class TestCase334878(DefaultEnvironment):
    """
    Import more than once VM with RO disk, and verify that it's impossible
    to write to the disk for both the original and the imported VMs
    https://tcms.engineering.redhat.com/case/334878/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '334878'
    imported_vm_1 = 'imported_vm_1'
    imported_vm_2 = 'imported_vm_2'
    export_domain = ''

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_import_more_than_once_VM_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Export the VM to an export domain
        - Import the same VM twice
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk:
        """
        self.vm_exported = False
        self.prepare_disks_for_vm(read_only=True)

        logger.info("Setting persistent network configuration")
        self.set_persistent_network()

        self.export_domain = findExportStorageDomains(
            config.DATA_CENTER_NAME
        )[0]

        logger.info("Exporting vm %s", self.vm_name)
        self.vm_exported = exportVm(True, self.vm_name, self.export_domain)
        self.assertTrue(
            self.vm_exported, "Couldn't export vm %s" % self.vm_name
        )
        logger.info(
            "Importing vm %s as %s", self.vm_name, self.imported_vm_1
        )
        assert importVm(
            True, self.vm_name, self.export_domain, self.storage_domains[0],
            config.CLUSTER_NAME, name=self.imported_vm_1
        )
        start_vms([self.imported_vm_1], max_workers=1, wait_for_ip=False)
        assert waitForVMState(self.imported_vm_1)

        logger.info(
            "Importing vm %s as %s", self.vm_name, self.imported_vm_2
        )
        assert importVm(
            True, self.vm_name, self.export_domain, self.storage_domains[0],
            config.CLUSTER_NAME, name=self.imported_vm_2
        )
        start_vms([self.imported_vm_2], max_workers=1, wait_for_ip=False)
        assert waitForVMState(self.imported_vm_2)

        helpers.write_on_vms_ro_disks(
            self.imported_vm_1, self.storage, imported_vm=True
        )
        helpers.write_on_vms_ro_disks(
            self.imported_vm_2, self.storage, imported_vm=True
        )

    def tearDown(self):
        vms = filter(does_vm_exist, [self.imported_vm_1, self.imported_vm_2])
        stop_vms_safely(vms)
        waitForVmsStates(True, vms, config.VM_DOWN)
        removeVms(True, vms)
        if self.vm_exported and not removeVmFromExportDomain(
                True, vm=self.vm_name, datacenter=config.DATA_CENTER_NAME,
                export_storagedomain=self.export_domain
        ):
            logger.error(
                "Failed to remove vm %s from export domain %s",
                self.imported_vm, self.export_domain
            )
        super(TestCase334878, self).tearDown()


@attr(tier=1)
class TestCase332483(DefaultSnapshotEnvironment):
    """
    Check that the RO disk is part of vm snapshot, and also after preview
    https://tcms.engineering.redhat.com/case/332483/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332483'
    snapshot_description = 'test_snap'
    create_snapshot = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preview_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the RO disk is part of the snapshot
        - Shutdown the VM and preview the snapshot. Start the VM
          and try to write to the RO disk
        """
        snap_disks = get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that RO disk %s is part of the snapshot",
                ro_disk.get_alias()
            )

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(
                is_part_of_disks,
                "RO disk %s is not part of the snapshot that was taken"
                % ro_disk.get_alias()
            )
        stop_vms_safely([self.vm_name])
        assert waitForVMState(self.vm_name, config.VM_DOWN)
        logger.info("Previewing snapshot %s", self.snapshot_description)
        self.create_snapshot = preview_snapshot(True, self.vm_name,
                                                self.snapshot_description)

        assert self.create_snapshot
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        # Wait in case the snapshot fails and there are jobs running
        wait_for_jobs()
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not undo_snapshot_preview(True, self.vm_name):
                logger.error("Error undoing snapshot snapshot preview for %s",
                             self.vm_name)

        super(TestCase332483, self).tearDown()
        waitForDisksStat(self.vm_name)

        if not removeSnapshot(
                True, self.vm_name, self.snapshot_description,
                timeout=REMOVE_SNAPSHOT_TIMEOUT
        ):
            logger.error(
                "Failed to remove snapshot %s", self.snapshot_description
            )

        wait_for_jobs()


@attr(tier=1)
class TestCase337931(DefaultSnapshotEnvironment):
    """
    Check that the RO disk is part of vm snapshot, and the disk
    should be remain RO for the VM after undoing the snapshot.
    https://tcms.engineering.redhat.com/case/337931/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '337931'
    snapshot_description = 'test_snap'
    create_snapshot = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preview_and_undo_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the RO disk is part of the snapshot
        - Shutdown the VM, preview and undo the snapshot.
        - Start the VM and try to write to the RO disk
        """
        snap_disks = get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that RO disk %s is part of the snapshot",
                ro_disk.get_alias()
            )

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(
                is_part_of_disks,
                "RO disk %s is not part of the snapshot that was taken"
                % ro_disk.get_alias()
            )
        stop_vms_safely([self.vm_name])
        assert waitForVMState(self.vm_name, config.VM_DOWN)
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )
        self.create_snapshot = status

        assert status
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )
        logger.info("Undoing snapshot %s", self.snapshot_description)
        status = undo_snapshot_preview(True, self.vm_name)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        assert status

        self.create_snapshot = not status

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not undo_snapshot_preview(True, self.vm_name):
                logger.error("Error previewing snapshot for %s", self.vm_name)

        super(TestCase337931, self).tearDown()
        if not removeSnapshot(
                True, self.vm_name, self.snapshot_description,
                timeout=REMOVE_SNAPSHOT_TIMEOUT
        ):
            logger.error(
                "Failed to remove snapshot %s", self.snapshot_description
            )
        wait_for_jobs()


@attr(tier=1)
class TestCase337930(DefaultSnapshotEnvironment):
    """
    Check that the RO disk is part of vm snapshot, and the disk
    should be remain RO for the VM after committing the snapshot.
    https://tcms.engineering.redhat.com/case/337930/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '337930'
    snapshot_description = 'test_snap'
    create_snapshot = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_preview_and_commit_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the RO disk is part of the snapshot
        - Shutdown the VM, preview and commit the snapshot.
        - Start the VM and try to write to the RO disk
        """
        snap_disks = get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that RO disk %s is part of the snapshot",
                ro_disk.get_alias()
            )

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(
                is_part_of_disks,
                "RO disk %s is not part of the snapshot that was taken"
                % ro_disk.get_alias()
            )
        stop_vms_safely([self.vm_name])
        assert waitForVMState(self.vm_name, config.VM_DOWN)
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = preview_snapshot(
            True, self.vm_name, self.snapshot_description
        )
        self.create_snapshot = True
        assert status
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW],
            [self.snapshot_description],
        )

        logger.info("Committing snapshot %s", self.snapshot_description)
        status = commit_snapshot(True, self.vm_name)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        assert status
        self.create_snapshot = not status

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        remove_snapshot = True
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if self.create_snapshot:
            logger.info("Undoing snapshot %s", self.snapshot_description)
            if not undo_snapshot_preview(True, self.vm_name):
                logger.error("Error previewing snapshot for %s", self.vm_name)
                # Something went wrong removing the snapshot, remove and
                # create the vm again
                removeVm(True, self.vm_name)
                self.ensure_vm_exists()
                remove_snapshot = False

        super(TestCase337930, self).tearDown()
        if remove_snapshot and not removeSnapshot(
                True, self.vm_name, self.snapshot_description,
                timeout=REMOVE_SNAPSHOT_TIMEOUT
        ):
            logger.error(
                "Failed to remove snapshot %s", self.snapshot_description
            )
        wait_for_jobs()


@attr(tier=1)
class TestCase337934(DefaultSnapshotEnvironment):
    """
    Checks that deleting a snapshot with RO disk shouldn't effect
    the RO disk
    https://tcms.engineering.redhat.com/case/337934/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '337934'
    snapshot_description = 'test_snap'
    snapshot_removed = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_delete_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the RO disk is part of the snapshot
        - Shutdown the VM and delete the snapshot.
        - Start the VM and try to write to the RO disk
        """
        snap_disks = get_snapshot_disks(
            self.vm_name, self.snapshot_description
        )
        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that RO disk %s is part of the snapshot",
                ro_disk.get_alias()
            )

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(
                is_part_of_disks,
                "RO disk %s is not part of the snapshot that was taken"
                % ro_disk.get_alias()
            )
        stop_vms_safely([self.vm_name])
        assert waitForVMState(self.vm_name, config.VM_DOWN)
        logger.info(
            "Removing snapshot %s", self.snapshot_description
        )

        status = removeSnapshot(
            True, self.vm_name, self.snapshot_description,
            timeout=REMOVE_SNAPSHOT_TIMEOUT,
        )

        self.snapshot_removed = status
        self.assertTrue(
            status, "Failed to remove snapshot %s from vm %s"
            % (self.snapshot_description, self.vm_name)
        )

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        helpers.write_on_vms_ro_disks(self.vm_name, self.storage)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)
        if not self.snapshot_removed:
            if not removeSnapshot(
                    True, self.vm_name, self.snapshot_description,
                    timeout=REMOVE_SNAPSHOT_TIMEOUT
            ):
                logger.error(
                    "Failed to remove snapshot %s", self.snapshot_description
                )
        super(TestCase337934, self).tearDown()
        wait_for_jobs()


@attr(tier=1)
class TestCase337935(DefaultEnvironment):
    """
    Checks that a cloned vm from a snapshot with RO disk shouldn't
    be able to write to the RO disk as well
    https://tcms.engineering.redhat.com/case/337935/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '337935'
    snapshot_description = 'test_snap'
    cloned = False
    cloned_vm_name = 'cloned_vm'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_clone_vm_from_snapshot_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Create a snapshot to the VM
        - Check that the RO disk is part of the snapshot
        - Clone a new VM from the snapshot
        - Try to write to the RO disk of the cloned VM
        """
        self.prepare_disks_for_vm(read_only=True)

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        logger.info("Setting persistent network configuration")
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)

        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))

        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert addSnapshot(
            True, self.vm_name, self.snapshot_description
        )
        wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], [self.snapshot_description],
        )

        snap_disks = get_snapshot_disks(self.vm_name,
                                        self.snapshot_description)

        for ro_disk in ro_vm_disks:
            logger.info(
                "Check that RO disk %s is part of the snapshot",
                ro_disk.get_alias()
            )

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(
                is_part_of_disks,
                "RO disk %s is not part of the snapshot that was taken"
                % ro_disk.get_alias()
            )
        status = cloneVmFromSnapshot(
            True, name=self.cloned_vm_name, snapshot=self.snapshot_description,
            cluster=config.CLUSTER_NAME, vm=self.vm_name
        )
        if status:
            self.cloned = True

        self.assertTrue(status, "Failed to clone vm from snapshot")
        start_vms([self.cloned_vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.cloned_vm_name)

        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.cloned_vm_name, disk.get_alias(),
            )
            logger.info("Trying to write to read only disk...")
            status = (not state) and ((READ_ONLY in out) or
                                      (NOT_PERMITTED in out))
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

    def tearDown(self):
        if self.cloned:
            if not removeVm(
                    True, self.cloned_vm_name, stopVM='true', wait=True
            ):
                logger.error(
                    "Failed to remove cloned vms %s", self.cloned_vm_name
                )

        stop_vms_safely([self.vm_name])
        super(TestCase337935, self).tearDown()

        if not removeSnapshot(
                True, self.vm_name, self.snapshot_description,
                timeout=REMOVE_SNAPSHOT_TIMEOUT
        ):
            logger.error(
                "Failed to remove snapshot %s", self.snapshot_description
            )

        wait_for_jobs()


@attr(tier=1)
class TestCase332481(DefaultEnvironment):
    """
    Create 2 VMs from a template with RO disk in 2 provisioning methods:
    the first cloned from template and the second as thin copy.
    https://tcms.engineering.redhat.com/case/332481/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332481'
    template_name = 'test_template'
    cloned_vm_name = 'cloned_vm'
    thin_cloned_vm_name = 'thin_cloned_vm'
    cloned_vms = [cloned_vm_name, thin_cloned_vm_name]
    cloned = False

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_create_vms_from_template_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Create a template from the VM
        - Create 2 VMs from the template in 2 provisioning methods:
            * the first cloned from template
            * the second as thin copy
        - Check that for the second disk of the new VMs, engine reports
          that its RO
        - Try to write to that disk from both the VMs
        """
        self.prepare_disks_for_vm(read_only=True)
        logger.info("Setting persistent network configuration")
        self.set_persistent_network()

        logger.info("creating template %s", self.template_name)
        assert createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domains[0]
        )

        logger.info("Cloning vm from template")

        self.cloned = cloneVmFromTemplate(
            True, self.cloned_vm_name, self.template_name, config.CLUSTER_NAME,
            storagedomain=self.storage_domains[0]
        )

        self.assertTrue(self.cloned, "Failed to clone vm from template")

        logger.info("Cloning vm from template as Thin copy")
        self.cloned = cloneVmFromTemplate(
            True, self.thin_cloned_vm_name, self.template_name,
            config.CLUSTER_NAME, clone=False
        )
        self.assertTrue(self.cloned, "Failed to clone vm from template")
        start_vms(self.cloned_vms, 2, wait_for_ip=False)
        assert waitForVmsStates(True, self.cloned_vms)
        for vm in self.cloned_vms:
            cloned_vm_disks = getVmDisks(vm)
            cloned_vm_disks = [disk for disk in cloned_vm_disks if
                               (not disk.get_bootable())]

            for disk in cloned_vm_disks:
                logger.info(
                    'check if disk %s is visible as RO to vm %s',
                    disk.get_alias(), vm
                )
                is_read_only = disk.get_read_only()
                self.assertTrue(
                    is_read_only,
                    "Disk %s is not visible to vm %s as Read Only disk"
                    % (disk.get_alias(), vm)
                )

                logger.info("Trying to write to read only disk...")
                state, out = storage_helpers.perform_dd_to_disk(
                    vm, disk.get_alias(),
                )
                status = (not state) and ((READ_ONLY in out) or
                                          (NOT_PERMITTED in out))
                self.assertTrue(status, "Write operation to RO disk succeeded")
                logger.info("Failed to write to read only disk")

    def tearDown(self):
        if self.cloned:
            if not removeVms(True, self.cloned_vms, stop='true'):
                logger.error("Failed to remove cloned vms")
        waitForTemplatesStates(self.template_name)

        if not removeTemplate(
                True, self.template_name, timeout=TEMPLATE_TIMOUT
        ):
            logger.error("Failed to remove template %s",
                         self.template_name)
        super(TestCase332481, self).tearDown()


@attr(tier=1)
class TestCase334877(DefaultEnvironment):
    """
    Checks that moving RO disk to a second storage domain will
    cause that the disk should remain RO for the VM after the move
    https://tcms.engineering.redhat.com/case/334877/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '334877'
    bz = {
        '1196049': {'engine': None, 'version': ['3.5.1']},
        '1176673': {'engine': None, 'version': ['3.6']},
    } if TestCase.storage == config.STORAGE_TYPE_ISCSI else None

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_moving_RO_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
          and plug it to the VM
        - Try to write to the disk, it should not be allowed
        - Unplug the disk from the VM
        - Try to move the disk to the second storage domain
          while disk is unplugged and RO
        """
        self.prepare_disks_for_vm(read_only=True)

        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk.get_alias(),
            )
            logger.info(
                "Trying to write to read only disk %s...", disk.get_alias(),
            )
            status = (not state) and (READ_ONLY in out) or (NOT_PERMITTED
                                                            in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

        for index, disk in enumerate(ro_vm_disks):
            logger.info("Unplugging vm disk %s", disk.get_alias())
            assert deactivateVmDisk(True, self.vm_name, disk.get_alias())

            move_vm_disk(
                self.vm_name, disk.get_alias(), self.storage_domains[1]
            )
            wait_for_disks_status(disk.get_alias())
            logger.info("disk %s moved", disk.get_alias())
            vm_disk = getVmDisk(self.vm_name, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(
                is_disk_ro,
                "Disk %s is not read only after move "
                "to different storage domain" % vm_disk.get_alias()
            )
            logger.info(
                "Disk %s is read only after move to different storage domain"
                % vm_disk.get_alias()
            )


@attr(tier=1)
class TestCase332477(DefaultEnvironment):
    """
    Checks that Live Storage Migration of RO disk should be possible
    https://tcms.engineering.redhat.com/case/332477/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332477'
    bz = {
        '1196049': {'engine': None, 'version': ['3.5.1']},
        '1176673': {'engine': None, 'version': ['3.6']},
    } if TestCase.storage == config.STORAGE_TYPE_ISCSI else None

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_live_migrate_RO_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the disk (LSM) to the second storage domain
        """
        assert self.prepare_disks_for_vm(read_only=True)

        ro_vm_disks = filter(not_bootable, getVmDisks(self.vm_name))
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        for index, disk in enumerate(ro_vm_disks):
            move_vm_disk(
                self.vm_name, disk.get_alias(), self.storage_domains[1]
            )

            logger.info("disk %s moved", disk.get_alias())
            vm_disk = getVmDisk(self.vm_name, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(
                is_disk_ro,
                "Disk %s is not read only after move "
                "to different storage domain" % vm_disk.get_alias()
            )
            logger.info(
                "Disk %s is read only after move to different storage domain"
                % vm_disk.get_alias()
            )

    def tearDown(self):
        super(TestCase332477, self).tearDown()
        remove_all_vm_lsm_snapshots(self.vm_name)


@attr(tier=1)
class TestCase332482(BaseTestCase):
    """

    https://tcms.engineering.redhat.com/case/332482/?from_plan=12049

    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332482'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_copy_template_RO_disk_to_second_SD(self):
        """
        - 2 storage domains
        - VM with OS (with disk on SD1)
        - Change the VM permissions on its bootable disk to RO
        - Create a template from the VM
        - Copy the template RO disk to SD2
        - Create a VM from the template and place its disk on SD2
        - Check that engine reports the VM disk as RO
        - Try to write from the new VM to its disk
        """
        pass


@attr(tier=1)
class TestCase334876(DefaultEnvironment):
    """
    Checks that Live Storage Migration of RW disk should be possible, even
    when a RO disk is attached to vm
    https://tcms.engineering.redhat.com/case/334876/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '334876'
    bz = {
        '1196049': {'engine': None, 'version': ['3.5.1']},
        '1176673': {'engine': None, 'version': ['3.6']},
    } if TestCase.storage == config.STORAGE_TYPE_ISCSI else None

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_live_migrate_RW_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the first RW to the second storage domain

        """
        bootable = get_vm_bootable_disk(self.vm_name)
        assert self.prepare_disks_for_vm(read_only=True)

        vm_disks = getVmDisks(self.vm_name)
        ro_vm_disks = [d for d in vm_disks if (not d.get_bootable())]

        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)

        move_vm_disk(self.vm_name, bootable, self.storage_domains[1])


@attr(tier=3)
class TestCase334921(DefaultEnvironment):
    """
    Check that the VM sees its second disk as RO, after killing qemu process
    https://tcms.engineering.redhat.com/case/334921/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '334921'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_kill_qemu_of_vm_with_RO_disk_attached(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutations)
          and hotplug it
        - Kill qemu process of the VM
        - Start the VM again
        """
        self.prepare_disks_for_vm(read_only=True)
        start_vms([self.vm_name], 1, wait_for_ip=False)
        logger.info("Killing qemu process")
        self.host = getVmHost(self.vm_name)[1]['vmHoster']
        status = kill_qemu_process(
            self.vm_name, self.host, config.HOSTS_USER, config.HOSTS_PW
        )
        self.assertTrue(status, "Failed to kill qemu process")
        logger.info("qemu process killed")
        start_vms([self.vm_name], 1, wait_for_ip=False)
        assert waitForVMState(self.vm_name)
        ro_vm_disks = getVmDisks(self.vm_name)
        ro_vm_disks = [d for d in ro_vm_disks if (not d.get_bootable())]
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])
        for disk in ro_vm_disks:
            state, out = storage_helpers.perform_dd_to_disk(
                self.vm_name, disk.get_alias(),
            )
            logger.info("Trying to write to read only disk...")
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")


@attr(tier=3)
class TestCase332485(BaseTestCase):
    """
    Restart vdsm during RO disk activation
    https://tcms.engineering.redhat.com/case/332485/?from_plan=12049
    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332485'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_vdsm_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change disk from RW to RO
        - Activate the disk and restart vdsm service right after
        """


@attr(tier=3)
class TestCase332486(BaseTestCase):
    """
    Restart ovirt-engine during RO disk activation
    https://tcms.engineering.redhat.com/case/332486/?from_plan=12049
    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332486'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_ovirt_engine_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change disk from RW to RO
        - Activate the disk and restart ovirt-engine service right after
        """


@attr(tier=3)
class TestCase332488(BaseTestCase):
    """
    Restart libvirt during RO disk activation
    https://tcms.engineering.redhat.com/case/332488/?from_plan=12049
    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332488'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_restart_libvirt_during_hotplug_of_RO_disk(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Deactivate the disk
        - Change the VM permissions on the disk to RO
        - Hotplug the disk and restart libvirtd service
          right after (initctl restart libvirtd)
        - Activate the disk when vdsm comes up
        """


@attr(tier=1)
class TestCase332487(BaseTestCase):
    """
    Changing RW disk to RO while disk is plugged to a running VM
    https://tcms.engineering.redhat.com/case/332487/?from_plan=12049
    Currently __test__ = False because update operation is needed:
    https://bugzilla.redhat.com/show_bug.cgi?id=1075140
    """
    __test__ = False
    tcms_test_case = '332487'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_change_RW_disk_to_RO_while_disk_is_plugged_to_running_vm(self):
        """
        - VM with OS
        - Attach a second RW disk to the VM
        - Activate the disk
        - Write to the disk from the guest, it should succeed
        - Try to change the disk to RO without unplugging the disk
        """
