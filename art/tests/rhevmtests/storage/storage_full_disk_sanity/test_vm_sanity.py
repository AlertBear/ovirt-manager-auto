"""
Storage VM sanity
Polarion plan: https://polarion.engineering.redhat.com/polarion/#/project/
RHEVM3/wiki/Storage/3_3_Storage_VM_Sanity
"""
import config
import logging
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level import vms, templates, storagedomains
from art.rhevm_api.utils import log_listener
from art.test_handler.tools import polarion  # pylint: disable=E0611
from common import create_vm

LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS

# TBD: Remove this when is implemented in the main story, storage sanity
# http://rhevm-qe-storage.pad.engineering.redhat.com/11?
# class TestCase4709(TestCase):
#     """
#     storage vm sanity test, creates and removes vm with a cow disk
#     https://polarion.engineering.redhat.com/polarion/#/project/
#     RHEVM3/wiki/Storage/3_3_Storage_VM_Sanity
#     """
#     __test__ = True
#     polarion_test_case = '4709'


def _prepare_data(sparse, vol_format, template_names, storage_type):
    """ prepares data for vm
    """
    storage_domain = storagedomains.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage_type)[0]
    template_name = "%s_%s_%s_%s" % (
        config.TEMPLATE_NAME, sparse, vol_format, storage_type)
    vm_name = '%s_%s_%s_%s_prep' % (
        config.TESTNAME, sparse, vol_format, storage_type)
    LOGGER.info("Creating vm %s %s %s..." % (sparse, vol_format, storage_type))
    if not create_vm(
            vm_name, config.INTERFACE_VIRTIO,
            sparse=sparse, volume_format=vol_format,
            storage_domain=storage_domain):
        raise exceptions.VMException("Creation of vm %s failed!" % vm_name)
    LOGGER.info("Waiting for ip of %s" % vm_name)
    vm_ip = vms.waitForIP(vm_name)[1]['ip']
    LOGGER.info("Setting persistent network")
    assert test_utils.setPersistentNetwork(vm_ip, config.VMS_LINUX_PW)
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


@attr(tier=1)
class TestCase4710(TestCase):
    """
    storage vm sanity test, cloning vm from template with changing disk type
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_VM_Sanity
    """
    __test__ = True
    polarion_test_case = '4710'
    template_names = {}

    @classmethod
    def setup_class(cls):
        for sparse in (True, False):
            for vol_format in (ENUMS['format_cow'], ENUMS['format_raw']):
                if not sparse and vol_format == ENUMS['format_cow']:
                    continue
                if (cls.storage != ENUMS['storage_type_nfs']
                        and sparse and vol_format == ENUMS['format_raw']):
                    continue
                _prepare_data(
                    sparse, vol_format, cls.template_names, cls.storage
                )

    def setUp(self):
        self.vm_names = []

    @polarion("RHEVM3-4710")
    def create_vm_from_template_validate_disks(
            self, name, template_name, sparse, vol_format):
        vm_name = "%s_%s_clone_%s" % (
            self.polarion_test_case, self.storage, name)
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
        if self.storage == ENUMS['storage_type_nfs']:
            name = '%s_sparse_raw' % name_prefix
            self.create_vm_from_template_validate_disks(
                name, template_name, True, ENUMS['format_raw'])
        name = '%s_preallocated_raw' % name_prefix
        self.create_vm_from_template_validate_disks(
            name, template_name, False, ENUMS['format_raw'])

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_cow_test(self):
        """ creates vms from template with sparse cow disk
        """
        self.create_vms_from_template_convert_disks(
            True, ENUMS['format_cow'], 'from_sparse_cow')

    @polarion("RHEVM3-4710")
    def test_disk_conv_from_sparse_raw_test(self):
        """ creates vms from template with sparse raw disk
        """
        if self.storage == ENUMS['storage_type_nfs']:
            self.create_vms_from_template_convert_disks(
                True, ENUMS['format_raw'], 'from_sparse_raw')

    @polarion("RHEVM3-4710")
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
# class TestCase4711(TestCase):
#     """
#     storage vm sanity test, creates 2 snapshots and removes them.
#     Check that actual disk size became the same it was
#     before snapshots were made.
#     https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
#     Storage/3_3_Storage_VM_Sanity
#     """

class TestReadLock(TestCase):
    """
    Create a template from a VM, then start to create 2 VMs from
    this template at once.
    """
    __test__ = False
    polarion_test_case = None
    vm_type = None
    vm_name = None
    template_name = None
    vm_name_1 = '%s_readlock_1' % config.TEST_NAME
    vm_name_2 = '%s_readlock_2' % config.TEST_NAME
    SLEEP_AMOUNT = 5

    @classmethod
    def setup_class(cls):
        cls.vm_name = '%s_readlock_%s' % (config.TEST_NAME, cls.vm_type)
        cls.template_name = "template_%s" % (cls.vm_name)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        if not create_vm(cls.vm_name, config.INTERFACE_VIRTIO,
                         vm_type=cls.vm_type,
                         storage_domain=storage_domain):
            raise exceptions.VMException(
                "Creation of VM %s failed!" % cls.vm_name)
        LOGGER.info("Waiting for vm %s state 'up'" % cls.vm_name)
        if not vms.waitForVMState(cls.vm_name):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % cls.vm_name)
        LOGGER.info("Waiting for ip of %s" % cls.vm_name)
        vm_ip = vms.waitForIP(cls.vm_name)[1]['ip']
        LOGGER.info("Setting persistent network")
        assert test_utils.setPersistentNetwork(vm_ip, config.VMS_LINUX_PW)

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
        log_listener.watch_logs(
            files_to_watch=config.ENGINE_LOG,
            regex='createVolume',
            time_out=60,
            ip_for_files=config.VDC,
            username='root',
            password=config.VDC_ROOT_PASSWORD
        )
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
