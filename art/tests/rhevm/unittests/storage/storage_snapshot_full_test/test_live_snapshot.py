"""
Storage live snapshot sanity tests - full test
https://tcms.engineering.redhat.com/plan/5588/
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr

from art.rhevm_api.tests_lib.high_level.vms import restore_snapshot, \
    shutdown_vm_if_up
from art.rhevm_api.tests_lib.high_level.hosts import switch_host_to_cluster
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.utils.test_utils import get_api, prepareDataForVm, \
    raise_if_exception, wait_for_tasks
from art.test_handler.settings import opts
from art.test_handler.tools import tcms, bz
import helpers
import config


LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']
VM_API = get_api('vm', 'vms')


BASE_SNAP = "base_snap"  # Base snapshot description
SNAP_1 = 'spm_snapshot1'
ACTIVE_SNAP = 'Active VM'
VM_ON_SPM = 'vm_on_spm'
VM_ON_HSM = 'vm_on_hsm'

SPM = None
HSM = None

VM_LIST = [VM_ON_SPM, VM_ON_HSM]


def setup_module():
    """
    Prepares VMs for testing, sets HSM and SPM hosts
    """
    global SPM
    global HSM
    assert hosts.waitForSPM(config.DC_NAME, timeout=100, sleep=10)
    SPM = hosts.returnSPMHost(config.HOSTS)[1]['spmHost']
    HSM = hosts.getAnyNonSPMHost(config.HOSTS)[1]['hsmHost']
    vm_args = {
        'positive': True,
        'vmDescription': '',
        'cluster': config.CLUSTER_NAME,
        'nic': 'nic1',
        'nicType': ENUMS['nic_type_virtio'],
        'storageDomainName': config.SD_NAME,
        'size': 3 * config.GB,
        'diskInterface': ENUMS['interface_virtio'],
        'volumeFormat': ENUMS['format_cow'],
        'volumeType': True,  # This means sparse
        'bootable': True,
        'type': ENUMS['vm_type_desktop'],
        'os_type': "rhel6x64",
        'memory': config.GB,
        'cpu_socket': 1,
        'cpu_cores': 1,
        'display_type': ENUMS['display_type_spice'],
        'start': True,
        'installation': True,
        'user': config.PARAMETERS['vm_linux_user'],
        'password': config.PARAMETERS['vm_linux_password'],
        'image': config.PARAMETERS['cobbler_profile'],
        'network': config.PARAMETERS['mgmt_bridge'],
        'useAgent': config.PARAMETERS.as_bool('useAgent'),
        # CUSTOM ARGUMENTS
        'vmName': VM_ON_SPM,
        'placement_host': SPM,
    }
    results = list()
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        # Create a vm on SPM
        results.append(executor.submit(helpers.prepare_vm, **vm_args))
        # Create a vm on HSM
        vm_args['vmName'] = VM_ON_HSM
        vm_args['placement_host'] = HSM
        results.append(executor.submit(helpers.prepare_vm, **vm_args))
    raise_if_exception(results)


def teardown():
    """
    Removes vms
    """
    results = list()
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        results.append(executor.submit(
            vms.removeVm, True, VM_ON_SPM, stopVM='true'))
        results.append(executor.submit(
            vms.removeVm, True, VM_ON_HSM, stopVM='true'))
    raise_if_exception(results)


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_plan_id = '5588'

    @classmethod
    def setup_class(cls):
        """
        Start machines
        """
        vms.start_vms(VM_LIST, config.MAX_WORKERS)

    @classmethod
    def teardown_class(cls):
        """
        Returns VM to the base snapshot and cleans out all other snapshots
        """
        results = list()
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for vm_name in VM_LIST:
                results.append(
                    executor.submit(restore_snapshot, vm_name, BASE_SNAP))
        raise_if_exception(results)


@attr(tier=0)
class LiveSnapshot(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141612

    Create live snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:
    Snapshot should be successfully created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    tcms_test_case = '141612'

    def _test_on_host(self, vm_name):
        """
        Tests live snapshot on given vm
        """
        LOGGER.info("Creating live snapshot %s on vm %s", SNAP_1, vm_name)
        self.assertTrue(
            vms.addSnapshot(True, vm=vm_name, description=SNAP_1))
        LOGGER.info("Preparing 3 files in /tmp")
        succeeded, data_path = prepareDataForVm(
            root_dir='/tmp', root_name_prefix='snap', dir_cnt=1, file_cnt=3)
        assert succeeded
        data_path = data_path['data_path']
        LOGGER.info("Copying files from %s to vm %s", data_path, vm_name)
        helpers.copy_data_to_vm(vm_name, data_path)
        LOGGER.info("Verifying that vm %s has same files in %s", vm_name,
                    data_path)
        assert helpers.verify_data_on_vm(True, vm_name, data_path)
        assert vms.stopVm(True, vm=vm_name)
        LOGGER.info("Waiting until all snapshots are ok on vm %s", vm_name)
        vms.wait_for_vm_snapshots(vm_name, states=['ok'])
        LOGGER.info("Restoring snapshot %s on vm %s", SNAP_1, vm_name)
        assert vms.restoreSnapshot(True, vm=vm_name, description=SNAP_1)
        assert vms.startVm(
            True, vm=vm_name, wait_for_status=ENUMS['vm_state_up'])
        assert vms.waitForIP(vm=vm_name)
        LOGGER.info("Checking that files in %s on vm %s no longer exist",
                    data_path, vm_name)
        assert helpers.verify_data_on_vm(False, vm_name, data_path)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_on_spm(self):
        """
        Create a snapshot while VM is running on SPM host
        """
        self._test_on_host(VM_ON_SPM)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_on_hsm(self):
        """
        Create a snapshot while VM is running on HSM host
        """
        self._test_on_host(VM_ON_HSM)

    def test_on_single_host(self):
        """
        Create a snapshot while VM is running on SPM host and there is one host
        in the cluster
        """
        assert vms.stopVm(True, VM_ON_HSM)
        switch_host_to_cluster(HSM, 'Default')
        self._test_on_host(VM_ON_SPM)
        switch_host_to_cluster(HSM, config.CLUSTER_NAME)


@attr(tier=0)
class LiveSnapshotMultipleDisks(LiveSnapshot):
    """
    https://tcms.engineering.redhat.com/case/141646/

    Add a disk to the VMs
    Create live snapshot
    Add 3 files to the VM
    Stop VM and restore snapshot

    Expected Results:

    Verify that the correct number of images were created
    Verify that a new data is written on new volumes
    """
    __test__ = True
    tcms_test_case = '141646'

    @classmethod
    def setup_class(cls):
        """
        Adds IDE cow disks to vms
        """
        for vm_name in VM_LIST:
            assert vms.addDisk(
                True, vm=vm_name, size=3 * config.GB, wait='True',
                storagedomain=config.SD_NAME, type=ENUMS['disk_type_data'],
                interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
                sparse='true')
        super(LiveSnapshotMultipleDisks, cls).setup_class()

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_on_spm(self):
        """
        Create a snapshot while VM is running on SPM host
        """
        self._test_on_host(VM_ON_SPM)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_on_hsm(self):
        """
        Create a snapshot while VM is running on HSM host
        """
        self._test_on_host(VM_ON_HSM)

    @classmethod
    def teardown_class(cls):
        """
        Removes the disks created in setup_class
        """
        super(LiveSnapshotMultipleDisks, cls).teardown_class()
        for vm_name in VM_LIST:
            disk_name = "%s_Disk2" % vm_name
            assert vms.removeDisk(True, vm_name, disk_name)


@attr(tier=2)
class SnapshotDescription(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141636

    Try to create a snapshot with max chars length
    Try to create a snapshot with special characters

    Expected Results:

    Should be possible to create a snapshot with special characters and backend
    should not limit chars length
    """
    __test__ = True
    tcms_test_case = '141636'

    def _test_snapshot_desc_length(self, positive, length, vm_name):
        """
        Tries to create snapshot with given length description
        Parameters:
            * length - how many 'a' chars should description contain
        """
        description = length * 'a'
        LOGGER.info("Trying to create snapshot on vm %s with description "
                    "containing %d 'a' letters", vm_name, length)
        self.assertTrue(
            vms.addSnapshot(positive, vm=vm_name, description=description))

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_description_length_positive(self):
        """
        Try to create a snapshot with max chars length
        """
        self._test_snapshot_desc_length(True, config.MAX_DESC_LENGTH,
                                        VM_ON_SPM)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        LOGGER.info("Trying to create snapshot with description %s",
                    config.SPECIAL_CHAR_DESC)
        assert vms.addSnapshot(True, vm=VM_ON_HSM,
                               description=config.SPECIAL_CHAR_DESC)


@attr(tier=0)
class PreviewSnapshot(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141644/

    Create 3 files on a VM
    Create live snapshot
    Remove the 3 files
    Stop VM
    Preview the snapshot on the VM
    Start the VM

    Expected Results:

    Verify that the snapshot being presented is the correct one (the files are
    there)
    """
    __test__ = True
    tcms_test_case = '141644'

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_preview(self):
        """
        Checking that erased file is presented in preview mode of snapshot
        """
        LOGGER.info("Preparing 3 files in /tmp")
        succeeded, data_path = prepareDataForVm(
            root_dir='/tmp', root_name_prefix='snap', dir_cnt=1, file_cnt=3)
        data_path = data_path['data_path']
        assert succeeded
        LOGGER.info("Copying files from %s to vm %s", data_path, VM_ON_SPM)
        helpers.copy_data_to_vm(VM_ON_SPM, data_path)
        LOGGER.info("Verifying that vm %s has same files in %s", VM_ON_SPM,
                    data_path)
        assert helpers.verify_data_on_vm(True, VM_ON_SPM, data_path)
        LOGGER.info("Creating live snapshot %s on vm %s", SNAP_1, VM_ON_SPM)
        self.assertTrue(
            vms.addSnapshot(True, vm=VM_ON_SPM, description=SNAP_1))
        vm_data_path = '/var%s' % data_path
        LOGGER.info("Removing files in %s from vm %s", vm_data_path, VM_ON_SPM)
        helpers.remove_dir_on_host(VM_ON_SPM, vm_data_path)
        assert vms.stopVm(True, vm=VM_ON_SPM)
        LOGGER.info("Waiting until all snapshots are ok on vm %s", VM_ON_SPM)
        vms.wait_for_vm_snapshots(VM_ON_SPM, states=['ok'])
        LOGGER.info("Previewing snapshot %s on vm %s", SNAP_1, VM_ON_SPM)
        assert vms.preview_snapshot(True, vm=VM_ON_SPM, description=SNAP_1)
        assert vms.startVm(
            True, vm=VM_ON_SPM, wait_for_status=ENUMS['vm_state_up'])
        assert vms.waitForIP(vm=VM_ON_SPM)
        LOGGER.info("Checking that files in %s on vm %s exist again",
                    data_path, VM_ON_SPM)
        self.assertTrue(helpers.verify_data_on_vm(True, VM_ON_SPM, data_path))

    @classmethod
    def teardown_class(cls):
        """
        Undo preview of snapshot, then continue with teardown
        """
        LOGGER.info('shutting down vm')
        shutdown_vm_if_up(VM_ON_SPM)
        LOGGER.info('Undo snapshot preview for snapshot %s', SNAP_1)
        assert vms.undo_snapshot_preview(True, VM_ON_SPM, SNAP_1)
        super(PreviewSnapshot, cls).teardown_class()


@attr(tier=1)
class MultipleStorageDomainDisks(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/147751

    Create 2 additional disks in a different storage domain
    to the VM on HSM
    Add snapshot

    Expected Results:

    You should be able to create a snapshot
    """
    __test__ = True
    tcms_test_case = '147751'

    @classmethod
    def setup_class(cls):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        for _ in range(2):
            LOGGER.info("Adding disk to vm %s", VM_ON_HSM)
            assert vms.addDisk(
                True, vm=VM_ON_HSM, size=3 * config.GB, wait='True',
                storagedomain=config.SD_NAME_1, type=ENUMS['disk_type_data'],
                interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
                sparse='true')
        super(MultipleStorageDomainDisks, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Removes the second disk of vm vm_on_spm
        """
        super(MultipleStorageDomainDisks, cls).teardown_class()
        for disk_index in [2, 3]:
            disk_name = "%s_Disk%d" % (VM_ON_HSM, disk_index)
            LOGGER.info("Removing disk %s of vm %s", disk_name, VM_ON_HSM)
            assert vms.removeDisk(True, VM_ON_HSM, disk_name)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on vm that has disks on multiple
        storage domains
        """
        self.assertTrue(
            vms.addSnapshot(True, vm=VM_ON_HSM, description=SNAP_1))


@attr(tier=1)
class CreateSnapshotWhileMigration(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141738

    Migrate a VM without waiting
    Add snapshot to the same VM while migrating it

    Expected Results:

    It should be impossible to create a snapshot while VMs migration
    """
    __test__ = True
    tcms_test_case = '141738'

    @classmethod
    def teardown_class(cls):
        """
        Waits until migration finishes
        """
        vms.waitForVMState(VM_ON_HSM)
        super(CreateSnapshotWhileMigration, cls).teardown_class()

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        assert vms.migrateVm(True, VM_ON_HSM, wait=False)
        self.assertTrue(
            vms.addSnapshot(False, vm=VM_ON_HSM, description=SNAP_1))


@attr(tier=0)
class SnapshotPresentation(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141614/

    Add a second disk to a VM
    Add snapshot
    Make sure that the new snapshot appears only once

    Expected Results:

    Only one snapshot should be available in UI, no matter how many disks do
    you have.
    """
    __test__ = True
    tcms_test_case = '141614'

    @classmethod
    def setup_class(cls):
        """
        Adds disk to vm_on_spm that will be on second domain
        """
        LOGGER.info("Adding disk to vm %s", VM_ON_SPM)
        assert vms.addDisk(
            True, vm=VM_ON_SPM, size=3 * config.GB, wait='True',
            storagedomain=config.SD_NAME_1, type=ENUMS['disk_type_data'],
            interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
            sparse='true')
        super(SnapshotPresentation, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Removes the second disk of vm vm_on_spm
        """
        super(SnapshotPresentation, cls).teardown_class()
        disk_name = "%s_Disk2" % VM_ON_SPM
        LOGGER.info("Removing disk %s of vm %s", disk_name, VM_ON_SPM)
        assert vms.removeDisk(True, VM_ON_SPM, disk_name)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_with_multiple_disks(self):
        """
        Checks that created snapshot appears only once although vm has more
        disks
        """
        snap_descs = set([SNAP_1, BASE_SNAP, ACTIVE_SNAP])
        self.assertTrue(
            vms.addSnapshot(True, vm=VM_ON_SPM, description=SNAP_1))
        snapshots = vms._getVmSnapshots(VM_ON_SPM, False)
        current_snap_descs = set([snap.description for snap in snapshots])
        self.assertTrue(snap_descs == current_snap_descs)


@attr(tier=1)
class LiveSnapshotOnVMCreatedFromTemplate(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/286330

    Create a template
    Create a thin provisioned VM from that template
    Create a cloned VM from that template
    Start the thin and cloned VMs
    Add snapshot for both thin and cloned VMs

    Expected Results:

    Live snapshots should be created for both cases
    """
    __test__ = True
    tcms_test_case = '286330'

    @classmethod
    def setup_class(cls):
        """
        Prepares template and two VMs based on this template: one clone and one
        thinly provisioned
        """
        assert templates.createTemplate(
            True, vm='vm_on_spm', name='template_test',
            cluster=config.CLUSTER_NAME)
        assert vms.addVm(
            True, name='vm_thin', description='', cluster=config.CLUSTER_NAME,
            storagedomain=config.SD_NAME, template='template_test')
        assert vms.addVm(
            True, name='vm_clone', description='', cluster=config.CLUSTER_NAME,
            storagedomain=config.SD_NAME, template='template_test',
            disk_clone='True')
        vms.start_vms(['vm_thin', 'vm_clone'], config.MAX_WORKERS)

    @classmethod
    def teardown_class(cls):
        """
        Removes cloned, thinly provisioned vm and template
        """
        assert vms.removeVm(True, 'vm_thin', stopVM='true')
        assert vms.removeVm(True, 'vm_clone', stopVM='true')
        assert templates.removeTemplate(True, template='template_test')
        wait_for_tasks(
            vdc=config.PARAMETERS['host'],
            vdc_password=config.PARAMETERS['vdc_root_password'],
            datacenter=config.DC_NAME)

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_thin', description=SNAP_1))

    @tcms(BaseTestCase.tcms_plan_id, tcms_test_case)
    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_clone', description=SNAP_1))
