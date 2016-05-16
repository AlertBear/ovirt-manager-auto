import logging
import time
from multiprocessing import Process

from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import storage_api
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase
from rhevmtests.storage import helpers as storage_helpers

import config

logger = logging.getLogger(__name__)

DC_TYPE = config.STORAGE_TYPE
FILE_TO_WRITE = "/tmp/resume_guests_tests"

NFS = config.STORAGE_TYPE_NFS
ISCSI = config.STORAGE_TYPE_ISCSI


def _wait_for_vm_booted(
        vm_name, os_type, user, password, timeout=300, interval=15
):
    return ll_vms.checkVMConnectivity(
        True, vm_name, os_type, timeout / interval, interval, user=user,
        password=password, nic=config.NIC_NAME[0]
    )


class TestResumeGuests(TestCase):
    __test__ = False
    remove_file = False

    def setUp(self):
        """
        Perform dd command
        """
        self.vm = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        cmd = "dd if=/dev/urandom of=%s bs=128M oflag=direct &" % FILE_TO_WRITE
        logger.info("Starting writing process")
        if not ll_vms.run_cmd_on_vm(
            self.vm, cmd, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        )[0]:
            raise exceptions.DiskException(
                "Failed to run dd command on %s" % self.vm
            )
        self.remove_file = True
        if not storage_helpers.wait_for_dd_to_start(self.vm):
            raise exceptions.DiskException(
                "dd didn't start writing to disk on %s" % self.vm
            )

    def tearDown(self):
        """
        Restart the vm (so kill writing process) & remove created file
        """
        # restart vm - this way we will also kill dd
        logger.info("Powering off the VM")
        if not ll_vms.stopVm(True, self.vm):
            logger.error("Failed to power off vm %s", self.vm)
            TestResumeGuests.test_failed = True
        logger.info("Powering on the VM")
        if not ll_vms.startVm(True, self.vm, config.VM_UP, True):
            logger.error("Failed to power on vm %s", self.vm)
            TestResumeGuests.test_failed = True

        if self.remove_file:
            cmd = "rm -f %s" % FILE_TO_WRITE
            logger.info("Removing file %s we were writing to", FILE_TO_WRITE)
            # long timeout is needed in case there are many large
            # files to remove
            rc, out = ll_vms.run_cmd_on_vm(
                self.vm, cmd, config.VMS_LINUX_USER, config.VMS_LINUX_PW, 3600
            )
            if not rc:
                logger.error(
                    "Failed to remove file %s from VM %s, out: %s",
                    FILE_TO_WRITE, self.vm, out
                )
                TestResumeGuests.test_failed = True
        TestResumeGuests.teardown_exception()

    def break_storage(self):
        pass

    def fix_storage(self):
        pass

    def check_vm_paused(self, vm_name):
        if not ll_vms.waitForVMState(vm_name, config.VM_PAUSED):
            raise exceptions.VMException(
                "Waiting for VM %s status 'paused' failed" % self.vm_name
            )

    def check_vm_unpaused(self, vm_name):
        logger.info("Waiting for VM being up")
        if not ll_vms.waitForVMState(vm_name, config.VM_UP):
            raise exceptions.VMException(
                "Waiting for VM %s status 'up' failed" % self.vm_name
            )
        logger.info("VM is up, waiting for connectivity")
        if not _wait_for_vm_booted(
            self.vm, config.OS_TYPE, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        ):
            raise exceptions.VMException(
                "Waiting for VM %s to booted failed" % self.vm_name
            )
        logger.info("VM is accessible")

    def run_flow(self):
        logger.info("Breaking storage")
        self.break_storage()
        logger.info("Checking if VM %s is paused", self.vm)
        self.check_vm_paused(self.vm)
        logger.info("Fixing storage")
        self.fix_storage()
        logger.info("Checking if VM %s is unpaused", self.vm)
        self.check_vm_unpaused(self.vm)
        logger.info("Test finished successfully")


class TestCaseBlockedConnection(TestResumeGuests):
    host = None
    sd = None

    def break_storage(self):
        """
        Block connection from host to storage server
        """
        rc, host = ll_vms.getVmHost(self.vm)
        if not rc:
            raise exceptions.HostException("host of %s not found" % self.vm)
        self.host_ip = ll_hosts.getHostIP(host)
        self.sd = ll_vms.get_vms_disks_storage_domain_name(self.vm)
        self.sd_ip = ll_sd.getDomainAddress(True, self.sd)

        logger.info(
            "Blocking outgoing connection from %s to %s", self.host, self.sd
        )
        if not storage_api.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip
        ):
            raise exceptions.NetworkException(
                "Failed to block outgoing connection between %s to %s" %
                (self.host, self.sd)
            )

    def fix_storage(self):
        """
        Unblock connection from host to storage server
        """
        logger.info("Unblocking connection from %s to %s", self.host, self.sd)
        if not storage_api.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip
        ):
            raise exceptions.NetworkException(
                "Failed to unblock connection between %s to %s" %
                (self.host, self.sd)
            )
        self.host = None
        self.sd = None

    def tearDown(self):
        """
        Additional step in tearDown - unblock connection if it is blocked
        """
        # in case test failed between blocking and unblocking connection
        if self.host and self.sd:
            logger.info(
                "Unblocking connection from %s to %s", self.host, self.sd
            )
            if not storage_api.unblockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW, self.sd_ip
            ):
                logger.error(
                    "Failed to unblocked outgoing connection for host %s",
                    self.host_ip
                )
                TestCaseBlockedConnection.test_failed = True
        super(TestCaseBlockedConnection, self).tearDown()


class TestNoSpaceLeftOnDevice(TestResumeGuests):
    big_disk_name = "big_disk_eio"
    left_space = int(1.5 * config.GB)

    def break_storage(self):
        """
        Create a very big disk on the storage domain
        """
        self.sd = ll_vms.get_vms_disks_storage_domain_name(self.vm)
        domain = ll_sd.util.find(self.sd)
        logger.info("Master domain: %s", self.sd)
        sd_size = domain.available
        logger.info("Available space: %s", sd_size)
        disk_size = int(domain.available) - self.left_space
        logger.info("Disk size: %s", disk_size)
        if not ll_disks.addDisk(
            True, alias=self.big_disk_name, size=disk_size,
            storagedomain=self.sd, format=config.RAW_DISK,
            interface=config.INTERFACE_VIRTIO, sparse=False
        ):
            raise exceptions.DiskException(
                "Failed to create disk %s" % self.big_disk_name
            )

        ll_disks.wait_for_disks_status(self.big_disk_name, timeout=3600)

        logger.info("Big disk created")

    def fix_storage(self):
        """
        Delete created big disk
        """
        logger.info("Delete big disk")
        if not ll_disks.deleteDisk(True, self.big_disk_name):
            raise exceptions.DiskException(
                "Failed to delete disk %s" % self.big_disk_name
            )

    def tearDown(self):
        """
        Additional step in tearDown - remove big disk
        """
        logger.info("Tear down - removing disk if needed")
        disk_names = [
            x.alias for x in ll_disks.getStorageDomainDisks(self.sd, False)
            ]
        logger.info("All disks: %s", disk_names)
        if self.big_disk_name in disk_names:
            if not ll_disks.deleteDisk(True, self.big_disk_name):
                logger.error("Failed to remove disk %s", self.big_disk_name)
                TestResumeGuests.test_failed = True
        logger.info("Upper tear down")
        super(TestNoSpaceLeftOnDevice, self).tearDown()


@attr(tier=4)
class TestCase5012(TestCaseBlockedConnection):
    # TODO: Why is this not running glusterfs?
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '5012'

    @polarion("RHEVM3-5012")
    def test_nfs_blocked_connection(self):
        """
        Checks if VM is paused after connection to sd is lost,
        Checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=2)
class TestCase5013(TestNoSpaceLeftOnDevice):
    # TODO: Why is this not running glusterfs?
    # TODO: this cases is disable due to ticket RHEVM-2524
    # __test__ = (NFS in opts['storages'])
    __test__ = False
    storages = set([NFS])
    polarion_test_case = '5013'
    left_space = 10 * config.GB

    @polarion("RHEVM3-5013")
    @bz({'1024353': {'engine': ['rest', 'sdk']}})
    def test_nfs_no_space_left_on_device(self):
        """
        Checks if VM is paused after no-space-left error on sd,
        Checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()


@attr(tier=4)
class TestCase5014(TestCaseBlockedConnection):
    __test__ = (ISCSI in opts['storages'])
    storages = set([ISCSI])
    polarion_test_case = '5014'

    @polarion("RHEVM3-5014")
    def test_iscsi_blocked_connection(self):
        """
        Checks if VM is paused after connection to sd is lost,
        Checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=2)
class TestCase5015(TestNoSpaceLeftOnDevice):
    # TODO: this cases is disable due to ticket RHEVM-2524
    # __test__ = (ISCSI in opts['storages'])
    __test__ = False
    storages = set([ISCSI])
    polarion_test_case = '5015'
    # The disk should be big enough so the operation to write data to the disk
    # runs for enough time until the big disk is created and the vm is
    # paused due to not enough space left on the storage domain
    disk_size = 3 * config.GB

    def setUp(self):
        self.process = None
        self.sd = ll_vms.get_vms_disks_storage_domain_name(self.vm)
        self.disk_alias = "second_disk_%s" % self.polarion_test_case
        logger.info("Adding disk %s to vm %s", self.disk_alias, self.vm)
        if not ll_vms.addDisk(
            True, self.vm, self.disk_size, storagedomain=self.sd,
            interface=config.VIRTIO, alias=self.disk_alias
        ):
            logger.error("Error adding disk %s", self.disk_alias)
        ll_disks.wait_for_disks_status(self.disk_alias)

        self.process = Process(
            target=storage_helpers.perform_dd_to_disk,
            args=(self.vm, self.disk_alias, True, self.disk_size)
        )
        self.process.start()
        # Wait for the operation to start
        # TODO: change the sleep to check the operation started
        time.sleep(5)

    @polarion("RHEVM3-5015")
    def test_iscsi_no_space_left_on_device(self):
        """
        Checks if VM is paused after no-space-left error on sd,
        Checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()

    def tearDown(self):
        """
        Remove vm's disk
        """
        if self.process:
            self.process.terminate()
        if not ll_vms.deactivateVmDisk(True, self.vm, self.disk_alias):
            logger.error(
                "Error deactivating disk %s from vm %s", self.disk_alias,
                self.vm
            )
            TestCase5015.test_failed = True
        if not ll_vms.removeDisk(True, self.vm, self.disk_alias):
            logger.error(
                "Error removing disk %s from vm %s", self.disk_alias, self.vm
            )
            TestCase5015.test_failed = True
        super(TestCase5015, self).tearDown()


@attr(tier=4)
class TestCase5016(TestCaseBlockedConnection):
    __test__ = ('fcp' in opts['storages'])
    storages = set(['fcp'])
    polarion_test_case = '5016'

    @polarion("RHEVM3-5016")
    def test_fc_blocked_connection(self):
        """
        Checks if VM is paused after connection to sd is lost,
        Checks if VM is unpaused after connection is restored
        """
        self.run_flow()


@attr(tier=2)
class TestCase5017(TestNoSpaceLeftOnDevice):
    # TODO: this cases is disable due to ticket RHEVM-2524
    # __test__ = ('fcp' in opts['storages'])
    __test__ = False
    storages = set(['fcp'])
    polarion_test_case = '5017'

    @polarion("RHEVM3-5017")
    def test_fc_no_space_left_on_device(self):
        """
        Checks if VM is paused after no-space-left error on sd,
        Checks if VM is unpaused after there is again free space on sd
        """
        self.run_flow()
