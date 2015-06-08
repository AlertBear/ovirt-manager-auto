"""
Export/import test cases
"""
import config
import logging
from concurrent.futures import ThreadPoolExecutor
from art.unittest_lib import StorageTest as TestCase, attr
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates
from common import _create_vm

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
BLANK_TEMPLATE_ID = "00000000-0000-0000-0000-000000000000"
MAX_WORKERS = config.MAX_WORKERS


class BaseExportImportTestCase(TestCase):
    """
    Base TestCase for export/import.
    * Creates one vm
    """
    __test__ = False
    polarion_test_case = ''
    vm_type = config.VM_TYPE_SERVER

    def setUp(self):
        """
        * Creates a vm and shuts it down
        """
        self.vm_name = "original_vm_%s" % self.polarion_test_case
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

        logger.info("Creating vm %s with type %s", self.vm_name, self.vm_type)
        if not _create_vm(self.vm_name, vm_type=self.vm_type,
                          storage_domain=self.storage_domain):
            raise exceptions.VMException('Unable to create vm %s for test' %
                                         self.vm_name)
        vms.stop_vms_safely([self.vm_name])
        if not vms.waitForVMState(self.vm_name, config.VM_DOWN):
            raise exceptions.VMException('Unable to stop vm %s for test' %
                                         self.vm_name)

    def tearDown(self):
        """
        * Removes vm
        """
        if not vms.safely_remove_vms([self.vm_name]):
            raise exceptions.VMException('Unable to remove vm %s for test' %
                                         self.vm_name)


@attr(tier=1)
class TestCase4665(BaseExportImportTestCase):
    """
    Test Force Override option
    """
    __test__ = True
    polarion_test_case = '4665'

    def setUp(self):
        """
        * Creates a template from the vm
        """
        super(TestCase4665, self).setUp()
        self.template_name = "origial_template_%s" % self.polarion_test_case

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

    @polarion("RHEVM3-4665")
    def test_import_force_override(self):
        """
        * export VM with force override enabled/disabled
        * export template with force override enabled/disabled
        """
        logger.info("Exporting VM %s with force override enabled should "
                    "succeed when there's not VM in the export domain",
                    self.vm_name)
        assert vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true')

        logger.info("Exporting VM %s with force override disabled should fail "
                    "when there's a VM in the export domain", self.vm_name)
        assert vms.exportVm(
            False, self.vm_name, self.export_domain, exclusive='false')

        logger.info("Exporting VM %s with force override enabled should "
                    "succeed when there's a VM in the export domain",
                    self.vm_name)
        assert vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true')

        logger.info("Exporting template %s with force override enabled "
                    "should succeed when there's not a template in the "
                    "export domain", self.template_name)
        assert templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true')

        logger.info("Exporting template %s with force override disabled should"
                    " fail because there's a template in the export domain",
                    self.template_name)
        assert templates.exportTemplate(
            False, self.template_name, self.export_domain, exclusive='false')

        logger.info("Exporting template %s with force override enabled should "
                    "succeed when there's a template in the export domain",
                    self.template_name)
        assert templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true')

    def tearDown(self):
        """
        * Remove existing VM/templates and from the export domain
        """
        # TBD: Wipe export domain better?
        assert templates.removeTemplateFromExportDomain(
            True, self.template_name, config.CLUSTER_NAME, self.export_domain)
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain)
        assert templates.removeTemplate(True, self.template_name)

        super(TestCase4665, self).tearDown()


@attr(tier=1)
class TestCase4684(BaseExportImportTestCase):
    """
    Test Case 4684 -  Collapse Snapshots
    """
    __test__ = True
    polarion_test_case = '4684'
    imported_vm = 'imported_%s' % polarion_test_case

    @polarion("RHEVM3-4684")
    def test_collapse_snapshots(self):
        """
        Test export/import with collapse snapshots option works
        """
        logger.info("Exporting vm %s with collapse snapshots enabled",
                    self.vm_name)
        assert vms.exportVm(
            True, self.vm_name, self.export_domain, discard_snapshots='true')

        logger.info("Importing vm with collapse snapshots enabled")
        assert vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME, name=self.imported_vm)

        logger.info("Starting vm %s should work")
        assert vms.startVm(True, self.imported_vm)

        logger.info("Template for vm %s should be Blank", self.imported_vm)
        self.assertEqual(vms.getVmTemplateId(self.imported_vm),
                         BLANK_TEMPLATE_ID)

        logger.info("Number of snapshots is only one")
        vms._getVmSnapshots(self.imported_vm, False)
        self.assertEqual(len(vms._getVmSnapshots(self.imported_vm, False)), 1)

    def tearDown(self):
        """
        Remove newly Vm imported
        """
        super(TestCase4684, self).tearDown()
        assert vms.removeVm(True, self.imported_vm, stopVM="true")
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain)


@attr(tier=0)
class TestCase11987(BaseExportImportTestCase):
    """
    Test case 11987 - Export a VM sanity
    Test import from Blank and from template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_VM_Import_Export_Sanity
    """
    __test__ = True
    polarion_test_case = '11987'
    vm_from_template = "vm_from_template_%s" % polarion_test_case
    prefix = "imported"

    def setUp(self):
        """
        * Create a new template where to clone a vm from
        """
        super(TestCase11987, self).setUp()
        self.template_name = "origial_template_%s" % self.polarion_test_case

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

        assert vms.cloneVmFromTemplate(
            True, self.vm_from_template, self.template_name,
            config.CLUSTER_NAME, vol_sparse=True,
            vol_format=config.COW_DISK)

        assert templates.removeTemplate(True, self.template_name)

    @polarion("RHEVM3-11987")
    def test_export_vm(self):
        """
        * Sanity export from Blank
        * Sanity export from another template
        """
        vmsList = [self.vm_name, self.vm_from_template]

        def export_vm(vm):
            logger.info("Exporting vm %s", vm)
            return vms.exportVm(True, vm, self.export_domain)

        def import_vm(vm):
            logger.info("Verifying vm %s", vm)
            return vms.importVm(
                True, vm, self.export_domain, self.storage_domain,
                config.CLUSTER_NAME, name="%s_%s" % (vm, self.prefix))

        def exec_with_threads(fn):
            execution = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for vm in vmsList:
                    execution.append((vm, executor.submit(fn, vm)))

            for vm, res in execution:
                if res.exception():
                    raise Exception("Failed to execute %s for %s:  %s"
                                    % (fn.__name__, vm, res.exception()))
                if not res.result():
                    raise Exception("Failed to execute %s for %s"
                                    % (fn.__name__, vm))
        exec_with_threads(export_vm)
        exec_with_threads(import_vm)

    def tearDown(self):
        """
        * Remove import and exported vms
        """
        super(TestCase11987, self).tearDown()
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain)
        assert vms.removeVmFromExportDomain(
            True, self.vm_from_template, config.CLUSTER_NAME,
            self.export_domain)
        vmsList = ",".join(["%s_%s" % (vm, self.prefix) for vm in
                           [self.vm_name, self.vm_from_template]]
                           + [self.vm_from_template])
        assert vms.removeVms(True, vmsList)
