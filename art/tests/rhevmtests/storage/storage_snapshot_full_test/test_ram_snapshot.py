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
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sds,
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from rhevmtests.storage import helpers as storage_helpers

logger = logging.getLogger(__name__)
VM_PREFIX = "vm_ram_snapshot"
VM_NAME = VM_PREFIX + "_%s"


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
        storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.vm = VM_NAME % self.storage
        args = config.create_vm_args.copy()
        args['storageDomainName'] = storage_domain
        args['vmName'] = self.vm
        logger.info('Creating vm %s and installing OS on it', self.vm)
        if not storage_helpers.create_vm_or_clone(**args):
            raise exceptions.VMException(
                "Failed to create vm %s" % self.vm
            )
        logger.info(
            'Creating base snapshot %s for vm %s', config.BASE_SNAPSHOT,
            self.vm
        )
        if not ll_vms.addSnapshot(True, self.vm, config.BASE_SNAPSHOT):
            raise exceptions.SnapshotException(
                "Failed to create snapshot %s" % config.BASE_SNAPSHOT
            )
        self.spm = ll_hosts.getSPMHost(config.HOSTS)
        self.hsm = ll_hosts.getAnyNonSPMHost(
            config.HOSTS, expected_states=[config.HOST_UP],
            cluster_name=config.CLUSTER_NAME
        )[1]['hsmHost']

        logger.info('SPM is: %s, HSM is %s', self.spm, self.hsm)

        if not self.spm and self.hsm:
            raise exceptions.TestException(
                "SPM or HSM not found"
            )

        self.storage_domain = ll_sds.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

    def tearDown(self):
        """
        Return to vm's base snapshot (with OS clean installation)
        """
        if not ll_vms.safely_remove_vms([self.vm]):
            logger.error("Failed to power off vm %s", self.vm)
            TestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        TestCase.teardown_exception()


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
        if not ll_vms.startVm(True, self.vm, wait_for_ip=True):
            raise exceptions.VMException(
                'Error waiting for vm %s to boot', self.vm
            )

        status, pid = start_cat_process_on_vm(self.vm, self.cmdlines[0])
        logger.info('PID for first cat process is: %s', pid)
        self.pids = [pid]

        if not status:
            raise exceptions.VMException(
                "Failed to start cat process on vm %s" % self.vm
            )

        if self.persist_network:
            vm_ip = storage_helpers.get_vm_ip(self.vm)
            logger.info('Setting persistent network on vm %s', self.vm)
            if not setPersistentNetwork(vm_ip, config.VM_PASSWORD):
                raise exceptions.VMException(
                    "Failed to seal vm %s" % self.vm
                )

        logger.info(
            'Creating snapshot %s with RAM state', self.memory_snapshot
        )
        if not ll_vms.addSnapshot(
            True, self.vm, self.memory_snapshot, persist_memory=True
        ):
            raise exceptions.VMException(
                'Unable to create RAM snapshot %s on vm %s' %
                (self.memory_snapshot, self.vm)
            )
        logger.info('Wait for snapshot %s to be created', self.memory_snapshot)
        ll_vms.wait_for_vm_snapshots(self.vm, config.SNAPSHOT_OK)
        logger.info('Snapshot created successfully')

        logger.info('Stopping vm %s', self.vm)
        if not ll_vms.stop_vms_safely([self.vm]):
            raise exceptions.VMException(
                "Failed to power off vm %s" % self.vm
            )


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
        ll_vms.startVms([self.vm], wait_for_status=config.VM_UP)
        logger.info('VM %s', self.vm)
        self.host_for_test = ll_vms.getVmHost(self.vm)[1]['vmHoster']
        logger.info(
            'Setting vm %s to run on host: %s', self.vm, self.host_for_test
        )

    def create_snapshot(self):
        """
        Create a snapshot with memory state
        """
        logger.info('Starting process on vm %s', self.vm)
        status, _ = start_cat_process_on_vm(self.vm, '/dev/zero')
        self.assertTrue(status)

        logger.info(
            'Creating snapshot %s on vm %s', self.snapshot, self.vm
        )
        self.assertTrue(
            ll_vms.addSnapshot(
                True, self.vm, self.snapshot, persist_memory=True),
            'Unable to create RAM snapshot on vm %s' % self.vm
        )

        logger.info('Ensuring snapshot %s has memory state', self.snapshot)
        self.assertTrue(
            ll_vms.is_snapshot_with_memory_state(
                self.vm, self.snapshot
            ), 'Snapshot %s does not contain memory state' % self.snapshot
        )


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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

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
        ll_jobs.wait_for_jobs(
            [config.JOB_RESTORE_SNAPSHOT, config.JOB_PREVIEW_SNAPSHOT]
        )

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(ll_vms.startVm(
            True, self.vm, config.VM_UP, True
        ), 'Error when resuming VM %s from memory snapshot %s' %
           (self.vm, self.memory_snapshot))

        logger.info('Checking if process is still running on vm %s', self.vm)
        self.assertTrue(
            is_pid_running_on_vm(
                self.vm, self.pids[0], self.cmdlines[0]
            ), 'Process %s not running on vm %s' % (self.pids[0], self.vm)
        )


@attr(tier=1)
class TestCase5139(ReturnToSnapshot):
    """
    Polarion Test Case 5139 - Preview to RAM Snapshot
    """
    __test__ = True
    polarion_test_case = '5139'
    action_to_call = staticmethod(ll_vms.preview_snapshot)
    # Bugzilla history
    # 1211588:  CLI auto complete options async and grace_period-expiry are
    # missing for preview_snapshot
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    # 1260177: Restoring a RAM snapshots in RHEL7.2 shows error stating the vm
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

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
        if not ll_vms.stop_vms_safely([self.vm]):
            logger.error("Failed to power off vm %s", self.vm)
            TestCase.test_failed = True
        logger.info(
            'Undo preview snapshot %s on vm %s', self.memory_snapshot, self.vm
        )
        if not ll_vms.undo_snapshot_preview(True, self.vm):
            logger.error("Failed to undo snapshot of vm %s", self.vm)
            TestCase.test_failed = True
        ll_vms.wait_for_vm_snapshots(self.vm, [config.SNAPSHOT_OK])
        super(TestCase5139, self).tearDown()
        TestCase.teardown_exception()


@attr(tier=1)
class TestCase5138(ReturnToSnapshot):
    """
    Polarion Test Case 5138 - Restore RAM Snapshot
    """
    __test__ = True
    polarion_test_case = '5138'
    action_to_call = staticmethod(ll_vms.restore_snapshot)
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    def setUp(self):
        """
        Restore first ram snapshot and resume the vm
        """
        super(TestCase5137, self).setUp()
        self.cmdlines.append('/dev/urandom')

        logger.info('Restoring first ram snapshot (%s) on vm %s', self.vm,
                    self.memory_snapshot)
        if not ll_vms.restore_snapshot(
            True, self.vm, self.memory_snapshot, restore_memory=True
        ):
            raise exceptions.VMException(
                "Failed to restore previewed snapshot on vm %s" % self.vm
            )

        logger.info('Resuming vm %s', self.vm)
        if not ll_vms.startVm(True, self.vm, config.VM_UP, True):
            raise exceptions.VMException("failed to start vm %s" % self.vm)

    @polarion("RHEVM3-5137")
    def test_vm_with_multiple_ram_snapshots(self):
        """
        * Start another process on the vm and create a new memory snapshot.
        * Preview first snapshot and check that only first process is running
        * Preview second snapshot and check that both processes are running
        """
        status, pid = start_cat_process_on_vm(self.vm, self.cmdlines[1])
        self.pids.append(pid)
        self.assertTrue(status, 'Unable to run process on VM %s' % self.vm)
        logger.info('Creating snapshot %s on vm %s',
                    self.second_snapshot_name, self.vm)
        self.assertTrue(
            ll_vms.addSnapshot(
                True, self.vm, self.second_snapshot_name, persist_memory=True
            ), 'Unable to create snapshot %s on vm %s' %
               (self.memory_snapshot, self.vm)
        )
        logger.info('Shutting down vm %s', self.vm)
        self.assertTrue(ll_vms.stopVm(True, self.vm))

        logger.info('Previewing first snapshot (%s) on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(
            ll_vms.preview_snapshot(
                True, self.vm, self.memory_snapshot, restore_memory=True
            ), 'Unable to preview snapshot %s on vm %s'
               % (self.memory_snapshot, self.vm)
        )
        self.previewed_snapshot = self.memory_snapshot

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(
            ll_vms.startVm(
                True, self.vm, wait_for_ip=True, wait_for_status=config.VM_UP
            )
        )
        logger.info('Checking if first process is running on vm %s', self.vm)
        self.assertTrue(
            is_pid_running_on_vm(
                self.vm, self.pids[0], self.cmdlines[0]
            ), 'First process is not running on vm - memory state not '
               'restored correctly'
        )
        logger.info(
            'Checking that second process is not running on vm %s', self.vm
        )
        self.assertFalse(
            is_pid_running_on_vm(self.vm, self.pids[1], self.cmdlines[1]),
            'Second process is running on vm - memory state not '
            'restored correctly'
        )
        logger.info('Powering vm %s off', self.vm)
        self.assertTrue(
            ll_vms.stopVm(True, self.vm), 'Could not power vm %s off' % self.vm
        )
        logger.info('Undoing snapshot preview')
        self.assertTrue(ll_vms.undo_snapshot_preview(True, self.vm))
        self.previewed_snapshot = None
        logger.info('Previewing second snapshot (%s) on vm %s',
                    self.second_snapshot_name, self.vm)
        self.assertTrue(ll_vms.preview_snapshot(
            True, self.vm, self.second_snapshot_name, restore_memory=True
        ), 'Unable to preview snapshot %s on vm %s' %
           (self.second_snapshot_name, self.vm))
        self.previewed_snapshot = self.second_snapshot_name

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(ll_vms.startVm(
            True, self.vm, wait_for_ip=True, wait_for_status=config.VM_UP
        ))

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
        ll_vms.stop_vms_safely([self.vm])
        if self.previewed_snapshot:
            if not ll_vms.undo_snapshot_preview(True, self.vm):
                logger.error("Failed to undo snapshot of vm %s", self.vm)
                TestCase.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm, [config.SNAPSHOT_OK]
            )
            self.previewed_snapshot = None
        super(TestCase5137, self).tearDown()
        TestCase.teardown_exception()


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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

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
            ll_vms.cloneVmFromSnapshot(
                True, name=self.cloned_vm_name, cluster=config.CLUSTER_NAME,
                vm=self.vm, snapshot=self.memory_snapshot,
                ),
            'Could not create vm %s from snapshot %s'
            % (self.cloned_vm_name, self.memory_snapshot)
        )

        logger.info('Starting VM %s', self.cloned_vm_name)
        self.assertTrue(
            ll_vms.startVms([self.cloned_vm_name], config.VM_UP),
            'Unable to start VM %s' % self.cloned_vm_name
        )
        status, ip = ll_vms.waitForIP(self.cloned_vm_name)
        if not status:
            raise exceptions.CanNotFindIP(
                "Failed to get IP for vm %s" % self.cloned_vm_name
            )

        self.assertFalse(is_pid_running_on_vm(self.cloned_vm_name,
                                              self.pids[0], self.cmdlines[0]))

    def tearDown(self):
        """
        Remove cloned vm
        """
        logger.info('Stopping and removing vm %s', self.cloned_vm_name)
        if not ll_vms.safely_remove_vms([self.cloned_vm_name]):
            logger.error("Failed to power off vm %s", self.cloned_vm_name)
            TestCase.test_failed = True
        super(TestCase5136, self).tearDown()
        TestCase.teardown_exception()


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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-5134")
    def test_import_vm_with_memory_state_snapshot(self):
        """
        Import a vm that has memory state snapshot and ensure it resumes memory
        state from that snapshot successfully
        """
        logger.info('Exporting vm %s to domain %s',
                    self.vm, config.EXPORT_DOMAIN)
        if not ll_vms.exportVm(True, self.vm, config.EXPORT_DOMAIN):
            raise exceptions.VMException(
                'Unable to export vm %s to domain %s' %
                (self.vm, config.EXPORT_DOMAIN)
            )
        logger.info('Removing original vm to allow import vm without collapse '
                    'snapshots')
        if not ll_vms.removeVm(True, self.vm):
            raise exceptions.VMException('Unable to remove vm %s', self.vm)

        logger.info(
            'Importing vm %s from export domain %s',
            self.vm, config.EXPORT_DOMAIN
        )
        self.assertTrue(
            ll_vms.importVm(
                True, self.vm, config.EXPORT_DOMAIN, self.storage_domain,
                config.CLUSTER_NAME
            ), 'Unable to import vm %s from export domain %s' %
               (self.vm, config.EXPORT_DOMAIN)
        )

        logger.info('Restoring snapshot %s with memory state on vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(
            ll_vms.restore_snapshot(
                True, self.vm, self.memory_snapshot, restore_memory=True
            ), 'Unable to restore snapshot %s on vm %s' %
               (self.memory_snapshot, self.vm)
        )

        logger.info('Starting vm %s', self.vm)
        self.assertTrue(
            ll_vms.startVm(
                True, self.vm, wait_for_status=config.VM_UP, wait_for_ip=True
            ), 'Unable to start vm %s' % self.vm
        )

        self.assertTrue(
            is_pid_running_on_vm(
                self.vm, self.pids[0], self.cmdlines[0]
            ), 'process is not running on vm %s, memory state not correctly '
               'restored' % self.vm
        )

    def tearDown(self):
        """
        Remove vm from export domain
        """
        logger.info(
            'Removing vm %s from export domain %s', self.vm,
            config.EXPORT_DOMAIN
        )
        ll_vms.remove_vm_from_export_domain(
            True, self.vm, config.DATA_CENTER_NAME, config.EXPORT_DOMAIN
        )
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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-5133")
    def test_remove_memory_state_snapshot(self):
        """
        Remove snapshot with memory state and check that vm starts
        successfully
        """
        logger.info('Removing snapshot %s with memory state from vm %s',
                    self.memory_snapshot, self.vm)
        self.assertTrue(
            ll_vms.removeSnapshot(
                True, self.vm, self.memory_snapshot
            ), 'Unable to remove snapshot %s from vm %s' %
               (self.memory_snapshot, self.vm)
        )
        logger.info('Starting vm %s', self.vm)
        self.assertTrue(
            ll_vms.startVm(
                True, self.vm, wait_for_ip=True, wait_for_status=config.VM_UP
            ), 'Unable to start VM %s' % self.vm
        )
        logger.info('Ensuring vm %s started without memory state', self.vm)
        self.assertFalse(
            is_pid_running_on_vm(
                self.vm, self.pids[0], self.cmdlines[0]
            )
        )


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
    # BZ1270583: Vm nic unplugged after previewing/undoing a snapshot

    @polarion("RHEVM3-5131")
    def test_stateless_vm_with_memory_snapshot(self):
        """
        * Restore memory snapshot
        * Set vm to stateless
        * Start vm - ensure it resumes from memory state
        * kill process and stop vm
        * Start vm - ensure it resumes from memory state again
        """
        logger.info(
            'Restoring memory snapshot %s on vm %s',
            self.memory_snapshot, self.vm
        )
        self.assertTrue(
            ll_vms.restore_snapshot(
                True, self.vm, self.memory_snapshot, restore_memory=True
            ), 'Unable to restore snapshot %s on vm %s' %
               (self.memory_snapshot, self.vm)
        )
        logger.info('Setting vm %s to stateless', self.vm)
        self.assertTrue(
            ll_vms.updateVm(True, self.vm, stateless=True),
            'Unable to set vm %s to be stateless' % self.vm
        )
        logger.info('Starting vm %s', self.vm)
        self.assertTrue(
            ll_vms.startVm(True, self.vm, wait_for_status=config.VM_UP)
        )
        self.assertTrue(
            is_pid_running_on_vm(self.vm, self.pids[0], self.cmdlines[0])
        )
        logger.info('Killing process %s', self.pids[0])
        self.assertTrue(
            ll_vms.kill_process_by_pid_on_vm(
                self.vm, self.pids[0], config.VM_USER, config.VM_PASSWORD
            )
        )
        logger.info('Power vm %s off', self.vm)
        self.assertTrue(ll_vms.shutdownVm(True, self.vm))

        logger.info('Starting vm %s again', self.vm)
        self.assertTrue(ll_vms.startVm(True, self.vm, config.VM_UP))
        self.assertTrue(
            is_pid_running_on_vm(self.vm, self.pids[0], self.cmdlines[0])
        )
