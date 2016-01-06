"""
Storage full snapshot test - ram snapshot
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Ram_Snapshots
"""
import config
import logging
from helpers import is_pid_running_on_vm, start_cat_process_on_vm
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.test_handler import exceptions as errors
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level.datacenters import (
    waitForDataCenterState,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, getAnyNonSPMHost,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    updateVm, startVm, addSnapshot, is_snapshot_with_memory_state,
    stopVm, restore_snapshot, undo_snapshot_preview, preview_snapshot,
    removeVm, exportVm, importVm, removeVmFromExportDomain,
    removeSnapshot, kill_process_by_pid_on_vm, shutdownVm,
    wait_for_vm_snapshots, stop_vms_safely,  startVms,
    cloneVmFromSnapshot, waitForIP, getVmHost, safely_remove_vms,
)
from art.rhevm_api.tests_lib.high_level.vms import shutdown_vm_if_up
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from rhevmtests.storage.helpers import create_vm_or_clone, get_vm_ip

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

vmArgs = {
    'positive': True,
    'vmDescription': "",
    'diskInterface': config.ENUMS['interface_virtio'],
    'volumeFormat': config.ENUMS['format_cow'],
    'cluster': config.CLUSTER_NAME,
    'installation': True,
    'size': config.VM_DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'image': config.COBBLER_PROFILE,
    'useAgent': True,
    'os_type': config.ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
}

VM_PREFIX = "vm_ram_snapshot"
VM_NAME = VM_PREFIX + "_%s"
VM_NAMES = []


def setup_module():
    """
    Create vm and install OS on it, with snapshot after OS installation
    """
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = VM_NAME % storage_type
        args = vmArgs.copy()
        args['storageDomainName'] = storage_domain
        args['vmName'] = vm_name
        logger.info('Creating vm %s and installing OS on it', vm_name)
        assert create_vm_or_clone(**args)
        VM_NAMES.append(vm_name)
        logger.info(
            'Creating base snapshot %s for vm %s', config.BASE_SNAPSHOT,
            vm_name
        )
        assert addSnapshot(True, vm_name, config.BASE_SNAPSHOT)

    logger.info('Shutting down vms %s', VM_NAMES)
    stop_vms_safely(VM_NAMES)


def teardown_module():
    """
    Remove created vms
    """
    safely_remove_vms(VM_NAMES)
    # Ensure the test doesn't finish before the job is removed from the db
    # because it will be mark as unstable in that case
    wait_for_jobs([ENUMS['job_remove_vm']])


class DCWithStoragesActive(TestCase):
    """
    A class that ensures DC is up with all storages active and SPM elected.
    """
    __test__ = False
    spm = None
    hsm = None
    storage_domain = None
    base_snapshot = config.BASE_SNAPSHOT

    def setUp(self):
        """
        Ensure DC is up, all storages are active and SPM is elected
        """
        self.vm = VM_NAME % self.storage
        logger.info('Checking DC %s state', config.DATA_CENTER_NAME)
        if not waitForDataCenterState(config.DATA_CENTER_NAME):
            raise errors.DataCenterException('DC %s is not up' %
                                             config.DATA_CENTER_NAME)

        self.spm = getSPMHost(config.HOSTS)
        rc, self.hsm = getAnyNonSPMHost(
            config.HOSTS, expected_states=[config.HOST_UP],
            cluster_name=config.CLUSTER_NAME
        )
        logger.info('Status: %s, Got HSM host: %s', rc, self.hsm)
        self.hsm = self.hsm['hsmHost']

        logger.info('SPM is: %s, HSM is %s', self.spm, self.hsm)

        assert self.spm
        assert self.hsm

        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

    def tearDown(self):
        """
        Return to vm's base snapshot (with OS clean installation)
        """
        logger.info('Shutting down vm %s if it is up', self.vm)
        assert shutdown_vm_if_up(self.vm)
        logger.info('Restoring base snapshot %s on vm %s',
                    self.base_snapshot, self.vm)
        assert restore_snapshot(True, self.vm, self.base_snapshot)
        wait_for_vm_snapshots(self.vm, config.SNAPSHOT_OK)


class VMWithMemoryStateSnapshot(DCWithStoragesActive):
    """
    Class with VM with base RAM snapshot to be used as base for tests that
    do not need to create RAM snapshot
    """
    __test__ = False
    memory_snapshot = config.RAM_SNAPSHOT % '0'
    persist_network = False
    pids = []
    cmdlines = ['/dev/zero']

    def setUp(self):
        """
        Start vm, run process on vm and create RAM snapshot
        """
        super(VMWithMemoryStateSnapshot, self).setUp()
        logger.info('Starting vm %s and waiting for it to boot', self.vm)
        if not startVm(True, self.vm, wait_for_ip=True):
            raise errors.VMException(
                'Error waiting for vm %s to boot', self.vm
            )

        status, pid = start_cat_process_on_vm(self.vm, self.cmdlines[0])
        logger.info('PID for first cat process is: %s', pid)
        self.pids = [pid]

        assert status

        if self.persist_network:
            vm_ip = get_vm_ip(self.vm)
            logger.info('Setting persistent network on vm %s', self.vm)
            assert setPersistentNetwork(vm_ip, config.VM_PASSWORD)

        logger.info(
            'Creating snapshot %s with RAM state', self.memory_snapshot
        )
        if not addSnapshot(True, self.vm, self.memory_snapshot,
                           persist_memory=True):
            raise errors.VMException('Unable to create RAM snapshot %s on vm '
                                     '%s' % (self.memory_snapshot, self.vm))
        logger.info('Wait for snapshot %s to be created', self.memory_snapshot)
        wait_for_vm_snapshots(self.vm, config.SNAPSHOT_OK)
        logger.info('Snapshot created successfully')

        logger.info('Stopping vm %s', self.vm)
        assert stopVm(True, self.vm)


class CreateSnapshotWithMemoryState(DCWithStoragesActive):
    """
    Create a snapshot with memory state on specified host according to
    run_test_on_spm
    """
    __test__ = False
    polarion_test_case = None
    run_test_on_spm = True
    host_for_test = None
    snapshot = config.RAM_SNAPSHOT % 0

    def setUp(self):
        """
        Set vm to run on specified host the start vm
        """
        super(CreateSnapshotWithMemoryState, self).setUp()
        startVms([self.vm], wait_for_status=config.VM_UP)
        logger.info('VM %s', self.vm)
        self.host_for_test = getVmHost(self.vm)[1]['vmHoster']
        logger.info('Setting vm %s to run on host: %s', self.vm,
                    self.host_for_test)

    def create_snapshot(self):
        """
        Create a snapshot with memory state
        """
        logger.info('Starting process on vm %s', self.vm)
        status, _ = start_cat_process_on_vm(self.vm, '/dev/zero')
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

    def tearDown(self):
        """
        Reset vm host placement to be on any host
        """
        logger.info('Shutting down vm %s if up', self.vm)
        assert shutdown_vm_if_up(self.vm)

        logger.info('Setting vm %s to run on any host', self.vm)

        kwargs = {'placement_affinity': config.VM_ANY_HOST,
                  'placement_host': None}
        assert updateVm(True, self.vm, **kwargs)
        super(CreateSnapshotWithMemoryState, self).tearDown()


@attr(tier=2)
class TestCase5129(CreateSnapshotWithMemoryState):
    """
    Polarion Test Case 5129 - Create Snapshot with Memory State on SPM
    """
    __test__ = True
    run_test_on_spm = True
    polarion_test_case = '5129'
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5129")
    def test_create_snapshot_spm(self):
        """
        Create ram snapshot on spm
        """
        self.create_snapshot()


@attr(tier=2)
class TestCase5140(CreateSnapshotWithMemoryState):
    """
    Polarion Test Case 5140 - Create Snapshot with Memory State on HSM
    """
    __test__ = True
    run_test_on_spm = False
    polarion_test_case = '5140'
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5140")
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
    polarion_test_case = None
    action_to_call = None

    def return_to_ram_snapshot(self):
        """
        Commit RAM snapshot
        """
        logger.info(
            'Checking RAM snapshot %s on vm %s using action %s',
            self.memory_snapshot, self.vm, self.action_to_call.__name__,
        )
        self.assertTrue(
            self.action_to_call(
                True, self.vm, self.memory_snapshot, restore_memory=True,
            ),
            'Could not restore RAM snapshot %s on vm %s' % (
                self.memory_snapshot, self.vm,
            )
        )
        logger.info("Wait for running jobs")
        wait_for_jobs(
            [ENUMS['job_restore_vm_snapshot'], ENUMS['job_preview_snapshot']]
        )

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, vm=self.vm, wait_for_ip=True,
                                wait_for_status=config.VM_UP),
                        'Error when resuming VM %s from memory snapshot %s' %
                        (self.vm, self.memory_snapshot))

        logger.info('Checking if process is still running on vm %s', self.vm)
        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0],
                                             self.cmdlines[0]),
                        'Process %s not running on vm %s' %
                        (self.pids[0], self.vm))


@attr(tier=1)
class TestCase5139(ReturnToSnapshot):
    """
    Polarion Test Case 5139 - Preview to RAM Snapshot
    """
    __test__ = True
    polarion_test_case = '5139'
    action_to_call = staticmethod(preview_snapshot)
    # Bugzilla history
    # 1211588:  CLI auto complete options async and grace_period-expiry are
    # missing for preview_snapshot
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    # 1260177: Restoring a RAM snapshots in RHEL7.2 shows error stating the vm
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5139")
    def test_preview_snapshot(self):
        """
        preview snapshot
        """
        self.return_to_ram_snapshot()

    def tearDown(self):
        """
        Undo preview snapshot
        """
        logger.info('Undo preview snapshot %s on vm %s', self.memory_snapshot,
                    self.vm)
        assert undo_snapshot_preview(True, self.vm, True)
        wait_for_vm_snapshots(self.vm, config.SNAPSHOT_OK)
        super(TestCase5139, self).tearDown()


@attr(tier=1)
class TestCase5138(ReturnToSnapshot):
    """
    Polarion Test Case 5138 - Restore RAM Snapshot
    """
    __test__ = True
    polarion_test_case = '5138'
    action_to_call = staticmethod(restore_snapshot)
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5138")
    def test_restore_snasphot(self):
        """
        restore snapshot
        """
        self.return_to_ram_snapshot()


@attr(tier=2)
class TestCase5137(VMWithMemoryStateSnapshot):
    """
    Polarion Test Case 5137 - VM with multiple RAM Snapshots
    """
    # TODO: Why is this case disabled?
    __test__ = False
    polarion_test_case = '5137'
    second_snapshot_name = config.RAM_SNAPSHOT % 1
    previewed_snapshot = None
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        """
        Restore first ram snapshot and resume the vm
        """
        super(TestCase5137, self).setUp()
        self.cmdlines.append('/dev/urandom')

        logger.info('Restoring first ram snapshot (%s) on vm %s', self.vm,
                    self.memory_snapshot)
        assert restore_snapshot(
            True, self.vm, self.memory_snapshot, restore_memory=True
        )

        logger.info('Resuming vm %s', self.vm)
        assert startVm(True, self.vm, wait_for_ip=True,
                       wait_for_status=config.VM_UP)

    @polarion("RHEVM3-5137")
    def test_vm_with_multiple_ram_snapshots(self):
        """
        * Start another process on the vm and create a new memory snapshot.
        * Preview first snapshot and check that only first process is running
        * Preview second snapshot and check that both processes are running
        """
        status, pid = start_cat_process_on_vm(self.vm,
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

    def tearDown(self):
        """
        Undo snapshot preview then continue with teardown
        """
        assert shutdown_vm_if_up(self.vm)

        if self.previewed_snapshot:
            logger.info('Undoing preview snapshot for snapshot %s',
                        self.previewed_snapshot)
            assert undo_snapshot_preview(True, self.vm)
            self.previewed_snapshot = None
        super(TestCase5137, self).tearDown()


@attr(tier=2)
class TestCase5136(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5136 - Create vm from snapshot with memory
    """

    __test__ = True
    persist_network = True
    polarion_test_case = '5136'
    # Bugzilla history
    # 1178508
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    def setUp(self):
        """
        Set cloned vm name
        """
        self.cloned_vm_name = '%s_%s_cloned' % (VM_PREFIX, self.storage)
        super(TestCase5136, self).setUp()

    @polarion("RHEVM3-5136")
    def test_create_vm_from_memory_state_snapshot(self):
        """
        Create vm from memory snapshot and check process is **not** running
        on new vm
        """

        logger.info('Creating new vm %s from snapshot %s of vm %s',
                    self.cloned_vm_name, self.memory_snapshot, self.vm)

        self.assertTrue(
            cloneVmFromSnapshot(
                True, name=self.cloned_vm_name, cluster=config.CLUSTER_NAME,
                vm=self.vm, snapshot=self.memory_snapshot,
                ),
            'Could not create vm %s from snapshot %s'
            % (self.cloned_vm_name, self.memory_snapshot)
        )

        logger.info('Starting VM %s', self.cloned_vm_name)
        self.assertTrue(
            startVms([self.cloned_vm_name], config.VM_UP),
            'Unable to start VM %s' % self.cloned_vm_name
        )
        status, ip = waitForIP(self.cloned_vm_name)
        if not status:
            raise errors.CanNotFindIP(
                "Failed to get IP for vm %s" % self.cloned_vm_name
            )

        self.assertFalse(is_pid_running_on_vm(self.cloned_vm_name,
                                              self.pids[0], self.cmdlines[0]))

    def tearDown(self):
        """
        Remove cloned vm
        """
        logger.info('Stopping vm %s', self.cloned_vm_name)
        assert stopVm(True, self.cloned_vm_name)

        logger.info('Removing vm %s', self.cloned_vm_name)
        assert removeVm(True, self.cloned_vm_name)
        super(TestCase5136, self).tearDown()


@attr(tier=2)
class TestCase5134(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5134 - Import a vm with memory snapshot
    """

    __test__ = True
    persist_network = True
    polarion_test_case = '5134'
    original_vm = '%s_%s_original' % (
        VM_PREFIX, VMWithMemoryStateSnapshot.storage
    )
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5134")
    def test_import_vm_with_memory_state_snapshot(self):
        """
        Import a vm that has memory state snapshot and ensure it resumes memory
        state from that snapshot successfully
        """
        logger.info('Exporting vm %s to domain %s',
                    self.vm, config.EXPORT_DOMAIN)
        if not exportVm(True, self.vm, config.EXPORT_DOMAIN):
            raise errors.VMException('Unable to export vm %s to domain %s' %
                                     (self.vm, config.EXPORT_DOMAIN))
        logger.info('Removing original vm to allow import vm without collapse '
                    'snapshots')
        if not removeVm(True, self.vm):
            raise errors.VMException('Unable to remove vm %s', self.vm)

        logger.info(
            'Importing vm %s from export domain %s',
            self.vm, config.EXPORT_DOMAIN
        )
        self.assertTrue(importVm(True, self.vm, config.EXPORT_DOMAIN,
                                 self.storage_domain, config.CLUSTER_NAME),
                        'Unable to import vm %s from export domain %s' %
                        (self.vm, config.EXPORT_DOMAIN))

        logger.info('Restoring snapshot %s with memory state on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(
            restore_snapshot(
                True, self.vm, self.memory_snapshot, restore_memory=True
            ), 'Unable to restore snapshot %s on vm %s' %
               (self.memory_snapshot, self.vm)
        )

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm,
                                wait_for_status=config.VM_UP,
                                wait_for_ip=True),
                        'Unable to start vm %s' % self.vm)

        self.assertTrue(is_pid_running_on_vm(self.vm,
                                             self.pids[0],
                                             self.cmdlines[0]),
                        'process is not running on vm %s, memory state not '
                        'correctly restored' % self.vm)

    def tearDown(self):
        """
        Remove vm from export domain
        """
        logger.info('Removing vm %s from export domain %s', self.vm,
                    config.EXPORT_DOMAIN)
        removeVmFromExportDomain(True, self.vm, config.DATA_CENTER_NAME,
                                 config.EXPORT_DOMAIN)
        logger.info('Stopping vm %s', self.vm)
        assert stopVm(True, self.vm)

        super(TestCase5134, self).tearDown()


@attr(tier=2)
class TestCase5133(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5133 - Remove a snapshot with memory state
    """
    __test__ = True
    polarion_test_case = '5133'
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5133")
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
        self.assertFalse(is_pid_running_on_vm(self.vm, self.pids[0],
                                              self.cmdlines[0]))


@attr(tier=4)
class TestCase5131(VMWithMemoryStateSnapshot):
    """
    Polarion test case 5131 - Stateless vm with memory snapshot
    """
    __test__ = True
    polarion_test_case = '5131'
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    bz = {'1270583': {'engine': None, 'version': ["3.6"]}}

    @polarion("RHEVM3-5131")
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
        self.assertTrue(restore_snapshot(
            True, self.vm, self.memory_snapshot, restore_memory=True
        ), 'Unable to restore snapshot %s on vm %s' %
           (self.memory_snapshot, self.vm))

        logger.info('Setting vm %s to stateless', self.vm)
        self.assertTrue(updateVm(True, self.vm, stateless=True),
                        'Unable to set vm %s to be stateless' % self.vm)

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_status=config.VM_UP))

        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0],
                                             self.cmdlines[0]))

        logger.info('Killing process %s', self.pids[0])
        self.assertTrue(kill_process_by_pid_on_vm(self.vm, self.pids[0],
                                                  config.VM_USER,
                                                  config.VM_PASSWORD))

        logger.info('Power vm %s off', self.vm)
        self.assertTrue(shutdownVm(True, self.vm))

        logger.info('Starting vm %s again', self.vm)
        self.assertTrue(startVm(True, self.vm, wait_for_status=config.VM_UP))

        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0],
                                             self.cmdlines[0]))

    def tearDown(self):
        """
        Set vm to not be stateless
        """
        logger.info('Setting vm %s to not be stateless', self.vm)
        assert updateVm(True, self.vm, stateless=False)
        super(TestCase5131, self).tearDown()
