"""
Storage live snapshot sanity test - 5588
https://tcms.engineering.redhat.com/plan/5588/
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from unittest import TestCase

from art.rhevm_api.tests_lib.high_level.vms import restore_snapshot, \
    shutdown_vm_if_up
from art.rhevm_api.tests_lib.high_level.hosts import switch_host_to_cluster
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.utils.resource_utils import copyDataToVm, verifyDataOnVm
from art.rhevm_api.utils.test_utils import get_api, prepareDataForVm, \
    removeDirOnHost, raise_if_exception, wait_for_tasks, setPersistentNetwork
from art.test_handler.settings import opts
from art.test_handler.tools import bz
import config


LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']
VM_API = get_api('vm', 'vms')


GB = 1024 ** 3
BASE_SNAP = "base_snap"  # Base snapshot description
SNAP_1 = 'spm_snapshot1'
ACTIVE_SNAP = 'Active VM'
VM_ON_SPM = 'vm_on_spm'
VM_ON_HSM = 'vm_on_hsm'
DEST_DIR = '/var/tmp'

SPM = None
HSM = None

VM_LIST = [VM_ON_SPM, VM_ON_HSM]
VM_IP_ADDRESSES = dict()


def verify_data_on_vm(positive, vm_name, path):
    """
    Verifies /var/tmp directory agains given path
    """
    return verifyDataOnVm(
        positive,
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.PARAMETERS['vm_linux_user'],
        password=config.PARAMETERS['vm_linux_password'],
        osType='linux',
        dest=DEST_DIR,
        destToCompare=path)


def copy_data_to_vm(vm_name, path):
    """
    Copies data from path to /var/tmp
    """
    assert copyDataToVm(
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.PARAMETERS['vm_linux_user'],
        password=config.PARAMETERS['vm_linux_password'],
        osType='linux',
        src=path,
        dest=DEST_DIR)


def remove_dir_on_host(vm_name, dirname):
    """
    Removes directory given by path from vm vm_name

    Parameters:
        * vm_name - name of the vm
        * dirname - path to the directory that will be remove
    """
    assert removeDirOnHost(
        True,
        ip=VM_IP_ADDRESSES[vm_name],
        user=config.PARAMETERS['vm_linux_user'],
        password=config.PARAMETERS['vm_linux_password'],
        osType='linux',
        dirname=dirname)


def setup_module():
    """
    Prepares VMs for testing, sets HSM and SPM hosts
    """
    def prepare_vm(**vm_args):
        """
        Installs vm and creates base snapshot
        """
        vm_name = vm_args['vmName']
        assert vms.createVm(**vm_args)
        vm_ip = vms.waitForIP(vm_name)[1]['ip']
        VM_IP_ADDRESSES[vm_name] = vm_ip
        assert setPersistentNetwork(
            vm_ip, config.PARAMETERS['vm_linux_password'])
        assert vms.stopVm(True, vm_name)
        assert vms.addSnapshot(True, vm=vm_name, description=BASE_SNAP)

    global SPM
    global HSM
    vds_string = ','.join(config.PARAMETERS.as_list('vds'))
    assert hosts.waitForSPM(config.DC_NAME, timeout=100, sleep=10)
    SPM = hosts.returnSPMHost(vds_string)[1]['spmHost']
    HSM = hosts.getAnyNonSPMHost(vds_string)[1]['hsmHost']
    vm_args = {
        'positive': True,
        'vmDescription': '',
        'cluster': config.CLUSTER_NAME,
        'nic': 'nic1',
        'nicType': ENUMS['nic_type_virtio'],
        'storageDomainName': config.SD_NAME,
        'size': 3 * GB,
        'diskInterface': ENUMS['interface_virtio'],
        'volumeFormat': ENUMS['format_cow'],
        'volumeType': True,  # This means sparse
        'bootable': True,
        'type': ENUMS['vm_type_desktop'],
        'os_type': "rhel6x64",
        'memory': GB,
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
        results.append(executor.submit(prepare_vm, **vm_args))
        vm_args['vmName'] = VM_ON_HSM
        vm_args['placement_host'] = HSM
        results.append(executor.submit(prepare_vm, **vm_args))
    raise_if_exception(results)


def teardown_module():
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
        Starts machines
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


class LiveSnapshot(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141612

    Expected Results:
    Snapshot should be succesfully created
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
        copy_data_to_vm(vm_name, data_path)
        LOGGER.info("Verifying that vm %s has same files in %s", vm_name,
                    data_path)
        assert verify_data_on_vm(True, vm_name, data_path)
        assert vms.stopVm(True, vm=vm_name)
        LOGGER.info("Waiting until all snapshots are ok on vm %s", vm_name)
        vms.wait_for_vm_snapshots(vm_name, states=['ok'])
        LOGGER.info("Restoring snapshot %s on vm %s", SNAP_1, vm_name)
        assert vms.restoreSnapshot(True, vm=vm_name, description=SNAP_1)
        assert vms.startVm(
            True, vm=vm_name, wait_for_status=ENUMS['vm_state_up'])
        assert vms.waitForIP(vm=vm_name)
        LOGGER.info("Checking that files in %s on vm %s no longer exists",
                    data_path, vm_name)
        assert verify_data_on_vm(False, vm_name, data_path)

    def test_on_spm(self):
        """
        Create a snapshot while VM is running on SPM host
        """
        self._test_on_host(VM_ON_SPM)

    def test_on_hsm(self):
        """
        Create a snapshot while VM is running on HSM host
        """
        self._test_on_host(VM_ON_HSM)

    @bz(988033)
    def test_on_single_host(self):
        """
        Create a snapshot while VM is running on SPM host and there is one host
        in the cluster
        """
        assert vms.stopVm(True, VM_ON_HSM)
        switch_host_to_cluster(HSM, 'Default')
        self._test_on_host(VM_ON_SPM)
        switch_host_to_cluster(HSM, config.CLUSTER_NAME)


class LiveSnapshotMultipleDisks(LiveSnapshot):
    """
    https://tcms.engineering.redhat.com/case/141646/

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
                True, vm=vm_name, size=3 * GB, wait='True',
                storagedomain=config.SD_NAME, type=ENUMS['disk_type_data'],
                interface=ENUMS['interface_ide'], format=ENUMS['format_cow'],
                sparse='true')
        super(LiveSnapshotMultipleDisks, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Removes the disks created in setup_class
        """
        super(LiveSnapshotMultipleDisks, cls).teardown_class()
        for vm_name in VM_LIST:
            disk_name = "%s_Disk2" % vm_name
            assert vms.removeDisk(True, vm_name, disk_name)


class SnapshotName(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141636

    Expected Results:

    Should be possible to create a snapshot with special chracters and backend
    should not limit chars length
    """
    __test__ = True
    tcms_test_case = '141636'

    def _test_snapshot_desc_length(self, positive, length, vm_name):
        """
        Tries to create snapshot with given length description
        Parameters:
            * length - how many 'a' chars should description contain
            * assert_func - function that decides whether test passes on
                            failure
        """
        description = length * 'a'
        LOGGER.info("Trying to create snapshot on vm %s with description "
                    "containing %d 'a' letters", vm_name, length)
        self.assertTrue(
            vms.addSnapshot(positive, vm=vm_name, description=description))

    def test_snapshot_decription_length_positive(self):
        """
        Try to create a snapshot with max chars length - 4000
        """
        self._test_snapshot_desc_length(True, 4000, VM_ON_SPM)

    def test_snapshot_decription_length_negative(self):
        """
        Try to create a snapshot with max chars length - 4001
        """
        self._test_snapshot_desc_length(False, 4001, VM_ON_SPM)

    def test_special_characters(self):
        """
        Try to create snapshots containing special characters
        """
        description = '!@#$\% ^&*/\\'
        LOGGER.info("Trying to create snapshot with description %s",
                    description)
        assert vms.addSnapshot(True, vm=VM_ON_HSM, description=description)


class PreviewSnapshot(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141644/

    Expected Results:

    Verify that the snapshot being presented is the correct one (check that
    disk number VM can see is correct)
    """
    __test__ = True
    tcms_test_case = '141644'

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
        copy_data_to_vm(VM_ON_SPM, data_path)
        LOGGER.info("Verifying that vm %s has same files in %s", VM_ON_SPM,
                    data_path)
        assert verify_data_on_vm(True, VM_ON_SPM, data_path)
        LOGGER.info("Creating live snapshot %s on vm %s", SNAP_1, VM_ON_SPM)
        self.assertTrue(
            vms.addSnapshot(True, vm=VM_ON_SPM, description=SNAP_1))
        vm_data_path = '/var%s' % data_path
        LOGGER.info("Removing files in %s from vm %s", vm_data_path, VM_ON_SPM)
        remove_dir_on_host(VM_ON_SPM, vm_data_path)
        assert vms.stopVm(True, vm=VM_ON_SPM)
        LOGGER.info("Waiting until all snapshots are ok on vm %s", VM_ON_SPM)
        vms.wait_for_vm_snapshots(VM_ON_SPM, states=['ok'])
        LOGGER.info("Previewing snapshot %s on vm %s", SNAP_1, VM_ON_SPM)
        assert vms.preview_snapshot(True, vm=VM_ON_SPM, description=SNAP_1)
        assert vms.startVm(
            True, vm=VM_ON_SPM, wait_for_status=ENUMS['vm_state_up'])
        assert vms.waitForIP(vm=VM_ON_SPM)
        LOGGER.info("Checking that files in %s on vm %s no longer exists",
                    data_path, VM_ON_SPM)
        self.assertTrue(verify_data_on_vm(True, VM_ON_SPM, data_path))

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


class MultipleStorageDomainDisks(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/147751

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
                True, vm=VM_ON_HSM, size=3 * GB, wait='True',
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

    def test_snapshot_on_multiple_domains(self):
        """
        Tests whether snapshot can be created on vm that has disks on multiple
        storage domains
        """
        self.assertTrue(
            vms.addSnapshot(True, vm=VM_ON_HSM, description=SNAP_1))


class CreateSnapshotWhileMigration(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141738

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

    def test_migration(self):
        """
        Tests live snapshot during migration
        """
        assert vms.migrateVm(True, VM_ON_HSM, wait=False)
        self.assertTrue(
            vms.addSnapshot(False, vm=VM_ON_HSM, description=SNAP_1))


class SnapshotPresentation(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/141614/

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
            True, vm=VM_ON_SPM, size=3 * GB, wait='True',
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


class LiveSnapshotOnVMCreatedFromTemplate(BaseTestCase):
    """
    https://tcms.engineering.redhat.com/case/286330

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
            vdc_password=config.PARAMETERS['password'],
            datacenter=config.DC_NAME)

    def test_snapshot_on_thin_vm(self):
        """
        Try to make a live snapshot from thinly provisioned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_thin', description=SNAP_1))

    def test_snapshot_on_cloned_vm(self):
        """
        Try to make a live snapshot from cloned VM
        """
        self.assertTrue(
            vms.addSnapshot(True, vm='vm_clone', description=SNAP_1))
