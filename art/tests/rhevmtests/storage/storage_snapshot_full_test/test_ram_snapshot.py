"""
Storage full snapshot test - ram snapshot
"""

import logging
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from nose.tools import istest

from art.rhevm_api.tests_lib.high_level.vms import shutdown_vm_if_up
from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost, \
    getAnyNonSPMHost
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getDCStorages,
    findMasterStorageDomain)
from art.rhevm_api.tests_lib.low_level.vms import updateVm, \
    startVm, addSnapshot, is_snapshot_with_memory_state, createVm, \
    stopVm, restoreSnapshot, undo_snapshot_preview, preview_snapshot, addVm, \
    removeVm, exportVm, importVm, removeVmFromExportDomain, \
    removeSnapshot, kill_process_by_pid_on_vm, shutdownVm, \
    wait_for_vm_snapshots
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler import exceptions as errors
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from helpers import is_pid_running_on_vm
import config
import helpers

logger = logging.getLogger(__name__)
TCMS_TEST_PLAN = '10134'


def setup_module():
    """
    Create datacenter with 2 hosts, 2 storage domains and 1 export domain
    Create vm and install OS on it, with snapshot after OS installation
    """
    rc, masterSD = findMasterStorageDomain(True, config.DC_NAME)
    assert rc
    masterSD = masterSD['masterDomain']

    logger.info('Creating vm and installing OS on it')

    vmArgs = {'positive': True,
              'vmName': config.VM_NAME[0],
              'vmDescription': config.VM_NAME[0],
              'diskInterface': config.ENUMS['interface_virtio'],
              'volumeFormat': config.ENUMS['format_cow'],
              'cluster': config.CLUSTER_NAME,
              'storageDomainName': masterSD,
              'installation': True,
              'size': config.DISK_SIZE,
              'nic': 'nic1',
              'image': config.COBBLER_PROFILE,
              'useAgent': True,
              'os_type': config.ENUMS['rhel6'],
              'user': config.VM_USER,
              'password': config.VM_PASSWORD
              }

    if not createVm(**vmArgs):
        raise errors.VMException('Unable to create vm %s for test'
                                 % config.VM_NAME[0])

    logger.info('Creating base snapshot %s for vm %s', config.BASE_SNAPSHOT,
                config.VM_NAME[0])
    if not addSnapshot(True, config.VM_NAME[0], config.BASE_SNAPSHOT):
        raise errors.VMException('Unable to create base snapshot for vm %s'
                                 % config.VM_NAME[0])

    logger.info('Shutting down VM %s', config.VM_NAME[0])
    shutdown_vm_if_up(config.VM_NAME[0])


class DCWithStoragesActive(TestCase):
    """
    A class that ensures DC is up with all storages active and SPM elected.
    """

    __test__ = False

    spm = None
    hsm = None
    master_sd = None
    non_master_sd = None
    base_snapshot = config.BASE_SNAPSHOT
    vm = config.VM_NAME[0]

    @classmethod
    def setup_class(cls):
        """
        Ensure DC is up, all storages are active and SPM is elected
        """
        logger.info('Checking DC %s state', config.DC_NAME)
        if not waitForDataCenterState(config.DC_NAME):
            raise errors.DataCenterException('DC %s is not up' %
                                             config.DC_NAME)

        storage_domains = getDCStorages(config.DC_NAME,
                                        get_href=False)

        logger.info('Ensuring all domains are up')
        inactive_domains = [domain.get_name() for domain in storage_domains if
                            domain.get_status().get_state() !=
                            config.SD_ACTIVE]

        if inactive_domains:
            raise errors.StorageDomainException('Domains %s not active' %
                                                inactive_domains)

        cls.spm = getSPMHost(config.HOSTS)
        rc, cls.hsm = getAnyNonSPMHost(config.HOSTS,
                                       expected_states=[config.HOST_UP])
        logger.info('Status: %s, Got HSM host: %s', rc, cls.hsm)
        cls.hsm = cls.hsm['hsmHost']

        logger.info('SPM is: %s, HSM is %s', cls.spm, cls.hsm)

        assert cls.spm
        assert cls.hsm

        for domain in storage_domains:
            if domain.get_master():
                cls.master_sd = domain.get_name()
            else:
                cls.non_master_sd = domain.get_name()

        assert cls.master_sd and cls.non_master_sd

    @classmethod
    def teardown_class(cls):
        """
        Return to vm's base snapshot (with OS clean installation)
        """
        logger.info('Shutting down vm %s if it is up', cls.vm)
        assert shutdown_vm_if_up(cls.vm)
        logger.info('Restoring base snapshot %s on vm %s',
                    cls.base_snapshot, cls.vm)
        assert restoreSnapshot(True, cls.vm, cls.base_snapshot)
        wait_for_vm_snapshots(cls.vm, config.SNAPSHOT_OK)


class VMWithMemoryStateSnapshot(DCWithStoragesActive):
    """
    Class with VM with base RAM snapshot to be used as base for tests that
    do not need to create RAM snapshot
    """

    __test__ = False
    memory_snapshot = config.RAM_SNAPSHOT % 0
    persist_network = False
    pids = []
    cmdlines = ['/dev/zero']

    @classmethod
    def setup_class(cls):
        """
        Start vm, run process on vm and create RAM snapshot
        """
        super(VMWithMemoryStateSnapshot, cls).setup_class()
        logger.info('Starting vm %s and waiting for it to boot', cls.vm)
        if not startVm(True, cls.vm, wait_for_ip=True):
            raise errors.VMException('Error waiting for vm %s to boot', cls.vm)

        status, pid = helpers.start_cat_process_on_vm(cls.vm, cls.cmdlines[0])
        logger.info('PID for first cat process is: %s', pid)
        cls.pids = [pid]

        assert status

        if cls.persist_network:
            vm_ip = LookUpVMIpByName('', '').get_ip(cls.vm)
            logger.info('Setting persistant network on vm %s', cls.vm)
            assert setPersistentNetwork(vm_ip, config.VM_PASSWORD)

        logger.info('Creating snapshot %s with RAM state', cls.memory_snapshot)
        if not addSnapshot(True, cls.vm, cls.memory_snapshot,
                           persist_memory=True):
            raise errors.VMException('Unable to create RAM snapshot %s on vm '
                                     '%s' % (cls.memory_snapshot, cls.vm))
        logger.info('Wait for snapshot %s to be created', cls.memory_snapshot)
        wait_for_vm_snapshots(cls.vm, config.SNAPSHOT_OK)
        logger.info('Snapshot created successfully')

        logger.info('Stopping vm %s', cls.vm)
        assert stopVm(True, cls.vm)


class CreateSnapshotWithMemoryState(DCWithStoragesActive):
    """
    Create a snapshot with memory state on specified host according to
    run_test_on_spm
    """

    __test__ = False
    tcms_test_case = None
    run_test_on_spm = True
    host_for_test = None
    snapshot = config.RAM_SNAPSHOT % 0

    @classmethod
    def setup_class(cls):
        """
        Set vm to run on specified host the start vm
        """
        super(CreateSnapshotWithMemoryState, cls).setup_class()

        logger.info('Shutting down vm %s', cls.vm)
        shutdown_vm_if_up(cls.vm)

        cls.host_for_test = cls.spm if cls.run_test_on_spm else cls.hsm
        logger.info('Setting vm %s to run on host: %s', cls.vm,
                    cls.host_for_test)
        kwargs = {'placement_affinity': config.VM_PINNED,
                  'placement_host': cls.host_for_test}
        if not updateVm(True, cls.vm, **kwargs):
            raise errors.VMException('Could not pin vm %s to host %s'
                                     % (cls.vm, cls.host_for_test))

        logger.info('Starting VM %s', cls.vm)
        if not startVm(True, cls.vm, wait_for_ip=True):
            raise errors.VMException('Error when booting vm %s', cls.vm)

    def create_snapshot(self):
        """
        Create a snapshot with memory state
        """
        logger.info('Starting process on vm %s', self.vm)
        status, _ = helpers.start_cat_process_on_vm(self.vm, '/dev/zero')
        self.assertTrue(status)

        logger.info('Creating snapshot %s on vm %s', self.snapshot,
                    self.vm)
        self.assertTrue(addSnapshot(True, self.vm, self.snapshot,
                                    persist_memory=True),
                        'Unable to create RAM snapshot on vm %s' % self.vm)

        logger.info('Ensuring snapshot %s has memory state', self.snapshot)
        self.assertTrue(is_snapshot_with_memory_state(self.vm,
                                                      self.snapshot),
                        'Snapshot %s does not contain memory state'
                        % self.snapshot)

    @classmethod
    def teardown_class(cls):
        """
        Reset vm host placement to be on any host
        """
        logger.info('Shutting down vm %s if up', cls.vm)
        assert shutdown_vm_if_up(cls.vm)

        logger.info('Setting vm %s to run on any host', cls.vm)

        kwargs = {'placement_affinity': config.VM_ANY_HOST,
                  'placement_host': None}
        assert updateVm(True, cls.vm, **kwargs)
        super(CreateSnapshotWithMemoryState, cls).teardown_class()


@attr(tier=0)
class TestCase294432(CreateSnapshotWithMemoryState):
    """
    TCMS Test Case 294432 - Create Snapshot with Memory State on SPM
    """
    __test__ = True
    run_test_on_spm = True
    tcms_test_case = '294432'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_create_snapshot_spm(self):
        """
        Create ram snapshot on spm
        """
        self.create_snapshot()


@attr(tier=0)
class TestCase294434(CreateSnapshotWithMemoryState):
    """
    TCMS Test Case 294434 - Create Snapshot with Memory State on HSM
    """
    __test__ = True
    run_test_on_spm = False
    tcms_test_case = '294434'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_create_snapshot_hsm(self):
        """
        Create ram snapshot on hsm
        """
        self.create_snapshot()


class ReturnToSnapshot(VMWithMemoryStateSnapshot):
    """
    Class that returns to snapshot (using preview or
    commit as specified)
    """
    __test__ = False
    tcms_test_case = None
    test_action = None

    def return_to_ram_snapshot(self):
        """
        Commit RAM snapshot
        """
        logger.info('Checking RAM snapshot %s on vm %s using action %s',
                    self.memory_snapshot, self.vm, self.test_action.__name__)
        self.assertTrue(self.test_action(True,
                                         self.vm,
                                         self.memory_snapshot,
                                         restore_memory=True),
                        'Could not restore RAM snapshot %s on vm %s' %
                        (self.memory_snapshot, self.vm))

        logger.info('Starting vm %s')
        self.assertTrue(startVm(True, vm=self.vm, wait_for_ip=True,
                                wait_for_status=config.VM_UP),
                        'Error when resuming VM %s from memory snapshot %s' %
                        (self.vm, self.memory_snapshot))

        logger.info('Checking if process is still running on vm %s', self.vm)
        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0],
                                             self.cmdlines[0]),
                        'Process %s not running on vm %s' %
                        (self.pids[0], self.vm))


@attr(tier=0)
class TestCase294435(ReturnToSnapshot):
    """
    TCMS Test Case 294435 - Preview to RAM Snapshot
    """
    __test__ = True
    tcms_test_case = '294435'
    test_action = staticmethod(preview_snapshot)

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_preview_snapshot(self):
        """
        preview snapshot
        """
        self.return_to_ram_snapshot()

    @classmethod
    def teardown_class(cls):
        """
        Undo preview snapshot
        """
        logger.info('Undo preview snapshot %s on vm %s', cls.memory_snapshot,
                    cls.vm)
        assert undo_snapshot_preview(True, cls.vm, True)
        wait_for_vm_snapshots(cls.vm, config.SNAPSHOT_OK)
        super(TestCase294435, cls).teardown_class()


@attr(tier=0)
class TestCase294437(ReturnToSnapshot):
    """
    TCMS Test Case 294437 - Commit to RAM Snapshot
    """
    __test__ = True
    tcms_test_case = '294437'
    test_action = staticmethod(restoreSnapshot)

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_restore_snasphot(self):
        """
        restore snapshot
        """
        self.return_to_ram_snapshot()


@attr(tier=1)
class TestCase294439(VMWithMemoryStateSnapshot):
    """
    TCMS Test Case 294439 - VM with multiple RAM Snapshots
    """

    __test__ = False
    tcms_test_case = '294439'
    second_snapshot_name = config.RAM_SNAPSHOT % 1
    previewed_snapshot = None

    @classmethod
    def setup_class(cls):
        """
        Restore first ram snapshot and resume the vm
        """
        super(TestCase294439, cls).setup_class()
        cls.cmdlines.append('/dev/urandom')

        logger.info('Restoring first ram snapshot (%s) on vm %s', cls.vm,
                    cls.memory_snapshot)
        assert restoreSnapshot(True, cls.vm, cls.memory_snapshot,
                               restore_memory=True)

        logger.info('Resuming vm %s', cls.vm)
        assert startVm(True, cls.vm, wait_for_ip=True,
                       wait_for_status=config.VM_UP)

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    @bz('1018554')
    def test_vm_with_multiple_ram_snapshots(self):
        """
        * Start another process on the vm and create a new memory snapshot.
        * Preview first snapshot and check that only first process is running
        * Preview second snapshot and check that both processes are running
        """
        status, pid = helpers.start_cat_process_on_vm(self.vm,
                                                      self.cmdlines[1])
        self.pids.append(pid)

        self.assertTrue(status, 'Unable to run process on VM %s' % self.vm)

        logger.info('Creating snapshot %s on vm %s',
                    self.second_snapshot_name, self.vm)
        self.assertTrue(addSnapshot(True, self.vm, self.second_snapshot_name,
                                    persist_memory=True),
                        'Unable to create snapshot %s on vm %s'
                        % (self.memory_snapshot, self.vm))

        logger.info('Shutting down vm %s', self.vm)
        self.assertTrue(stopVm(True, self.vm))

        logger.info('Previewing first snapshot (%s) on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(preview_snapshot(True, self.vm,
                                         self.memory_snapshot,
                                         restore_memory=True),
                        'Unable to preview snapshot %s on vm %s'
                        % (self.memory_snapshot, self.vm))
        self.previewed_snapshot = self.memory_snapshot

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_ip=True,
                                wait_for_status=config.VM_UP))

        logger.info('Checking if first process is running on vm %s', self.vm)
        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0],
                                             self.cmdlines[0]),
                        'First process is not running on vm - memory state '
                        'not restored correctly')

        logger.info('Checking that second process is not running on vm %s',
                    self.vm)
        self.assertFalse(is_pid_running_on_vm(self.vm, self.pids[1],
                                              self.cmdlines[1]),
                         'Second process is running on vm - memory state '
                         'not restored correctly')

        logger.info('Powering vm %s off', self.vm)
        self.assertTrue(stopVm(True, self.vm),
                        'Could not power vm %s off' % self.vm)

        logger.info('Undoing snapshot preview')
        self.assertTrue(undo_snapshot_preview(True, self.vm))

        self.previewed_snapshot = None

        logger.info('Previewing second snapshot (%s) on vm %s',
                    self.second_snapshot_name, self.vm)
        self.assertTrue(preview_snapshot(True, self.vm,
                                         self.second_snapshot_name,
                                         restore_memory=True),
                        'Unable to preview snapshot %s on vm %s'
                        % (self.second_snapshot_name, self.vm))
        self.previewed_snapshot = self.second_snapshot_name

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_ip=True,
                                wait_for_status=config.VM_UP))

        logger.info('Checking that both processes are running on vm %s',
                    self.vm)
        first = is_pid_running_on_vm(self.vm, self.pids[0], self.cmdlines[0])
        second = is_pid_running_on_vm(self.vm, self.pids[1], self.cmdlines[1])
        self.assertTrue(first and second,
                        'Processes not both running on vm. First process: %s '
                        'second process: %s' % (first, second))

    @classmethod
    def teardown_class(cls):
        """
        Undo snapshot preview then continue with teardown
        """
        assert shutdown_vm_if_up(cls.vm)

        if cls.previewed_snapshot:
            logger.info('Undoing preview snapshot for snapshot %s',
                        cls.previewed_snapshot)
            assert undo_snapshot_preview(True, cls.vm)
            cls.previewed_snapshot = None
        super(TestCase294439, cls).teardown_class()


@attr(tier=1)
class TestCase294617(VMWithMemoryStateSnapshot):
    """
    TCMS test case 294617 - Create vm from memory snapshot
    """

    __test__ = True
    persist_network = True
    tcms_test_case = '294617'
    cloned_vm_name = '%s_cloned' % config.VM_NAME[0]

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_create_vm_from_memory_state_snapshot(self):
        """
        Create vm from memory snapshot and check process is **not** running
        on new vm
        """

        logger.info('Creating new vm %s from snapshot %s of vm %s',
                    self.cloned_vm_name, self.memory_snapshot, self.vm)

        self.assertTrue(addVm(True,
                              name=self.cloned_vm_name,
                              description=self.cloned_vm_name,
                              snapshot=self.memory_snapshot,
                              cluster=config.CLUSTER_NAME),
                        'Could not create vm %s from snapshot %s'
                        % (self.cloned_vm_name, self.memory_snapshot))

        logger.info('Starting VM %s', self.cloned_vm_name)
        self.assertTrue(startVm(True, self.cloned_vm_name, wait_for_ip=True),
                        'Unable to start VM %s' % self.cloned_vm_name)

        self.assertFalse(is_pid_running_on_vm(self.cloned_vm_name,
                                              self.pids[0], self.cmdlines[0]))

    @classmethod
    def teardown_class(cls):
        """
        Remove cloned vm
        """
        logger.info('Stopping vm %s', cls.cloned_vm_name)
        assert stopVm(True, cls.cloned_vm_name)

        logger.info('Removing vm %s', cls.cloned_vm_name)
        assert removeVm(True, cls.cloned_vm_name)
        super(TestCase294617, cls).teardown_class()


@attr(tier=1)
class TestCase294623(VMWithMemoryStateSnapshot):
    """
    TCMS test case 294623 - Export a vm with memory snapshot
    """

    __test__ = True
    tcms_test_case = '294623'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_export_vm_with_memory_state_snapshot(self):
        """
        Export vm with memory state snapshot and check if export vm has
        snapshot and the snapshot contains memory state
        """
        logger.info('Exporting vm %s to export domain %s', self.vm,
                    config.EXPORT_DOMAIN)
        self.assertTrue(exportVm(True, self.vm, config.EXPORT_DOMAIN),
                        'Unable to export vm %s to export domain %s'
                        % (self.vm, config.EXPORT_DOMAIN))

        # TODO: check that vm was exported with snapshots - currently not
        # possible - RFE?

    @classmethod
    def teardown_class(cls):
        """
        Remove vm from export domain
        """
        logger.info('Removing vm %s from export domain %s', cls.vm,
                    config.EXPORT_DOMAIN)
        removeVmFromExportDomain(True, cls.vm, config.DC_NAME,
                                 config.EXPORT_DOMAIN)
        super(TestCase294623, cls).teardown_class()


@attr(tier=1)
class TestCase294624(VMWithMemoryStateSnapshot):
    """
    TCMS test case 294624 - Import a vm with memory snapshot
    """

    __test__ = True
    persist_network = True

    tcms_test_case = '294624'
    original_vm = '%s_original' % config.VM_NAME[0]

    @classmethod
    def setup_class(cls):
        """
        Export the vm
        """
        super(TestCase294624, cls).setup_class()

        logger.info('Exporting vm %s to domain %s', cls.vm,
                    config.EXPORT_DOMAIN)
        if not exportVm(True, cls.vm, config.EXPORT_DOMAIN):
            raise errors.VMException('Unable to export vm %s to domain %s' %
                                     (cls.vm, config.EXPORT_DOMAIN))
        logger.info('Removing original vm to allow import vm without collapse '
                    'snapshots', )
        if not removeVm(True, cls.vm):
            raise errors.VMException('Unable to remove vm %s', cls.vm)

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_import_vm_with_memory_state_snapshot(self):
        """
        Import a vm that has memory state snapshot and ensure it resumes memory
        state from that snapshot successfully
        """
        logger.info('Importing vm %s from export domain %s', self.vm,
                    config.EXPORT_DOMAIN)
        self.assertTrue(importVm(True, self.vm, config.EXPORT_DOMAIN,
                                 self.master_sd, config.CLUSTER_NAME),
                        'Unable to import vm %s from export domain %s' %
                        (self.vm, config.EXPORT_DOMAIN))

        logger.info('Restoring snapshot %s with memory state on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(restoreSnapshot(True, self.vm,
                                        self.memory_snapshot,
                                        restore_memory=True),
                        'Unable to restore snapshot %s on vm %s' %
                        (self.memory_snapshot, self.vm))

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm,
                                wait_for_status=config.VM_UP),
                        'Unable to start vm %s' % self.vm)

        self.assertTrue(helpers.is_pid_running_on_vm(self.vm,
                                                     self.pids[0],
                                                     self.cmdlines[0]),
                        'process is not running on vm %s, memory state not '
                        'correctly restored' % self.vm)

    @classmethod
    def teardown_class(cls):
        """
        Remove vm from export domain
        """
        logger.info('Removing vm %s from export domain %s', cls.vm,
                    config.EXPORT_DOMAIN)
        removeVmFromExportDomain(True, cls.vm, config.DC_NAME,
                                 config.EXPORT_DOMAIN)
        logger.info('Stopping vm %s', cls.vm)
        assert stopVm(True, cls.vm)

        super(TestCase294624, cls).teardown_class()


@attr(tier=1)
class TestCase294631(VMWithMemoryStateSnapshot):
    """
    TCMS test case 294631 - Remove a snapshot with memory state
    """

    __test__ = True
    tcms_test_case = '294631'

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_remove_memory_state_snapshot(self):
        """
        Remove snapshot with memory state and check that vm starts
        successfully
        """
        logger.info('Removing snapshot %s with memory state from vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(removeSnapshot(True, self.vm, self.memory_snapshot),
                        'Unable to remove snapshot %s from vm %s' %
                        (self.memory_snapshot, self.vm))

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_ip=True,
                                wait_for_status=config.VM_UP),
                        'Unable to start VM %s' % self.vm)

        logger.info('Ensuring vm %s started without memory state', self.vm)
        self.assertFalse(helpers.is_pid_running_on_vm(self.vm, self.pids[0],
                                                      self.cmdlines[0]))


@attr(tier=2)
class TestCase305433(VMWithMemoryStateSnapshot):
    """
    TCMS test case 305433 - Stateless vm with memory snapshot
    """

    __test__ = True
    tcms_test_case = '305433'

    @classmethod
    def setup_class(cls):
        pass

    @istest
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    @bz('1004184')
    def test_stateless_vm_with_memory_snapshot(self):
        """
        * Restore memory snapshot
        * Set vm to stateless
        * Start vm - ensure it resumes from memory state
        * kill process and stop vm
        * Start vm - ensure it resumes from memory state again
        """
        logger.info('Restoring memory snapshot %s on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(restoreSnapshot(True, self.vm, self.memory_snapshot,
                                        restore_memory=True),
                        'Unable to restore snapshot %s on vm %s' %
                        (self.memory_snapshot, self.vm))

        logger.info('Setting vm %s to stateless', self.vm)
        self.assertTrue(updateVm(True, self.vm, stateless=True),
                        'Unable to set vm %s to be stateless' % self.vm)

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_status=config.VM_UP))

        self.assertTrue(helpers.is_pid_running_on_vm(self.vm, self.pids[0],
                                                     self.cmdlines[0]))

        logger.info('Killing process %d', self.pids[0])
        self.assertTrue(kill_process_by_pid_on_vm(self.vm, self.pids[0],
                                                  config.VM_USER,
                                                  config.VM_PASSWORD))

        logger.info('Power vm %s off', self.vm)
        self.assertTrue(shutdownVm(True, self.vm))

        logger.info('Starting vm %s again', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_status=config.VM_UP))

        self.assertTrue(helpers.is_pid_running_on_vm(self.vm, self.pids[0],
                                                     self.cmdlines[0]))

    @classmethod
    def teardown_class(cls):
        """
        Set vm to not be stateless
        """
        logger.info('Setting vm %s to not be stateless', cls.vm)
        assert updateVm(True, cls.vm, stateless=False)
        super(TestCase305433, cls).teardown_class()
