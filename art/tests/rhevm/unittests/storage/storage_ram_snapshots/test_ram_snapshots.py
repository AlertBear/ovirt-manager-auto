import logging
import unittest

from nose.tools import istest

from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.high_level.vms import shutdown_vm_if_up
from art.rhevm_api.tests_lib.low_level.datacenters import \
    waitForDataCenterState
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost, \
    getAnyNonSPMHost
from art.rhevm_api.tests_lib.low_level.storagedomains import getDCStorages, \
    findMasterStorageDomain, cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import updateVm, \
    startVm, addSnapshot, is_snapshot_with_memory_state, createVm, \
    stopVm, restoreSnapshot, undo_snapshot_preview, preview_snapshot, addVm, \
    removeVm, exportVm, importVm, removeVmFromExportDomain, \
    removeSnapshot, check_snapshot_on_export_domain, \
    kill_process_by_pid_on_vm, shutdownVm, wait_for_vm_snapshots
from art.test_handler import exceptions as errors
from art.test_handler.tools import tcms
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
    logger.info('Creating datacenter')
    build_setup(config=config.PARAMETERS, storage=config.PARAMETERS,
                storage_type=config.DATA_CENTER_TYPE)

    rc, masterSD = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
    assert rc
    masterSD = masterSD['masterDomain']

    logger.info('Creating vm and installing OS on it')

    vmArgs = {'positive': True,
              'vmName': config.VM_NAME,
              'vmDescription': config.VM_NAME,
              'diskInterface': config.ENUMS['interface_virtio'],
              'volumeFormat': config.ENUMS['format_cow'],
              'cluster': config.CLUSTER_NAME,
              'storageDomainName': masterSD,
              'installation': True,
              'size': config.DISK_SIZE,
              'nic': 'nic1',
              'cobblerAddress': config.COBBLER_ADDRESS,
              'cobblerUser': config.COBBLER_USER,
              'cobblerPasswd': config.COBBLER_PASSWD,
              'image': config.COBBLER_PROFILE,
              'useAgent': True,
              'os_type': config.ENUMS['rhel6'],
              'user': config.VM_USER,
              'password': config.VM_PASSWORD
              }

    if not createVm(**vmArgs):
        raise errors.VMException('Unable to create vm %s for test'
                                 % config.VM_NAME)


    logger.info('Creating base snapshot %s for vm %s', config.BASE_SNAPSHOT,
                config.VM_NAME)
    if not addSnapshot(True, config.VM_NAME, config.BASE_SNAPSHOT):
        raise errors.VMException('Unable to create base snapshot for vm %s'
                                 % config.VM_NAME)

    logger.info('Shutting down VM %s', config.VM_NAME)
    shutdown_vm_if_up(config.VM_NAME)


def teardown_module():
    """
    Clean datacenter
    """
    logger.info('Cleaning datacenter')
    cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD)


class DCWithStoragesActive(unittest.TestCase):
    """
    A class that ensures DC is up with all storages active and SPM elected.
    """

    __test__ = False

    spm = None
    hsm = None
    master_sd = None
    non_master_sd = None
    base_snapshot = config.BASE_SNAPSHOT
    vm = config.VM_NAME

    @classmethod
    def setup_class(cls):
        """
        Ensure DC is up, all storages are active and SPM is elected
        """
        logger.info('Checking DC %s state', config.DATA_CENTER_NAME)
        if not waitForDataCenterState(config.DATA_CENTER_NAME):
            raise errors.DataCenterException('DC %s is not up' %
                                             config.DATA_CENTER_NAME)

        storage_domains = getDCStorages(config.DATA_CENTER_NAME, get_href=False)

        logger.info('Ensuring all domains are up')
        inactive_domains = [domain.get_name() for domain in storage_domains if
                            domain.get_status().get_state() != config.SD_ACTIVE]

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
    pids = []

    @classmethod
    def setup_class(cls):
        """
        Start vm, run process on vm and create RAM snapshot
        """
        super(VMWithMemoryStateSnapshot, cls).setup_class()
        logger.info('Starting vm %s and waiting for it to boot', cls.vm)
        if not startVm(True, cls.vm, wait_for_ip=True):
            raise errors.VMException('Error waiting for vm %s to boot', cls.vm)

        status, pid = helpers.start_cat_process_on_vm(cls.vm, '/dev/zero')
        logger.info('PID for first cat process is: %s', pid)
        cls.pids = [pid]

        assert status

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
        self.assertTrue(is_pid_running_on_vm(self.vm, self.pids[0]),
                        'Process %s not running on vm %s' %
                        (self.pids[0], self.vm))


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
        assert undo_snapshot_preview(True, cls.vm, cls.memory_snapshot, True)
        wait_for_vm_snapshots(cls.vm, config.SNAPSHOT_OK)
        super(TestCase294435, cls).teardown_class()



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
