"""
Test exposing BZ 908327, checks if roll-back of the import removes
already imported disks - if it doesn't, the second import will fail

"""
import config
import logging

from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.tools import tcms, bz

from common import _create_vm

LOGGER = logging.getLogger(__name__)
GB = config.GB

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


@attr(tier=2)
class TestCase281164(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=908327
    scenario:
    * create a template with two disks of different sizes
    * export the template
    * start importing the template
    * fail the import by restarting vdsm daemon
    * try to import the template once again

    https://tcms.engineering.redhat.com/case/281164/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '281164'
    vm_name = "vm_%s" % tcms_test_case
    templ_name = "templ_%s" % tcms_test_case

    def setUp(self):
        """
        creates a template with 2 disks of different sizes
        """
        status, domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = domain['masterDomain']
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]

        LOGGER.info("Create a VM")
        assert _create_vm(self.vm_name)
        assert vms.shutdownVm(True, self.vm_name, 'false')

        LOGGER.info("Create second VM disk")
        disk_name, disk_size = "disk_%s_1" % self.tcms_test_case, GB

        assert disks.addDisk(
            True, alias=disk_name, shareable=False, bootable=False,
            size=disk_size, storagedomain=self.master_domain, sparse=False,
            format=config.RAW_DISK, interface=config.INTERFACE_IDE)

        assert disks.waitForDisksState(disk_name)

        assert disks.attachDisk(True, disk_name, self.vm_name)

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.templ_name)

        LOGGER.info("Remove the VM")
        assert vms.removeVm(True, self.vm_name)

    @bz('1072400')
    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def import_template_after_failed_import_test(self):
        """
        * exports the template
        * removes the original template
        * starts importing the template
        * during the import restarts vdsm
        * tries to import the template again
        """

        LOGGER.info("Export the template")
        assert templates.exportTemplate(
            True, self.templ_name, self.export_domain, wait=True)

        assert templates.removeTemplate(True, self.templ_name)

        LOGGER.info("Get SPM and password")
        host = hosts.getSPMHost(config.HOSTS)
        password = None
        for h, p in zip(config.HOSTS, config.PASSWORDS):
            if h == host:
                password = p

        LOGGER.info("Start importing template")
        assert templates.importTemplate(
            True, self.templ_name, self.export_domain, self.master_domain,
            config.CLUSTER_NAME, async=True)

        LOGGER.info("Waiting for migration to start")
        # importing should start right away, timeout=10 is more than enough
        assert templates.waitForTemplatesStates(
            self.templ_name, state=ENUMS['template_state_locked'],
            timeout=10, sleep=1)

        LOGGER.info("Restarting VDSM")
        assert test_utils.restartVdsmd(host, password)

        LOGGER.info("Waiting for host %s to be down", host)
        assert hosts.waitForHostsStates(False, host)

        LOGGER.info("Waiting for host %s to get up", host)
        assert hosts.waitForHostsStates(True, host)

        LOGGER.info("Wait until import fail")
        assert templates.waitForTemplatesGone(True, self.templ_name)

        LOGGER.info("Importing second time")
        assert templates.importTemplate(
            True, self.templ_name, self.export_domain, self.master_domain,
            config.CLUSTER_NAME)

    def tearDown(self):
        """
        * Removing template
        """
        templates.removeTemplate(True, self.templ_name)
