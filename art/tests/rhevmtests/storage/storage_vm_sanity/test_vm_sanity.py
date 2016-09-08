"""
Storage VM sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage/3_1_Virtual_Machines_Sanity
"""
import logging
from threading import Thread
import time
import pytest
import config
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as TestCase, testflow
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils import resource_utils
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
    templates as ll_templates,
)
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import polarion, bz
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    create_vm, remove_vms,
)

logger = logging.getLogger(__name__)
GB = config.GB


@pytest.fixture(scope='class')
def prepare_data(request):
    """
    Prepare data
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Removing templates %s" % self.template_names)
        for _, template_name in self.template_names.iteritems():
            ll_templates.removeTemplate(True, template=template_name)

    request.addfinalizer(finalizer)
    testflow.setup(
        "Creating templates for permutation of sparse and disk format"
    )
    for sparse in (True, False):
        for vol_format in (config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW):
            if not sparse and vol_format == config.DISK_FORMAT_COW:
                continue
            if (self.storage != config.STORAGE_TYPE_NFS
                    and sparse and vol_format == config.DISK_FORMAT_RAW):
                continue
            _prepare_data(
                sparse, vol_format, self.template_names, self.storage
            )


@pytest.fixture()
def clean_leftover_data(request):
    """
    Clean leftover data in the slave
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Cleaning leftover data in the slave")
        for data_path in self.data_for_vm:
            # we don't need try-except, as cleanupData uses
            # rmtree(path, ignore_errors=True)
            test_utils.cleanupData(data_path)

    request.addfinalizer(finalizer)


def _prepare_data(sparse, vol_format, template_names, storage_type):
    """
    prepares data for vm
    """
    template_name = "%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type, sparse, vol_format)
    vm_description = '%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type)
    logger.info("Creating vm %s %s ...", sparse, vol_format)
    storage_domain = storagedomains.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage_type)[0]
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_description
    vm_args['volumeType'] = sparse
    vm_args['volumeFormat'] = vol_format
    vm_args['storageDomainName'] = storage_domain
    vm_args['start'] = 'true'
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException("Creation of vm %s failed!" % vm_name)
    logger.info("Waiting for ip of %s", vm_name)
    vm_ip = ll_vms.waitForIP(vm_name)[1]['ip']
    logger.info("Setting persistent network")
    test_utils.setPersistentNetwork(vm_ip, config.VM_LINUX_PASSWORD)
    logger.info("Stopping VM %s", vm_name)
    if not ll_vms.shutdownVm(True, vm_name):
        raise exceptions.VMException("Stopping vm %s failed" % vm_name)
    ll_vms.waitForVMState(vm_name, state=config.VM_DOWN)
    logger.info(
        "Creating template %s from vm %s", template_name, vm_name)
    if not templates.createTemplate(
            True, vm=vm_name, name=template_name, cluster=config.CLUSTER_NAME):
        raise exceptions.TemplateException(
            "Creation of template %s from vm %s failed!" % (
                template_name, vm_name))
    logger.info("Removing vm %s", vm_name)
    if not ll_vms.removeVm(True, vm=vm_name):
        raise exceptions.VMException("Removal of vm %s failed" % vm_name)
    logger.info(
        "Template for sparse=%s and volume format '%s' prepared",
        sparse, vol_format
    )
    template_names[(sparse, vol_format)] = template_name


@pytest.mark.usefixtures(
    create_vm.__name__,
    clean_leftover_data.__name__,
)
@attr(tier=2)
class TestCase11834(TestCase):
    """
    storage vm sanity test, creates and removes snapshots
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Virtual_Machines_Sanity
    """
    __test__ = True
    polarion_test_case = '11834'
    data_for_vm = []

    def _prepare_data(self):
        """ don't move it to setUp! if setUp fails, tearDown WON'T be called
        and we do want to remove all prepared data (no need to care for the
        VMs as they will be eventually removed by module-level tearDown)
        """
        self.data_for_vm = []
        logger.info("Preparing data for copying to VM")
        for i in range(6):
            success, result = test_utils.prepareDataForVm(
                root_dir=config.DATA_ROOT_DIR,
                root_name_prefix='snap',
                dir_cnt=config.DATA_DIR_CNT,
                file_cnt=config.DATA_FILE_CNT)
            assert success, "Preparing data %d failed!" % i
            self.data_for_vm.append(result['data_path'])

    def _copy_data_to_vm_and_make_snapshot(self, source_path, snapshot_name):
        logger.info("Copying data from %s to %s", source_path, self.vm_name)
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        assert resource_utils.copyDataToVm(
            ip=vm_ip, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, osType='linux',
            src=source_path, dest=config.DEST_DIR
        ), "Copying data to vm %s failed" % self.vm_ip
        logger.info("Verify that all data were really copied")
        self._verify_data_on_vm([source_path])
        logger.info("Stopping VM %s", self.vm_name)
        assert ll_vms.shutdownVm(
            True, self.vm_name
        ), "Stopping vm %s failed!" % self.vm_name
        ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        logger.info("Creating snapshot %s", snapshot_name)
        assert ll_vms.addSnapshot(
            True, self.vm_name, snapshot_name
        ), "Creating snapshot of vm %s failed!" % self.vm_name
        logger.info("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        ), "Starting vm %s failed!" % self.vm_name

    def _verify_data_on_vm(self, paths):
        for path in paths:
            logger.info("Verify data from %s in VM %s", path, self.vm_name)
            vm_ip = storage_helpers.get_vm_ip(self.vm_name)
            assert resource_utils.verifyDataOnVm(
                positive=True, ip=vm_ip,
                user=config.VM_LINUX_USER,
                password=config.VM_LINUX_PASSWORD, osType='linux',
                dest=config.DEST_DIR, destToCompare=path
            ), "Data verification of %s on %s failed!" % (path, self.vm_name)

    def _remove_snapshot_verify_data(self, snapshot_name, expected_data):
        logger.info("Stopping VM %s", self.vm_name)
        assert ll_vms.shutdownVm(
            True, vm=self.vm_name
        ), "Stopping vm %s failed!" % self.vm_name
        ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        logger.info("Removing snapshot %s", snapshot_name)
        assert ll_vms.removeSnapshot(
            True, vm=self.vm_name, description=snapshot_name,
            timeout=2100
        ), "Removing snapshot %s failed!" % snapshot_name
        logger.info(
            "Starting VM %s and waiting for status 'up'", self.vm_name)
        assert ll_vms.startVm(
            True, vm=self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        ), "Starting vm %s failed!" % self.vm_name
        logger.info("Verifying data on VM %s", self.vm_name)
        self._verify_data_on_vm(expected_data)

    @polarion("RHEVM3-11834")
    def test_delete_snapshots_advanced(self):
        """
        Deleting snapshots
        """
        assert ll_vms.startVm(
            True, self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
        self._prepare_data()
        logger.info("Data prepared")
        first_snap_name, second_snap_name = 'first_snapshot', 'second_snapshot'
        logger.info("Loading data and creating first snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[0], first_snap_name)
        logger.info("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:1])
        logger.info("Loading data and creating second snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[1], second_snap_name)

        logger.info("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:2])

        logger.info("Removing first snapshot and verifying data")
        self._remove_snapshot_verify_data(
            first_snap_name, self.data_for_vm[:2])

        logger.info("Removing second snapshot and verifying data")
        self._remove_snapshot_verify_data(
            second_snap_name, self.data_for_vm[:2])

        third_snap_name = 'third_snapshot'
        logger.info("Loading data and creating third snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[2], third_snap_name)
        logger.info("Loading data and creating fourth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[3], 'fourth_snapshot')
        logger.info("Loading data and creating fifth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[4], 'fifth_snapshot')

        logger.info("Removing third snapshot and verifying data")
        self._remove_snapshot_verify_data(
            third_snap_name, self.data_for_vm[:5])

        logger.info("Loading data and creating sixth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[5], 'sixth_snapshot')
        logger.info("Verifying data")
        self._verify_data_on_vm(self.data_for_vm)


@pytest.mark.usefixtures(
    create_vm.__name__,
)
@attr(tier=2)
class TestCase11586(TestCase):
    """
    storage vm sanity test, creates 2 snapshots and removes them.
    Check that actual disk size became the same it was
    before snapshots were made.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11586'
    data_for_vm = []
    snapShot1_name = "%s_snapshot1" % config.VM_BASE_NAME
    snapShot2_name = "%s_snapshot2" % config.VM_BASE_NAME
    snapshots = [snapShot1_name, snapShot2_name]
    disk_size_before = 0
    disk_size_after = 0

    def _make_snapshots(self):
        for snapshot in self.snapshots:
            logger.info("Creating snapshot %s", snapshot)
            assert ll_vms.addSnapshot(
                True, self.vm_name, description=snapshot
            ), "Creating snapshot of vm %s failed!" % self.vm_name
            logger.info("successfully created snapshot %s", snapshot)

    def _remove_snapshots(self):
        for snapshot in self.snapshots:
            logger.info("Removing snapshot %s", snapshot)
            assert ll_vms.removeSnapshot(
                True, vm=self.vm_name, description=snapshot,
                timeout=2100
            ), "Removing snapshot %s failed!" % snapshot

    @polarion("RHEVM3-11586")
    @bz({'1185782': {}})
    def test_delete_snapshot(self):
        """
        Create 2 snapshot, Deleting them and Check that actual disk
        size became the same it was before snapshots were made.
        """
        self.disk_alias = ll_vms.get_vm_bootable_disk(self.vm_name)
        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        self.disk_size_before = diskObj.get_actual_size()
        logger.info(
            "Disk %s size - %s before snapshot creation",
            self.disk_alias, self.disk_size_before
        )

        logger.info("Make sure vm %s is up", self.vm_name)
        if ll_vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            ll_vms.startVms([self.vm_name])
            ll_vms.waitForVMState(self.vm_name)
        self._make_snapshots()

        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        logger.info(
            "Disk %s size - %s after snapshot",
            self.disk_alias, diskObj.get_actual_size()
        )

        ll_vms.stop_vms_safely([self.vm_name])
        self._remove_snapshots()

        diskObj = ll_disks.getVmDisk(self.vm_name, self.disk_alias)
        self.disk_size_after = diskObj.get_actual_size()
        logger.info(
            "Disk %s size - %s after snapshot deletion",
            self.disk_alias, self.disk_size_after
        )

        # VDSM allocates more 1 extent for metadata
        assert (
            self.disk_size_after - self.disk_size_before <= config.EXTENT_SIZE
        ), "Failed to auto shrink qcow volumes on merge of block volumes"


@pytest.mark.usefixtures(
    remove_vms.__name__,
)
@attr(tier=2)
class TestCase11830(TestCase):
    """
    Create 2 VMs from template at once.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Virtual_Machines_General
    """
    __test__ = True
    polarion_test_case = '11830'

    @polarion("RHEVM3-11830")
    def test_create_vm_from_template_basic_flow(self):
        """
        Start creating a VM from template
        Wait until template is locked
        Start creating another VM from the same template
        """
        self.vm_name_1 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        t = Thread(target=log_listener.watch_logs, args=(
            config.ENGINE_LOG, config.REGEX, None, 60, config.VDC,
            config.HOSTS_USER, config.VDC_ROOT_PASSWORD
        ))
        logger.info("Waiting for createVolume command in engine.log")
        t.start()
        time.sleep(5)

        logger.info("Creating first vm %s", self.vm_name_1)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = storage_domain
        vm_args['name'] = self.vm_name_1
        vm_args['wait'] = False
        assert ll_vms.cloneVmFromTemplate(**vm_args)
        t.join()
        self.vm_names.append(self.vm_name_1)

        logger.info("Starting to create second vm %s", self.vm_name_2)
        vm_args = config.clone_vm_args.copy()
        vm_args['storagedomain'] = storage_domain
        vm_args['name'] = self.vm_name_2
        assert ll_vms.cloneVmFromTemplate(**vm_args)
        self.vm_names.append(self.vm_name_2)

        logger.info("Starting VMs")
        ll_vms.start_vms(
            [self.vm_name_1, self.vm_name_2], wait_for_status=config.VM_UP,
            wait_for_ip=True
        )


@pytest.mark.usefixtures(
    prepare_data.__name__,
    remove_vms.__name__,
)
@attr(tier=2)
class TestCase4710(TestCase):
    """
    storage vm sanity test, cloning vm from template with changing disk type
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_VM_Sanity
    """
    __test__ = True
    polarion_test_case = '4710'
    template_names = {}

    @polarion("RHEVM3-4710")
    def create_vm_from_template_validate_disks(
            self, name, template_name, sparse, vol_format):
        vm_name = "%s_%s_clone_%s" % (
            self.polarion_test_case, self.storage, name)
        logger.info("Clone vm %s, from %s, sparse=%s, volume format = %s" % (
            vm_name, template_name, sparse, vol_format))
        assert ll_vms.cloneVmFromTemplate(
            True, name=vm_name, cluster=config.CLUSTER_NAME,
            vol_sparse=sparse, vol_format=vol_format,
            template=template_name, clone=True, timeout=900), (
            "cloning vm %s from template %s failed" % (vm_name, template_name)
        )
        self.vm_names.append(vm_name)
        logger.info("Validating disk type and format")
        assert ll_vms.validateVmDisks(
            True, vm=vm_name, sparse=sparse, format=vol_format), (
            "Validation of disks on vm %s failed" % vm_name
        )
        logger.info("Validation passed")

    def create_vms_from_template_convert_disks(
            self, sparse, vol_format, name_prefix
    ):
        name = '%s_sparse_cow' % name_prefix
        template_name = self.template_names[(sparse, vol_format)]
        self.create_vm_from_template_validate_disks(
            name, template_name, True, config.DISK_FORMAT_COW
        )
        if self.storage == config.STORAGE_TYPE_NFS:
            name = '%s_sparse_raw' % name_prefix
            self.create_vm_from_template_validate_disks(
                name, template_name, True, config.DISK_FORMAT_RAW
            )
        name = '%s_preallocated_raw' % name_prefix
        self.create_vm_from_template_validate_disks(
            name, template_name, False, config.DISK_FORMAT_RAW
        )

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_cow_test(self):
        """ creates vms from template with sparse cow disk
        """
        self.create_vms_from_template_convert_disks(
            True, config.DISK_FORMAT_COW, 'from_sparse_cow'
        )

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_raw_test(self):
        """ creates vms from template with sparse raw disk
        """
        if self.storage == config.STORAGE_TYPE_NFS:
            self.create_vms_from_template_convert_disks(
                True, config.DISK_FORMAT_RAW, 'from_sparse_raw'
            )

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_preallocated_raw_test(self):
        """ creates vms from templates with preallocated raw disk
        """
        self.create_vms_from_template_convert_disks(
            False, config.DISK_FORMAT_RAW, 'from_prealloc_raw'
        )
