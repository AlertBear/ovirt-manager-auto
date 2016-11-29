"""
Export/import test cases
"""
import logging
import config
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.test_handler import exceptions
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, StorageTest as TestCase
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
BLANK_TEMPLATE_ID = "00000000-0000-0000-0000-000000000000"
MAX_WORKERS = config.MAX_WORKERS


class BaseExportImportTestCase(TestCase):
    """
    Base TestCase for export/import.
    Creates one vm
    """
    __test__ = False
    polarion_test_case = ''
    vm_type = config.VM_TYPE_SERVER

    def setUp(self):
        """
        Creates a vm and shuts it down
        """
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        export_domains = ll_sd.findExportStorageDomains(
            config.DATA_CENTER_NAME
        )
        if not export_domains:
            raise exceptions.StorageDomainException(
                "No Export storage domains were found in Data center '%s'" %
                config.DATA_CENTER_NAME
            )
        self.export_domain = export_domains[0]
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        logger.info("Creating vm %s with type %s", self.vm_name, self.vm_type)
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['type'] = self.vm_type
        vm_args['installation'] = False
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )

    def tearDown(self):
        """
        Removes vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            logger.error("Failed to remove VM %s", self.vm_name)
            BaseExportImportTestCase.test_failed = True
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        BaseExportImportTestCase.teardown_exception()


@attr(tier=2)
class TestCase11976(BaseExportImportTestCase):
    """
    Test Force Override option
    """
    __test__ = True
    polarion_test_case = '11976'
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain stucks

    def setUp(self):
        """
        Creates a template from the vm
        """
        super(TestCase11976, self).setUp()
        self.template_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
        )
        if not ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        ):
            raise exceptions.TemplateException(
                "Failed to create template %s", self.template_name
            )

    @bz({'1365384': {}})
    @polarion("RHEVM3-11976")
    def test_import_force_override(self):
        """
        Export VM with force override enabled/disabled
        Export template with force override enabled/disabled
        """
        logger.info(
            "Exporting VM %s with force override enabled should "
            "succeed when there's no VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true'
        ), "Exporting VM %s with force override enabled failed" % self.vm_name

        logger.info(
            "Exporting VM %s with force override disabled should fail "
            "when there's a VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            False, self.vm_name, self.export_domain, exclusive='false'
        ), (
            "Exporting VM %s with force override disabled succeeded although "
            "the VM already exists in the export domain" % self.vm_name
        )

        logger.info(
            "Exporting VM %s with force override enabled should "
            "succeed when there's a VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true'
        ), "Exporting VM %s with force override enabled failed" % self.vm_name

        logger.info(
            "Exporting template %s with force override enabled "
            "should succeed when there's not a template in the "
            "export domain", self.template_name
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true'
        ), "Exporting template %s with force override failed" % (
            self.template_name
        )

        logger.info(
            "Exporting template %s with force override disabled should"
            " fail because there's a template in the export domain",
            self.template_name
        )
        assert ll_templates.exportTemplate(
            False, self.template_name, self.export_domain,
            exclusive='false'
        ), (
            "Exporting template %s with force override disabled succeeded "
            "although the template already exists in the export domain" %
            self.template_name
        )

        logger.info(
            "Exporting template %s with force override enabled should "
            "succeed when there's a template in the export domain",
            self.template_name
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true'
        ), "Exporting template %s with force override enabled failed" % (
            self.template_name
        )

    def tearDown(self):
        """
        Remove existing VM/templates and from the export domain
        """
        if not ll_templates.removeTemplateFromExportDomain(
            True, self.template_name, self.export_domain
        ):
            logger.error(
                "Failed to remove template %s from export domain",
                self.template_name
            )
            BaseExportImportTestCase.test_failed = True

        if not ll_vms.remove_vm_from_export_domain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain
        ):
            logger.error(
                "Failed to remove VM %s from export domain", self.vm_name
            )
            BaseExportImportTestCase.test_failed = True

        if not ll_templates.removeTemplate(True, self.template_name):
            logger.error("Failed to remove template %s", self.template_name)
            BaseExportImportTestCase.test_failed = True

        ll_jobs.wait_for_jobs([config.JOB_REMOVE_TEMPLATE])
        super(TestCase11976, self).tearDown()


@attr(tier=2)
class TestCase11995(BaseExportImportTestCase):
    """
    Collapse Snapshots
    """
    __test__ = True
    polarion_test_case = '11995'
    snap_desc = 'snap_%s' % polarion_test_case

    @polarion("RHEVM3-11995")
    def test_collapse_snapshots(self):
        """
        Test export/import with collapse snapshots option works
        """
        self.imported_vm = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        logger.info("Add snapshot to VM %s", self.vm_name)
        assert ll_vms.addSnapshot(True, self.vm_name, self.snap_desc), (
            "Failed to add snapshot to %s" % self.vm_name
        )

        logger.info(
            "Exporting vm %s with collapse snapshots enabled", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain,
            discard_snapshots='true'
        ), "Exporting vm %s with collapse snapshots enabled failed" % (
            self.vm_name
        )

        logger.info("Importing vm with collapse snapshots enabled")
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME, name=self.imported_vm
        ), "Importing vm with collapse snapshots enabled failed"

        logger.info("Powering on VM %s should work")
        assert ll_vms.startVm(True, self.imported_vm), (
            "Failed to power on VM %s" % self.imported_vm
        )

        logger.info("Template for vm %s should be Blank", self.imported_vm)
        assert ll_vms.getVmTemplateId(self.imported_vm) == BLANK_TEMPLATE_ID

        logger.info("Number of snapshots is only one")
        assert len(ll_vms._getVmSnapshots(self.imported_vm, False)) == 1

    def tearDown(self):
        """
        Remove newly Vm imported
        """
        if not ll_vms.safely_remove_vms([self.imported_vm]):
            logger.error("Failed to remove VM %s", self.imported_vm)
            BaseExportImportTestCase.test_failed = True
        if not ll_vms.remove_vm_from_export_domain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain
        ):
            logger.error(
                "Failed to remove VM %s from export domain", self.imported_vm
            )
            BaseExportImportTestCase.test_failed = True
        super(TestCase11995, self).tearDown()


@attr(tier=1)
class TestCase11987(BaseExportImportTestCase):
    """
    Export a VM sanity
    Test import from Blank and from template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_VM_Import_Export_Sanity
    """
    __test__ = True
    polarion_test_case = '11987'
    vm_from_template = "vm_from_template_%s" % polarion_test_case
    prefix = "imported"
    # Bugzilla history:
    # 1269948: Failed to import VM / VM Template

    def setUp(self):
        """
        Create a new template where to clone a vm from
        """
        super(TestCase11987, self).setUp()
        self.template_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
        )

        if not ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        ):
            raise exceptions.TemplateException(
                "Failed to create template %s" % self.template_name
            )

        if not ll_vms.cloneVmFromTemplate(
            True, self.vm_from_template, self.template_name,
            config.CLUSTER_NAME, vol_sparse=True, vol_format=config.COW_DISK
        ):
            raise exceptions.VMException(
                "Failed to clone VM %s from template %s" %
                (self.vm_from_template, self.template_name)
            )

        if not ll_templates.removeTemplate(True, self.template_name):
            raise exceptions.TemplateException(
                "Failed to remove template %s" % self.template_name
            )

    @polarion("RHEVM3-11987")
    def test_export_vm(self):
        """
        Sanity export from Blank
        Sanity export from another template
        """
        vms_list = [self.vm_name, self.vm_from_template]

        def export_vm(vm):
            logger.info("Exporting vm %s", vm)
            return ll_vms.exportVm(True, vm, self.export_domain, async=True)

        def import_vm(vm):
            logger.info("Verifying vm %s", vm)
            return ll_vms.importVm(
                True, vm, self.export_domain, self.storage_domain,
                config.CLUSTER_NAME, name="%s_%s" % (vm, self.prefix),
                async=True
            )

        for vm in vms_list:
            export_vm(vm)
        ll_jobs.wait_for_jobs([config.JOB_EXPORT_VM])
        logger.info("Removing existing vm %s", self.vm_name)
        assert ll_vms.removeVm(
            True, self.vm_name, wait=True
        ), "Failed to remove VM %s" % self.vm_name
        for vm in vms_list:
            import_vm(vm)
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_VM])

    def tearDown(self):
        """
        Remove import and exported vms
        """
        if not ll_vms.remove_vm_from_export_domain(
            True, self.vm_name, config.CLUSTER_NAME, self.export_domain
        ):
            logger.error(
                "Failed to remove VM %s from export domain", self.vm_name
            )
            BaseExportImportTestCase.test_failed = True

        if not ll_vms.remove_vm_from_export_domain(
            True, self.vm_from_template, config.CLUSTER_NAME,
            self.export_domain
        ):
            logger.error(
                "Failed to remove VM %s from export domain", self.imported_vm
            )
            BaseExportImportTestCase.test_failed = True

        vms_list = [
            "%s_%s" % (vm, self.prefix) for vm in [
                self.vm_name, self.vm_from_template
            ]
        ] + [self.vm_from_template]
        if not ll_vms.safely_remove_vms(vms_list):
            logger.error(
                "Failed to remove VM %s from export domain", ','.join(vms_list)
            )
            BaseExportImportTestCase.test_failed = True
        BaseExportImportTestCase.teardown_exception()


@attr(tier=2)
class TestCase11986(BaseExportImportTestCase):
    """
    Export a template sanity
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_VM_Import_Export_Sanity
    """
    __test__ = True
    polarion_test_case = '11986'
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain stucks

    def setUp(self):
        """
        Create a new template which will be used to clone a vm
        """
        super(TestCase11986, self).setUp()
        self.template_name = "original_template_%s" % self.polarion_test_case

        if not ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        ):
            raise exceptions.TemplateException(
                "Failed to create template %s" % self.template_name
            )

    @polarion("RHEVM3-11986")
    def test_export_template(self):
        """
        Export template to an export domain
        """
        logger.info(
            "Exporting template %s to export domain %s", self.template_name,
            self.export_domain
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain
        ), "Failed to export template %s to %s" % (
            self.template_name, self.export_domain
        )

    def tearDown(self):
        """
        Remove exported template
        """
        if not ll_templates.removeTemplateFromExportDomain(
                True, self.template_name, self.export_domain
        ):
            self.test_failed = True
            logger.error(
                "Failed to remove template %s from export domain",
                self.template_name
            )

        if not ll_templates.removeTemplate(True, self.template_name):
            self.test_failed = True
            logger.error("Failed to remove template %s", self.template_name)

        ll_jobs.wait_for_jobs([config.JOB_REMOVE_TEMPLATE])
        super(TestCase11986, self).tearDown()
