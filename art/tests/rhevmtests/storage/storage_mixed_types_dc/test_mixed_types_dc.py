"""
Test mixed types DC suite
https://tcms.engineering.redhat.com/plan/12285
"""
import config
import helpers
import logging

from utilities.machine import Machine
from art.core_api.apis_exceptions import (
    EntityNotFound,
)
from art.unittest_lib import attr, StorageTest as TestCase

from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter

import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.clusters as ll_cl
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from rhevmtests.storage.helpers import get_vm_ip
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

TCMS_TEST_PLAN = '12285'

TIMEOUT_DATA_CENTER_RECONSTRUCT = 900
TIMEOUT_DATA_CENTER_NON_RESPONSIVE = 300

SDK_ENGINE = 'sdk'

ALL_TYPES = (
    config.STORAGE_TYPE_NFS, config.STORAGE_TYPE_GLUSTER,
    config.STORAGE_TYPE_POSIX, config.STORAGE_TYPE_ISCSI,
)


class BaseCaseDCMixed(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    version. Environment is cleaned up after.

    This makes the code more cleanear for the tests, adding a bit of time
    for installing a host every time
    """
    __test__ = False
    storages = 'N/A'

    compatibility_version = config.COMP_VERSION
    storagedomains = []
    data_center_name = config.DATA_CENTER_NAME
    cluster_name = config.CLUSTER_NAME
    new_datacenter_for_ge = False

    def setUp(self):
        """
        Add a DC/Cluster with host with the storage domains
        """
        self.remove_datacenter = False
        if not config.GOLDEN_ENV or (
                config.GOLDEN_ENV and self.new_datacenter_for_ge
        ):

            if config.GOLDEN_ENV:
                status, host = ll_hosts.getAnyNonSPMHost(
                    config.HOSTS, cluster_name=config.CLUSTER_NAME,
                )
                self.host = host['hsmHost']
                self.host_ip = ll_hosts.getHostIP(self.host)
                ll_hosts.deactivateHost(True, self.host)
                ll_hosts.removeHost(True, self.host)

            else:
                self.host = config.HOSTS[0]
                self.host_ip = self.host

            self.remove_datacenter = True
            helpers.build_environment(
                compatibility_version=self.compatibility_version,
                storage_domains=self.storagedomains,
                datacenter_name=self.data_center_name,
                cluster_name=self.cluster_name,
                hosts_for_cluster=[self.host_ip],
            )

        for storage_domain_type in ALL_TYPES:
            storage_domain_names = ll_sd.getStorageDomainNamesForType(
                self.data_center_name, storage_domain_type,
            )
            if storage_domain_names:
                # Generate self.storage_type = storage_domain_name:
                # self.nfs = "nfs_0", self.iscsi = "iscsi_0"
                setattr(self, storage_domain_type, storage_domain_names[0])

        self.vms_to_remove = []
        self.vms_to_remove_from_export_domain = []
        self.templates_to_remove = []

    def tearDown(self):
        """
        Clean the whole environment
        """
        if self.remove_datacenter:
            test_utils.wait_for_tasks(
                config.VDC, config.VDC_ROOT_PASSWORD, self.data_center_name,
            )
            clean_datacenter(
                True, self.data_center_name, vdc=config.VDC,
                vdc_password=config.VDC_ROOT_PASSWORD,
                formatExpStorage='true')

            if self.new_datacenter_for_ge:
                ll_hosts.addHost(
                    True, name=self.host, cluster=config.CLUSTER_NAME,
                    root_password=config.HOSTS_PW,
                    address=self.host_ip,
                )
                ll_hosts.waitForHostsStates(True, self.host)
        else:
            ll_vms.safely_remove_vms(self.vms_to_remove)
            for vm in self.vms_to_remove_from_export_domain:
                ll_vms.removeVmFromExportDomain(
                    True, vm, self.data_center_name, self.export_domain,
                )
            for template in self.templates_to_remove:
                ll_templates.removeTemplate(True, self.template_name)


class IscsiNfsSD(BaseCaseDCMixed):
    """
    Base case with ISCSI (master) and NFS domain
    """
    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN]


class IscsiNfsSdVMs(IscsiNfsSD):
    """
    Create a vm on each SD
    """
    __test__ = False

    iscsi_vm = "iscsi_vm"
    nfs_vm = "nfs_vm"

    def setUp(self):
        """
        * Create a nfs and iscsi SD, and a vm on each SD.
        """
        super(IscsiNfsSD, self).setUp()

        helpers.create_and_start_vm(self.nfs_vm, self.nfs)
        helpers.create_and_start_vm(self.iscsi_vm, self.iscsi)

        self.vms_to_remove = [self.nfs_vm, self.iscsi_vm]


# TODO: doesn't work - need verification when FC is available
@attr(tier=1)
class TestCase336356(BaseCaseDCMixed):
    """
    * Create FC and iSCSI Storage Domains.
    * Create disks on each domain.
    * Move disk (offline movement) between domains
      (FC to iSCSI and iSCSI to FC).
    """
    tcms_test_case = '336356'
    __test__ = False  # No host with HBA port in broker

    storage_domains = [config.FC_DOMAIN, config.ISCSI_DOMAIN_0]
    fc = config.FC_DOMAIN['name']

    def setUp(self):
        """
        * Create disks on each domain.
        """
        super(TestCase336356, self).setUp()

        logger.info("Add a disk to each storage domain")
        self.iscsi_disk = "iscsi_disk"
        self.fc_disk = "fc_disk"

        helpers.add_disk_to_sd(self.iscsi, self.iscsi_disk)
        helpers.add_disk_to_sd(self.fc, self.fc_disk)

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


@attr(tier=1)
class TestCase336360(IscsiNfsSD):
    """
    * Create a shared DC.
    * Create ISCSI and NFS storage domains.
    * Create VMs with disks on the same domain type.
    * Export/Import VM.
    * Create Vm with disks on different domain types.
    * Export/Import VM.
    """
    __test__ = True
    tcms_test_case = '336360'

    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN,
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
            self.vms_to_remove.append(vm)

            logger.info("Trying export/import for vm %s", vm)
            assert ll_vms.exportVm(True, vm, self.export_domain)
            self.vms_to_remove_from_export_domain.append(vm)
            assert ll_vms.removeVm(True, vm)
            self.vms_to_remove.remove(vm)

            assert ll_vms.importVm(True, vm, self.export_domain,
                                   sd, self.cluster_name)
            self.vms_to_remove.append(vm)

        logger.info("Creating vm %s with disk in different domains",
                    self.vm_name)
        helpers.create_and_start_vm(self.vm_name, self.iscsi,
                                    installation=False)
        self.vms_to_remove.append(self.vm_name)
        second_disk = "vm_%s_Disk2" % self.tcms_test_case
        helpers.add_disk_to_sd(second_disk, self.nfs,
                               attach_to_vm=self.vm_name)

        logger.info("Trying export/import for vm with multiple disks %s", vm)
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        self.vms_to_remove_from_export_domain.append(self.vm_name)
        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, self.cluster_name)


@attr(tier=1)
class TestCase336361(IscsiNfsSdVMs):
    """
    * Create a shared DC.
    * Create ISCSI and NFS storage domains.
    * Create 2 VMs
    * Attach disks to VM from different storage domains.
    * Create a snapshot.
    * Clone VM from snapshot.
    """
    __test__ = True
    tcms_test_case = '336361'

    def setUp(self):
        """
        * Add a new disk to each vms on different sd
        """
        super(TestCase336361, self).setUp()

        nfs_vm_disk2 = "%s_Disk2" % self.nfs_vm
        iscsi_vm_disk2 = "%s_Disk2" % self.iscsi_vm
        helpers.add_disk_to_sd(
            nfs_vm_disk2, self.iscsi, attach_to_vm=self.nfs_vm,
        )
        helpers.add_disk_to_sd(
            iscsi_vm_disk2, self.nfs, attach_to_vm=self.iscsi_vm,
        )

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
                True, cloned_vm_name, cluster=self.cluster_name,
                vm=vm_name, snapshot=snapshot_name,
            )

            self.vms_to_remove.append(cloned_vm_name)
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


@attr(tier=1)
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
    __test__ = True
    tcms_test_case = '336522'

    vm_name = "vm_%s" % tcms_test_case
    template_name = "%s_template" % vm_name

    def setUp(self):
        """
        * Create a vm on a nfs storage domain
        """
        super(TestCase336522, self).setUp()

        helpers.create_and_start_vm(self.vm_name, self.nfs, installation=False)
        ll_vms.stop_vms_safely([self.vm_name])
        self.vms_to_remove.append(self.vm_name)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_copy_template(self):
        """
        Make template and copy it
        """
        logger.info("Creating template %s from vm %s", self.template_name,
                    self.vm_name)
        assert ll_templates.createTemplate(
            True, name=self.template_name, vm=self.vm_name,
            cluster=self.cluster_name, storagedomain=self.nfs)

        self.templates_to_remove.append(self.template_name)
        disk = ll_templates.getTemplateDisks(self.template_name)[0]
        logger.info("Copy template disk %s to %s storage domain",
                    disk.get_alias(), self.iscsi)
        ll_disks.copy_disk(disk_id=disk.get_id(), target_domain=self.iscsi)

        def clone_and_verify(storagedomain):
            logger.info("Clone a vm from the Template for storage domains %s",
                        storagedomain)
            vm_name = "vm_cloned_%s_%s" % (self.tcms_test_case, storagedomain)
            assert ll_vms.cloneVmFromTemplate(
                True, vm_name, self.template_name,
                self.cluster_name, storagedomain=storagedomain, clone='true')
            self.vms_to_remove.append(vm_name)

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


@attr(tier=1)
class TestCase336529(IscsiNfsSD):
    """
    Create a shared DC.
    Create 2 SDs - ISCSI and NFS
    Create VM with two disks - one on NFS and the second on ISCSI
    Perform basic snapshot sanity (create,preview,commit,undo,delete)
    """
    __test__ = True
    tcms_test_case = '336529'
    vm_name = "vm_%s" % tcms_test_case

    def setUp(self):
        """
        * Create a vm on nfs sd.
        * Add a disk on iscsi sd to the vm.
        """
        super(TestCase336529, self).setUp()

        helpers.create_and_start_vm(self.vm_name, self.nfs)
        disk_name = "%s_Disk2" % self.vm_name
        helpers.add_disk_to_sd(
            disk_name, self.iscsi, attach_to_vm=self.vm_name,
        )
        self.vms_to_remove.append(self.vm_name)

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


@attr(tier=1)
class TestCase336530(IscsiNfsSD):
    """
    Create a shared DC.
    Create 2 SDs - ISCSI and NFS
    Choose Active Domain and switch it to maintenance.
    After reconstruct is finished, perform operations in the
    storage pool like disk creation, removal and move.
    """
    __test__ = True
    tcms_test_case = '336530'

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_basic_operations_reconstruct(self):
        """
        Perform basic disk sanity after reconstruct
        """
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_ROOT_PASSWORD,
                                  self.data_center_name)
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, self.data_center_name,
        )
        assert found
        self.master_domain = master_domain['masterDomain']
        logger.info("Maintenance master domain %s", self.master_domain)
        assert ll_sd.deactivateStorageDomain(True, self.data_center_name,
                                             self.master_domain)

        logger.info("Waiting for Datacenter to reconstruct")
        assert ll_dc.waitForDataCenterState(self.data_center_name)

        found, master_domain = ll_sd.findMasterStorageDomain(
            True, self.data_center_name,
        )
        assert found
        new_master_domain = master_domain['masterDomain']

        assert new_master_domain != self.master_domain
        ll_sd.wait_for_storage_domain_available_size(
            self.data_center_name, new_master_domain,
        )

        disk_name = "disk_%s" % self.tcms_test_case
        logger.info("Add disk %s", disk_name)
        helpers.add_disk_to_sd(disk_name, new_master_domain)

        logger.info("Activate non master domain %s", self.master_domain)
        assert ll_sd.activateStorageDomain(
            True, self.data_center_name, self.master_domain,
        )

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_ROOT_PASSWORD, self.data_center_name,
        )

        ll_sd.wait_for_storage_domain_available_size(
            self.data_center_name, self.master_domain,
        )
        assert ll_disks.move_disk(
            disk_name=disk_name, target_domain=self.master_domain,
            positive=True,
        )

        logger.info("Delete disk %s", disk_name)
        assert ll_disks.deleteDisk(True, disk_name, async=False)
        assert ll_disks.waitForDisksGone(True, [disk_name])


# TODO: doesn't work - wait until reinitialize is on rest
# RFE https://bugzilla.redhat.com/show_bug.cgi?id=1092374
@attr(tier=1)
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
    __test__ = False
    tcms_test_case = '336594'

    storagedomains = [config.ISCSI_DOMAIN_0]

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_reinitialize(self):
        """
        Reinitialize from unattached storage domain
        """
        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_ROOT_PASSWORD,
                                  self.data_center_name)
        logger.info("Deactivate iSCSI domain")
        ll_sd.deactivateStorageDomain(True, self.data_center_name,
                                      self.iscsi)

        logger.info("Wait for DC state not operational")
        ll_dc.waitForDataCenterState(
            self.data_center_name, state=config.ENUMS[
                'data_center_state_not_operational'],
        )

        logger.info("Create unattached NFS storage domain")
        assert ll_sd.addStorageDomain(
            True, host=self.host, **config.NFS_DOMAIN)

        # TODO: Reinitialize - needs implementation


# TODO: doesn't work, need FC
@attr(tier=1)
class TestCase343102(IscsiNfsSD):
    """
    Create DataCenter of shared type.
    Create FC/iSCSI and NFS/Gluster/POSIX Storage Domains.
    Create disks on each domain.
    Move disk (offline movement) between domains (file to block and block
    to file).
    """
    __test__ = False
    tcms_test_case = '343102'

    def setUp(self):
        """
        * Create ISCSI and NFS SDs.
        * Create a disk on each SD.
        """
        super(TestCase343102, self).setUp()

        # create disks

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_move_between_types(self):
        """
        Move disk (offline movement) between domains (file to block and
        block to file).
        """
        logger.info("Moving disks")
        # Make matrix...


@attr(tier=1)
class TestCase343101(BaseCaseDCMixed):
    """
    Create DataCenter of shared type.
    Create NFS and GlusterFS Storage Domains.
    Create disks on each domain.
    Move disk (offline movement) between domains (NFS to Gluster and
    Gluster to NFS).
    """
    __test__ = True
    tcms_test_case = '343101'

    storagedomains = [config.NFS_DOMAIN, config.GLUSTER_DOMAIN]

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_move_nfs_to_nfs(self):
        """
        Move disks from one nfs storage to another
        """
        self.gluster_disk_name = "gluster_disk"
        self.nfs_disk_name = "nfs_disk"
        helpers.add_disk_to_sd(self.nfs_disk_name, self.nfs)
        helpers.add_disk_to_sd(self.gluster_disk_name, self.glusterfs)

        assert ll_disks.move_disk(
            disk_name=self.nfs_disk_name, target_domain=self.glusterfs,
        )
        assert ll_disks.move_disk(
            disk_name=self.gluster_disk_name, target_domain=self.nfs,
        )

    def tearDown(self):
        """
        Remove created disks
        """
        ll_disks.wait_for_disks_status(
            [self.gluster_disk_name, self.nfs_disk_name],
        )
        if not self.remove_datacenter:
            ll_disks.deleteDisk(True, self.gluster_disk_name)
            ll_disks.deleteDisk(True, self.nfs_disk_name)
            ll_disks.waitForDisksGone(
                True, [self.gluster_disk_name, self.nfs_disk_name],
            )

        super(TestCase343101, self).tearDown()


@attr(tier=3)
class TestCase343383(IscsiNfsSD):
    """
    Create a shared DC.
    Create two Storage Domains - NFS and ISCSI
    Block connectivity from all hosts to storage server which master
    domain is located on.
    After reconstruct is finished, perform operations in the storage
    pool like disk creation, removal and move
    """
    __test__ = True
    tcms_test_case = '343383'

    def setUp(self):
        """
        For GE, set all hosts except for one to maintenance mode
        """
        if config.GOLDEN_ENV:
            status, host = ll_hosts.getAnyNonSPMHost(
                config.HOSTS, cluster_name=self.cluster_name
            )
            self.host = host['hsmHost']
            for host in config.HOSTS:
                if host != self.host:
                    ll_hosts.deactivateHost(True, host)
        else:
            self.host = config.HOSTS[0]
        self.host_ip = ll_hosts.getHostIP(self.host)
        super(TestCase343383, self).setUp()
        self.disk_alias = "disk_{0}".format(self.tcms_test_case)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_reconstruct_master(self):
        """
        Block connectivity from the host to the storage.
        Wait until DC is up.
        Create a disk and remove it.
        """
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, self.data_center_name,
        )
        assert found
        self.master_domain = master_domain['masterDomain']
        found, non_master = ll_sd.findNonMasterStorageDomains(
            True, self.data_center_name,
        )
        assert found
        self.non_master = non_master['nonMasterDomains']

        rc, master_address = ll_sd.getDomainAddress(True, self.master_domain)
        assert rc
        self.master_address = master_address['address']

        # Make sure non master domain is active
        assert ll_sd.waitForStorageDomainStatus(
            True, self.data_center_name, self.non_master[0],
            expectedStatus=config.ENUMS['storage_domain_state_active'])

        logger.info(
            "Blocking outgoing connection from %s to %s", self.host_ip,
            self.master_address,
        )
        assert blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.master_address)

        logger.info("Waiting for the data center to be non responsive")
        assert ll_dc.waitForDataCenterState(
            self.data_center_name,
            config.ENUMS['data_center_state_non_responsive'],
            timeout=TIMEOUT_DATA_CENTER_NON_RESPONSIVE)

        logger.info("... and be up again")
        assert ll_dc.waitForDataCenterState(
            self.data_center_name, timeout=TIMEOUT_DATA_CENTER_RECONSTRUCT)

        logger.info("Add a disk")
        disk_args = {
            'alias': self.disk_alias,
            'provisioned_size': config.GB,
            'sparse': False,
            'format': config.DISK_FORMAT_RAW,
            'interface': config.INTERFACE_IDE,
            'storagedomain': self.non_master[0],
            'bootable': False,
        }
        assert ll_disks.addDisk(True, **disk_args)
        ll_disks.wait_for_disks_status([self.disk_alias])

        logger.info("Delete the disk")
        assert ll_disks.deleteDisk(True, self.disk_alias)

    def tearDown(self):
        """
        Unblock connection and remove created disk in case it stil exists
        """
        unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.master_address,
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_ROOT_PASSWORD, self.data_center_name,
        )

        logger.info("Make sure DC %s is up before cleaning the env",
                    self.data_center_name)
        ll_dc.waitForDataCenterState(
            self.data_center_name, timeout=TIMEOUT_DATA_CENTER_RECONSTRUCT,
        )

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_ROOT_PASSWORD, self.data_center_name,
        )

        if ll_disks.checkDiskExists(True, self.disk_alias):
            ll_disks.wait_for_disks_status([self.disk_alias])
            ll_disks.deleteDisk(True, self.disk_alias)

        if config.GOLDEN_ENV:
            for host in config.HOSTS:
                if ll_hosts.isHostInMaintenance(True, host):
                    ll_hosts.activateHost(True, host)

        super(TestCase343383, self).tearDown()


# TODO: doesn't work - FC
@attr(tier=1)
class TestCase336357(BaseCaseDCMixed):
    """
    Create a shared DC.
    Create 2 Storage Domains of same type (ISCSI and FC, NFS and Gluster)
    Create 2 VMs - First VM with disk on NFS and second VM with disk on ISCSI
    Start VMs.
    Move disk of first VM from NFS domain to Gluster domain
    Move disk of second VM from ISCSI domain to FC domain.
    """
    __test__ = False  # TODO: No FC, write test when FC is available


# TODO: syncAction in doesn't return the response, only the status
# compare the message after is implemented in the framework
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
        self.nfs_vm_disk = ll_vms.getVmDisks(self.nfs_vm)[0].get_alias()
        self.iscsi_vm_disk = ll_vms.getVmDisks(self.iscsi_vm)[0].get_alias()

        assert ll_disks.move_disk(
            disk_name=self.nfs_vm_disk, target_domain=self.iscsi,
            positive=False,
        )
        assert ll_disks.move_disk(
            disk_name=self.iscsi_vm_disk, target_domain=self.nfs,
            positive=False,
        )


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
        self.vms_to_remove.append(self.vm_name)
        helpers.add_disk_to_sd("vm_second_disk", self.nfs,
                               attach_to_vm=self.vm_name)

        vm_ip = get_vm_ip(self.vm_name)
        linux_machine = Machine(
            host=vm_ip, user=config.VM_USER,
            password=config.VM_PASSWORD).util('linux')

        logger.info("Create a partition in newly attached disk")
        success, output = linux_machine.runCmd(
            'echo 0 1024 | sfdisk /dev/sda -uM'.split())
        self.assertTrue(success, "Failed to create partition: %s" % output)

        success, output = linux_machine.runCmd('mkfs.ext4 /dev/sda1'.split())
        self.assertTrue(success, "Failed to create filesystem: %s" % output)


@attr(tier=1)
class TestCase336601(BaseCaseDCMixed):
    """
    Create a shared DC version 3.0
    Create Storage Domain ISCSI and attacht it to DC.            success
    Create Storage Domain NFS and try to attach it to DC.        failure
    Create another Storage Domain ISCSI and try to attach to DC  success
    Remove ISCSI domains from DC and attach NFS domain.           success
    """
    __test__ = True
    tcms_test_case = '336601'

    compatibility_version = "3.0"
    data_center_name = "data_center_{0}".format(tcms_test_case)
    cluster_name = "cluster_name_{0}".format(tcms_test_case)
    new_datacenter_for_ge = True

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_data_centers_compabitility_version_30(self):
        """
        Data centers with compatibility version of 3.0
        """
        self.nfs = config.NFS_DOMAIN['name']
        self.iscsi = config.ISCSI_DOMAIN_0['name']
        self.iscsi2 = config.ISCSI_DOMAIN_1['name']

        assert helpers.add_storage_domain(
            self.data_center_name, self.host_ip, **config.ISCSI_DOMAIN_0)

        logger.info("Try attaching NFS storage domain to the data center")
        assert ll_sd.addStorageDomain(True, host=self.host_ip,
                                      **config.NFS_DOMAIN)
        assert ll_sd.attachStorageDomain(
            False, self.data_center_name, self.nfs, True,
        )

        logger.info("Ading a second iscsi storage domain")
        assert helpers.add_storage_domain(
            self.data_center_name, self.host_ip, **config.ISCSI_DOMAIN_1
        )

        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_ROOT_PASSWORD,
                                  self.data_center_name)
        logger.info("Removing storage domain")
        assert ll_sd.removeStorageDomains(
            True, [self.iscsi2], self.host_ip, 'true',
        )

        logger.info("Waiting for tasks before deactivating the storage domain")
        test_utils.wait_for_tasks(config.VDC, config.VDC_ROOT_PASSWORD,
                                  self.data_center_name)
        assert ll_sd.deactivateStorageDomain(
            True, self.data_center_name, self.iscsi,
        )

        logger.info("Make sure to remove Data Center")
        assert ll_dc.removeDataCenter(True, self.data_center_name)
        assert ll_dc.addDataCenter(
            True, name=self.data_center_name, local=False,
            version=self.compatibility_version,
        )
        assert ll_sd.removeStorageDomain(
            True, self.iscsi, self.host_ip, 'true',
        )
        assert ll_hosts.deactivateHost(True, self.host_ip)
        assert ll_cl.updateCluster(
            True, self.cluster_name, data_center=self.data_center_name,
        )
        assert ll_hosts.activateHost(True, self.host_ip)

        logger.info("Attaching a NFS now should work")
        assert ll_sd.attachStorageDomain(
            True, self.data_center_name, self.nfs,
        )


@attr(tier=1)
class TestCase336617(TestCase):
    """
    Create shared DCs versions 3.0, 3.1, 3.2 and 3.3.
    Create ISCSI domain in this DC.
    Create Gluster Storage Domain and try to attach it to DC. should fail
    """
    __test__ = True
    tcms_test_case = '336617'
    storages = 'N/A'

    data_center_name = "data_center_{0}".format(tcms_test_case)
    cluster_name = "cluster_name_{0}".format(tcms_test_case)

    def setUp(self):
        """
        For Golden Environment remove one host from the data center
        to be used in this test
        """
        if config.GOLDEN_ENV:
            status, host = ll_hosts.getAnyNonSPMHost(
                config.HOSTS, cluster_name=config.CLUSTER_NAME,
            )
            self.host = host['hsmHost']
            self.host_ip = ll_hosts.getHostIP(self.host)
            ll_hosts.deactivateHost(True, self.host)
            ll_hosts.removeHost(True, self.host)
        else:
            self.host = config.HOSTS[0]
            self.host_ip = self.host

    def tearDown(self):
        """
        For Golden Environment put the host back in the original data center
        """
        # In case the test fails, the data center needs to be removed
        try:
            clean_datacenter(
                True, self.data_center_name, vdc=config.VDC,
                vdc_password=config.VDC_ROOT_PASSWORD,
            )
        except EntityNotFound:
            pass

        if config.GOLDEN_ENV:
            ll_hosts.addHost(
                True, name=self.host, root_password=config.HOSTS_PW,
                cluster=config.CLUSTER_NAME, address=self.host_ip,
            )
            ll_hosts.waitForHostsStates(True, self.host)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_gluster_different_compatibility_versions(self):
        """
        Ensure older data center versions do not allow gluster storage domains
        """
        for version in ["3.0", "3.1", "3.2", "3.3"]:
            logger.info("Trying to add glusterfs for DC version %s", version)
            helpers.build_environment(
                compatibility_version=version,
                storage_domains=[config.ISCSI_DOMAIN_0],
                datacenter_name=self.data_center_name,
                cluster_name=self.cluster_name,
                hosts_for_cluster=[self.host_ip],
            )

            # For data center version 3.0, the gluster domain cannot even be
            # added, so don't try to attach the domain
            if version == "3.0":
                added_successfully = False
            else:
                added_successfully = True
            assert ll_sd.addStorageDomain(
                added_successfully, host=self.host_ip, **config.GLUSTER_DOMAIN
            )

            if added_successfully:
                assert ll_sd.attachStorageDomain(
                    False, self.data_center_name,
                    config.GLUSTER_DOMAIN['name'], True,
                )

                assert ll_sd.removeStorageDomain(
                    True, config.GLUSTER_DOMAIN['name'], self.host_ip, 'true'
                )

            clean_datacenter(
                True, self.data_center_name, vdc=config.VDC,
                vdc_password=config.VDC_ROOT_PASSWORD,
            )


@attr(tier=1)
class TestCase336874(BaseCaseDCMixed):
    """
    Create a shared Data Center version 3.0.
    Create POSIX Storage domain.
    Try to attach POSIX SD to Data Center -> should fail with message
    """
    __test__ = True
    tcms_test_case = '336874'
    compatibility_version = "3.0"

    data_center_name = "data_center_{0}".format(tcms_test_case)
    cluster_name = "cluster_name_{0}".format(tcms_test_case)
    new_datacenter_for_ge = True

    message = "The Action add Storage is not supported for this Cluster " \
              "or Data Center compatibility version"

    def test_posix_data_center_30(self):
        """
        Posix domain and Data Center 3.0
        """
        sd = ll_sd._prepareStorageDomainObject(
            positive=False, host=self.host_ip, **config.POSIX_DOMAIN
        )
        response, status = ll_sd.util.create(sd, positive=False, async=False)

        # status is True since we're expecting to fail
        self.assertTrue(
            status, "Adding a POSIX storage domain to a DC 3.0 should fail")
        if opts['engine'] != SDK_ENGINE:
            self.assertTrue(self.message in response.get_detail(),
                            "Error message should be %s" % self.message)


@attr(tier=1)
class TestCase336876(IscsiNfsSD):
    """
    Create a shared DC with two Storage Domans - ISCSI and NFS.
    Create VM with disks on NFS.
    Create template from this VM.
    Copy template's disk from NFS domain to ISCSI domain.
    Create new VM from template that resied on NFS and
    choose thin copy in Resource Allocation.
    """
    __test__ = True

    tcms_test_case = '336876'
    vm_name = "vm_%s" % tcms_test_case
    template_name = "template_%s" % tcms_test_case
    vm_cloned_name = "vm_cloned_%s" % tcms_test_case

    def setUp(self):
        """
        Create a vm in nfs storage and create a template
        """
        super(TestCase336876, self).setUp()
        helpers.create_and_start_vm(self.vm_name, self.nfs)
        self.vms_to_remove.append(self.vm_name)
        assert ll_vms.shutdownVm(True, self.vm_name, async='false')

        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
        )
        self.templates_to_remove.append(self.template_name)

    @tcms(TCMS_TEST_PLAN, tcms_test_case)
    def test_thin_provision_on_block(self):
        """
        Thin provision disk on block form template that resides on NFS

        """
        disk_id = ll_templates.getTemplateDisks(self.template_name)[0].get_id()

        assert ll_disks.copy_disk(disk_id=disk_id, target_domain=self.iscsi)

        logger.info("Cloning vm from template with thin privisioning")
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_cloned_name, self.template_name,
            self.cluster_name, storagedomain=self.nfs, clone='false',
        )
        self.vms_to_remove.append(self.vm_cloned_name)

        disk = ll_vms.getVmDisks(self.vm_cloned_name)[0]
        self.assertTrue(
            disk.get_sparse(),
            "Disk %s should be Thin Proivisioning" % disk.get_alias())


@attr(tier=1)
class TestCase337426(TestCase):
    """
    have a RHEV 3.3 with DC 3.3 of type ISCSI
    upgrade ovirt to 3.4
    Open UI and see if DC type remained 3.3 or 3.4
    Change the comp version of DC to 3.4 and check that it type becomes shared.
    """
    # TODO: This needs to be implemented, and tested using RHEV-H
    __test__ = False
    storages = 'N/A'


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
    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN,
                      config.EXPORT_DOMAIN]

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
        self.vms_to_remove.append(self.vm_name)
        helpers.add_disk_to_sd("vm_second_disk", self.nfs, self.vm_name)

        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        self.vms_to_remove_from_export_domain.append(self.vm_name)
        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, self.cluster_name,
                               self.vm_imported)
        self.vms_to_remove.append(self.vm_imported)
