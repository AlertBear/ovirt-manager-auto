"""
3.4 Feature: Read only (RO) disk - 12049
https://tcms.engineering.redhat.com/plan/12049
"""
import logging
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter,\
    removeDataCenter
from art.rhevm_api.tests_lib.low_level.hosts import updateHost,\
    deactivateHost, activateHost, kill_qemu_process
from art.rhevm_api.utils.test_utils import setPersistentNetwork, wait_for_tasks
from art.unittest_lib.common import StorageTest as TestCase
from utilities.utils import getIpAddressByHostName
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.clusters import addCluster,\
    removeCluster
from art.rhevm_api.tests_lib.low_level.disks import updateDisk, getVmDisk,\
    getStorageDomainDisks, waitForDisksState, addDisk, attachDisk
from art.rhevm_api.tests_lib.low_level.storagedomains import \
    cleanDataCenter, getDomainAddress, get_master_storage_domain_name,\
    attachStorageDomain, deactivateStorageDomain, findExportStorageDomains
from art.rhevm_api.tests_lib.low_level.templates import removeTemplate,\
    createTemplate, waitForTemplatesStates
from art.rhevm_api.tests_lib.low_level.vms import createVm, addSnapshot, \
    getVmDisks, removeDisk, start_vms,\
    deactivateVmDisk, waitForVMState, removeSnapshot, \
    migrateVm, suspendVm, startVm, exportVm, importVm, get_snapshot_disks,\
    cloneVmFromSnapshot, removeVm, cloneVmFromTemplate, stop_vms_safely,\
    removeVms, move_vm_disk, waitForVmsStates, preview_snapshot,\
    undo_snapshot_preview, commit_snapshot, addVm, get_vm_ip,\
    removeVmFromExportDomain
from art.rhevm_api.utils.storage_api import blockOutgoingConnection,\
    unblockOutgoingConnection

from art.test_handler.tools import tcms, bz
from art.test_handler import exceptions
from art.unittest_lib import attr

import helpers
import config

logger = logging.getLogger(__name__)

TASK_TIMEOUT = 1500
TEMPLATE_TIMOUT = 360

TEST_PLAN_ID = '12049'
ENUMS = config.ENUMS
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'

vmArgs = {'positive': True,
          'vmName': config.VM_NAME,
          'vmDescription': config.VM_NAME,
          'diskInterface': config.VIRTIO,
          'volumeFormat': config.FORMAT_COW,
          'cluster': config.CLUSTER_NAME,
          'storageDomainName': None,
          'installation': True,
          'size': config.DISK_SIZE,
          'nic': 'nic1',
          'cobblerAddress': config.COBBLER_ADDRESS,
          'cobblerUser': config.COBBLER_USER,
          'cobblerPasswd': config.COBBLER_PASSWORD,
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
    logger.info("Preparing datacenter %s with hosts %s",
                config.DC_NAME, config.VDC)

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

    vmArgs['storageDomainName'] = \
        get_master_storage_domain_name(config.DC_NAME)

    logger.info('Creating vm and installing OS on it')

    if not createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    stop_vms_safely([config.VM_NAME])


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DC_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class DefaultEnvironment(TestCase):
    """
    A class with common setup and teardown methods
    """

    __test__ = False

    spm = None
    master_sd = None
    vm = config.VM_NAME
    shared = False

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        helpers.start_creating_disks_for_test(shared=self.shared)
        assert waitForDisksState(helpers.DISKS_NAMES, timeout=TASK_TIMEOUT)
        stop_vms_safely([self.vm])
        waitForVMState(vm=self.vm, state=ENUMS['vm_state_down'])

    def tearDown(self):
        """
        Clean environment
        """
        stop_vms_safely([self.vm])
        logger.info("Removing all disks")
        for disk in helpers.DISKS_NAMES:
            deactivateVmDisk(True, self.vm, disk)
            if not removeDisk(True, self.vm, disk):
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk)
            logger.info("Disk %s removed successfully", disk)
        sd_disks = getStorageDomainDisks(config.SD_NAME, get_href=False)
        disks_to_remove = [d.get_alias for d in sd_disks if
                           (not d.get_bootable)]
        for disk in disks_to_remove:
            deactivateVmDisk(True, self.vm, disk)
            status = removeDisk(True, self.vm, disk)
            if not status:
                raise exceptions.DiskException("Failed to remove disk %s"
                                               % disk)
            logger.info("Disk %s removed successfully", disk)
        logger.info("Finished testCase")


class DefaultSnapshotEnvironment(DefaultEnvironment):
    """
    A class with common setup and teardown methods
    """

    __test__ = False

    spm = None
    master_sd = None
    vm = config.VM_NAME
    snapshot_description = 'test_snap'

    def setUp(self):
        """
        Creating all possible combinations of disks for test
        """
        super(DefaultSnapshotEnvironment, self).setUp()
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert addSnapshot(True, config.VM_NAME,
                           self.snapshot_description)

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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)


@attr(tier=1)
class TestCase332473(TestCase):
    """
    Attach a RO direct LUN disk to vm and try to write to the disk
    https://tcms.engineering.redhat.com/case/332473/?from_plan=12049
    """
    __test__ = config.STORAGE_TYPE in config.BLOCK_TYPES
    tcms_test_case = '332473'
    disk_alias = ''

    @tcms(TEST_PLAN_ID, tcms_test_case)
    @bz('1082673')
    def test_attach_RO_direct_LUN_disk(self):
        """
        - VM with OS
        - Attach a second RO direct LUN disk to the VM
        - Activate the disk
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk:
        """
        for interface in [config.VIRTIO, config.VIRTIO_SCSI]:
            direct_lun_args = {
                'wipe_after_delete': config.BLOCK_FS,
                'bootable': False,
                'shareable': False,
                'active': True,
                'format': config.FORMAT_COW,
                'interface': interface,
                'alias': "direct_lun_disk",
                'lun_address': config.DIRECT_LUN_ADDRESS,
                'lun_target': config.DIRECT_LUN_TARGET,
                'lun_id': config.DIRECT_LUN,
                "type_": config.STORAGE_TYPE}

            self.disk_alias = direct_lun_args['alias']

            assert addDisk(True, **direct_lun_args)
            helpers.DISKS_NAMES.append(self.disk_alias)

            logger.info("Attaching disk %s as RO disk to vm %s",
                        self.disk_alias, config.VM_NAME)
            status = attachDisk(True, self.disk_alias, config.VM_NAME,
                                active=True, read_only=True)

            self.assertTrue(status, "Failed to attach direct lun as read only")

            start_vms([config.VM_NAME], 1, wait_for_ip=False)
            waitForVMState(config.VM_NAME)

            helpers.write_on_vms_ro_disks(config.VM_NAME)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        status = removeDisk(True, config.VM_NAME, self.disk_alias)
        self.assertTrue(status, "Failed to remove disk %s"
                                % self.disk_alias)

        logger.info("Disk %s removed successfully",
                    self.disk_alias)


@attr(tier=0)
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

        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=False)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        self.test_vm_name = 'test_%s' % self.tcms_test_case
        vmArgs['vmName'] = self.test_vm_name
        vmArgs['storageDomainName'] = \
            get_master_storage_domain_name(config.DC_NAME)

        logger.info('Creating vm and installing OS on it')
        if not createVm(**vmArgs):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)
        assert waitForVMState(self.test_vm_name)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_shared_RO_disk(self):
        """
        - 2 VMs with OS
        - Add a second disk to VM1 as shared disk
        - Attach VM1 shared disk to VM2 as RO disk and activate it
        - On VM2, Verify that it's impossible to write to the RO disk
        """
        helpers.prepare_disks_for_vm(self.test_vm_name, helpers.DISKS_NAMES,
                                     read_only=True)
        for index, disk in enumerate(helpers.DISKS_NAMES):
            state, out = helpers.verify_write_operation_to_disk(
                self.test_vm_name, disk_number=index)
            logger.info("Trying to write to read only disk %s", disk)
            status = (not state) and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

    def tearDown(self):
        assert removeVm(True, self.test_vm_name, stopVM='true', wait=True)
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

        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=False)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        self.test_vm_name = 'test_%s' % self.tcms_test_case
        vmArgs['vmName'] = self.test_vm_name
        vmArgs['storageDomainName'] = \
            get_master_storage_domain_name(config.DC_NAME)

        logger.info('Creating vm and installing OS on it')
        if not createVm(**vmArgs):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)
        waitForVMState(self.test_vm_name)

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
        helpers.prepare_disks_for_vm(self.test_vm_name, helpers.DISKS_NAMES,
                                     read_only=True)

        ro_vm_disks = filter(not_bootable, getVmDisks(self.test_vm_name))

        rw_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info('check if disk %s is visible as RO to vm %s'
                        % (ro_disk.get_alias(), self.test_vm_name))
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(is_read_only,
                            "Disk %s is not visible to vm %s as Read "
                            "Only disk"
                            % (ro_disk.get_alias(), self.test_vm_name))
        logger.info("Adding new snapshot %s", self.snapshot_description)
        assert addSnapshot(True, config.VM_NAME,
                           self.snapshot_description)

        ro_vm_disks = filter(not_bootable, getVmDisks(self.test_vm_name))

        rw_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk, rw_disk in zip(ro_vm_disks, rw_vm_disks):
            logger.info('check if disk %s is still visible as RO to vm %s'
                        'after snapshot was taken', ro_disk.get_alias(),
                        self.test_vm_name)
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(is_read_only,
                            "Disk %s is not visible to vm %s as Read "
                            "Only disk"
                            % (ro_disk.get_alias(), self.test_vm_name))

    def tearDown(self):
        assert removeVm(True, self.test_vm_name, stopVM='true', wait=True)
        stop_vms_safely([config.VM_NAME])
        super(TestCase337630, self).tearDown()

        if not removeSnapshot(True,
                              config.VM_NAME,
                              self.snapshot_description):
            raise exceptions.SnapshotException("Failed to remove "
                                               "snapshot %s"
                                               % self.snapshot_description)


@attr(tier=0)
class TestCase332475(TestCase):
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
        helpers.start_creating_disks_for_test()
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=False)

        vm_disks = getVmDisks(config.VM_NAME)
        for disk in [vm_disk.get_alias() for vm_disk in vm_disks]:
            status = updateDisk(True, alias=disk, read_only=True)
            self.assertFalse(status, "Succeeded to change RW disk %s to RO" %
                             disk)
            assert deactivateVmDisk(True, config.VM_NAME, disk)

            status = updateDisk(True, alias=disk, read_only=True)
            self.assertTrue(status, "Failed to change RW disk %s to RO" % disk)


@attr(tier=1)
class TestCase337936(TestCase):
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


@attr(tier=2)
class TestCase332489(DefaultEnvironment):
    """
    Block connectivity from vdsm to the storage domain
    where the VM RO disk is located
    https://tcms.engineering.redhat.com/case/332489/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332489'
    blocked = False
    master_domain_ip = ''

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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        for index, disk in enumerate(helpers.DISKS_NAMES):
            state, out = helpers.verify_write_operation_to_disk(
                config.VM_NAME, disk_number=index)
            logger.info("Trying to write to read only disk...")
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

        master_domain = get_master_storage_domain_name(config.DC_NAME)
        logger.info("Master domain found : %s", master_domain)

        found, self.master_domain_ip = getDomainAddress(True, master_domain)
        assert found
        master_domain_ip = self.master_domain_ip['address']
        logger.info("Master domain ip found : %s", master_domain_ip)

        host_ip = getIpAddressByHostName(config.HOSTS[0])
        logger.info("Blocking connection from vdsm to storage domain")
        status = blockOutgoingConnection(host_ip,
                                         config.VDS_USER[0],
                                         config.VDS_PASSWORD[0],
                                         master_domain_ip)
        if status:
            self.blocked = True

        waitForVMState(config.VM_NAME, state=config.VM_PAUSED)
        assert status

        logger.info("Unblocking connection from vdsm to storage domain")
        status = unblockOutgoingConnection(host_ip,
                                           config.VDS_USER[0],
                                           config.VDS_PASSWORD[0],
                                           master_domain_ip)
        if status:
            self.blocked = False

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        for index, disk in enumerate(helpers.DISKS_NAMES):
            state, out = helpers.verify_write_operation_to_disk(
                config.VM_NAME, disk_number=index)
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
            logger.info("Unblocking connectivity from host %s to storage "
                        "domain %s", config.HOSTS[0], config.SD_NAME)

            logger.info("Unblocking connection from vdsm to storage domain")
            status = unblockOutgoingConnection(config.HOSTS[0],
                                               config.VDS_USER[0],
                                               config.VDS_PASSWORD[0],
                                               self.master_domain_ip)

            if not status:
                raise exceptions.HostException("Failed to unblock "
                                               "connectivity from host %s to "
                                               "storage domain %s"
                                               % (config.HOSTS[0],
                                                  self.master_domain_ip))
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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk in vm_disks:
            logger.info('check if disk %s is visible as RO to vm %s'
                        % (ro_disk.get_alias(), config.VM_NAME))
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(is_read_only,
                            "Disk %s is not visible to vm %s as Read "
                            "Only disk"
                            % (ro_disk.get_alias(), config.VM_NAME))

        self.is_migrated = migrateVm(True, config.VM_NAME)

        for ro_disk in vm_disks:
            logger.info('check if disk %s is still visible as RO to vm %s'
                        'after migration', ro_disk.get_alias(),
                        config.VM_NAME)
            is_read_only = ro_disk.get_read_only()
            self.assertTrue(is_read_only,
                            "Disk %s is not visible to vm %s as Read "
                            "Only disk"
                            % (ro_disk.get_alias(), config.VM_NAME))

    def tearDown(self):
        if self.is_migrated:
            status = migrateVm(True, config.VM_NAME)
            if not status:
                raise exceptions.VMException("Failed to migrate vm")
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
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)
        logger.info("Suspending vm %s", config.VM_NAME)
        suspendVm(True, config.VM_NAME)
        logger.info("Re activating vm %s", config.VM_NAME)
        startVm(True, config.VM_NAME)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)


@attr(tier=1)
class TestCase332480(DefaultEnvironment):
    """
    Export and import a vm with RO disk attached to it
    https://tcms.engineering.redhat.com/case/332480/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '332480'
    imported_vm = 'imported_vm'
    export_domain = ''

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_export_and_import_vm_with_RO_disk(self):
        """
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Export the VM to an export domain
        - Import the same VM
        - Check that disk is visible to the VM
        - Verify that it's impossible to write to the disk
        """
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)

        master_domain = get_master_storage_domain_name(config.DC_NAME)
        self.export_domain = findExportStorageDomains(config.DC_NAME)[0]

        logger.info("Exporting vm %s", config.VM_NAME)
        start_vms([config.VM_NAME], max_workers=1, wait_for_ip=True)
        waitForVMState(config.VM_NAME)
        vm_ip = get_vm_ip(config.VM_NAME)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        stop_vms_safely([config.VM_NAME])
        assert exportVm(True, config.VM_NAME, self.export_domain)
        logger.info("Importing vm %s as %s", config.VM_NAME, self.imported_vm)
        assert importVm(True, vm=config.VM_NAME,
                        export_storagedomain=self.export_domain,
                        import_storagedomain=master_domain,
                        cluster=config.CLUSTER_NAME, name=self.imported_vm)

        start_vms([self.imported_vm], 1, wait_for_ip=False)
        waitForVMState(self.imported_vm)
        helpers.write_on_vms_ro_disks(self.imported_vm, imported_vm=True)

    def tearDown(self):
        assert removeVm(True, self.imported_vm, stopVM='true', wait=True)
        assert removeVmFromExportDomain(
            True, vm=config.VM_NAME, datacenter=config.DC_NAME,
            export_storagedomain=self.export_domain)
        super(TestCase332480, self).tearDown()


@attr(tier=2)
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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)
        master_domain = get_master_storage_domain_name(config.DC_NAME)
        self.export_domain = findExportStorageDomains(config.DC_NAME)[0]

        logger.info("Exporting vm %s", config.VM_NAME)
        start_vms([config.VM_NAME], max_workers=1, wait_for_ip=True)
        waitForVMState(config.VM_NAME)
        vm_ip = get_vm_ip(config.VM_NAME)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        stop_vms_safely([config.VM_NAME])

        assert exportVm(True, config.VM_NAME, self.export_domain)
        logger.info("Importing vm %s as %s", config.VM_NAME,
                    self.imported_vm_1)
        assert importVm(True, config.VM_NAME, self.export_domain,
                        master_domain,
                        config.CLUSTER_NAME, name=self.imported_vm_1)
        start_vms([self.imported_vm_1], max_workers=1, wait_for_ip=False)
        waitForVMState(self.imported_vm_1)

        logger.info("Importing vm %s as %s", config.VM_NAME,
                    self.imported_vm_2)
        assert importVm(True, config.VM_NAME, self.export_domain,
                        master_domain,
                        config.CLUSTER_NAME, name=self.imported_vm_2)
        start_vms([self.imported_vm_2], max_workers=1, wait_for_ip=False)
        waitForVMState(self.imported_vm_2)

        helpers.write_on_vms_ro_disks(self.imported_vm_1, imported_vm=True)
        helpers.write_on_vms_ro_disks(self.imported_vm_2, imported_vm=True)

    def tearDown(self):
        stop_vms_safely([self.imported_vm_1, self.imported_vm_2])
        removeVms(True, [self.imported_vm_1, self.imported_vm_2])
        assert removeVmFromExportDomain(
            True, vm=config.VM_NAME, datacenter=config.DC_NAME,
            export_storagedomain=self.export_domain)
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
        snap_disks = get_snapshot_disks(config.VM_NAME,
                                        self.snapshot_description)
        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk in ro_vm_disks:
            logger.info("Check that RO disk %s is part of the snapshot",
                        ro_disk.get_alias())

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(is_part_of_disks, "RO disk %s is not part of the "
                                              "snapshot that was taken"
                                              % ro_disk.get_alias())
        stop_vms_safely([config.VM_NAME])
        logger.info("Previewing snapshot %s", self.snapshot_description)
        self.create_snapshot = preview_snapshot(True, config.VM_NAME,
                                                self.snapshot_description)

        assert self.create_snapshot
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        if self.create_snapshot:
            assert undo_snapshot_preview(True, config.VM_NAME)

        super(TestCase332483, self).tearDown()

        if not removeSnapshot(True,
                              config.VM_NAME,
                              self.snapshot_description):
            raise exceptions.SnapshotException("Failed to remove "
                                               "snapshot %s"
                                               % self.snapshot_description)


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
        snap_disks = get_snapshot_disks(config.VM_NAME,
                                        self.snapshot_description)
        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk in ro_vm_disks:
            logger.info("Check that RO disk %s is part of the snapshot",
                        ro_disk.get_alias())

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(is_part_of_disks, "RO disk %s is not part of the "
                                              "snapshot that was taken"
                                              % ro_disk.get_alias())
        stop_vms_safely([config.VM_NAME])
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = preview_snapshot(True, config.VM_NAME,
                                  self.snapshot_description)
        self.create_snapshot = status

        assert status

        status = undo_snapshot_preview(True, config.VM_NAME)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        assert status

        self.create_snapshot = not status

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        if self.create_snapshot:
            undo_snapshot_preview(True, config.VM_NAME)

        super(TestCase337931, self).tearDown()
        if not removeSnapshot(True,
                              config.VM_NAME,
                              self.snapshot_description):
            raise exceptions.SnapshotException("Failed to remove "
                                               "snapshot %s"
                                               % self.snapshot_description)


@attr(tier=0)
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
        snap_disks = get_snapshot_disks(config.VM_NAME,
                                        self.snapshot_description)
        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk in ro_vm_disks:
            logger.info("Check that RO disk %s is part of the snapshot",
                        ro_disk.get_alias())

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(is_part_of_disks, "RO disk %s is not part of the "
                                              "snapshot that was taken"
                                              % ro_disk.get_alias())
        stop_vms_safely([config.VM_NAME])
        logger.info("Previewing snapshot %s", self.snapshot_description)
        status = preview_snapshot(True, config.VM_NAME,
                                  self.snapshot_description)
        self.create_snapshot = True
        assert status

        status = commit_snapshot(True, config.VM_NAME)
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        assert status
        self.create_snapshot = not status

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        if self.create_snapshot:
            undo_snapshot_preview(True, config.VM_NAME)

        super(TestCase337930, self).tearDown()
        if not removeSnapshot(True,
                              config.VM_NAME,
                              self.snapshot_description):
            raise exceptions.SnapshotException("Failed to remove "
                                               "snapshot %s"
                                               % self.snapshot_description)


@attr(tier=0)
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
        snap_disks = get_snapshot_disks(config.VM_NAME,
                                        self.snapshot_description)
        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        for ro_disk in ro_vm_disks:
            logger.info("Check that RO disk %s is part of the snapshot",
                        ro_disk.get_alias())

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(is_part_of_disks, "RO disk %s is not part of the "
                                              "snapshot that was taken"
                                              % ro_disk.get_alias())
        stop_vms_safely([config.VM_NAME])
        logger.info("Removing snapshot %s", self.snapshot_description)

        status = removeSnapshot(True, config.VM_NAME,
                                self.snapshot_description,
                                timeout=TASK_TIMEOUT)

        assert status
        self.snapshot_removed = status

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        helpers.write_on_vms_ro_disks(config.VM_NAME)

    def tearDown(self):
        stop_vms_safely([config.VM_NAME])
        if not self.snapshot_removed:
            if not removeSnapshot(True,
                                  config.VM_NAME,
                                  self.snapshot_description):
                raise exceptions.SnapshotException("Failed to remove "
                                                   "snapshot %s"
                                                   % self.snapshot_description)
        super(TestCase337934, self).tearDown()


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
    @bz('1072471')
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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        vm_ip = get_vm_ip(config.VM_NAME)

        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))

        logger.info("Adding new snapshot %s", self.snapshot_description)
        setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        assert addSnapshot(True, config.VM_NAME,
                           self.snapshot_description)

        snap_disks = get_snapshot_disks(config.VM_NAME,
                                        self.snapshot_description)

        for ro_disk in ro_vm_disks:
            logger.info("Check that RO disk %s is part of the snapshot",
                        ro_disk.get_alias())

            is_part_of_disks = ro_disk.get_id() in [d.get_id() for d in
                                                    snap_disks]

            self.assertTrue(is_part_of_disks, "RO disk %s is not part of the "
                                              "snapshot that was taken"
                                              % ro_disk.get_alias())
        status = cloneVmFromSnapshot(True, name=self.cloned_vm_name,
                                     snapshot=self.snapshot_description,
                                     cluster=config.CLUSTER_NAME)
        if status:
            self.cloned = True

        self.assertTrue(status, "Failed to clone vm from snapshot")

        for index, disk in enumerate(ro_vm_disks):
            state, out = helpers.verify_write_operation_to_disk(
                self.cloned_vm_name, disk_number=index)
            logger.info("Trying to write to read only disk...")
            status = (not state) and ((READ_ONLY in out) or
                                      (NOT_PERMITTED in out))
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

    def tearDown(self):
        if self.cloned:
            if not removeVm(True, self.cloned_vm_name, stopVM='true',
                            wait=True):
                raise exceptions.VMException("Failed to remove cloned vm %s"
                                             % self.cloned_vm_name)

        stop_vms_safely([config.VM_NAME])
        super(TestCase337935, self).tearDown()

        if not removeSnapshot(True,
                              config.VM_NAME,
                              self.snapshot_description):
            raise exceptions.SnapshotException("Failed to remove "
                                               "snapshot %s"
                                               % self.snapshot_description)


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
        helpers.prepare_disks_for_vm(config.VM_NAME, helpers.DISKS_NAMES,
                                     read_only=True)

        sd = get_master_storage_domain_name(config.DC_NAME)

        stop_vms_safely([config.VM_NAME])

        logger.info("creating template %s", self.template_name)
        assert createTemplate(True, vm=config.VM_NAME,
                              name=self.template_name,
                              cluster=config.CLUSTER_NAME,
                              storagedomain=sd)

        logger.info("Cloning vm from template")

        self.cloned = cloneVmFromTemplate(True, self.cloned_vm_name,
                                          self.template_name,
                                          config.CLUSTER_NAME)

        self.assertTrue(self.cloned, "Failed to clone vm from template")

        logger.info("Cloning vm from template as Thin copy")
        self.cloned = cloneVmFromTemplate(True, self.thin_cloned_vm_name,
                                          self.template_name,
                                          config.CLUSTER_NAME,
                                          clone=False)
        self.assertTrue(self.cloned, "Failed to clone vm from template")
        start_vms(self.cloned_vms, 2, wait_for_ip=False)
        assert waitForVmsStates(True, self.cloned_vms)
        for vm in self.cloned_vms:
            cloned_vm_disks = getVmDisks(vm)
            cloned_vm_disks = [disk for disk in cloned_vm_disks if
                               (not disk.get_bootable())]

            for index, disk in enumerate(cloned_vm_disks):
                logger.info('check if disk %s is visible as RO to vm %s',
                            disk.get_alias(), vm)
                is_read_only = disk.get_read_only()
                self.assertTrue(is_read_only,
                                "Disk %s is not visible to vm %s as Read "
                                "Only disk"
                                % (disk.get_alias(), vm))

                logger.info("Trying to write to read only disk...")
                state, out = helpers.verify_write_operation_to_disk(
                    vm, disk_number=index)
                status = (not state) and ((READ_ONLY in out) or
                                          (NOT_PERMITTED in out))
                self.assertTrue(status, "Write operation to RO disk succeeded")
                logger.info("Failed to write to read only disk")

    def tearDown(self):
        if self.cloned:
            if not removeVms(True, self.cloned_vms, stop='true'):
                raise exceptions.VMException("Failed to remove cloned vm")
        waitForTemplatesStates(self.template_name)

        if not removeTemplate(True, self.template_name,
                              timeout=TEMPLATE_TIMOUT):
            raise exceptions.TemplateException("Failed to remove "
                                               "template %s"
                                               % self.template_name)
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
        assert helpers.prepare_disks_for_vm(config.VM_NAME,
                                            helpers.DISKS_NAMES,
                                            read_only=True)

        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        for index, disk in enumerate(ro_vm_disks):
            state, out = helpers.verify_write_operation_to_disk(
                config.VM_NAME, disk_number=index)
            logger.info("Trying to write to read only disk %s...", disk)
            status = (not state) and ((READ_ONLY in out)) or (NOT_PERMITTED
                                                              in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")

        for index, disk in enumerate(ro_vm_disks):
            logger.info("Unplugging vm disk %s", disk.get_alias())
            assert deactivateVmDisk(True, config.VM_NAME, disk.get_alias())

            move_vm_disk(config.VM_NAME, disk.get_alias(), config.SD_NAME_1)
            waitForDisksState(disk.get_alias())
            logger.info("disk %s moved", disk.get_alias())
            vm_disk = getVmDisk(config.VM_NAME, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(is_disk_ro, "Disk %s is not read only after move "
                                        "to different storage domain"
                                        % vm_disk.get_alias())
            logger.info("Disk %s is read only after move "
                        "to different storage domain" % vm_disk.get_alias())


@attr(tier=1)
class TestCase332477(DefaultEnvironment):
    """
    Checks that Live Storage Migration of RO disk should be possible
    https://tcms.engineering.redhat.com/case/332477/?from_plan=12049

    Currently __test__ = False due to bug 1091956 that corrupt the
    image volumes:
    https://bugzilla.redhat.com/show_bug.cgi?id=1091956
    """
    __test__ = False
    tcms_test_case = '332477'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_live_migrate_RO_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the disk (LSM) to the second storage domain
        """
        assert helpers.prepare_disks_for_vm(config.VM_NAME,
                                            helpers.DISKS_NAMES,
                                            read_only=True)

        ro_vm_disks = filter(not_bootable, getVmDisks(config.VM_NAME))
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        for index, disk in enumerate(ro_vm_disks):
            move_vm_disk(config.VM_NAME, disk.get_alias(), config.SD_NAME_1)

            logger.info("disk %s moved", disk.get_alias())
            vm_disk = getVmDisk(config.VM_NAME, disk.get_alias())
            is_disk_ro = vm_disk.get_read_only()
            self.assertTrue(is_disk_ro, "Disk %s is not read only after move "
                                        "to different storage domain"
                                        % vm_disk.get_alias())
            logger.info("Disk %s is read only after move "
                        "to different storage domain" % vm_disk.get_alias())


@attr(tier=1)
class TestCase332482(TestCase):
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

    Currently __test__ = False due to bug 1091956 that corrupt the
    image volumes:
    https://bugzilla.redhat.com/show_bug.cgi?id=1091956
    """
    __test__ = False
    tcms_test_case = '334876'

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_live_migrate_RW_disk(self):
        """
        - 2 storage domains
        - VM with OS
        - Attaching RO disks to the VM (all possible permutation)
        - Activate the disk
        - Try to move the first RW to the second storage domain

        """
        bootable = getVmDisks(config.VM_NAME)[0]
        assert helpers.prepare_disks_for_vm(config.VM_NAME,
                                            helpers.DISKS_NAMES,
                                            read_only=True)

        vm_disks = getVmDisks(config.VM_NAME)
        ro_vm_disks = [d for d in vm_disks if (not d.get_bootable())]

        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])

        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)

        move_vm_disk(config.VM_NAME, bootable.get_alias(), config.SD_NAME_1)


@attr(tier=1)
class TestCase334923(TestCase):
    """
    Check that RO disk is available for lower versions than 3.4
    https://tcms.engineering.redhat.com/case/334923/?from_plan=12049
    """
    __test__ = True
    tcms_test_case = '334923'
    cluster_name = 'test_cluster_334923'
    datacenter_name = 'low_dc_334923'
    version = '3.3'
    test_vm_name = 'test_vm_334923'
    sd_name = 'sd_334923'
    disk_name = 'disk_334923'

    def setUp(self):
        if not addDataCenter(True, name=self.datacenter_name,
                             local=False, version=self.version):
            raise exceptions.DataCenterException("addDataCenter %s with "
                                                 "storage type %s and "
                                                 "version %s failed."
                                                 % (self.datacenter_name,
                                                    config.STORAGE_TYPE,
                                                    self.version))
        logger.info("Datacenter %s was created successfully",
                    self.datacenter_name)

        if not addCluster(True, name=self.cluster_name, cpu=config.CPU_NAME,
                          data_center=self.datacenter_name,
                          version=self.version):
            raise exceptions.ClusterException("addCluster %s with cpu_"
                                              "type %s and version %s to "
                                              "datacenter %s failed"
                                              % (self.cluster_name,
                                                 config.CPU_NAME,
                                                 self.version,
                                                 self.datacenter_name))
        logger.info("Cluster %s was created successfully", self.cluster_name)

        deactivateHost(True, config.HOSTS[0])
        updateHost(True, config.HOSTS[0], cluster=self.cluster_name)
        activateHost(True, config.HOSTS[0])

        helpers.create_third_sd(self.sd_name, config.HOSTS[0])

        attachStorageDomain(True, self.datacenter_name, self.sd_name)
        disk_args = {
            'provisioned_size': config.DISK_SIZE,
            'wipe_after_delete': config.BLOCK_FS,
            'storagedomain': self.sd_name,
            'bootable': False,
            'shareable': False,
            'active': True,
            'size': config.DISK_SIZE,
            'format': config.FORMAT_COW,
            'interface': config.VIRTIO,
            'sparse': True,
            'alias': self.disk_name}
        assert addDisk(True, **disk_args)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_RO_disk_available_compatibility_version(self):
        """
        - Create a VM
        - Add a disk to the VM
        """
        logger.info('Creating vm')
        if not addVm(True, wait=True, name=self.test_vm_name,
                     cluster=self.cluster_name):
            raise exceptions.VMException("Failed to create vm %s"
                                         % self.test_vm_name)
        stop_vms_safely([self.test_vm_name])
        logger.info("Attaching a RO in %s cluster", self.version)
        assert helpers.prepare_disks_for_vm(self.test_vm_name,
                                            [self.disk_name],
                                            read_only=True)

    def tearDown(self):
        logger.info("Removing vm %s", self.test_vm_name)
        assert removeVm(True, self.test_vm_name, stopVM='true', wait=True)
        wait_for_tasks(config.VDC, config.VDC_PASSWORD, self.datacenter_name)
        logger.info("Restoring environment")

        assert deactivateStorageDomain(True, self.datacenter_name,
                                       self.sd_name)
        assert removeDataCenter(True, self.datacenter_name)
        assert deactivateHost(True, config.HOSTS[0])
        assert updateHost(True, config.HOSTS[0], cluster=config.CLUSTER_NAME)
        assert activateHost(True, config.HOSTS[0])
        assert removeCluster(True, cluster=self.cluster_name)


@attr(tier=2)
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
        assert helpers.prepare_disks_for_vm(config.VM_NAME,
                                            helpers.DISKS_NAMES,
                                            read_only=True)
        logger.info("Killing qemu process")
        status = kill_qemu_process(config.VM_NAME, config.HOSTS[0],
                                   config.VDS_USER[0],
                                   config.VDS_PASSWORD[0])
        self.assertTrue(status, "Failed to kill qemu process")
        logger.info("qemu process killed")
        start_vms([config.VM_NAME], 1, wait_for_ip=False)
        waitForVMState(config.VM_NAME)
        ro_vm_disks = getVmDisks(config.VM_NAME)
        ro_vm_disks = [d for d in ro_vm_disks if (not d.get_bootable())]
        logger.info("VM disks: %s", [d.get_alias() for d in ro_vm_disks])
        for index, disk in enumerate(ro_vm_disks):
            state, out = helpers.verify_write_operation_to_disk(
                config.VM_NAME, disk_number=index)
            logger.info("Trying to write to read only disk...")
            status = not state and (READ_ONLY in out or NOT_PERMITTED in out)
            self.assertTrue(status, "Write operation to RO disk succeeded")
            logger.info("Failed to write to read only disk")


@attr(tier=2)
class TestCase332485(TestCase):
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


@attr(tier=2)
class TestCase332486(TestCase):
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


@attr(tier=2)
class TestCase332488(TestCase):
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
class TestCase332487(TestCase):
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
