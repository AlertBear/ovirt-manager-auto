"""
Test exposing BZ 890922, checks if roll-back of the import removes
already imported disks - if it doesn't, the second import will fail
"""
import config
import logging
from art.unittest_lib.common import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import (
    disks, vms, hosts, storagedomains,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.storage.helpers as helpers

logger = logging.getLogger(__name__)
GB = config.GB
ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


@attr(tier=4)
class TestCase11627(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=890922
    scenario:
    * create a VM with two disks of different sizes
    * export the VM
    * start importing the VM
    * fail the import by restarting vdsm daemon
    * try to import the VM once again

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_Bug_Coverage
    """
    __test__ = True
    polarion_test_case = '11627'
    vm_name = "vm_%s" % polarion_test_case

    def setUp(self):
        """
        * creates a VM and installs an OS on it
        * adds second, much smaller disk to it
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]

        logger.info("Create a VM")
        assert helpers.create_vm(
            self.vm_name, storage_domain=self.storage_domain
        )
        assert vms.shutdownVm(True, self.vm_name, 'false')

        logger.info("Create second VM disk")
        disk_name, disk_size = "disk_%s_1" % self.polarion_test_case, GB

        assert disks.addDisk(
            True, alias=disk_name, shareable=False, bootable=False,
            size=disk_size, storagedomain=self.storage_domain, sparse=False,
            format=config.RAW_DISK, interface=config.INTERFACE_IDE)

        assert disks.wait_for_disks_status(disk_name)

        assert disks.attachDisk(True, disk_name, self.vm_name)

    @polarion("RHEVM3-11627")
    def test_import_vm_after_failed_import(self):
        """
        * exports the VM
        * removes the original VM
        * starts importing the VM
        * during the import restarts vdsm
        * tries to import the VM again
        """
        logger.info("Export the VM")
        assert vms.exportVm(True, self.vm_name, self.export_domain)

        logger.info("Remove the VM")
        assert vms.removeVm(True, self.vm_name)
        assert vms.waitForVmsGone(True, self.vm_name)

        logger.info("Get SPM and password")
        host = hosts.getSPMHost(config.HOSTS)
        host_ip = hosts.getHostIP(host)

        logger.info("Start importing VM")
        assert vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME, async=True)

        assert vms.waitForVMState(self.vm_name, ENUMS['vm_state_image_locked'])
        logger.info("Restarting VDSM")
        assert test_utils.restartVdsmd(host_ip, config.HOSTS_PW)
        logger.info("Waiting for host %s (%s) to get up", host, host_ip)
        assert hosts.waitForHostsStates(True, host)

        logger.info("Wait until import fail")
        assert vms.waitForVmsGone(True, self.vm_name, timeout=300)

        logger.info("Importing second time")
        assert vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            config.CLUSTER_NAME)

    def tearDown(self):
        """
        * Remove Vm
        """
        logger.info("Waiting for jobs")
        wait_for_jobs([ENUMS['job_import_vm']])
        logger.info("Removing vm %s from DC and from the export domain",
                    self.vm_name)
        vms.removeVm(True, self.vm_name)
        vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain)
