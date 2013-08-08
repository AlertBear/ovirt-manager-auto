"""
Storage VM sanity
TCMS plan: https://tcms.engineering.redhat.com/plan/8676
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from nose.tools import istest
from unittest import TestCase

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils import resource_utils
from art.test_handler import exceptions

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.tools import tcms

import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


def _create_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=ENUMS['format_cow']):
    """ helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    LOGGER.info("Creating VM %s" % vm_name)
    storage_domain_name = STORAGE_DOMAIN_API.get(absLink=False)[0].name
    LOGGER.info("storage domain: %s" % storage_domain_name)
    return vms.createVm(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=GB, cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
        type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
        cobblerAddress=config.COBBLER_ADDRESS, cobblerUser=config.COBBLER_USER,
        cobblerPasswd=config.COBBLER_PASSWORD, image=config.COBBLER_PROFILE,
        network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT)


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
            config.VM_BASE_NAME, config.DATA_CENTER_TYPE)
        vm_description = '%s_%s_virtio' % (
            config.VM_BASE_NAME, config.DATA_CENTER_TYPE)
        self.assertTrue(
            _create_vm(vm_name, vm_description, config.INTERFACE_VIRTIO),
            "VM %s creation failed!" % vm_name)
        LOGGER.info("Removing created VM")
        self.assertTrue(
            vms.removeVm(True, vm=vm_name, stopVM='true'),
            "Removal of vm %s failed!" % vm_name)


def _prepare_data(sparse, vol_format, template_names):
    """ prepares data for vm
    """
    template_name = "%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.VM_BASE_NAME, config.DATA_CENTER_TYPE, sparse, vol_format)
    vm_description = '%s_%s_prep' % (
        config.VM_BASE_NAME, config.DATA_CENTER_TYPE)
    LOGGER.info("Creating vm %s %s ..." % (sparse, vol_format))
    if not _create_vm(
            vm_name, vm_description, config.INTERFACE_IDE,
            sparse=sparse, volume_format=vol_format):
        raise exceptions.VMException("Creation of vm %s failed!" % vm_name)
    LOGGER.info("Waiting for ip of %s" % vm_name)
    vm_ip = vms.waitForIP(vm_name)[1]['ip']
    LOGGER.info("Setting persistent network")
    test_utils.setPersistentNetwork(vm_ip, config.VM_LINUX_PASSWORD)
    LOGGER.info("Stopping VM %s" % vm_name)
    if not vms.stopVm(True, vm_name):
        raise exceptions.VMException("Stopping vm %s failed" % vm_name)
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


class TestCase248132(TestCase):
    """
    storage vm sanity test, cloning vm from template with changing disk type
    https://tcms.engineering.redhat.com/case/248132/?from_plan=8676
    """
    __test__ = True
    tcms_plan_id = '8676'
    tcms_test_case = '248132'
    template_names = {}

    @classmethod
    def setup_class(cls):
        results = list()
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for sparse in (True, False):
                for vol_format in (ENUMS['format_cow'], ENUMS['format_raw']):
                    if not sparse and vol_format == ENUMS['format_cow']:
                        continue
                    if (config.DATA_CENTER_TYPE != ENUMS['storage_type_nfs']
                            and sparse and vol_format == ENUMS['format_raw']):
                        continue
                    results.append(executor.submit(
                        _prepare_data, sparse, vol_format, cls.template_names))
        # TODO: test_utils.raise_if_exception(results) after gerrit 8896
        # is  merged
        for result in results:
            if result.exception():
                LOGGER.error(result.exception())
                raise result.exception()

    def setUp(self):
        self.vm_names = []

    @tcms(tcms_plan_id, tcms_test_case)
    def create_vm_from_template_validate_disks(
            self, name, template_name, sparse, vol_format):
        vm_name = "%s_%s_clone_%s" % (
            config.VM_BASE_NAME, config.DATA_CENTER_TYPE, name)
        LOGGER.info("Clone vm %s, from %s, sparse=%s, volume format = %s" % (
            vm_name, template_name, sparse, vol_format))
        self.assertTrue(
            vms.cloneVmFromTemplate(
                True, name=vm_name, cluster=config.CLUSTER_NAME,
                vol_sparse=sparse, vol_format=vol_format,
                template=template_name, clone='true', timeout=900),
            "cloning vm %s from template %s failed" % (vm_name, template_name))
        self.vm_names.append(vm_name)
        LOGGER.info("Validating disk type and format")
        self.assertTrue(
            vms.validateVmDisks(
                True, vm=vm_name, sparse=sparse, format=vol_format),
            "Validation of disks on vm %s failed" % vm_name)
        LOGGER.info("Validation passed")

    def create_vms_from_template_convert_disks(
            self, sparse, vol_format, name_prefix):
        name = '%s_sparse_cow' % name_prefix
        template_name = self.template_names[(sparse, vol_format)]
        self.create_vm_from_template_validate_disks(
            name, template_name, True, ENUMS['format_cow'])
        if config.DATA_CENTER_TYPE == ENUMS['storage_type_nfs']:
            name = '%s_sparse_raw' % name_prefix
            self.create_vm_from_template_validate_disks(
                name, template_name, True, ENUMS['format_raw'])
        name = '%s_preallocated_raw' % name_prefix
        self.create_vm_from_template_validate_disks(
            name, template_name, False, ENUMS['format_raw'])

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def disk_conv_from_sparse_cow_test(self):
        """ creates vms from template with sparse cow disk
        """
        self.create_vms_from_template_convert_disks(
            True, ENUMS['format_cow'], 'from_sparse_cow')

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def disk_conv_from_sparse_raw_test(self):
        """ creates vms from template with sparse raw disk
        """
        if config.DATA_CENTER_TYPE == ENUMS['storage_type_nfs']:
            self.create_vms_from_template_convert_disks(
                True, ENUMS['format_raw'], 'from_sparse_raw')

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def disk_conv_from_preallocated_raw_test(self):
        """ creates vms from templates with preallocated cow disk
        """
        self.create_vms_from_template_convert_disks(
            False, ENUMS['format_raw'], 'from_prealloc_raw')

    def tearDown(self):
        vm_names = ",".join(self.vm_names)
        vms.removeVms(True, vm_names, stop='true')

    @classmethod
    def teardown_class(cls):
        for _, template_name in cls.template_names.iteritems():
            templates.removeTemplate(True, template=template_name)


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
    vm_name = '%s_%s_snap' % (config.VM_BASE_NAME, config.DATA_CENTER_TYPE)

    @classmethod
    def setup_class(cls):
        vm_description = '%s_%s_snap' % (
            config.VM_BASE_NAME, config.DATA_CENTER_TYPE)
        if not _create_vm(cls.vm_name, vm_description, config.INTERFACE_IDE):
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
        self.assertTrue(
            resource_utils.copyDataToVm(
                ip=TestCase248138.vms_ip_address, user=config.VM_LINUX_USER,
                password=config.VM_LINUX_PASSWORD, osType='linux',
                src=source_path, dest=config.DEST_DIR),
            "Copying data to vm %s failed" % self.vms_ip_address)
        LOGGER.info("Verify that all data were really copied")
        self._verify_data_on_vm([source_path])
        LOGGER.info("Stopping VM %s" % self.vm_name)
        self.assertTrue(
            vms.stopVm(True, self.vm_name),
            "Stopping vm %s failed!" % self.vm_name)
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
            self.assertTrue(
                resource_utils.verifyDataOnVm(
                    positive=True, vmName=self.vm_name,
                    user=config.VM_LINUX_USER,
                    password=config.VM_LINUX_PASSWORD, osType='linux',
                    dest=config.DEST_DIR, destToCompare=path),
                "Data verification of %s on %s failed!" % (path, self.vm_name))

    def _remove_snapshot_verify_data(self, snapshot_name, expected_data):
        LOGGER.info("Stopping VM %s" % self.vm_name)
        self.assertTrue(
            vms.stopVm(True, vm=self.vm_name),
            "Stopping vm %s failed!" % self.vm_name)
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
