"""
Test Iso Storage Domain

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/2_3_Storage_Import_ISO_Export_Domains

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Sanity

Check with shared and local DCs
Check with RHEL and windows OSs
Check with NFS, POSIXFS and local ISO domains
"""
import config
import logging
import helpers
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler.tools import polarion  # pylint: disable=E0611
from utilities import machine
from utilities.rhevm_tools.base import Utility, Setup
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS


def setup_module():
    """
    Sets the iso uploader config file's password
    """
    logger.info("Set the iso uploader config file password")
    setup = Setup(config.VDC, config.VDC_ROOT_USER, config.VDC_PASSWORD)
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
        diskInterface=config.INTERFACE_VIRTIO_SCSI, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        os_type=config.OS_TYPE, type=config.VM_TYPE_DESKTOP,
    )


class BaseCaseIsoDomains(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    version. Environment is cleaned up afterwards.

    """
    local = None
    machine = None
    vm_name = None
    mount_target = None
    storagedomains = []

    @classmethod
    def setup_class(cls):
        """
        Creates the environment with the storage domains
        Adds a vm
        """
        if not config.GOLDEN_ENV:
            helpers.build_environment(
                storage_domains=cls.storagedomains,
                local=cls.local
            )

        cls.data_center_name = config.DATA_CENTER_NAME

        found, master_domain = ll_sd.findMasterStorageDomain(
            True, cls.data_center_name)
        assert found
        cls.master_domain = master_domain['masterDomain']
        cls.spm_host = getSPMHost(config.HOSTS)
        assert create_vm(cls.vm_name, cls.master_domain)

        cls.machine = machine.LinuxMachine(
            config.VDC, config.VDC_ROOT_USER, config.VDC_PASSWORD, local=False)

    @classmethod
    def teardown_class(cls):
        """
        Clean the whole environment
        """
        if config.GOLDEN_ENV:
            ll_vms.stop_vms_safely([cls.vm_name])
            assert ll_vms.removeVm(True, cls.vm_name)
        else:
            clean_datacenter(
                True, cls.data_center_name, vdc=config.VDC,
                vdc_password=config.VDC_PASSWORD)

    def tearDown(self):
        self.clean_environment()

    def clean_environment(self):
        """
        Make sure vm is stopped and doesn't have an iso attached
        Clean the iso domains
        """
        ll_vms.start_vms([self.vm_name], wait_for_status=config.VM_UP)
        if not ll_vms.eject_cdrom_vm(self.vm_name):
            logger.error("Failed to eject cdrom from vm %s", self.vm_name)
        ll_vms.stop_vms_safely([self.vm_name])

        if self.iso_domain_name:
            logger.info("Removing iso domain %s", self.iso_domain_name)
            hl_sd.remove_storage_domain(
                self.iso_domain_name, self.data_center_name, self.spm_host,
                format_disk=True
            )
        wait_for_jobs([ENUMS['job_remove_storage_domain']])

    def attach_iso_and_maintenance(self, run_once=None, iso_domain=None):
        """
        1. Attach an ISO domain to the DC
        2. Attach an ISO from the ISO domain to a VM
        3. Enter the ISO domain to maintenance while the ISO is attached
        4. Eject the ISO and try to put the domain in maintenance
        """
        logger.info("Adding iso domain %s", iso_domain['name'])
        self.iso_domain_name = None
        assert helpers.add_storage_domain(
            self.data_center_name, self.spm_host, **iso_domain
        )
        self.iso_domain_name = iso_domain['name']

        # Mount the nfs partition with all the isos
        logger.info("Mounting nfs partition %s:%s to upload isos to the "
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
                ssh = "--ssh-user=%s" % config.HOSTS_USER
            else:
                ssh = ""
            upload_cmd = "engine-iso-uploader -f upload -i %s %s %s" % (
                self.iso_domain_name, ssh, path)
            logger.info("Executing %s", upload_cmd)
            rc, out = self.machine.runCmd(
                upload_cmd.split(), data=config.HOSTS_PW)
            if not rc:
                logger.error("Error uploading iso %s to domain %s => %s",
                             path, self.iso_domain_name, out)
                assert rc

        if run_once:
            assert ll_vms.runVmOnce(
                True, self.vm_name, cdrom_image=config.ISO_IMAGE
            )
        else:
            assert ll_vms.attach_cdrom_vm(True, self.vm_name, config.ISO_IMAGE)
            assert ll_vms.startVm(True, self.vm_name)

        logger.info("Wait for tasks to complete before deactivating the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD, self.data_center_name)
        status = ll_sd.deactivateStorageDomain(
            False, self.data_center_name, self.iso_domain_name
        )
        self.assertTrue(
            status, "ISO domain %s was deactivated while one of the isos "
            "is attached to vm %s" % (iso_domain['name'], self.vm_name)
        )

        assert ll_vms.eject_cdrom_vm(self.vm_name)
        logger.info("Wait for tasks to complete before deactivating the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD, self.data_center_name)
        status = ll_sd.deactivateStorageDomain(
            True, self.data_center_name, self.iso_domain_name)
        self.assertTrue(
            status, "ISO domain %s wasn't deactivated after ejecting one of "
            "the isos from the vm %s" % (self.iso_domain_name, self.vm_name)
        )


@attr(tier=1)
class TestCase11576Shared(BaseCaseIsoDomains):
    """
    Test detaching iso domains when an iso image is inserted in a vm under a
    shared DC
    """
    # Please note that the following bug may cause this case to fail
    # intermittently: https://bugzilla.redhat.com/show_bug.cgi?id=1215402
    # The Posix ISO domain fails to Detach and can only be removed by using
    # the Destroy option (which the code doesn't do)
    # Gluster doesn't support being used as an ISO domain
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_ISCSI in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_NFS])
    local = False
    vm_name = "TestCase11576Shared"
    storagedomains = [config.ISCSI_DOMAIN]
    # Bugzilla history
    # 1225356: CLI: update cdrom is not ejecting the ISO image when the file-id
    # option is not provided
    # 1254936: Deactivate storage domain sometimes fails without any warning

    @polarion("RHEVM3-11576")
    def test_detaching_iso_vm_and_vm_runonce(self):
        """
        Try detaching a posixfs/nfs iso domain from vm while iso is attached
        """
        logger.info("Testing detaching posixfs iso domain while iso image is "
                    "attached to vm")
        self.attach_iso_and_maintenance(iso_domain=config.ISO_POSIX_DOMAIN)
        self.clean_environment()

        logger.info("Testing detaching nfs iso domain while iso image is "
                    "attached to vm")
        self.attach_iso_and_maintenance(iso_domain=config.ISO_NFS_DOMAIN)
        self.clean_environment()

        logger.info("Testing detaching posixfs iso domain while iso image is "
                    "attached to vm and run it once")
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_POSIX_DOMAIN)
        self.clean_environment()

        logger.info("Testing detaching nfs iso domain while iso image is "
                    "attached to vm and run it once")
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_NFS_DOMAIN)


@attr(tier=2)
class PlanIsoDomainLocal(BaseCaseIsoDomains):
    """
    Test detaching iso domains when an iso image is inserted in a vm under a
    local DC
    """
    # Local data center tests are not supported by the golden environment
    __test__ = not config.GOLDEN_ENV
    local = True
    vm_name = "TestCasePlanIsoDomainLocal"
    storagedomains = [config.LOCAL_DOMAIN]
    bz = {'1188326': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    @polarion("RHEVM3-11859")
    def test_detaching_local_iso_vm(self):
        """
        Try detaching a local iso domain from vm while iso is attached
        """
        self.attach_iso_and_maintenance(iso_domain=config.ISO_LOCAL_DOMAIN)

    @polarion("RHEVM3-11860")
    def test_detaching_local_iso_vm_runonce(self):
        """
        Try detaching a local iso domain from vm after attaching it with
        run once
        """
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_LOCAL_DOMAIN)
