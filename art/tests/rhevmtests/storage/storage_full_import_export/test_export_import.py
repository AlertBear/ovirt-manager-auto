"""
Export/import test cases
"""
import pytest
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    templates as ll_templates,
    vms as ll_vms,
)
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, StorageTest as TestCase
from art.unittest_lib.common import testflow
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.storage_full_import_export.fixtures import (
    initialize_export_domain_param, remove_template_setup,
    remove_second_vm_from_export_domain,
)
from rhevmtests.storage.fixtures import (
    create_vm, create_template, remove_vm_from_export_domain, remove_vms,
    remove_template_from_export_domain, clone_vm_from_template
)
from rhevmtests.storage.fixtures import remove_vm  # noqa


@pytest.mark.usefixtures(
    initialize_export_domain_param.__name__,
    create_vm.__name__,
)
class BaseExportImportTestCase(TestCase):
    """
    Base TestCase for export/import.
    Creates one vm
    """
    __test__ = False
    polarion_test_case = ''
    # vm_type = config.VM_TYPE_SERVER
    installation = False
    vm_args = {'type': config.VM_TYPE_SERVER}


@pytest.mark.usefixtures(
    create_template.__name__,
    remove_template_from_export_domain.__name__,
    remove_vm_from_export_domain.__name__
)
class TestCase11976(BaseExportImportTestCase):
    """
    Test Force Override option
    """
    __test__ = True
    polarion_test_case = '11976'
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain stucks

    @bz({'1365384': {}})
    @polarion("RHEVM3-11976")
    @attr(tier=2)
    def test_import_force_override(self):
        """
        Export VM with force override enabled/disabled
        Export template with force override enabled/disabled
        """
        testflow.step(
            "Exporting VM %s with force override enabled should "
            "succeed when there's no VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true'
        ), "Exporting VM %s with force override enabled failed" % self.vm_name

        testflow.step(
            "Exporting VM %s with force override disabled should fail "
            "when there's a VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            False, self.vm_name, self.export_domain, exclusive='false'
        ), (
            "Exporting VM %s with force override disabled succeeded although "
            "the VM already exists in the export domain" % self.vm_name
        )

        testflow.step(
            "Exporting VM %s with force override enabled should "
            "succeed when there's a VM in the export domain", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain, exclusive='true'
        ), "Exporting VM %s with force override enabled failed" % self.vm_name

        testflow.step(
            "Exporting template %s with force override enabled "
            "should succeed when there's not a template in the "
            "export domain", self.template_name
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true'
        ), "Exporting template %s with force override failed" % (
            self.template_name
        )

        testflow.step(
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

        testflow.step(
            "Exporting template %s with force override enabled should "
            "succeed when there's a template in the export domain",
            self.template_name
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, exclusive='true'
        ), "Exporting template %s with force override enabled failed" % (
            self.template_name
        )


@pytest.mark.usefixtures(
    remove_vm_from_export_domain.__name__,
    remove_vms.__name__,
)
class TestCase11995(BaseExportImportTestCase):
    """
    Collapse Snapshots
    """
    __test__ = True
    polarion_test_case = '11995'
    snap_desc = 'snap_%s' % polarion_test_case

    @polarion("RHEVM3-11995")
    @attr(tier=2)
    def test_collapse_snapshots(self):
        """
        Test export/import with collapse snapshots option works
        """
        self.imported_vm = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        testflow.step("Add snapshot to VM %s", self.vm_name)
        assert ll_vms.addSnapshot(True, self.vm_name, self.snap_desc), (
            "Failed to add snapshot to %s" % self.vm_name
        )

        testflow.step(
            "Exporting VM %s with collapse snapshots enabled", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, self.export_domain,
            discard_snapshots='true'
        ), "Exporting vm %s with collapse snapshots enabled failed" % (
            self.vm_name
        )

        testflow.step(
            "Importing VM %s with collapse snapshots enabled with name %s",
            self.vm_name, self.imported_vm
        )
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME, name=self.imported_vm
        ), "Importing vm with collapse snapshots enabled failed"

        self.vm_names.append(self.imported_vm)

        testflow.step("Start VM %s", self.imported_vm)
        assert ll_vms.startVm(True, self.imported_vm), (
            "Failed to power on VM %s" % self.imported_vm
        )

        testflow.step("Verify VM %s template is Blank", self.imported_vm)
        assert (
            ll_vms.getVmTemplateId(
                self.imported_vm
            ) == config.BLANK_TEMPLATE_ID
        ), "Template ID of VM %s is not blank" % self.imported_vm

        testflow.step(
            "Verify VM %s number of snapshots is one",  self.imported_vm
        )
        assert len(ll_vms._getVmSnapshots(self.imported_vm, False)) == 1, (
            "VM %s number of snapshots is not one" % self.imported_vm
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_template.__name__,
    clone_vm_from_template.__name__,
    remove_template_setup.__name__,
    remove_vm_from_export_domain.__name__,
    remove_second_vm_from_export_domain.__name__,
    remove_vms.__name__,
)
class TestCase11987(BaseExportImportTestCase):
    """
    Export a VM sanity
    Test import from Blank and from template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/2_3_Storage_VM_Import_Export_Sanity
    """
    __test__ = True
    polarion_test_case = '11987'
    prefix = "imported"
    # Bugzilla history:
    # 1269948: Failed to import VM / VM Template

    @polarion("RHEVM3-11987")
    @attr(tier=1)
    def test_export_vm(self):
        """
        Sanity export from Blank
        Sanity export from another template
        """
        vms_list = [self.vm_name, self.vm_from_template]

        def export_vm(vm):
            return ll_vms.exportVm(True, vm, self.export_domain, async=True)

        def import_vm(vm, imported_name):
            return ll_vms.importVm(
                True, vm, self.export_domain, self.storage_domain,
                config.CLUSTER_NAME, name=imported_name,
                async=True
            )

        for vm in vms_list:
            testflow.step(
                "Export VM %s to export domain %s", vm, self.export_domain
            )
            assert export_vm(vm), "Failed to export VM %s" % vm
        ll_jobs.wait_for_jobs([config.JOB_EXPORT_VM])

        testflow.step("Removing existing VM %s", self.vm_name)
        assert ll_vms.removeVm(
            True, self.vm_name, wait=True
        ), "Failed to remove VM %s" % self.vm_name
        for vm in vms_list:
            name = "%s_%s" % (vm, self.prefix)
            testflow.step(
                "Import VM %s from export domain %s with name %s",
                vm, self.export_domain, name
            )
            assert import_vm(vm, imported_name=name), (
                "Failed to import VM %s with name %s" % (vm, name)
            )
            self.vm_names.append(name)
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_VM])
        self.vm_names.append(self.vm_from_template)


@pytest.mark.usefixtures(
    create_template.__name__,
    remove_template_from_export_domain.__name__,
)
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

    @polarion("RHEVM3-11986")
    @attr(tier=2)
    def test_export_template(self):
        """
        Export template to an export domain
        """
        testflow.step(
            "Exporting template %s to export domain %s", self.template_name,
            self.export_domain
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain
        ), "Failed to export template %s to %s" % (
            self.template_name, self.export_domain
        )
