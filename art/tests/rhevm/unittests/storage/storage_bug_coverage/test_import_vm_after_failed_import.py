"""
Test exposing BZ 890922, checks if roll-back of the import removes
already imported disks - if it doesn't, the second import will fail
"""
import time

import logging
from nose.tools import istest
from unittest import TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.tools import tcms

import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)


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
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']

        LOGGER.info("Create a VM")
        assert vms.createVm(
            True, self.vm_name, self.vm_name, config.CLUSTER_NAME,
            storageDomainName=master_domain, size=config.DISK_SIZE,
            installation=True, diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_DESKTOP,
            slim=True, cobblerAddress=config.COBBLER_ADDRESS,
            cobblerUser=config.COBBLER_USER, nic=config.HOST_NICS[0],
            cobblerPasswd=config.COBBLER_PASSWORD, volumeType=False,
            volumeFormat=ENUMS['format_raw'], useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE)
        assert vms.shutdownVm(True, self.vm_name, 'false')

        LOGGER.info("Create second VM disk")
        disk_1 = ("disk_%s_1" % self.tcms_test_case, GB)

        for (disk_name, disk_size) in [disk_1]:
            assert disks.addDisk(
                True, alias=disk_name, shareable=False, bootable=False,
                size=disk_size, storagedomain=master_domain, sparse=False,
                format=ENUMS['format_raw'], interface=ENUMS['interface_ide'])

        assert disks.waitForDisksState(disk_1[0])

        for (disk_name, _) in [disk_1]:
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
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']

        export_domain = "export_domain"

        LOGGER.info("Export the VM")
        assert vms.exportVm(True, self.vm_name, export_domain)

        LOGGER.info("Remove the VM")
        assert vms.removeVm(True, self.vm_name)
        assert vms.waitForVmsGone(True, self.vm_name)

        LOGGER.info("Get SPM and password")
        host = hosts.getSPMHost(config.HOSTS)
        password = None
        for h, p in zip(config.HOSTS, config.PASSWORDS):
            if h == host:
                password = p

        LOGGER.info("Start importing VM")
        assert vms.importVm(
            True, self.vm_name, export_domain, master_domain,
            config.CLUSTER_NAME, async=True)

        time.sleep(60)
        LOGGER.info("Restarting VDSM")
        test_utils.restartVdsmd(host, password)
        time.sleep(60)  # give vdsm time for restart

        LOGGER.info("Wait until import fail")
        assert vms.waitForVmsGone(True, self.vm_name, timeout=300)

        LOGGER.info("Importing second time")
        assert vms.importVm(
            True, self.vm_name, export_domain, master_domain,
            config.CLUSTER_NAME)

    def tearDown(self):
        vms.removeVm(True, self.vm_name)
