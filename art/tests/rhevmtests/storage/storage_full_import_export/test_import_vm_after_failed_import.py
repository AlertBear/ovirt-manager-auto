"""
Test exposing BZ 890922, checks if roll-back of the import removes
already imported disks - if it doesn't, the second import will fail
"""
import config
import logging

from nose.tools import istest
from art.unittest_lib.common import StorageTest as TestCase
from art.unittest_lib import attr

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.tools import tcms

from common import _create_vm

logger = logging.getLogger(__name__)
GB = config.GB
ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


@attr(tier=2)
class TestCase281163(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=890922
    scenario:
    * create a VM with two disks of different sizes
    * export the VM
    * start importing the VM
    * fail the import by restarting vdsm daemon
    * try to import the VM once again

    https://tcms.engineering.redhat.com/case/281163/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '281163'
    vm_name = "vm_%s" % tcms_test_case

    def setUp(self):
        """
        * creates a VM and installs an OS on it
        * adds second, much smaller disk to it
        """
        status, domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert status
        self.master_domain = domain['masterDomain']
        self.export_domain = storagedomains.findExportStorageDomains(
            config.DATA_CENTER_NAME)[0]

        logger.info("Create a VM")
        assert _create_vm(self.vm_name)
        assert vms.shutdownVm(True, self.vm_name, 'false')

        logger.info("Create second VM disk")
        disk_name, disk_size = "disk_%s_1" % self.tcms_test_case, GB

        assert disks.addDisk(
            True, alias=disk_name, shareable=False, bootable=False,
            size=disk_size, storagedomain=self.master_domain, sparse=False,
            format=config.RAW_DISK, interface=config.INTERFACE_IDE)

        assert disks.waitForDisksState(disk_name)

        assert disks.attachDisk(True, disk_name, self.vm_name)

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def import_vm_after_failed_import_test(self):
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
        password = None
        for h, p in zip(config.HOSTS, config.PASSWORDS):
            if h == host:
                password = p

        logger.info("Start importing VM")
        assert vms.importVm(
            True, self.vm_name, self.export_domain, self.master_domain,
            config.CLUSTER_NAME, async=True)

        assert vms.waitForVMState(self.vm_name, ENUMS['vm_state_image_locked'])
        logger.info("Restarting VDSM")
        assert test_utils.restartVdsmd(host, password)
        logger.info("Waiting for host %s to get up", host)
        assert hosts.waitForHostsStates(True, host)

        logger.info("Wait until import fail")
        assert vms.waitForVmsGone(True, self.vm_name, timeout=300)

        logger.info("Importing second time")
        assert vms.importVm(
            True, self.vm_name, self.export_domain, self.master_domain,
            config.CLUSTER_NAME)

    def tearDown(self):
        """
        * Remove Vm
        """
        logger.info("Removing vm %s from DC and from the export domain",
                    self.vm_name)
        vms.removeVm(True, self.vm_name)
        vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain)
