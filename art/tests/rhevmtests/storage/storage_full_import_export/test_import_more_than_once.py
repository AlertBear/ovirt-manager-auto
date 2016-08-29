"""
Import more than one vm/template
Polarion case 11588
"""
import logging

import config
from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms,
    templates as ll_templates,
)
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.unittest_lib import StorageTest as TestCase, attr
from rhevmtests.networking import helper as network_helper
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')


@attr(tier=2)
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
    vm_name = polarion_test_case + '_vm_original'
    from_vm1 = polarion_test_case + '_vm1'
    from_vm2 = polarion_test_case + '_vm2'
    vm_cloned1 = polarion_test_case + '_cloned_vm1'
    vm_cloned2 = polarion_test_case + '_cloned_vm2'
    template_name = polarion_test_case + "_template_original"
    from_template1 = polarion_test_case + '_template1'
    from_template2 = polarion_test_case + '_template2'
    vms_dict = {
        vm_name: False, from_vm1: False, from_vm2: False, vm_cloned1: False,
        vm_cloned2: False
    }
    templates_dict = {
        template_name: False, from_template1: False, from_template2: False
    }
    initial_vm_exported = False
    initial_template_exported = False
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain gets stuck

    def setUp(self):
        """
        * create one vm and one template
        * export both of them
        * remove them
        """
        self.export_domain = ll_sd.findExportStorageDomains(
            config.DATA_CENTER_NAME
        )[0]
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        logger.info("Create vm and template")
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['deep_copy'] = True

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_dict[self.vm_name] = True

        if not network_helper.seal_vm(self.vm_name, config.VM_PASSWORD):
            raise exceptions.NetworkException(
                "Failed to set a persistent network for VM '%s'" % self.vm_name
            )

        if not ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        ):
            raise exceptions.TemplateException(
                "Failed to create template '%s' from VM '%s'" %
                (self.template_name, self.vm_name)
            )
        self.templates_dict[self.template_name] = True

        logger.info("Export vm %s", self.vm_name)
        if not ll_vms.exportVm(True, self.vm_name, self.export_domain):
            raise exceptions.VMException(
                "Failed to export VM '%s' into export domain" % self.vm_name
            )
        self.initial_vm_exported = True

        logger.info("Export template %s", self.template_name)
        if not ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, wait=True
        ):
            raise exceptions.TemplateException(
                "Failed to export template '%s' into export domain" %
                self.template_name
            )
        self.initial_template_exported = True

    @polarion("RHEVM3-11588")
    def test_import_more_than_once(self):
        """
        Import a vm and a template more than once and make sure it works
        """
        for vm_import in [self.from_vm1, self.from_vm2]:
            logger.info(
                "Importing vm %s from %s to vm %s",
                self.vm_name, self.export_domain, vm_import
            )
            ll_vms.importVm(
                True, self.vm_name, self.export_domain, self.storage_domain,
                config.CLUSTER_NAME, vm_import, async=True
            )

        for vm_name in [self.from_vm1, self.from_vm2]:
            if not ll_vms.waitForVMState(vm_name, config.VM_DOWN):
                raise exceptions.VMException(
                    "VM '%s' was not created successfully" % vm_name
                )
            self.vms_dict[vm_name] = True

        for template_import in [self.from_template1, self.from_template2]:
            logger.info(
                "Importing template %s from %s to %s",
                self.template_name, self.export_domain, template_import
            )
            ll_templates.import_template(
                True, self.template_name, self.export_domain,
                self.storage_domain, cluster=config.CLUSTER_NAME,
                name=template_import, async=True
            )

        if not ll_templates.waitForTemplatesStates(
            names=",".join([self.from_template1, self.from_template2])
        ):
            raise exceptions.TemplateException(
                "Templates '%s' and '%s' were not created successfully" %
                (self.from_template1, self.from_template2)
            )
        self.templates_dict[self.from_template1] = True
        self.templates_dict[self.from_template2] = True

        logger.info("Run vms that were just imported")
        ll_vms.start_vms([self.from_vm1, self.from_vm2])

        logger.info("Clone one vm from each template")
        for template, vm in zip([self.from_template1, self.from_template2],
                                [self.vm_cloned1, self.vm_cloned2]):
            logger.info("Cloning vm %s from template %s", vm, template)
            ll_vms.cloneVmFromTemplate(
                True, vm, template, config.CLUSTER_NAME,
                vol_sparse=True, vol_format=config.COW_DISK, wait=False
            )

        for vm_name in [self.vm_cloned1, self.vm_cloned2]:
            if not ll_vms.waitForVMState(vm_name, config.VM_DOWN):
                raise exceptions.VMException(
                    "VM '%s' was not created successfully" % vm_name
                )
            self.vms_dict[vm_name] = True

        logger.info("Start the cloned vms")
        ll_vms.start_vms([self.vm_cloned1, self.vm_cloned2])

    def tearDown(self):
        """
        * Remove vms/templates created
        """
        logger.info("Removing vms created during the test")
        for vm, vm_created in zip(
                self.vms_dict.keys(), self.vms_dict.values()
        ):
            if vm_created:
                if not ll_vms.removeVms(True, vm, stop='true'):
                    TestCase.test_failed = True
                    logger.error("Could not remove VM '%s'", vm)

        logger.info("Removing templates created during the test")
        for template, template_created in zip(
                self.templates_dict.keys(), self.templates_dict.values()
        ):
            if template_created:
                if not ll_templates.removeTemplates(True, template):
                    TestCase.test_failed = True
                    logger.error("Could not remove Template '%s'", template)

        if self.initial_vm_exported:
            logger.info("Remove vm and template created in the export domain")
            if not ll_vms.remove_vm_from_export_domain(
                True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain
            ):
                TestCase.test_failed = True
                logger.error(
                    "Could not remove VM '%s' from export domain", self.vm_name
                )

        if self.initial_template_exported:
            if not ll_templates.removeTemplateFromExportDomain(
                True, self.template_name, self.export_domain
            ):
                TestCase.test_failed = True
                logger.error(
                    "Could not remove Template '%s' from export domain",
                    self.template_name
                )
        self.teardown_exception()
