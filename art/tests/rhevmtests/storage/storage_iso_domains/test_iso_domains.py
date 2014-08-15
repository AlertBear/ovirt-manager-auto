"""
Test Iso Storage Domain
https://tcms.engineering.redhat.com/plan/6107

Check with shared and local DCs
Check with RHEL and windows OSs
Check with NFS, POSIXFS and local ISO domains
"""
import logging
import helpers
import config

from art.unittest_lib import StorageTest as TestCase

import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

from art.rhevm_api.utils import test_utils

from art.test_handler.tools import tcms, bz  # pylint: disable=E0611

from utilities import machine
from utilities.rhevm_tools.base import Utility, Setup
logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
TCMS_TEST_PLAN = '6107'
TCMS_CASE_ATTACH = '340691'
TCMS_CASE_RUNONCE = '347379'


def setup_module():
    """
    Sets the iso uploader config file's password
    """
    setup = Setup(config.VDC, config.VDC_USER, config.VDC_PASSWORD)
    utility = Utility(setup)
    assert utility.setRestConnPassword(
        "iso-uploader", config.ISO_UPLOADER_CONF_FILE, config.REST_PASS)


def create_vm(vm_name, master_domain):
    """
    Create a vm
    """
    return ll_vms.createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        storageDomainName=master_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.DISK_FORMAT_COW,
        diskInterface=config.VIRTIO_SCSI, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        os_type=config.OS_TYPE, type=config.VM_TYPE_DESKTOP,
    )


def clean_iso_domains(datacenter=None, format_disk=False):
    """
    Find all the ISO domains and remove them
        * datacenter - only from the specified datacenter
        * format_disk - if the storage domain should be formatted
    """
    for iso_domain in ll_sd.findIsoStorageDomains(datacenter):
        hl_sd.remove_storage_domain(
            iso_domain, config.DATA_CENTER_NAME, config.HOST,
            format_disk=format_disk
        )


class BaseCaseIsoDomains(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    version. Environment is cleaned up afterwards.

    """
    local = None
    machine = None
    vm_name = None
    storagedomains = []

    @classmethod
    def setup_class(cls):
        """
        Creates the environment with the storage domains
        Adds a vm
        Remove all the iso storages domains
        """
        helpers.build_environment(
            storage_domains=cls.storagedomains,
            local=cls.local
        )

        if cls.storagedomains:
            found, master_domain = ll_sd.findMasterStorageDomain(
                True, config.DATA_CENTER_NAME)
            assert found
            cls.master_domain = master_domain['masterDomain']

            if len(cls.storagedomains) > 1:
                found, non_master = ll_sd.findNonMasterStorageDomains(
                    True, config.DATA_CENTER_NAME)
                assert found
                cls.non_master = non_master['nonMasterDomains']

        assert create_vm(cls.vm_name, cls.master_domain)

        # Make sure there's no ISO Domains in the environment
        clean_iso_domains()
        cls.machine = machine.LinuxMachine(
            config.VDC, config.VDC_USER, config.VDC_PASSWORD, local=False)

    @classmethod
    def teardown_class(cls):
        """
        Clean the whole environment
        """
        # Wait for all the tasks to finish in case of error
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

        ll_sd.cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)


class TestCasesPlan6107(BaseCaseIsoDomains):

    mount_target = None

    def tearDown(self):
        """
        Make sure vm is stopped and doesn't have an iso attached
        Clean the iso domains
        """
        assert ll_vms.remove_cdrom_vm(True, self.vm_name)
        if ll_vms.checkVmState(False, self.vm_name, config.VM_DOWN):
            assert ll_vms.shutdownVm(True, self.vm_name)

        # Safely remove the iso domain
        # WARNING: It will be formatted too
        clean_iso_domains(config.DATA_CENTER_NAME, format_disk=True)

        # Make sure the iso domain is removed
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

    def attach_iso_and_maintenance(self, run_once=None, iso_domain=None):
        """
        1. Attach an ISO domain to the DC
        2. Attach an ISO from the ISO domain to a VM
        3. Enter the ISO domain to maintenance while the ISO is attached
        4. Eject the ISO and try to put the domain in maintenance
        """
        logger.info("Adding iso domain %s", iso_domain['name'])
        assert helpers.add_storage_domain(
            config.DATA_CENTER_NAME, **iso_domain)

        # Mount the nfs partition with all the isos
        logger.info("Mouting nfs partition %s:%s to upload isos to the "
                    "domain", config.iso_address, config.iso_path)
        with self.machine.mount(
            "%s:%s" % (config.iso_address, config.iso_path),
            opts=['-t', 'nfs'],
        ) as mount_target:
            logger.info("Uploading iso %s to the domain", config.ISO_IMAGE)
            # This will upload one iso to the new created iso domain
            find_cmd = "find %s | grep %s" % (mount_target, config.ISO_IMAGE)
            logger.info("Executing %s", find_cmd)
            rc, path = self.machine.runCmd(find_cmd.split())
            if not rc:
                logger.error("Error finding iso path for %s => %s",
                             config.ISO_IMAGE, path)
                assert rc

            path.rstrip("\r\n")
            if iso_domain['storage_type'] == ENUMS['storage_type_local']:
                # Can only upload to local domains via ssh
                ssh = "--ssh-user=%s" % config.HOST_ADMIN
            else:
                ssh = ""
            upload_cmd = "engine-iso-uploader -f upload -i %s %s %s" % (
                iso_domain['name'], ssh, path)
            logger.info("Executing %s", upload_cmd)
            rc, out = self.machine.runCmd(
                upload_cmd.split(), data=config.HOST_PASSWORD)
            if not rc:
                logger.error("Error uploading iso %s to domain %s => %s",
                             path, iso_domain['name'], out)
                assert rc

        if run_once:
            assert ll_vms.runVmOnce(
                True, self.vm_name, cdrom_image=config.ISO_IMAGE)
        else:
            assert ll_vms.attach_cdrom_vm(True, self.vm_name, config.ISO_IMAGE)
            assert ll_vms.startVm(True, self.vm_name)

        status = ll_sd.deactivateStorageDomain(
            False, config.DATA_CENTER_NAME, iso_domain['name'])
        self.assertTrue(
            status, "ISO domain %s was deactivated while one of the isos "
            "is attached to vm %s" % (iso_domain['name'], self.vm_name))

        assert ll_vms.remove_cdrom_vm(True, self.vm_name)
        status = ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, iso_domain['name'])
        self.assertTrue(
            status, "ISO domain %s wasn't deactivated after ejecting one of "
            "the isos from the vm %s" % (iso_domain['name'], self.vm_name))

    @tcms(TCMS_TEST_PLAN, TCMS_CASE_ATTACH)
    def test_detaching_posixfs_iso_vm(self):
        """
        Try detaching a posixfs iso domain from vm while iso is attached
        """
        self.attach_iso_and_maintenance(iso_domain=config.ISO_POSIX_DOMAIN)

    @tcms(TCMS_TEST_PLAN, TCMS_CASE_ATTACH)
    def test_detaching_nfs_iso_vm(self):
        """
        Try detaching a nfs iso domain from vm while iso is attached
        """
        self.attach_iso_and_maintenance(iso_domain=config.ISO_NFS_DOMAIN)

    @bz("1065719")
    @tcms(TCMS_TEST_PLAN, TCMS_CASE_RUNONCE)
    def test_detaching_posixfs_iso_vm_runonce(self):
        """
        Try detaching a posixfs iso domain from vm after attaching it with
        run once
        """
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_POSIX_DOMAIN)

    @bz("1065719")
    @tcms(TCMS_TEST_PLAN, TCMS_CASE_RUNONCE)
    def test_detaching_nfs_iso_vm_runonce(self):
        """
        Try detaching a nfs iso domain from vm after attaching it with run once
        """
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_NFS_DOMAIN)


class TestCasesPlan6107Shared(TestCasesPlan6107):
    """
    Test detaching iso domains when an iso is inserted in a vm
    Shared DC
    """
    __test__ = True
    local = False
    vm_name = "TestCasesPlan6107Shared"

    storagedomains = [config.ISCSI_DOMAIN]


class TestCasesPlan6107Local(TestCasesPlan6107):
    """
    Test detaching iso domains when an iso is inserted in a vm
    Local DC
    """
    __test__ = True
    local = True
    vm_name = "TestCasesPlan6107Local"
    storagedomains = [config.LOCAL_DOMAIN]

    @bz("1097789")
    @tcms(TCMS_TEST_PLAN, TCMS_CASE_ATTACH)
    def test_detaching_local_iso_vm(self):
        """
        Try detaching a local iso domain from vm while iso is attached
        """
        self.attach_iso_and_maintenance(iso_domain=config.ISO_LOCAL_DOMAIN)

    @bz("1097789")
    @tcms(TCMS_TEST_PLAN, TCMS_CASE_RUNONCE)
    def test_detaching_local_iso_vm_runonce(self):
        """
        Try detaching a local iso domain from vm after attaching it with
        run once
        """
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_LOCAL_DOMAIN)
