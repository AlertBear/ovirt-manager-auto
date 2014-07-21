"""
Test mixed types DC suite
https://tcms.engineering.redhat.com/plan/12285
"""
import time
import logging
import helpers
import config

from utilities.machine import Machine

from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr

import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.clusters as ll_cl
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.storage_api import blockOutgoingConnection, \
    unblockOutgoingConnection

from art.test_handler.tools import tcms, bz
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

TCMS_TEST_PLAN = '12285'

TIMEOUT_CREATE_DISK = 420
TIMEOUT_MOVE_DISK = 300
TIMEOUT_DATA_CENTER_RECONSTRUCT = 600

SDK_ENGINE = 'sdk'


class BaseCaseDCMixed(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    version. Environment is cleaned up after.

    This makes the code more cleanear for the tests, adding a bit of time
    for installing a host every time
    """
    __test__ = False
    compatibility_version = "3.4"
    storagedomains = []

    @classmethod
    def setup_class(cls):
        """
        Add a DC/Cluster with host with the storage domains
        """
        helpers.build_environment(
            compatibility_version=cls.compatibility_version,
            storage_domains=cls.storagedomains
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
            vdc_password=config.VDC_PASSWORD,
            formatExpStorage='true')


class IscsiNfsSD(BaseCaseDCMixed):
    """
    Base case with ISCSI (master) and NFS domain
    """
    storagedomains = [config.ISCSI_DOMAIN, config.NFS_DOMAIN]

    nfs = config.NFS_DOMAIN['name']
    iscsi = config.ISCSI_DOMAIN['name']


class IscsiNfsSdVMs(IscsiNfsSD):
    """
    Create a vm on each SD
    """

    __test__ = False

    iscsi_vm = "iscsi_vm"
    nfs_vm = "nfs_vm"

    @classmethod
    def setup_class(cls):
        """
        * Create a nfs and iscsi SD, and a vm on each SD.
        """
        logger.info("Create nfs and iscsi SDs")
        super(IscsiNfsSD, cls).setup_class()

        # Creating a vm with a disk on both sds
        helpers.create_and_start_vm(cls.nfs_vm, cls.nfs)
        helpers.create_and_start_vm(cls.iscsi_vm, cls.iscsi)


# doesn't work - need verification when FC is available
@attr(tier=0)
class TestCase336356(BaseCaseDCMixed):
    """
    * Create FC and iSCSI Storage Domains.
    * Create disks on each domain.
    * Move disk (offline movement) between domains
      (FC to iSCSI and iSCSI to FC).

    """
    tcms_test_case = '336356'
    __test__ = False  # No host with HBA port in broker

    storage_domains = [config.FC_DOMAIN, config.ISCSI_DOMAIN]
    iscsi = config.ISCSI_DOMAIN['name']
    fc = config.FC_DOMAIN['name']

    @classmethod
    def setup_class(cls):
        """
        * Create disks on each domain.
        """
        super(TestCase336356, cls).setup_class()

        logger.info("Add a disk to each storage domain")
        cls.iscsi_disk = "iscsi_disk"
        cls.fc_disk = "fc_disk"

        helpers.add_disk_to_sd(cls.iscsi, cls.iscsi_disk)
        helpers.add_disk_to_sd(cls.fc, cls.fc_disk)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_move_disks(self):
        """
        Move disk (offline movement) between domains
        (FC to iSCSI and iSCSI to FC).
        """
        # Skipping until python sdk supports move of disks
        logger.info("Moving disks between domains")
        assert ll_disks.move_disk(
            disk_name=self.iscsi_disk, target_domain=self.fc)
        assert ll_disks.move_disk(
            disk_name=self.fc_disk, target_domain=self.iscsi)


@attr(tier=0)
class TestCase336360(IscsiNfsSD):
    """
    * Create a shared DC.
    * Create ISCSI and NFS storage domains.
    * Create VMs with disks on the same domain type.
    * Export/Import VM.
    * Create Vm with disks on different domain types.
    * Export/Import VM.
    """
    tcms_test_case = '336360'
    __test__ = True

    storagedomains = [config.ISCSI_DOMAIN, config.NFS_DOMAIN,
                      config.EXPORT_DOMAIN]
    export_domain = config.EXPORT_DOMAIN['name']
    vm_name = "vm_%s" % tcms_test_case

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_export_import_vm(self):
        """
        Export-import VMs
        """
        for sd in self.iscsi, self.nfs:
            vm = "vm_%s_%s" % (sd, self.tcms_test_case)
            logger.info("Creating vm %s in storage domain %s", vm, sd)
            helpers.create_and_start_vm(vm, sd, installation=False)

            logger.info("Trying export/import for vm %s", vm)
            assert ll_vms.exportVm(True, vm, self.export_domain)
            assert ll_vms.removeVm(True, vm)

            assert ll_vms.importVm(True, vm, self.export_domain,
                                   sd, config.CLUSTER_NAME)

        logger.info("Creating vm %s with disk in different domains",
                    self.vm_name)
        helpers.create_and_start_vm(self.vm_name, self.iscsi,
                                    installation=False)
        second_disk = "vm_%s_Disk2" % self.tcms_test_case
        helpers.add_disk_to_sd(second_disk, self.nfs,
                               attach_to_vm=self.vm_name)

        logger.info("Trying export/import for vm with multiple disks %s", vm)
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, config.CLUSTER_NAME)


@attr(tier=0)
class TestCase336361(IscsiNfsSdVMs):
    """
    * Create a shared DC.
    * Create ISCSI and NFS storage domains.
    * Create 2 VMs
    * Attach disks to VM from different storage domains.
    * Create a snapshot.
    * Clone VM from snapshot.
    """

    tcms_test_case = '336361'
    __test__ = False  # Failing sdk at super

    @classmethod
    def setup_class(cls):
        """
        * Add a new disk to each vms on different sd
        """
        super(TestCase336361, cls).setup_class()

        nfs_vm_disk2 = "%s_Disk2" % cls.nfs_vm
        iscsi_vm_disk2 = "%s_Disk2" % cls.iscsi_vm
        helpers.add_disk_to_sd(
            nfs_vm_disk2, cls.iscsi, attach_to_vm=cls.nfs_vm)
        helpers.add_disk_to_sd(
            iscsi_vm_disk2, cls.nfs, attach_to_vm=cls.iscsi_vm)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_clone_from_snapshot(self):
        """
        Creates a new snapshots and clones vm from it for both vms
        """
        get_sd_id = lambda w: w.get_storage_domains(
            ).get_storage_domain()[0].get_id()

        def add_snapshot_and_clone(vm_name):
            snapshot_name = "%s_snaphot" % vm_name
            cloned_vm_name = "%s_cloned" % vm_name
            assert ll_vms.addSnapshot(True, vm_name, snapshot_name)

            assert ll_vms.cloneVmFromSnapshot(
                True, cloned_vm_name, cluster=config.CLUSTER_NAME,
                vm=vm_name, snapshot=snapshot_name)

            disks = ll_vms.getVmDisks(cloned_vm_name)
            self.assertNotEqual(
                get_sd_id(disks[0]), get_sd_id(disks[1]),
                "Disks are not in different storage domains"
            )

            logger.info("Starting up vm %s to make sure is operational")
            assert ll_vms.startVm(
                True, cloned_vm_name, config.VM_UP)

        add_snapshot_and_clone(self.nfs_vm)
        add_snapshot_and_clone(self.iscsi_vm)


@attr(tier=0)
class TestCase336522(IscsiNfsSD):
    """
    * Create a shared DC.
    * Create 2 SDs - ISCSI and NFS
    * Create VM with disks on NFS
    * Make template from this VM.
    * Copy template disk's from NFS domain to ISCSI domain.
    * Clone a new VM from the template with its disk located on the iSCSI
    domain
    """

    tcms_test_case = '336522'
    __test__ = True

    vm_name = "vm_%s" % tcms_test_case
    template_name = "%s_template" % vm_name
    apis = IscsiNfsSD.apis - set(['sdk'])  # copy not supported on sdk

    @classmethod
    def setup_class(cls):
        """
        * Create a vm on a nfs storage domain
        """
        logger.info("Create nfs and iscsi SDs")
        super(TestCase336522, cls).setup_class()

        logger.info("Creating a vm with a disk on nfs storage domain")
        helpers.create_and_start_vm(cls.vm_name, cls.nfs, installation=False)

        logger.info("Stopping VM")
        ll_vms.stop_vms_safely([cls.vm_name])

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_copy_template(self):
        """
        Make template and copy it
        """
        logger.info("Creating template %s from vm %s", self.template_name,
                    self.vm_name)
        assert ll_templates.createTemplate(
            True, name=self.template_name, vm=self.vm_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.nfs)

        disk = ll_templates._getTemplateDisks(self.template_name)[0]
        logger.info("Copy template disk %s to %s storage domain",
                    disk.get_alias(), self.iscsi)
        ll_disks.copy_disk(disk_id=disk.get_id(), target_domain=self.iscsi)

        def clone_and_verify(storagedomain):
            logger.info("Clone a vm from the Template for storage domains %s",
                        storagedomain)
            vm_name = "vm_cloned_%s_%s" % (self.tcms_test_case, storagedomain)
            assert ll_vms.cloneVmFromTemplate(
                True, vm_name, self.template_name,
                config.CLUSTER_NAME, storagedomain=storagedomain, clone='true')

            disk_id = ll_vms.getVmDisks(vm_name)[0].get_id()
            logger.info("Verify disk %s is in storage domain %s",
                        disk_id, storagedomain)
            self.assertTrue(
                disk_id in map(
                    lambda w: w.get_id(),
                    ll_disks.getStorageDomainDisks(storagedomain, False)
                )
            )

        clone_and_verify(self.iscsi)
        clone_and_verify(self.nfs)


@attr(tier=0)
class TestCase336529(IscsiNfsSD):
    """
    Create a shared DC.
    Create 2 SDs - ISCSI and NFS
    Create VM with two disks - one on NFS and the second on ISCSI
    Perform basic snapshot sanity (create,preview,commit,undo,delete)
    """

    tcms_test_case = '336529'
    __test__ = True
    apis = IscsiNfsSD.apis - set(['sdk'])  # snapshots op not supported
    vm_name = "vm_%s" % tcms_test_case

    @classmethod
    def setup_class(cls):
        """
        * Create a vm on nfs sd.
        * Add a disk on iscsi sd to the vm.
        """
        logger.info("Create nfs and iscsi SDs")
        super(TestCase336529, cls).setup_class()

        logger.info("Creating a vm with a disk on NFS sd")
        helpers.create_and_start_vm(cls.vm_name, cls.nfs)

        logger.info("Add additional disk to the vm, on ISCSI sd")
        disk_name = "%s_Disk2" % cls.vm_name
        helpers.add_disk_to_sd(disk_name, cls.iscsi, attach_to_vm=cls.vm_name)

    @bz("867339")
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_snapshot_operations(self):
        """
        Perform basic snapshot sanity (create, preview, commit, undo, delete)
        """
        snap_name = "%s_snap_1" % self.vm_name

        logger.info("Create a snapshot")
        assert ll_vms.addSnapshot(True, self.vm_name, snap_name)

        logger.info("Preview a snapshot")
        assert ll_vms.preview_snapshot(True, self.vm_name,
                                       snap_name, ensure_vm_down=True)

        logger.info("Commit a snapshot")
        assert ll_vms.commit_snapshot(True, self.vm_name,
                                      ensure_vm_down=True)

        logger.info("Undo a snapshot")
        assert ll_vms.preview_snapshot(True, self.vm_name,
                                       snap_name, ensure_vm_down=True)
        assert ll_vms.undo_snapshot_preview(True, self.vm_name,
                                            ensure_vm_down=True)

        logger.info("Restore a snapshot")
        assert ll_vms.restoreSnapshot(True, self.vm_name,
                                      snap_name, ensure_vm_down=True)

        logger.info("Delete a snapshot")
        assert ll_vms.removeSnapshot(True, self.vm_name, snap_name)


@attr(tier=0)
class TestCase336530(IscsiNfsSD):
    """
    Create a shared DC.
    Create 2 SDs - ISCSI and NFS
    Choose Active Domain and switch it to maintenance.
    After reconstruct is finished, perform operations in the
    storage pool like disk creation, removal and move.
    """

    tcms_test_case = '336530'
    __test__ = True

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_basic_operations_reconstruct(self):
        """
        Perform basic disk sanity after reconstruct
        """
        logger.info("Maintenance master domain %s", self.master_domain)
        assert ll_sd.deactivateStorageDomain(True, config.DATA_CENTER_NAME,
                                             self.master_domain)

        logger.info("Waiting for Datacenter to reconstruct")
        assert ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME)

        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert found
        new_master_domain = master_domain['masterDomain']

        assert new_master_domain != self.master_domain

        disk_name = "disk_%s" % self.tcms_test_case
        logger.info("Add disk %s", disk_name)
        helpers.add_disk_to_sd(disk_name, new_master_domain)

        logger.info("Activate non master domain %s", self.master_domain)
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.master_domain)

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

        # Printing for weird behaviour after activation
        timer = 0
        timeout = 180
        sleep_time = 5
        while timer <= timeout:
            sdObj = ll_sd.getStorageDomainObj(self.master_domain)
            available = sdObj.get_available()
            if available:
                logger.info("Available size for %s domain is %d",
                            self.master_domain, available)
                break
            timer += sleep_time
            time.sleep(sleep_time)

        if timer >= timeout:
            logger.error(
                "Move will fail with 'Cannot move Virtual Machine Disk. "
                "Low disk space on target Storage Domain iscsi_sd."
            )
            move_operation = False
        else:
            move_operation = True

        # Skipping until python sdk supports move of disks BZ1097681
        if opts['engine'] != SDK_ENGINE:
            logger.info("Move disk %s from %s to %s", disk_name,
                        new_master_domain, self.master_domain)
            assert ll_disks.move_disk(
                disk_name=disk_name, target_domain=self.master_domain,
                positive=move_operation)

        logger.info("Delete disk %s", disk_name)
        assert ll_disks.deleteDisk(True, disk_name, async=False)
        assert ll_disks.waitForDisksGone(True, [disk_name])


# doesn't work - wait until reinitialize is on rest
# RFE https://bugzilla.redhat.com/show_bug.cgi?id=1092374
@attr(tier=0)
class TestCase336594(BaseCaseDCMixed):
    """
    Create a shared DC.
    Create SD of ISCSI type.
    Attach to DC.
    Maintenance ISCSI domain.
    Create unattached NFS SD (when creating Storage Domain choose 'None' DC)
    Go to DC-->right click--->Reinitialize DC and choose NFS domain from
    the list.
    """

    storagedomains = [config.ISCSI_DOMAIN]
    iscsi = config.ISCSI_DOMAIN['name']

    tcms_test_case = '336594'

    __test__ = False  # Change to True when reinitial via rest exists

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_reinitialize(self):
        """
        Reinitialize from unattached storage domain
        """
        logger.info("Maintenance ISCSI domain")
        ll_sd.deactivateStorageDomain(True, config.DATA_CENTER_NAME,
                                      self.iscsi)

        logger.info("Wait for DC state not operational")
        ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, state=config.ENUMS[
                'data_center_state_not_operational'])

        logger.info("Create unattached NFS storage domain")
        assert ll_sd.addStorageDomain(
            True, host=config.HOST, **config.NFS_DOMAIN)

        # XXX Reinitialize - needs implementation


# doesn't work, need FC
@attr(tier=0)
class TestCase343102(IscsiNfsSD):
    """
    Create DataCenter of shared type.
    Create FC/iSCSI and NFS/Gluster/POSIX Storage Domains.
    Create disks on each domain.
    Move disk (offline movement) between domains (file to block and block
    to file).
    """

    tcms_test_case = '343102'

    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        * Create ISCSI and NFS SDs.
        * Create a disk on each SD.
        """
        super(TestCase343102, cls).setup_class()

        # create disks

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_move_between_types(self):
        """
        Move disk (offline movement) between domains (file to block and
        block to file).
        """
        logger.info("Moving disks")
        # Make matrix...


@attr(tier=0)
class TestCase343101(BaseCaseDCMixed):
    """
    Create DataCenter of shared type.
    Create NFS and GlusterFS Storage Domains.
    Create disks on each domain.
    Move disk (offline movement) between domains (NFS to Gluster and
    Gluster to NFS).
    """
    tcms_test_case = '343101'
    __test__ = True
    apis = BaseCaseDCMixed.apis - set(['sdk'])  # move is not supported on sdk

    storagedomains = [config.NFS_DOMAIN, config.GLUSTER_DOMAIN]
    gluster = config.GLUSTER_DOMAIN['name']
    nfs = config.NFS_DOMAIN['name']

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    @bz(1091956)
    def test_move_nfs_to_nfs(self):
        """
        Move disks from one nfs storage to another
        """
        helpers.add_disk_to_sd("nfs_disk", self.nfs)
        helpers.add_disk_to_sd("gluster_disk", self.gluster)

        assert ll_disks.move_disk(
            disk_name="nfs_disk", target_domain=self.gluster)
        assert ll_disks.move_disk(
            disk_name="gluster_disk", target_domain=self.nfs)


@attr(tier=1)
class TestCase343383(IscsiNfsSD):
    """
    Create a shared DC.
    Create two Storage Domains - NFS and ISCSI
    Block connectivity from all hosts to storage server which master
    domain is located on.
    After reconstruct is finished, perform operations in the storage
    pool like disk creation, removal and move
    """

    tcms_test_case = '343383'
    __test__ = False  # Broken - cannot recover from BZs, so better disable it

    @bz("1078907")
    @bz("1072900")
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_reconstruct_master(self):
        """
        Block connectivity from the host to the storage.
        Wait until DC is up.
        Create a disk and remove it.
        """
        rc, master_address = ll_sd.getDomainAddress(True, self.master_domain)
        assert rc
        self.master_address = master_address['address']

        # Make sure non master domain is active
        assert ll_sd.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.non_master[0],
            expectedStatus=config.ENUMS['storage_domain_state_active'])

        assert blockOutgoingConnection(
            config.HOST, config.HOST_ADMIN, config.HOST_PASSWORD,
            self.master_address)

        logger.info("Waiting for the data center to be non responsive")
        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME,
            config.ENUMS['data_center_state_non_responsive'],
            timeout=TIMEOUT_DATA_CENTER_RECONSTRUCT)

        logger.info("... and be up again")
        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, timeout=TIMEOUT_DATA_CENTER_RECONSTRUCT)

        logger.info("Add a disk")
        disk_args = {
            'alias': "disk_4",
            'size': config.DISK_SIZE,
            'sparse': False,
            'format': config.DISK_FORMAT_RAW,
            'interface': config.INTERFACE_IDE,
            'storagedomain': self.non_master[0],
        }
        assert ll_disks.addDisk(True, **disk_args)

        logger.info("Wait for disk to be created")
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

        logger.info("Delete the disk")
        assert ll_disks.deleteDisk(True, "disk_4")

    def tearDown(self):
        """
        Unblock connection
        """
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)

        assert unblockOutgoingConnection(
            config.HOST, config.HOST_ADMIN, config.HOST_PASSWORD,
            self.master_address)

        logger.info("Make sure DC %s is up before cleaning the env",
                    config.DATA_CENTER_NAME)
        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, timeout=TIMEOUT_DATA_CENTER_RECONSTRUCT)

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)


# doesn't work - FC
@attr(tier=0)
class TestCase336357(BaseCaseDCMixed):
    """
    Create a shared DC.
    Create 2 Storage Domains of same type (ISCSI and FC, NFS and Gluster)
    Create 2 VMs - First VM with disk on NFS and second VM with disk on ISCSI
    Start VMs.
    Move disk of first VM from NFS domain to Gluster domain
    Move disk of second VM from ISCSI domain to FC domain.
    """
    __test__ = False  # No FC


# syncAction in doesn't return the response, only the status
@attr(tier=1)
class TestCase336358(IscsiNfsSdVMs):
    """
    Live Storage Migration between storage domains not of same type: block/file

    Create DC of mixed type and 2 sds, ISCSI domain and NFS domain
    Create 2 VMs - First VM with disk on NFS and second VM with disk on ISCSI.
    Start VMs.
    Move disk of first VM from NFS domain to ISCSI domain
    Move disk of second VM from ISCSI to NFS.

    Both moves should fail with a proper message
    """
    __test__ = True
    apis = IscsiNfsSdVMs.apis - set(['sdk'])  # move is not supported on sdk

    tcms_test_case = '336358'
    # message = "Cannot move Virtual Machine Disk. Source and target domains" \
    #           " must both be either file domains or block domains."

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_move_disks_between_different_sd_types(self):
        """
        Live Storage Migration between storage domains not of same type
        """
        logger.info("Moving a disk while the VM is running to a different "
                    "storage domain type should fail")
        nfs_vm_disk = ll_vms.getVmDisks(self.nfs_vm)[0].get_alias()
        iscsi_vm_disk = ll_vms.getVmDisks(self.iscsi_vm)[0].get_alias()

        assert ll_disks.move_disk(
            disk_name=nfs_vm_disk, target_domain=self.iscsi, positive=False)
        assert ll_disks.move_disk(
            disk_name=iscsi_vm_disk, target_domain=self.nfs, positive=False)


@attr(tier=0)
class TestCase336526(IscsiNfsSD):
    """
    Create a shared DC.
    Create 2 SDs - ISCSI and NFS.
    Create VM with 2 disks - on ISCSI domain and the other in NFS domain
    Install OS and make file system on both disks
    """
    __test__ = True

    tcms_test_case = '336526'
    vm_name = "vm_%s" % tcms_test_case

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_vm_disk_two_domain_types(self):
        """
        Test having two disks in two different storage domain types
        """
        logger.info("Creating vm %s in iscsi storage domain and installin OS",
                    self.vm_name)
        helpers.create_and_start_vm(self.vm_name, self.iscsi)
        helpers.add_disk_to_sd("vm_second_disk", self.nfs,
                               attach_to_vm=self.vm_name)

        vm_ip = ll_vms.get_vm_ip(self.vm_name)
        linux_machine = Machine(
            host=vm_ip, user=config.VM_USER,
            password=config.VM_PASSWORD).util('linux')

        logger.info("Create a partition in newly attached disk")
        success, output = linux_machine.runCmd(
            'echo 0 1024 | sfdisk /dev/sda -uM'.split())
        self.assertTrue(success, "Failed to create partition: %s" % output)

        success, output = linux_machine.runCmd('mkfs.ext4 /dev/sda1'.split())
        self.assertTrue(success, "Failed to create filesystem: %s" % output)


# works - have to update the case though, is need to remove DC
@attr(tier=2)
class TestCase336601(BaseCaseDCMixed):
    """
    Create a shared DC version 3.0
    Create Storage Domain ISCSI and attacht it to DC.            success
    Create Storage Domain NFS and try to attach it to DC.        failure
    Create another Storage Domain ISCSI and try to attach to DC  success
    Remove ISCSI domains from DC and attach NFS domain.           success
    """
    compatibility_version = "3.0"

    iscsi = config.ISCSI_DOMAIN['name']
    iscsi2 = config.ISCSI_DOMAIN2['name']
    nfs = config.NFS_DOMAIN['name']

    __test__ = True
    tcms_test_case = '336601'

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_data_centers_compabitility_version_30(self):
        """
        Data centers with compatibility version of 3.0
        """
        assert helpers.add_storage_domain(
            config.DATA_CENTER_NAME, **config.ISCSI_DOMAIN)

        logger.info("Try attaching NFS storage domain to the data center")
        assert ll_sd.addStorageDomain(True, host=config.HOST,
                                      **config.NFS_DOMAIN)
        assert ll_sd.attachStorageDomain(
            False, config.DATA_CENTER_NAME, self.nfs, True)

        logger.info("Ading a second iscsi storage domain")
        assert helpers.add_storage_domain(
            config.DATA_CENTER_NAME, **config.ISCSI_DOMAIN2)

        logger.info("Removing storage doamins")
        assert ll_sd.removeStorageDomains(
            True, [self.iscsi2], config.HOST)

        logger.info("Make sure to remove Data Center")
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.iscsi)

        assert ll_sd.removeDataCenter(True, config.DATA_CENTER_NAME)
        assert ll_dc.addDataCenter(
            True, name=config.DATA_CENTER_NAME, local=False,
            version=self.compatibility_version)
        assert ll_sd.removeStorageDomain(True, self.iscsi, config.HOST)
        assert ll_hosts.deactivateHost(True, config.HOST)
        assert ll_cl.updateCluster(
            True, config.CLUSTER_NAME, data_center=config.DATA_CENTER_NAME)
        assert ll_hosts.activateHost(True, config.HOST)

        logger.info("Attaching a NFS now should work")
        assert ll_sd.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.nfs)


@attr(tier=2)
class TestCase336617(TestCase):
    """
    Create shared DCs versions 3.0, 3.1 and 3.2.
    Create ISCSI domain in this DC.
    Create Gluster Storage Domain and try to attach it to DC. should fail
    """
    __test__ = True
    tcms_test_case = '336617'

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_gluster_different_compatibility_versions(self):
        """
        Make sure differente data centers version don't allow gluster
        """
        for version in ["3.0", "3.1", "3.2"]:
            logger.info("Trying to add glusterfs for DC version %s", version)
            helpers.build_environment(
                compatibility_version=version,
                storage_domains=[config.ISCSI_DOMAIN])

            # Cannot add the storage, so no attachment beacuse of version
            added_successfully = True if version in ["3.1", "3.2"] else False
            assert ll_sd.addStorageDomain(
                added_successfully, host=config.HOST, **config.GLUSTER_DOMAIN)

            if added_successfully:
                assert ll_sd.attachStorageDomain(
                    False, config.DATA_CENTER_NAME,
                    config.GLUSTER_DOMAIN['name'], True)

                assert ll_sd.removeStorageDomain(
                    True, config.GLUSTER_DOMAIN['name'], config.HOST)

            ll_sd.cleanDataCenter(
                True, config.DATA_CENTER_NAME, vdc=config.VDC,
                vdc_password=config.VDC_PASSWORD)

    @classmethod
    def teardown_class(cls):
        """Clean in case the Glusterfs fails"""
        ll_sd.cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)


# works - but need to check for message
@attr(tier=2)
class TestCase336874(BaseCaseDCMixed):
    """
    Create a shared Data Center version 3.0.
    Create POSIX Storage domain.
    Try to attach POSIX SD to Data Center -> should fail
    """
    __test__ = True
    tcms_test_case = '336874'
    compatibility_version = "3.0"

    message = "The Action ${action} is not supported for this Cluster " \
              "or Data Center compatibility version"

    def test_posix_data_center_30(self):
        """
        Posix domain and Data Center 3.0
        """
        sd = ll_sd._prepareStorageDomainObject(
            positive=False, host=config.HOST, **config.POSIX_DOMAIN)
        response, status = ll_sd.util.create(sd, positive=False, async=False)

        # status is True since we're expecting to fail
        self.assertTrue(
            status, "Adding a POSIX storage domain to a DC 3.0 should fail")
        if opts['engine'] != SDK_ENGINE:
            self.assertTrue(self.message in response.get_detail(),
                            "Error message should be %s" % self.message)

    @classmethod
    def teardown_class(cls):
        """
        Remove data center and cluster
        """
        assert ll_sd.removeDataCenter(True, config.DATA_CENTER_NAME)
        assert ll_hosts.deactivateHost(True, config.HOST)
        assert ll_hosts.removeHost(True, config.HOST)
        assert ll_cl.removeCluster(True, config.CLUSTER_NAME)


@attr(tier=0)
class TestCase336876(IscsiNfsSD):
    """
    Create a shared DC with two Storage Domans - ISCSI and NFS.
    Create VM with disks on NFS.
    Create template from this VM.
    Copy template's disk from NFS domain to ISCSI domain.
    Create new VM from template that resied on NFS and
    choose thin copy in Resource Allocation.
    """
    __test__ = True  # bz decorator should mark it as expected failure
    apis = IscsiNfsSD.apis - set(['sdk'])  # copy is not supported on sdk

    tcms_test_case = '336876'
    vm_name = "vm_%s" % tcms_test_case
    template_name = "template_%s" % tcms_test_case
    vm_cloned_name = "vm_cloned_%s" % tcms_test_case

    @classmethod
    def setup_class(cls):
        """
        Create a vm in nfs storage and create a template
        """
        super(TestCase336876, cls).setup_class()
        helpers.create_and_start_vm(cls.vm_name, cls.nfs)
        assert ll_vms.shutdownVm(True, cls.vm_name, async='false')

        assert ll_templates.createTemplate(
            True, vm=cls.vm_name, name=cls.template_name)

    @bz("1084789")
    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_thin_provision_on_block(self):
        """
        Thin provision disk on block form template that resides on NFS

        """
        disk_id = ll_templates._getTemplateDisks(
            self.template_name)[0].get_id()

        assert ll_disks.copy_disk(disk_id=disk_id, target_domain=self.iscsi)

        logger.info("Cloning vm from template with thin privisioning")
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_cloned_name, self.template_name,
            config.CLUSTER_NAME, storagedomain=self.nfs, clone='false')

        disk = ll_vms.getVmDisks(self.vm_cloned_name)[0]
        self.assertTrue(
            disk.get_sparse(),
            "Disk %s should be Thin Proivisioning" % disk.get_alias())


# need work
@attr(tier=0)
class TestCase337426(TestCase):
    """
    have a RHEV 3.3 with DC 3.3 of type ISCSI
    upgrade ovirt to 3.4
    Open UI and see if DC type remained 3.3 or 3.4
    Change the comp version of DC to 3.4 and check that it type becomes shared.
    """
    __test__ = False


@attr(tier=1)
class TestCase339619(IscsiNfsSD):
    """
    Create shared DC.
    Create ISCSI and NFS domains
    Create VM with disks on different domains (iscsi and nfs)
    Export this VM.
    Import VM and choose disk location on different SD.
    """
    __test__ = True
    tcms_test_case = '339619'
    storagedomains = [config.ISCSI_DOMAIN, config.NFS_DOMAIN,
                      config.EXPORT_DOMAIN]

    nfs = config.NFS_DOMAIN['name']
    iscsi = config.ISCSI_DOMAIN['name']
    export_domain = config.EXPORT_DOMAIN['name']

    vm_name = "vm_%s" % tcms_test_case
    vm_imported = "vm_imported_%s" % tcms_test_case

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_export_import(self):
        """
        Import VM and choose disk location on different SD
        """
        helpers.create_and_start_vm(
            self.vm_name, self.iscsi, installation=False)
        helpers.add_disk_to_sd("vm_second_disk", self.nfs, self.vm_name)

        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)

        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, config.CLUSTER_NAME,
                               self.vm_imported)
