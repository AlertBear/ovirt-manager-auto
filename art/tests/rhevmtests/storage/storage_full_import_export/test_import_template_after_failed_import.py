"""
Test exposing BZ 908327, checks if roll-back of the import removes
already imported disks - if it doesn't, the second import will fail
"""
import config
import logging
from art.test_handler import exceptions
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler.tools import polarion
import rhevmtests.storage.helpers as helpers

logger = logging.getLogger(__name__)
GB = config.GB

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


@attr(tier=4)
class TestCase11628(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=908327
    scenario:
    * create a template with two disks of different sizes
    * export the template
    * start importing the template
    * fail the import by restarting vdsm daemon
    * try to import the template once again

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Bug_Coverage
    """
    __test__ = not config.GOLDEN_ENV
    polarion_test_case = '11628'
    vm_name = "vm_%s" % polarion_test_case
    templ_name = "templ_%s" % polarion_test_case

    def setUp(self):
        """
        creates a template with 2 disks of different sizes
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]

        logger.info("Create a VM")
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.storage_domain
        vm_args['vmName'] = self.vm_name
        vm_args['installation'] = False
        vm_args['start'] = 'false'

        if not helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )

        logger.info("Create second VM disk")
        disk_name, disk_size = "disk_%s_1" % self.polarion_test_case, GB

        assert disks.addDisk(
            True, alias=disk_name, shareable=False,
            bootable=False, provisioned_size=disk_size,
            storagedomain=self.storage_domain, sparse=False,
            format=config.RAW_DISK, interface=config.INTERFACE_IDE
        )

        assert disks.wait_for_disks_status(disk_name)

        assert disks.attachDisk(True, disk_name, self.vm_name)

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.templ_name)

        logger.info("Remove the VM")
        assert vms.removeVm(True, self.vm_name)

    @polarion("RHEVM3-11628")
    def test_import_template_after_failed_import(self):
        """
        * exports the template
        * removes the original template
        * starts importing the template
        * during the import restarts vdsm
        * tries to import the template again
        """

        logger.info("Export the template")
        assert templates.exportTemplate(
            True, self.templ_name, self.export_domain, wait=True)

        assert templates.removeTemplate(True, self.templ_name)

        logger.info("Get SPM and password")
        host = hosts.getSPMHost(config.HOSTS)
        host_ip = hosts.getHostIP(host)

        logger.info("Start importing template")
        assert templates.import_template(
            True, self.templ_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME, async=True)

        logger.info("Waiting for migration to start")
        # importing should start right away, timeout=10 is more than enough
        assert templates.waitForTemplatesStates(
            self.templ_name, state=ENUMS['template_state_locked'],
            timeout=10, sleep=1)

        logger.info("Restarting VDSM")
        assert test_utils.restartVdsmd(host_ip, config.HOSTS_PW)

        logger.info("Waiting for host %s to be down", host)
        assert hosts.waitForHostsStates(False, host)

        logger.info("Waiting for host %s to get up", host)
        assert hosts.waitForHostsStates(True, host)

        logger.info("Wait until import fail")
        assert templates.waitForTemplatesGone(True, self.templ_name,
                                              timeout=1200)

        logger.info("Importing second time")
        assert templates.import_template(
            True, self.templ_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME)

    def tearDown(self):
        """
        * Removing template
        """
        wait_for_jobs([ENUMS['job_import_vm_template']])
        templates.removeTemplate(True, self.templ_name)
