from art.unittest_lib import StorageTest as TestCase
import logging
import time
from multiprocessing import Process
from art.unittest_lib import attr
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import vms, storagedomains, disks, hosts
from art.rhevm_api.tests_lib.low_level.vms import (
    addDisk, get_vms_disks_storage_domain_name, get_vm_disk_logical_name,
)
from art.rhevm_api.utils import storage_api
from rhevmtests.storage.helpers import perform_dd_to_disk

import config

LOGGER = logging.getLogger(__name__)

TCMS_PLAN_ID = '9852'
DC_TYPE = config.STORAGE_TYPE
FILE_TO_WRITE = "/tmp/resume_guests_tests"

GB = 1024 ** 3

VM_USER = config.VMS_LINUX_USER
VM_PASSWORD = config.VMS_LINUX_PW


def _wait_for_vm_booted(
        vm_name, os_type, user, password, timeout=300, interval=15):
    return vms.checkVMConnectivity(
        True, vm_name, os_type, timeout / interval, interval, user=user,
        password=password, nic=config.NIC_NAME[0])


class TestResumeGuests(TestCase):
    __test__ = False
    vm = "%s_%s" % (config.VM_NAME, TestCase.storage)
    remove_file = False

    def setUp(self):
        """ just start writing
        """
        cmd = "dd of=%s if=/dev/urandom bs=128M oflag=direct &" % FILE_TO_WRITE
        LOGGER.info("Starting writing process")
        assert vms.run_cmd_on_vm(
            self.vm, cmd, VM_USER, VM_PASSWORD)[0]
        self.remove_file = True
        # give it time to really start writing
        time.sleep(10)

    def tearDown(self):
        """ restart the vm (so kill writing process) & remove created file
        """
        # restart vm - this way we will also kill dd
        LOGGER.info("Stopping the VM")
        assert vms.stopVm(True, self.vm)

        LOGGER.info("Starting the VM")
        assert vms.startVm(True, self.vm, config.VM_UP, True)

        if self.remove_file:
            cmd = "rm -f %s" % FILE_TO_WRITE
            LOGGER.info("Removing file %s we were writing to" % FILE_TO_WRITE)
            # big timeout as rm may take a lot of time in case of big files
            assert vms.run_cmd_on_vm(
                self.vm, cmd, VM_USER, VM_PASSWORD, 3600)[0]

    def break_storage(self):
        pass

    def fix_storage(self):
        pass

    def check_vm_paused(self, vm_name):
        assert vms.waitForVMState(
            vm_name, config.ENUMS['vm_state_paused'], timeout=3600)

    def check_vm_unpaused(self, vm_name):
        LOGGER.info("Waiting for VM being up")
        assert vms.waitForVMState(
            vm_name, config.ENUMS['vm_state_up'], timeout=1800)
        LOGGER.info("VM is up, waiting for connectivity")
        assert _wait_for_vm_booted(
            self.vm, config.OS_TYPE, VM_USER,
            VM_PASSWORD)
        LOGGER.info("VM is accessible")

    def run_flow(self):
        LOGGER.info("Breaking storage")
        self.break_storage()
        LOGGER.info("Checking if VM %s is paused", self.vm)
        self.check_vm_paused(self.vm)
        LOGGER.info("Fixing storage")
        self.fix_storage()
        LOGGER.info("Checking if VM %s is unpaused", self.vm)
        self.check_vm_unpaused(self.vm)
        LOGGER.info("Test finished successfully")


class TestCaseBlockedConnection(TestResumeGuests):
    host = None
    sd = None

    def break_storage(self):
        """ block connection from host to storage server
        """
        rc, host = vms.getVmHost(self.vm)
        assert rc
        self.host_ip = hosts.getHostIP(host)
        self.sd = vms.get_vms_disks_storage_domain_name(self.vm)
        self.sd_ip = storagedomains.getDomainAddress(True, self.sd)

        LOGGER.info(
            "Blocking outgoing connection from %s to %s", self.host, self.sd)
        assert storage_api.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip)

    def fix_storage(self):
        """ unblock connection from host to storage server
        """
        LOGGER.info("Unblocking connection from %s to %s", self.host, self.sd)
        assert storage_api.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip)
        self.host = None
        self.sd = None

    def tearDown(self):
        """ additional step in tearDown - unblock connection if it is blocked
        """
        # in case test failed between blocking and unblocking connection
        if self.host and self.sd:
            LOGGER.info(
                "Unblocking connection from %s to %s", self.host, self.sd)
            assert storage_api.unblockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip)
        super(TestCaseBlockedConnection, self).tearDown()


class TestNoSpaceLeftOnDevice(TestResumeGuests):
    big_disk_name = "big_disk_eio"
    left_space = int(1.5 * GB)

    def break_storage(self):
        """ create a very big disk on the storage domain
        """
        self.sd = vms.get_vms_disks_storage_domain_name(self.vm)
        domain = storagedomains.util.find(self.sd)
        LOGGER.info("Master domain: %s", self.sd)
        sd_size = domain.available
        LOGGER.info("Available space: %s", sd_size)
        disk_size = int(domain.available) - self.left_space
        LOGGER.info("Disk size: %s", disk_size)
        assert disks.addDisk(
            True, alias=self.big_disk_name, size=disk_size,
            storagedomain=self.sd, format=config.ENUMS['format_raw'],
            interface=config.INTERFACE_VIRTIO, sparse=False)

        disks.wait_for_disks_status(self.big_disk_name, timeout=3600)

        LOGGER.info("Big disk created")

    def fix_storage(self):
        """ delete created big disk
        """
        LOGGER.info("Delete big disk")
        assert disks.deleteDisk(True, self.big_disk_name)

    def tearDown(self):
        """ additional step in tearDown - remove big disk
        """
        LOGGER.info("Tear down - removing disk if needed")
        disk_names = [
            x.alias for x in disks.getStorageDomainDisks(self.sd, False)]
        LOGGER.info("All disks: %s" % disk_names)
        if self.big_disk_name in disk_names:
            disks.deleteDisk(True, self.big_disk_name)
        LOGGER.info("Upper tear down")
        super(TestNoSpaceLeftOnDevice, self).tearDown()


@attr(tier=3)
class TestCase285357(TestCaseBlockedConnection):
    __test__ = (TestCaseBlockedConnection.storage == 'nfs')
    tcms_test_case = '285357'
    bz = {'1138144': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_nfs_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=1)
class TestCase285370(TestNoSpaceLeftOnDevice):
    __test__ = (TestNoSpaceLeftOnDevice.storage == 'nfs')
    tcms_test_case = '285370'
    left_space = 10 * GB
    bz = {'1024353': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_nfs_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()


@attr(tier=3)
class TestCase285371(TestCaseBlockedConnection):
    __test__ = (TestCaseBlockedConnection.storage == 'iscsi')
    tcms_test_case = '285371'
    bz = {'1138144': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_iscsi_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=1)
class TestCase285372(TestNoSpaceLeftOnDevice):
    __test__ = (TestNoSpaceLeftOnDevice.storage == 'iscsi')
    tcms_test_case = '285372'

    def setUp(self):
        storage = get_vms_disks_storage_domain_name(self.vm)
        self.disk_alias = "second_disk_%s" % self.tcms_test_case
        LOGGER.info("Adding disk %s to vm %s", self.disk_alias, self.vm)
        if not addDisk(
            True, self.vm, config.DISK_SIZE, storagedomain=storage,
            interface=config.VIRTIO, alias=self.disk_alias,
        ):
            LOGGER.error("Error adding disk %s", self.disk_alias)
        disks.wait_for_disks_status(self.disk_alias)

        LOGGER.info(
            "Waiting for %s logical name to be available", self.disk_alias,
        )
        if not get_vm_disk_logical_name(self.vm, self.disk_alias):
            LOGGER.error("Couldn't get %s logical name", self.disk_alias)

        self.process = Process(
            target=perform_dd_to_disk,
            args=(self.vm, self.disk_alias, True, config.DISK_SIZE,),
        )
        self.process.start()
        # Wait for the operation to start
        # TODO: change the sleep to check the operation started
        time.sleep(5)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_iscsi_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()

    def tearDown(self):
        """Remove vm's disk"""
        self.process.terminate()
        if not vms.deactivateVmDisk(True, self.vm, self.disk_alias):
            LOGGER.error(
                "Error deactivating disk %s from vm %s", self.disk_alias,
                self.vm,
            )
        if not vms.removeDisk(True, self.vm, self.disk_alias):
            LOGGER.error(
                "Error removing disk %s from vm %s", self.disk_alias, self.vm,
            )
        super(TestCase285372, self).tearDown()


@attr(tier=3)
class TestCase285375(TestCaseBlockedConnection):
    __test__ = (TestCaseBlockedConnection.storage == 'fcp')
    tcms_test_case = '285375'
    bz = {'1138144': {'engine': ['rest', 'sdk'], 'version': ["3.5"]}}

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_fc_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=1)
class TestCase285376(TestNoSpaceLeftOnDevice):
    __test__ = (TestNoSpaceLeftOnDevice.storage == 'fcp')
    tcms_test_case = '285376'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_fc_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()
