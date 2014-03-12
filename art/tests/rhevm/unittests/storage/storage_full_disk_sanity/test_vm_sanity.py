"""
Storage VM sanity
TCMS plan: https://tcms.engineering.redhat.com/plan/8676
"""
from concurrent.futures import ThreadPoolExecutor
import logging
from art.unittest_lib import BaseTestCase as TestCase
import time

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils import resource_utils
from art.test_handler import exceptions

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms, disks
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import tcms

import config
from common import _create_vm

LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS

# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
#class TestCase248112(TestCase):
#    """
#    storage vm sanity test, creates and removes vm with a cow disk
#    https://tcms.engineering.redhat.com/case/248112/?from_plan=8676
#    """
#    __test__ = True
#    tcms_plan_id = '8676'
#    tcms_test_case = '248112'


def _prepare_data(sparse, vol_format, template_names):
    """ prepares data for vm
    """
    template_name = "%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.VM_BASE_NAME, config.DATA_CENTER_TYPE, sparse, vol_format)
    LOGGER.info("Creating vm %s %s ..." % (sparse, vol_format))
    if not _create_vm(
            vm_name, config.INTERFACE_IDE,
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

        test_utils.raise_if_exception(results)

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

    @tcms(tcms_plan_id, tcms_test_case)
    def test_disk_conv_from_sparse_cow_test(self):
        """ creates vms from template with sparse cow disk
        """
        self.create_vms_from_template_convert_disks(
            True, ENUMS['format_cow'], 'from_sparse_cow')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_disk_conv_from_sparse_raw_test(self):
        """ creates vms from template with sparse raw disk
        """
        if config.DATA_CENTER_TYPE == ENUMS['storage_type_nfs']:
            self.create_vms_from_template_convert_disks(
                True, ENUMS['format_raw'], 'from_sparse_raw')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_disk_conv_from_preallocated_raw_test(self):
        """ creates vms from templates with preallocated raw disk
        """
        self.create_vms_from_template_convert_disks(
            False, ENUMS['format_raw'], 'from_prealloc_raw')

    def tearDown(self):
        if self.vm_names:
            vms.removeVms(True, self.vm_names, stop='true')

    @classmethod
    def teardown_class(cls):
        for _, template_name in cls.template_names.iteritems():
            templates.removeTemplate(True, template=template_name)


# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
#class TestCase300867(TestCase):
#    """
#    storage vm sanity test, creates 2 snapshots and removes them.
#    Check that actual disk size became the same it was
#    before snapshots were made.
#    https://tcms.engineering.redhat.com/case/248138/?from_plan=8676
#    """

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
    vm_name_1 = '%s_1' % (config.VM_BASE_NAME)
    vm_name_2 = '%s_2' % (config.VM_BASE_NAME)
    SLEEP_AMOUNT = 5

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_%s' % (config.VM_BASE_NAME, cls.vm_type)
        cls.template_name = "template_%s" % (cls.vm_name)
        if not _create_vm(cls.vm_name, config.INTERFACE_IDE,
                          vm_type=cls.vm_type):
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
        vms_list = [cls.vm_name, cls.vm_name_1, cls.vm_name_2]
        LOGGER.info("Removing VMs %s" % vms_list)
        if not vms.removeVms(True, vms_list, stop='true'):
            raise exceptions.VMException("Failed removing vms %s" % vms_list)
        LOGGER.info("Removing template")
        if not templates.removeTemplate(True, cls.template_name):
            raise exceptions.TemplateException("Failed removing template %s"
                                               % cls.template_name)


class TestCase320224(TestReadLock):
    """
    TCMS Test Case 320224 - Run on desktop
    """
    __test__ = True
    tcms_test_case = '320224'
    vm_type = config.VM_TYPE_DESKTOP

    @tcms(TestReadLock.tcms_plan_id, tcms_test_case)
    def test_create_vms(self):
        """
        Start creating a VM from template (desktop)
        Wait until template is locked
        Start creating another VM from the same template
        """
        self.create_two_vms_simultaneously()


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
