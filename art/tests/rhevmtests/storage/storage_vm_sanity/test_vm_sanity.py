"""
Storage VM sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage/3_1_Virtual_Machines_Sanity
"""
import config
import logging
import time
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils import resource_utils
from art.test_handler import exceptions
from threading import Thread
from art.rhevm_api.tests_lib.low_level import vms, disks
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from rhevmtests.storage import helpers as storage_helpers

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024
REGEX = 'createVolume'

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


def _prepare_data(sparse, vol_format, template_names, storage_type):
    """ prepares data for vm
    """
    template_name = "%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type, sparse, vol_format)
    vm_description = '%s_%s_prep' % (
        config.VM_BASE_NAME, storage_type)
    LOGGER.info("Creating vm %s %s ..." % (sparse, vol_format))
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
    LOGGER.info("Waiting for ip of %s" % vm_name)
    vm_ip = vms.waitForIP(vm_name)[1]['ip']
    LOGGER.info("Setting persistent network")
    test_utils.setPersistentNetwork(vm_ip, config.VM_LINUX_PASSWORD)
    LOGGER.info("Stopping VM %s" % vm_name)
    if not vms.shutdownVm(True, vm_name):
        raise exceptions.VMException("Stopping vm %s failed" % vm_name)
    vms.waitForVMState(vm_name, state=config.VM_DOWN)
    LOGGER.info(
        "Creating template %s from vm %s" % (template_name, vm_name))
    if not templates.createTemplate(
            True, vm=vm_name, name=template_name, cluster=config.CLUSTER_NAME):
        raise exceptions.TemplateException(
            "Creation of template %s from vm %s failed!" % (
                template_name, vm_name))
    LOGGER.info("Removing vm %s" % vm_name)
    if not vms.removeVm(True, vm=vm_name):
        raise exceptions.VMException("Removal of vm %s failed" % vm_name)
    LOGGER.info(
        "Template for sparse=%s and volume format '%s' prepared" % (
            sparse, vol_format))
    template_names[(sparse, vol_format)] = template_name


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
    vms_ip_address = None

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_%s_snap' % (config.VM_BASE_NAME, cls.storage)
        vm_description = '%s_%s_snap' % (
            config.VM_BASE_NAME, cls.storage)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = cls.vm_name
        vm_args['vmDescription'] = vm_description
        vm_args['storageDomainName'] = storage_domain
        vm_args['start'] = 'true'
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Creation of VM %s failed!" % cls.vm_name)
        LOGGER.info("Waiting for vm %s state 'up'" % cls.vm_name)
        if not vms.waitForVMState(cls.vm_name):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % cls.vm_name)
        LOGGER.info("Getting IP of vm %s" % cls.vm_name)
        status, vm_ip = vms.waitForIP(cls.vm_name)
        if not status:
            raise exceptions.VMException("Can't get IP of vm %s" % cls.vm_name)
        cls.vms_ip_address = vm_ip['ip']
        LOGGER.info("setup finished with success")

    def _prepare_data(self):
        """ don't move it to setUp! if setUp fails, tearDown WON'T be called
        and we do want to remove all prepared data (no need to care for the
        VMs as they will be eventually removed by module-level tearDown)
        """
        self.data_for_vm = []
        LOGGER.info("Preparing data for copying to VM")
        for i in range(6):
            success, result = test_utils.prepareDataForVm(
                root_dir=config.DATA_ROOT_DIR,
                root_name_prefix='snap',
                dir_cnt=config.DATA_DIR_CNT,
                file_cnt=config.DATA_FILE_CNT)
            self.assertTrue(success, "Preparing data %d failed!" % i)
            self.data_for_vm.append(result['data_path'])

    def _copy_data_to_vm_and_make_snapshot(self, source_path, snapshot_name):
        LOGGER.info("Copying data from %s to %s" % (source_path, self.vm_name))
        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        self.assertTrue(
            resource_utils.copyDataToVm(
                ip=vm_ip, user=config.VM_LINUX_USER,
                password=config.VM_LINUX_PASSWORD, osType='linux',
                src=source_path, dest=config.DEST_DIR),
            "Copying data to vm %s failed" % self.vms_ip_address)
        LOGGER.info("Verify that all data were really copied")
        self._verify_data_on_vm([source_path])
        LOGGER.info("Stopping VM %s" % self.vm_name)
        self.assertTrue(
            vms.shutdownVm(True, self.vm_name),
            "Stopping vm %s failed!" % self.vm_name)
        vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        LOGGER.info("Creating snapshot %s" % snapshot_name)
        self.assertTrue(
            vms.addSnapshot(True, self.vm_name, snapshot_name),
            "Creating snapshot of vm %s failed!" % self.vm_name)
        LOGGER.info("Starting VM %s" % self.vm_name)
        self.assertTrue(
            vms.startVm(
                True, self.vm_name, wait_for_status='up', wait_for_ip=True),
            "Starting vm %s failed!" % self.vm_name)

    def _verify_data_on_vm(self, paths):
        for path in paths:
            LOGGER.info("Verify data from %s in VM %s" % (path, self.vm_name))
            vm_ip = storage_helpers.get_vm_ip(self.vm_name)
            self.assertTrue(
                resource_utils.verifyDataOnVm(
                    positive=True, ip=vm_ip,
                    user=config.VM_LINUX_USER,
                    password=config.VM_LINUX_PASSWORD, osType='linux',
                    dest=config.DEST_DIR, destToCompare=path),
                "Data verification of %s on %s failed!" % (path, self.vm_name))

    def _remove_snapshot_verify_data(self, snapshot_name, expected_data):
        LOGGER.info("Stopping VM %s" % self.vm_name)
        self.assertTrue(
            vms.shutdownVm(True, vm=self.vm_name),
            "Stopping vm %s failed!" % self.vm_name)
        vms.waitForVMState(self.vm_name, state=config.VM_DOWN)
        LOGGER.info("Removing snapshot %s" % snapshot_name)
        self.assertTrue(
            vms.removeSnapshot(
                True, vm=self.vm_name, description=snapshot_name,
                timeout=2100),
            "Removing snapshot %s failed!" % snapshot_name)
        LOGGER.info(
            "Starting VM %s and waiting for status 'up'" % self.vm_name)
        self.assertTrue(
            vms.startVm(
                True, vm=self.vm_name, wait_for_status='up', wait_for_ip=True),
            "Starting vm %s failed!" % self.vm_name)
        LOGGER.info("Verifying data on VM %s" % self.vm_name)
        self._verify_data_on_vm(expected_data)

    @polarion("RHEVM3-11834")
    def test_delete_snapshots_advanced(self):
        """ Deleting snapshots
        """
        self._prepare_data()
        LOGGER.info("Data prepared")
        first_snap_name, second_snap_name = 'first_snapshot', 'second_snapshot'
        LOGGER.info("Loading data and creating first snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[0], first_snap_name)
        LOGGER.info("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:1])
        LOGGER.info("Loading data and creating second snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[1], second_snap_name)

        LOGGER.info("Verify that all data were really copied")
        self._verify_data_on_vm(self.data_for_vm[:2])

        LOGGER.info("Removing first snapshot and verifying data")
        self._remove_snapshot_verify_data(
            first_snap_name, self.data_for_vm[:2])

        LOGGER.info("Removing second snapshot and verifying data")
        self._remove_snapshot_verify_data(
            second_snap_name, self.data_for_vm[:2])

        third_snap_name = 'third_snapshot'
        LOGGER.info("Loading data and creating third snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[2], third_snap_name)
        LOGGER.info("Loading data and creating fourth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[3], 'fourth_snapshot')
        LOGGER.info("Loading data and creating fifth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[4], 'fifth_snapshot')

        LOGGER.info("Removing third snapshot and verifying data")
        self._remove_snapshot_verify_data(
            third_snap_name, self.data_for_vm[:5])

        LOGGER.info("Loading data and creating sixth snapshot")
        self._copy_data_to_vm_and_make_snapshot(
            self.data_for_vm[5], 'sixth_snapshot')
        LOGGER.info("Verifying data")
        self._verify_data_on_vm(self.data_for_vm)

    @classmethod
    def teardown_class(cls):
        for data_path in cls.data_for_vm:
            # we don't need try-except, as cleanupData uses
            # rmtree(path, ignore_errors=True)
            test_utils.cleanupData(data_path)
        vms.removeVm(True, vm=cls.vm_name, stopVM='true')


@attr(tier=1)
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
    vms_ip_address = None
    snapShot1_name = "%s_snapshot1" % config.VM_BASE_NAME
    snapShot2_name = "%s_snapshot2" % config.VM_BASE_NAME
    snapshots = [snapShot1_name, snapShot2_name]
    disk_size_before = 0
    disk_size_after = 0

    def setUp(self):
        self.vm_name = '%s_%s_snap' % (config.VM_BASE_NAME, self.storage)
        vm_description = '%s_%s_snap' % (
            config.VM_BASE_NAME, self.storage)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['vmDescription'] = vm_description
        vm_args['storageDomainName'] = storage_domain
        vm_args['start'] = 'true'
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Creation of VM %s failed" % self.vm_name)
        LOGGER.info("Waiting for vm %s state 'up'" % self.vm_name)
        if not vms.waitForVMState(self.vm_name):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % self.vm_name)
        LOGGER.info("Getting IP of vm %s" % self.vm_name)
        self.vms_ip_address = storage_helpers.get_vm_ip(self.vm_name)
        self.alias = vms.get_vm_bootable_disk(self.vm_name)

        vms.stop_vms_safely([self.vm_name])

    def _make_snapshots(self):
        for snapshot in self.snapshots:
            LOGGER.info("Creating snapshot %s" % snapshot)
            self.assertTrue(
                vms.addSnapshot(True, self.vm_name, description=snapshot),
                "Creating snapshot of vm %s failed!" % self.vm_name)
            LOGGER.info("successfully created snapshot %s" % snapshot)

    def _remove_snapshots(self):
        for snapshot in self.snapshots:
            LOGGER.info("Removing snapshot %s" % snapshot)
            self.assertTrue(
                vms.removeSnapshot(
                    True, vm=self.vm_name, description=snapshot,
                    timeout=2100),
                "Removing snapshot %s failed!" % snapshot)

    @polarion("RHEVM3-11586")
    @bz({'1185782': {}})
    def test_delete_snapshot(self):
        """
        Create 2 snapshot, Deleting them and Check that actual disk
        size became the same it was before snapshots were made.
        """
        diskObj = disks.getVmDisk(self.vm_name, self.alias)
        self.disk_size_before = diskObj.get_actual_size()
        LOGGER.info(
            "Disk %s size - %s before snapshot creation",
            self.alias, self.disk_size_before
        )

        LOGGER.info("Make sure vm %s is up", self.vm_name)
        if vms.get_vm_state(self.vm_name) == config.VM_DOWN:
            vms.startVms([self.vm_name])
            vms.waitForVMState(self.vm_name)
        self._make_snapshots()

        diskObj = disks.getVmDisk(self.vm_name, self.alias)
        LOGGER.info("Disk %s size - %s after snapshot",
                    self.alias,
                    diskObj.get_actual_size())

        vms.stop_vms_safely([self.vm_name])
        self._remove_snapshots()

        diskObj = disks.getVmDisk(self.vm_name, self.alias)
        self.disk_size_after = diskObj.get_actual_size()
        LOGGER.info("Disk %s size - %s after snapshot deletion",
                    self.alias,
                    self.disk_size_after)

        # VDSM allocates more 1 extent for metadata
        self.assertTrue(
            self.disk_size_after - self.disk_size_before <= config.EXTENT_SIZE,
            "Failed to auto shrink qcow volumes on merge of block volumes")

    def tearDown(self):
        if not vms.safely_remove_vms([self.vm_name]):
            LOGGER.error("Failed to power off and remove vm %s", self.vm_name)
            TestCase.test_failed = True
        TestCase.teardown_exception()


@attr(tier=1)
class TestCase11830(TestCase):
    """
    Create a template from a VM, then start to create 2 VMs from
    this template at once.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Virtual_Machines_General
    """
    __test__ = True
    polarion_test_case = '11830'
    vm_type = config.VM_TYPE_SERVER
    vm_name = None
    template_name = None
    vm_name_1 = '%s_1' % config.VM_BASE_NAME
    vm_name_2 = '%s_2' % config.VM_BASE_NAME
    SLEEP_AMOUNT = 5

    def setUp(self):
        self.vm_name = '%s_%s' % (config.VM_BASE_NAME, self.vm_type)
        self.template_name = "template_%s" % self.vm_name
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['vmDescription'] = self.vm_name
        vm_args['storageDomainName'] = storage_domain
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                "Creation of VM %s failed!" % self.vm_name)

    @polarion("RHEVM3-11830")
    def test_create_vm_from_template_basic_flow(self):
        """
        Create template from vm
        Start creating a VM from this template
        Wait until template is locked
        Start creating another VM from the same template
        """
        template_args = {
            "vm": self.vm_name,
            "name": self.template_name,
            "cluster": config.CLUSTER_NAME
        }
        LOGGER.info("Creating template %s from VM %s" % (self.template_name,
                                                         self.vm_name))

        if not templates.createTemplate(True, **template_args):
            raise exceptions.TemplateException(
                "Failed creating template %s" % self.template_name)

        t = Thread(target=log_listener.watch_logs, args=(
            config.ENGINE_LOG, REGEX, None, 60, config.VDC,
            config.HOSTS_USER, config.VDC_ROOT_PASSWORD
        ))
        LOGGER.info("Waiting for createVolume command in engine.log")
        t.start()

        time.sleep(5)

        LOGGER.info("Creating first vm %s from template %s" %
                    (self.vm_name_1, self.template_name))
        assert vms.createVm(True, self.vm_name_1, self.vm_name_1,
                            template=self.template_name,
                            cluster=config.CLUSTER_NAME)

        t.join()
        time.sleep(5)

        LOGGER.info("Starting to create vm %s from template %s" %
                    (self.vm_name_2, self.template_name))
        assert vms.createVm(True, self.vm_name_2, self.vm_name_2,
                            template=self.template_name,
                            cluster=config.CLUSTER_NAME)
        LOGGER.info("Starting VMs")
        assert vms.startVm(True, self.vm_name_1,
                           wait_for_status=ENUMS['vm_state_up'])
        assert vms.startVm(True, self.vm_name_2,
                           wait_for_status=ENUMS['vm_state_up'])

    def tearDown(self):
        vms_list = filter(vms.does_vm_exist,
                          [self.vm_name, self.vm_name_1, self.vm_name_2])
        LOGGER.info("Removing VMs %s" % vms_list)
        vms.stop_vms_safely(vms_list)
        for vm in vms_list:
            if not vms.removeVm(True, vm):
                LOGGER.error("Failed removing vm %s", vm)
        LOGGER.info("Removing template")
        if not templates.removeTemplate(True, self.template_name):
            raise exceptions.TemplateException("Failed removing template %s"
                                               % self.template_name)
