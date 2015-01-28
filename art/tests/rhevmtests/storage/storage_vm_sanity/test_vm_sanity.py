"""
Storage VM sanity
TCMS plan: https://tcms.engineering.redhat.com/plan/8676
"""

import logging
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as TestCase

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils import resource_utils
from art.test_handler import exceptions

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms, disks
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611

import config
from rhevmtests.storage.helpers import get_vm_ip

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE, basename=config.TESTNAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        storagedomains.cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)


def _create_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=ENUMS['format_cow'],
               vm_type=config.VM_TYPE_DESKTOP,
               storage_type=config.STORAGE_TYPE):
    """ helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    LOGGER.info("Creating VM %s" % vm_name)
    storage_domain = storagedomains.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage_type)[0]
    return vms.createVm(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=GB,
        cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
        type=vm_type, installation=True, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)


@attr(tier=1)
class TestCase248112(TestCase):
    """
    storage vm sanity test, creates and removes vm with a cow disk
    https://tcms.engineering.redhat.com/case/248112/?from_plan=8676
    """
    __test__ = True
    tcms_plan_id = '8676'
    tcms_test_case = '248112'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def create_and_remove_vm_test(self):
        """ creates and removes vm
        """
        vm_name = '%s_%s_virtio' % (
            config.VM_BASE_NAME, self.storage)
        self.assertTrue(
            _create_vm(vm_name, vm_name, config.INTERFACE_VIRTIO,
                       storage_type=self.storage),
            "VM %s creation failed!" % vm_name)
        LOGGER.info("Removing created VM")
        self.assertTrue(
            vms.removeVm(True, vm=vm_name, stopVM='true'),
            "Removal of vm %s failed!" % vm_name)


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
    if not _create_vm(
            vm_name, vm_description, config.INTERFACE_VIRTIO,
            sparse=sparse, volume_format=vol_format,
            storage_type=storage_type):
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


@attr(tier=1)
class TestCase248138(TestCase):
    """
    storage vm sanity test, creates and removes snapshots
    https://tcms.engineering.redhat.com/case/248138/?from_plan=8676
    """
    __test__ = True
    tcms_plan_id = '8676'
    tcms_test_case = '248138'
    data_for_vm = []
    vms_ip_address = None

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_%s_snap' % (config.VM_BASE_NAME, cls.storage)
        vm_description = '%s_%s_snap' % (
            config.VM_BASE_NAME, cls.storage)
        if not _create_vm(cls.vm_name, vm_description, config.INTERFACE_VIRTIO,
                          storage_type=cls.storage):
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
        vm_ip = get_vm_ip(self.vm_name)
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
            vm_ip = get_vm_ip(self.vm_name)
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

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def delete_snapshots_test(self):
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


@attr(tier=0)
class TestCase300867(TestCase):
    """
    storage vm sanity test, creates 2 snapshots and removes them.
    Check that actual disk size became the same it was
    before snapshots were made.
    https://tcms.engineering.redhat.com/case/300867/?from_plan=6458
    """
    __test__ = True
    tcms_plan_id = '6458'
    tcms_test_case = '300867'
    data_for_vm = []
    vms_ip_address = None
    snapShot1_name = "%s_snapshot1" % config.VM_BASE_NAME
    snapShot2_name = "%s_snapshot2" % config.VM_BASE_NAME
    snapshots = [snapShot1_name, snapShot2_name]
    disk_size_before = 0
    disk_size_after = 0

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_%s_snap' % (config.VM_BASE_NAME, cls.storage)
        cls.alias = "%s_Disk1" % cls.vm_name
        vm_description = '%s_%s_snap' % (
            config.VM_BASE_NAME, cls.storage)
        # create vm with thin provision disk
        if not _create_vm(cls.vm_name, vm_description, config.INTERFACE_VIRTIO,
                          sparse=True, volume_format=ENUMS['format_cow'],
                          storage_type=cls.storage):
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
        LOGGER.info("Stopping VM %s" % cls.vm_name)
        vms.shutdownVm(True, cls.vm_name)
        if not vms.waitForVMState(cls.vm_name, state=config.VM_DOWN):
            vms.stopVm(True, cls.vm_name)
        LOGGER.info("setup finished with success")

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

    @bz({"1185782": {'engine': ['rest', 'sdk'], 'version': ['3.5']}})
    @tcms(tcms_plan_id, tcms_test_case)
    def test_delete_snapshot(self):
        """
        Create 2 snapshot, Deleting them and Check that actual disk
        size became the same it was before snapshots were made.
        """
        diskObj = disks.getVmDisk(self.vm_name, self.alias)
        self.disk_size_before = diskObj.get_actual_size()
        LOGGER.info("Disk %s size - %s before snapshot creation",
                    self.alias,
                    self.disk_size_before)

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

    @classmethod
    def teardown_class(cls):
        vms.removeVm(True, vm=cls.vm_name, stopVM='true')


class TestReadLock(TestCase):
    """
    Create a template from a VM, then start to create 2 VMs from
    this template at once.
    """
    __test__ = False
    tcms_plan_id = '8040'
    tcms_test_case = None
    vm_type = None
    vm_name = None
    template_name = None
    vm_name_1 = '%s_1' % config.VM_BASE_NAME
    vm_name_2 = '%s_2' % config.VM_BASE_NAME
    SLEEP_AMOUNT = 5

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_%s' % (config.VM_BASE_NAME, cls.vm_type)
        cls.template_name = "template_%s" % cls.vm_name
        if not _create_vm(cls.vm_name, cls.vm_name, config.INTERFACE_IDE,
                          vm_type=cls.vm_type, storage_type=cls.storage):
            raise exceptions.VMException(
                "Creation of VM %s failed!" % cls.vm_name)
        LOGGER.info("Waiting for vm %s state 'up'" % cls.vm_name)
        if not vms.waitForVMState(cls.vm_name):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % cls.vm_name)
        LOGGER.info("Shutting down %s" % cls.vm_name)
        if not vms.shutdownVm(True, cls.vm_name, async='false'):
            raise exceptions.VMException("Can't shut down vm %s" %
                                         cls.vm_name)
        vms.waitForVMState(cls.vm_name, state=config.VM_DOWN)
        LOGGER.info("Creating template %s from VM %s" % (cls.template_name,
                                                         cls.vm_name))
        template_args = {
            "vm": cls.vm_name,
            "name": cls.template_name,
            "cluster": config.CLUSTER_NAME
        }
        if not templates.createTemplate(True, **template_args):
            raise exceptions.TemplateException("Failed creating template %s" %
                                               cls.template_name)

    def create_two_vms_simultaneously(self):
        """
        Start creating a VM from template
        Wait until template is locked
        Start creating another VM from the same template
        """
        LOGGER.info("Creating first vm %s from template %s" %
                    (self.vm_name_1, self.template_name))
        assert vms.createVm(True, self.vm_name_1, self.vm_name_1,
                            template=self.template_name,
                            cluster=config.CLUSTER_NAME)
        LOGGER.info("Waiting for createVolume command in engine.log")
        log_listener.watch_logs('/var/log/ovirt-engine/engine.log',
                                'createVolume',
                                '',
                                time_out=60,
                                ip_for_files=config.VDC,
                                username='root',
                                password=config.VDC_ROOT_PASSWORD)
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

    @classmethod
    def teardown_class(cls):
        vms_list = filter(vms.does_vm_exist,
                          [cls.vm_name, cls.vm_name_1, cls.vm_name_2])
        LOGGER.info("Removing VMs %s" % vms_list)
        vms.stop_vms_safely(vms_list)
        for vm in vms_list:
            if not vms.removeVm(True, vm):
                LOGGER.error("Failed removing vm %s", vm)
        LOGGER.info("Removing template")
        if not templates.removeTemplate(True, cls.template_name):
            raise exceptions.TemplateException("Failed removing template %s"
                                               % cls.template_name)


@attr(tier=0)
class TestCase320225(TestReadLock):
    """
    TCMS Test Case 320225 - Run on server
    """
    __test__ = True
    tcms_test_case = '320225'
    vm_type = config.VM_TYPE_SERVER

    @tcms(TestReadLock.tcms_plan_id, tcms_test_case)
    def test_create_vms(self):
        """
        Start creating a VM from template (server)
        Wait until template is locked
        Start creating another VM from the same template
        """
        self.create_two_vms_simultaneously()
