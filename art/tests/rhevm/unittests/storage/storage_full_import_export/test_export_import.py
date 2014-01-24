"""
Export/import test cases
"""
import config
import logging

from concurrent.futures import ThreadPoolExecutor
from nose.tools import istest
from unittest import TestCase

from art.test_handler.tools import tcms, bz
from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates

from common import _create_vm

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
BLANK_TEMPLATE_ID = "00000000-0000-0000-0000-000000000000"
TCMS_PLAN_ID = '2092'
MAX_WORKERS = config.MAX_WORKERS

# Remove this part when is integrated in stories
# http://rhevm-qe-storage.pad.engineering.redhat.com/11
#class TestCase41240(TestCase):
#    """ Attacht export domain, verify it works


class BaseExportImportTestCase(TestCase):
    """
    Base TestCase for export/import.
    * Creates one vm
    """
    __test__ = False
    tcms_test_case = ''
    vm_type = config.VM_TYPE_SERVER

    def setUp(self):
        """
        * Creates a vm and shuts it down
        """
        self.vm_name = "original_vm_%s" % self.tcms_test_case
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]
        status, domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = domain['masterDomain']

        logger.info("Creating vm %s with type %s", self.vm_name, self.vm_type)
        assert _create_vm(self.vm_name, vm_type=self.vm_type)
        assert vms.shutdownVm(True, self.vm_name, 'false')

    def tearDown(self):
        """
        * Removes vm
        """
        assert vms.removeVm(True, self.vm_name)


class TestCase42054(BaseExportImportTestCase):
    """
    Test Force Override option
    """
    __test__ = True
    tcms_test_case = '42054'

    def setUp(self):
        """
        * Creates a template from the vm
        """
        super(TestCase42054, self).setUp()
        self.template_name = "origial_template_%s" % self.tcms_test_case

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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

        super(TestCase42054, self).tearDown()


class TestCase41256(BaseExportImportTestCase):
    """
    Test Case 41256 -  Collapse Snapshots
    """
    __test__ = True
    tcms_test_case = '41256'
    imported_vm = 'imported_%s' % tcms_test_case

    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
            True, self.vm_name, self.export_domain, self.master_domain,
            config.CLUSTER_NAME, name=self.imported_vm)

        logger.info("Starting vm %s should work")
        assert vms.startVm(True, self.imported_vm)

        logger.info("Template for vm %s should be Blank", self.imported_vm)
        self.assertEqual(vms.getVmTemplateId(self.imported_vm),
                         BLANK_TEMPLATE_ID)

        logger.info("Number of snapshots is only one")
        a = vms._getVmSnapshots(self.imported_vm, False)
        self.assertEqual(len(vms._getVmSnapshots(self.imported_vm, False)), 1)

    def tearDown(self):
        """
        Remove newly Vm imported
        """
        super(TestCase41256, self).tearDown()
        assert vms.removeVm(True, self.imported_vm, stopVM="true")
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain)


class TestCase41242(BaseExportImportTestCase):
    """
    Test case 41242 - Export a VM sanity
    Bugzilla 882632 - Fails to export a VM cloned from a template to a
                      storage domain without the original template
    Test import from Blank and from template
    """
    __test__ = True
    tcms_test_case = '41242'
    vm_from_template = "vm_from_template_%s" % tcms_test_case
    prefix = "imported"

    def setUp(self):
        """
        * Create a new template where to clone a vm from
        """
        super(TestCase41242, self).setUp()
        self.template_name = "origial_template_%s" % self.tcms_test_case

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

        assert vms.cloneVmFromTemplate(
            True, self.vm_from_template, self.template_name,
            config.CLUSTER_NAME, vol_sparse=True,
            vol_format=config.COW_DISK)

        assert templates.removeTemplate(True, self.template_name)

    @bz('882632')
    @tcms(TCMS_PLAN_ID, tcms_test_case)
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
                True, vm, self.export_domain, self.master_domain,
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
        super(TestCase41242, self).tearDown()
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain)
        assert vms.removeVmFromExportDomain(
            True, self.vm_from_template, config.CLUSTER_NAME,
            self.export_domain)
        vmsList = ",".join(["%s_%s" % (vm, self.prefix) for vm in
                           [self.vm_name, self.vm_from_template]]
                           + [self.vm_from_template])
        assert vms.removeVms(True, vmsList)
