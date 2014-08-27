"""
Import more than once vm/template
TCMS case 174617
"""
import config
import logging

from concurrent.futures import ThreadPoolExecutor

from art.unittest_lib import StorageTest as TestCase, attr
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.rhevm_api.utils.test_utils import get_api, setPersistentNetwork
from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates

from common import _create_vm

logger = logging.getLogger(__name__)
GB = config.GB
ENUMS = config.ENUMS
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')


@attr(tier=0)
class TestCase174617(TestCase):
    """
    Test Case 174617 - Import more than once
    Bugzilla 853045 - 500 when exporting/import template/vm

    * Import the same VM twice
    * Import the same template twice
    * Create 2 VMs from both imported templates
    * Remove VMs and templates
    ** Verify all should pass

    https://tcms.engineering.redhat.com/case/174617/
    """
    __test__ = True
    tcms_plan_id = '6458'
    tcms_test_case = '174617'
    vm_name = 'original_%s' % tcms_test_case
    template_name = "template_%s" % tcms_test_case

    from_vm1, from_vm2 = 'vm1_from_vm', 'vm2_from_vm'
    from_template1, from_template2 = 'vm1_from_template', 'vm2_from_template'

    vm_cloned1, vm_cloned2 = 'vm_cloned1', 'vm_cloned2'

    def setUp(self):
        """
        * create one vm and one template
        * export both of them
        * remove them
        """
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]
        status, domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = domain['masterDomain']

        logger.info("Create vm and template")
        assert _create_vm(self.vm_name)
        vm_ip = vms.waitForIP(vm=self.vm_name)[1]['ip']
        assert setPersistentNetwork(vm_ip, config.VM_PASSWORD)
        assert vms.shutdownVm(True, self.vm_name, 'false')
        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

        logger.info("Export vm %s and template %s",
                    self.vm_name, self.template_name)
        assert vms.exportVm(True, self.vm_name, self.export_domain)
        assert templates.exportTemplate(
            True, self.template_name, self.export_domain, wait=True)

        logger.info("Remove vm and template")
        assert vms.removeVm(True, self.vm_name)
        assert templates.removeTemplate(True, self.template_name)

    @bz('1083488')
    @bz('853045')
    @tcms(tcms_plan_id, tcms_test_case)
    def test_import_more_than_once(self):
        """
        Import a vm and a template more than onces and make sure it works
        """
        def inspect_execution(execution):
            """
            Expects a list of tuples, each tuple with name of vm, function and
            execution of the callable
            """
            for vm, fn, res in execution:
                if res.exception():
                    raise Exception("Failed to execute %s for %s: %s"
                                    % (fn.__name__, vm, res.exception()))
                if not res.result():
                    raise Exception("Failed to execute %s for %s"
                                    % (fn.__name__, vm))

        execution = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for new_name in [self.from_vm1, self.from_vm2]:
                logger.info("Importing vm %s from %s to %s",
                            self.vm_name, self.export_domain, new_name)
                execution.append([
                    new_name, vms.importVm,
                    executor.submit(
                        vms.importVm, True, self.vm_name, self.export_domain,
                        self.master_domain, config.CLUSTER_NAME, new_name)])

            for new_name in [self.from_template1, self.from_template2]:
                logger.info("Importing template %s from %s to %s",
                            self.template_name, self.export_domain, new_name)
                execution.append([
                    new_name, templates.importTemplate,
                    executor.submit(
                        templates.importTemplate, True, self.template_name,
                        self.export_domain, self.master_domain,
                        config.CLUSTER_NAME, new_name)])

            inspect_execution(execution)

        logger.info("Start vms just imported")
        vms.start_vms([self.from_vm1, self.from_vm2], config.MAX_WORKERS,
                      wait_for_status=ENUMS['vm_state_up'])

        execution = []
        logger.info("Clone one vm from each template")
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for template, vm in zip([self.from_template1, self.from_template2],
                                    [self.vm_cloned1, self.vm_cloned2]):
                logger.info("Clonning vm %s from template %s", vm, template)
                execution.append([
                    vm, vms.cloneVmFromTemplate,
                    executor.submit(
                        vms.cloneVmFromTemplate, True, vm,
                        template, config.CLUSTER_NAME,
                        vol_sparse=True, vol_format=config.COW_DISK)])

            inspect_execution(execution)

        logger.info("Start those cloned vms")
        vms.start_vms([self.vm_cloned1, self.vm_cloned2], config.MAX_WORKERS,
                      wait_for_status=ENUMS['vm_state_up'])

    def tearDown(self):
        """
        * Remove vms/template created
        """
        logger.info("Removing vms and templates")
        vmsList = ",".join([self.from_vm1, self.from_vm2,
                           self.vm_cloned1, self.vm_cloned2])
        vms.removeVms(True, vmsList, stop='true')

        templatesList = ",".join([self.from_template1, self.from_template2])
        templates.removeTemplates(True, templatesList)

        logger.info("Remove vms and templates from the export domain")
        vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain)
        templates.removeTemplateFromExportDomain(
            True, self.template_name, config.DATA_CENTER_NAME,
            self.export_domain)
