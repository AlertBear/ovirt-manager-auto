"""
Import more than one vm/template
Polarion case 11588
"""
import pytest
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    templates as ll_templates,
)
from art.test_handler.tools import polarion
from art.unittest_lib import StorageTest as TestCase, attr
from art.unittest_lib.common import testflow
from rhevmtests.storage.storage_full_import_export.fixtures import (
    initialize_export_domain_param, initialize_vm_and_template_names,
    initialize_first_template_name,
)
from rhevmtests.storage.fixtures import (
    create_vm, create_template, export_vm, export_template,
    remove_vm_from_export_domain, remove_vms,
    remove_template_from_export_domain, remove_templates,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa


@pytest.mark.usefixtures(
    initialize_export_domain_param.__name__,
    initialize_vm_and_template_names.__name__,
    create_vm.__name__,
    initialize_first_template_name.__name__,
    create_template.__name__,
    export_vm.__name__,
    export_template.__name__,
    remove_vms.__name__,
    remove_templates.__name__,
    remove_vm_from_export_domain.__name__,
    remove_template_from_export_domain.__name__,
)
class TestCase11588(TestCase):
    """
    Test Case 11588 - Import more than once

    * Import the same VM twice
    * Import the same template twice
    * Create 2 VMs from both imported templates
    * Remove VMs and templates
    ** Verify all operations pass

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11588'

    deep_copy = True
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain gets stuck

    @polarion("RHEVM3-11588")
    @attr(tier=2)
    def test_import_more_than_once(self):
        """
        Import a vm and a template more than once and make sure it works
        """
        self.templates_names.append(self.template_name)

        for vm_import in [self.from_vm1, self.from_vm2]:
            testflow.step(
                "Importing VM %s from %s with name %s",
                self.vm_name, self.export_domain, vm_import
            )
            assert ll_vms.importVm(
                True, self.vm_name, self.export_domain, self.storage_domain,
                config.CLUSTER_NAME, vm_import, async=True
            ), "Failed to import VN %s with name %s" % (
                self.vm_name, vm_import
            )
            self.vm_names.append(vm_import)

        for vm_name in [self.from_vm1, self.from_vm2]:
            assert ll_vms.waitForVMState(vm_name, config.VM_DOWN), (
                "VM %s was not created successfully" % vm_name
            )

        for template_import in [self.from_template1, self.from_template2]:
            testflow.step(
                "Importing template %s from %s with name %s",
                self.template_name, self.export_domain, template_import
            )
            assert ll_templates.import_template(
                True, self.template_name, self.export_domain,
                self.storage_domain, cluster=config.CLUSTER_NAME,
                name=template_import, async=True
            ), "Failed to import template %s with name %s" % (
                self.template_name, template_import
            )
            self.templates_names.append(template_import)

        assert ll_templates.waitForTemplatesStates(
            names=",".join([self.from_template1, self.from_template2])
        ), "Templates %s and %s were not created successfully" % (
            self.from_template1, self.from_template2
        )

        testflow.step("Start VMs %s", [self.from_vm1, self.from_vm2])
        ll_vms.start_vms([self.from_vm1, self.from_vm2])

        for template, vm in zip(
            [self.from_template1, self.from_template2],
            [self.vm_cloned1, self.vm_cloned2]
        ):
            testflow.step("Cloning VM %s from template %s", vm, template)
            assert ll_vms.cloneVmFromTemplate(
                True, vm, template, config.CLUSTER_NAME,
                vol_sparse=True, vol_format=config.COW_DISK, wait=False
            ), "Failed to clone VM %s from %s" % (vm, template)
            self.vm_names.append(vm)

        for vm_name in [self.vm_cloned1, self.vm_cloned2]:
            assert ll_vms.waitForVMState(vm_name, config.VM_DOWN), (
                "VM %s was not created successfully" % vm_name
            )

        testflow.step("Start VMs %s", [self.vm_cloned1, self.vm_cloned2])
        ll_vms.start_vms([self.vm_cloned1, self.vm_cloned2])
