from art.unittest_lib import StorageTest as TestCase
import logging
import time
from art.unittest_lib import attr
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.utils import storage_api

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
        password=password, nic=config.HOST_NICS[0])


class TestResumeGuests(TestCase):
    __test__ = False

    def setUp(self):
        """ just start writing
        """
        cmd = "dd of=%s if=/dev/urandom &" % FILE_TO_WRITE
        LOGGER.info("Starting writing process")
        assert vms.run_cmd_on_vm(
            config.VM_NAME[0], cmd, VM_USER, VM_PASSWORD)[0]
        # give it time to really start writing
        time.sleep(10)

    def tearDown(self):
        """ restart the vm (so kill writing process) & remove created file
        """
        # restart vm - this way we will also kill dd
        LOGGER.info("Stopping the VM")
        assert vms.stopVm(True, config.VM_NAME[0])

        LOGGER.info("Starting the VM")
        assert vms.startVm(
            True, config.VM_NAME[0], config.ENUMS['vm_state_up'], True, 3600)

        cmd = "rm -f %s" % FILE_TO_WRITE
        LOGGER.info("Removing file %s we were writing to" % FILE_TO_WRITE)
        # big timeout as rm may take a lot of time in case of big files
        assert vms.run_cmd_on_vm(
            config.VM_NAME[0], cmd, VM_USER, VM_PASSWORD, 3600)[0]

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
            config.VM_NAME[0], config.OS_TYPE, VM_USER,
            VM_PASSWORD)
        LOGGER.info("VM is accessible")

    def run(self):
        LOGGER.info("Breaking storage")
        self.break_storage()
        LOGGER.info("Checking if VM %s is paused", config.VM_NAME[0])
        self.check_vm_paused(config.VM_NAME[0])
        LOGGER.info("Fixing storage")
        self.fix_storage()
        LOGGER.info("Checking if VM %s is unpaused", config.VM_NAME[0])
        self.check_vm_unpaused(config.VM_NAME[0])
        LOGGER.info("Test finished successfully")


class TestCaseBlockedConnection(TestResumeGuests):
    host = None
    sd = None

    def break_storage(self):
        """ block connection from host to storage server
        """
        self.host = config.HOSTS[0]
        self.sd = config.STORAGE_SERVER
        LOGGER.info(
            "Blocking outgoing connection from %s to %s", self.host, self.sd)
        assert storage_api.blockOutgoingConnection(
            self.host, 'root', config.HOSTS_PWD[0], self.sd)

    def fix_storage(self):
        """ unblock connection from host to storage server
        """
        LOGGER.info("Unblocking connection from %s to %s", self.host, self.sd)
        assert storage_api.unblockOutgoingConnection(
            self.host, 'root', config.HOSTS_PWD[0], self.sd)
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
                self.host, 'root', config.HOSTS_PWD[0], self.sd)
        super(TestCaseBlockedConnection, self).tearDown()


class TestNoSpaceLeftOnDevice(TestResumeGuests):
    big_disk_name = "big_disk_eio"
    left_space = int(4.1 * GB)

    def break_storage(self):
        """ create a very big disk on the storage domain
        """
        master = storagedomains.findMasterStorageDomain(
            True, config.DC_NAME)[1]['masterDomain']
        domain = storagedomains.util.find(master)
        LOGGER.info("Master domain: %s", master)
        sd_size = domain.available
        LOGGER.info("Available space: %s", sd_size)
        disk_size = int(domain.available) - self.left_space
        LOGGER.info("Disk size: %s", disk_size)
        assert disks.addDisk(
            True, alias=self.big_disk_name, size=disk_size,
            storagedomain=master, format=config.ENUMS['format_raw'],
            interface=config.INTERFACE_VIRTIO, sparse=False)
        # NFS storage on orion is sloooow
        disks.waitForDisksState(self.big_disk_name, timeout=3600)

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
        master = storagedomains.findMasterStorageDomain(
            True, config.DC_NAME)[1]['masterDomain']
        disk_names = [
            x.alias for x in disks.getStorageDomainDisks(master, False)]
        LOGGER.info("All disks: %s" % disk_names)
        if self.big_disk_name in disk_names:
            disks.deleteDisk(True, self.big_disk_name)
        LOGGER.info("Upper tear down")
        super(TestNoSpaceLeftOnDevice, self).tearDown()


@attr(tier=2)
class TestCase285357(TestCaseBlockedConnection):
    __test__ = (DC_TYPE == 'nfs')
    tcms_test_case = '285357'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @bz(1003588)
    def test_nfs_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run()


@attr(tier=2)
class TestCase285370(TestNoSpaceLeftOnDevice):
    __test__ = (DC_TYPE == 'nfs')
    tcms_test_case = '285370'
    left_space = 10 * GB

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @bz(1024353)
    def test_nfs_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run()


@attr(tier=2)
class TestCase285371(TestCaseBlockedConnection):
    __test__ = (DC_TYPE == 'iscsi')
    tcms_test_case = '285371'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @bz(1003588)
    def test_iscsi_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run()


@attr(tier=1)
class TestCase285372(TestNoSpaceLeftOnDevice):
    __test__ = (DC_TYPE == 'iscsi')
    tcms_test_case = '285372'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_iscsi_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run()


@attr(tier=2)
class TestCase285375(TestCaseBlockedConnection):
    __test__ = (DC_TYPE == 'fcp')
    tcms_test_case = '285375'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_fc_blocked_connection(self):
        """ checks if VM is paused after connection to sd is lost,
            checks if VM is unpaused after connection is restored
        """
        self.run()


@attr(tier=1)
class TestCase285376(TestNoSpaceLeftOnDevice):
    __test__ = (DC_TYPE == 'fcp')
    tcms_test_case = '285376'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_fc_no_space_left_on_device(self):
        """ checks if VM is paused after no-space-left error on sd,
            checks if VM is unpaused after there is again free space on sd
        """
        self.run()
