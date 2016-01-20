"""
Test mixed types DC suite
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Mixed_Types_Data_Center]
"""
import config
import helpers
import logging

from utilities.machine import Machine
from art.unittest_lib import attr, StorageTest as TestCase
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.test_handler.exceptions as exceptions

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.storage_api import (
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

TIMEOUT_DATA_CENTER_RECONSTRUCT = 900
TIMEOUT_DATA_CENTER_NON_RESPONSIVE = 300
CREATE_TEMPLATE_TIMEOUT = 1500
CLONE_FROM_TEMPLATE_TIMEOUT = 1500

SDK_ENGINE = 'sdk'
GLUSTERFS = config.STORAGE_TYPE_GLUSTER
ISCSI = config.STORAGE_TYPE_ISCSI
NFS = config.STORAGE_TYPE_NFS
POSIX = config.STORAGE_TYPE_POSIX
PARTITION_CREATE_CMD = 'echo 0 1024 | sfdisk %s -uM'
MKFS_CMD = 'mkfs.ext4 %s1'


ALL_TYPES = (
    GLUSTERFS, ISCSI, NFS, POSIX
)
VM_ARGS = dict()


def setup_module():
    """
    Prepares environment
    """
    global VM_ARGS
    VM_ARGS = config.create_vm_args.copy()
    VM_ARGS['volumeType'] = False  # Preallocated
    VM_ARGS['volumeFormat'] = config.DISK_FORMAT_RAW


class BaseCaseDCMixed(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    versions. The environment is cleaned up after the run.

    This makes the code cleaner for the tests, adding a bit of time for
    installing a host every time
    """
    __test__ = False

    storagedomains = []
    data_center_name = config.DATA_CENTER_NAME
    cluster_name = config.CLUSTER_NAME

    def setUp(self):
        """
        Add a DC/Cluster with host with the storage domains
        """
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
        if not ll_vms.safely_remove_vms(self.vms_to_remove):
            logger.error(
                "Failed to power off and remove vms %s", self.vms_to_remove
            )
            TestCase.test_failed = True
        for vm in self.vms_to_remove_from_export_domain:
            if not ll_vms.remove_vm_from_export_domain(
                True, vm, self.data_center_name, self.export_domain,
            ):
                logger.error("Failed to remove vm %sd from export domain", vm)
                TestCase.test_failed = True
        for template in self.templates_to_remove:
            if not ll_templates.removeTemplate(True, template):
                logger.error("Failed to remove template %s", template)
                TestCase.test_failed = True
        TestCase.teardown_exception()


class IscsiNfsSD(BaseCaseDCMixed):
    """
    Base case with ISCSI (master) and NFS domain
    """
    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN]


# TODO: doesn't work - need verification when FC is available
@attr(tier=2)
class TestCase4558(BaseCaseDCMixed):
    """
    * Create FC and iSCSI Storage Domains
    * Create disks on each domain
    * Move disk (offline movement) between domains (FC to iSCSI and iSCSI to
    FC)
    """
    polarion_test_case = '4558'
    __test__ = False  # No host with HBA port in broker

    storage_domains = [config.FC_DOMAIN, config.ISCSI_DOMAIN_0]
    fc = config.FC_DOMAIN['name']

    def setUp(self):
        """
        * Create disks on each domain.
        """
        super(TestCase4558, self).setUp()

        logger.info("Add a disk to each storage domain")
        self.iscsi_disk = "iscsi_disk"
        self.fc_disk = "fc_disk"

        helpers.add_disk_to_sd(self.iscsi, self.iscsi_disk)
        helpers.add_disk_to_sd(self.fc, self.fc_disk)

    @polarion("RHEVM3-4558")
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


@attr(tier=2)
class TestCase4561(IscsiNfsSD):
    """
    * Create a shared DC
    * Create ISCSI and NFS storage domains
    * Create VMs with disks on the same domain type
    * Export/Import VM
    * Create Vm with disks on different domain types
    * Export/Import VM
    """
    __test__ = True
    polarion_test_case = '4561'

    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN,
                      config.EXPORT_DOMAIN]
    export_domain = config.EXPORT_DOMAIN['name']
    vm_name = "vm_%s" % polarion_test_case

    @polarion("RHEVM3-4561")
    def test_export_import_vm(self):
        """
        Export-import VMs
        """
        for sd in self.iscsi, self.nfs:
            vm = "vm_%s_%s" % (sd, self.polarion_test_case)
            logger.info("Creating vm %s in storage domain %s", vm, sd)
            vm_args = VM_ARGS.copy()
            vm_args['vmName'] = vm
            vm_args['storageDomainName'] = sd
            vm_args['installation'] = False

            if not storage_helpers.create_vm_or_clone(**vm_args):
                raise exceptions.VMException(
                    'Unable to create vm %s for test' % vm
                )
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
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.iscsi
        vm_args['installation'] = False

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove.append(self.vm_name)
        second_disk = "vm_%s_Disk2" % self.polarion_test_case
        helpers.add_disk_to_sd(second_disk, self.nfs,
                               attach_to_vm=self.vm_name)

        logger.info("Trying export/import for vm %s with multiple disks ", vm)
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        self.vms_to_remove_from_export_domain.append(self.vm_name)
        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, self.cluster_name)


@attr(tier=2)
class TestCase4562(IscsiNfsSD):
    """
    * Create a shared DC
    * Create ISCSI and NFS storage domains
    * Create VM
    * Attach disks to VM from different storage domains
    * Create a snapshot
    * Clone VM from snapshot
    """
    __test__ = True
    polarion_test_case = '4562'

    def setUp(self):
        """
        * Add a new disk to each vms on different sd
        """
        self.vm_name = "vm_{0}_{1}".format(
            self.storage, self.polarion_test_case
        )
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        super(TestCase4562, self).setUp()
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.storage_domains[0]
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove = [self.vm_name]

        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        target_sd = ll_disks.get_other_storage_domain(
            disk=vm_disk, force_type=False
        )
        vm_disk2 = "%s_Disk2_%s" % (self.vm_name, self.polarion_test_case)
        helpers.add_disk_to_sd(
            vm_disk2, target_sd, attach_to_vm=self.vm_name,
        )

    @polarion("RHEVM3-4562")
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

        add_snapshot_and_clone(self.vm_name)


@attr(tier=2)
class TestCase4563(IscsiNfsSD):
    """
    * Create a shared DC
    * Create 2 SDs - ISCSI and NFS
    * Create VM with disks on NFS
    * Make template from this VM
    * Copy template disk's from NFS domain to ISCSI domain
    * Clone a new VM from the template with its disk located on the iSCSI
    domain
    """
    __test__ = True
    polarion_test_case = '4563'

    vm_name = "vm_%s" % polarion_test_case
    template_name = "%s_template" % vm_name

    def setUp(self):
        """
        * Create a vm on a nfs storage domain
        """
        super(TestCase4563, self).setUp()
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.nfs
        vm_args['installation'] = False

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove.append(self.vm_name)

    @polarion("RHEVM3-4563")
    def test_copy_template(self):
        """
        Make template and copy it
        """
        logger.info("Creating template %s from vm %s", self.template_name,
                    self.vm_name)
        assert ll_templates.createTemplate(
            True, timeout=CREATE_TEMPLATE_TIMEOUT, name=self.template_name,
            vm=self.vm_name, cluster=self.cluster_name, storagedomain=self.nfs
        )

        self.templates_to_remove.append(self.template_name)
        disk = ll_templates.getTemplateDisks(self.template_name)[0]
        logger.info("Copy template disk %s to %s storage domain",
                    disk.get_alias(), self.iscsi)
        ll_disks.copy_disk(disk_id=disk.get_id(), target_domain=self.iscsi)

        def clone_and_verify(storagedomain):
            logger.info("Clone a vm from the Template for storage domains %s",
                        storagedomain)
            vm_name = "vm_cloned_%s_%s" % (self.polarion_test_case,
                                           storagedomain)
            assert ll_vms.cloneVmFromTemplate(
                True, vm_name, self.template_name, self.cluster_name,
                timeout=CLONE_FROM_TEMPLATE_TIMEOUT,
                storagedomain=storagedomain, clone='true'
            )
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


@attr(tier=2)
class TestCase4565(IscsiNfsSD):
    """
    * Create a shared DC
    * Create 2 SDs - ISCSI and NFS
    * Create VM with two disks - one on NFS and the second on ISCSI
    * Perform basic snapshot sanity (create, preview, commit, undo, delete)
    """
    __test__ = True
    polarion_test_case = '4565'
    vm_name = "vm_%s" % polarion_test_case
    # Bugzilla history
    # 1253338: restore snapshot via API results in snapshot being stuck on
    # "In preview" status

    def setUp(self):
        """
        * Create a vm on nfs sd.
        * Add a disk on iscsi sd to the vm.
        """
        super(TestCase4565, self).setUp()
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.nfs

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        disk_name = "%s_Disk2" % self.vm_name
        helpers.add_disk_to_sd(
            disk_name, self.iscsi, attach_to_vm=self.vm_name,
        )
        self.vms_to_remove.append(self.vm_name)

    @polarion("RHEVM3-4565")
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

        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], [snap_name]
        )
        logger.info("Commit a snapshot")
        assert ll_vms.commit_snapshot(True, self.vm_name,
                                      ensure_vm_down=True)

        logger.info("Undo a snapshot")
        assert ll_vms.preview_snapshot(True, self.vm_name,
                                       snap_name, ensure_vm_down=True)
        assert ll_vms.undo_snapshot_preview(True, self.vm_name,
                                            ensure_vm_down=True)
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])

        logger.info("Restore a snapshot")
        assert ll_vms.restore_snapshot(
            True, self.vm_name, snap_name, ensure_vm_down=True
        )

        logger.info("Delete a snapshot")
        assert ll_vms.removeSnapshot(True, self.vm_name, snap_name)


@attr(tier=2)
class TestCase4557(IscsiNfsSD):
    """
    * Create a shared DC
    * Create 2 SDs - ISCSI and NFS
    * Choose Active Domain and switch it to maintenance
    * After reconstruct is finished, perform operations in the storage pool
    like disk creation, removal and move
    """
    __test__ = True
    polarion_test_case = '4557'

    @polarion("RHEVM3-4557")
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

        disk_name = "disk_%s" % self.polarion_test_case
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
@attr(tier=2)
class TestCase4556(BaseCaseDCMixed):
    """
    * Create a shared DC
    * Create SD of ISCSI type
    * Attach to DC
    * Maintenance ISCSI domain
    * Create unattached NFS SD (when creating Storage Domain choose 'None' DC)
    * Go to DC-->right click--->Reinitialize DC and choose NFS domain from
    the list
    """
    __test__ = False  # reinitialize not implemented on rest
    polarion_test_case = '4556'

    storagedomains = [config.ISCSI_DOMAIN_0]

    @polarion("RHEVM3-4556")
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
@attr(tier=2)
class TestCase4555(IscsiNfsSD):
    """
    * Create DataCenter of shared type
    * Create FC/iSCSI and NFS/Gluster/POSIX Storage Domains
    * Create disks on each domain
    * Move disk (offline movement) between domains (file to block and block to
    file)
    """
    __test__ = False  # Not running on FC
    polarion_test_case = '4555'

    def setUp(self):
        """
        * Create ISCSI and NFS SDs.
        * Create a disk on each SD.
        """
        super(TestCase4555, self).setUp()

        # create disks

    @polarion("RHEVM3-4555")
    def test_move_between_types(self):
        """
        Move disk (offline movement) between domains (file to block and
        block to file).
        """
        logger.info("Moving disks")
        # Make matrix...


@attr(tier=2)
class TestCase4554(BaseCaseDCMixed):
    """
    * Create DataCenter of shared type
    * Create NFS and GlusterFS Storage Domains
    * Create disks on each domain
    * Move disk (offline movement) between domains (NFS to Gluster and
    Gluster to NFS)
    """
    __test__ = (NFS in opts['storages'] or GLUSTERFS in opts['storages'])
    polarion_test_case = '4554'
    storages = set([NFS, GLUSTERFS])
    storagedomains = [config.NFS_DOMAIN, config.GLUSTER_DOMAIN]

    @polarion("RHEVM3-4554")
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
        for disk in [self.nfs_disk_name, self.gluster_disk_name]:
            if not ll_disks.deleteDisk(True, disk):
                logger.error("Failed to delete disk %s", disk)
                TestCase.test_failed = True

        super(TestCase4554, self).tearDown()


@attr(tier=4)
class TestCase4566(IscsiNfsSD):
    """
    * Create a shared DC
    * Create two Storage Domains - NFS and ISCSI
    * Block connectivity from all hosts to storage server which master domain
    is located on
    * After reconstruct is finished, perform operations in the storage pool
    like disk creation, removal and move
    """
    __test__ = True
    polarion_test_case = '4566'

    def setUp(self):
        """
        For GE, set all hosts except for one to maintenance mode
        """
        if config.GOLDEN_ENV:
            status, host = ll_hosts.getAnyNonSPMHost(
                config.HOSTS, cluster_name=self.cluster_name
            )
            self.host = host['hsmHost']
            # TODO: Remember to make sure there are no tasks running on host
            # before deactivate it
            for host in config.HOSTS:
                if host != self.host:
                    ll_hosts.deactivateHost(True, host)
        else:
            self.host = config.HOSTS[0]
        self.host_ip = ll_hosts.getHostIP(self.host)
        super(TestCase4566, self).setUp()
        self.disk_alias = "disk_{0}".format(self.polarion_test_case)

    @polarion("RHEVM3-4566")
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

        super(TestCase4566, self).tearDown()


@attr(tier=1)
class TestCase4564(IscsiNfsSD):
    """
    * Create a shared DC
    * Create 2 SDs - ISCSI and NFS
    * Create VM with 2 disks - on ISCSI domain and the other in NFS domain
    * Install OS and make file system on both disks
    """
    __test__ = ISCSI in opts['storages'] or NFS in opts['storages']
    storages = set([ISCSI, NFS])

    polarion_test_case = '4564'
    vm_name = "vm_%s" % polarion_test_case
    second_disk_alias = "vm_second_disk_%s" % polarion_test_case

    # Bugzilla history:
    # 1265672: [SCALE] Disk performance is really slow

    @polarion("RHEVM3-4564")
    def test_vm_disk_two_domain_types(self):
        """
        Test having two disks in two different storage domain types
        """
        logger.info(
            "Creating vm %s in iscsi storage domain and installing OS",
            self.vm_name
        )
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.iscsi

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove.append(self.vm_name)
        helpers.add_disk_to_sd(
            self.second_disk_alias, self.nfs, attach_to_vm=self.vm_name
        )
        ll_vms.startVm(True, self.vm_name, config.VM_UP)

        vm_ip = storage_helpers.get_vm_ip(self.vm_name)
        linux_machine = Machine(
            host=vm_ip, user=config.VM_USER,
            password=config.VM_PASSWORD).util('linux')

        device_name = ll_vms.get_vm_disk_logical_name(
            self.vm_name, self.second_disk_alias
        )
        logger.info("Create a partition in newly attached disk")
        partition_cmd = PARTITION_CREATE_CMD % device_name
        success, output = linux_machine.runCmd(partition_cmd.split())
        self.assertTrue(success, "Failed to create partition: %s" % output)
        mkfs_cmd = MKFS_CMD % device_name
        success, output = linux_machine.runCmd(mkfs_cmd.split())
        self.assertTrue(success, "Failed to create filesystem: %s" % output)


@attr(tier=2)
class TestCase4551(IscsiNfsSD):
    """
    * Create a shared DC with two Storage Domains - ISCSI and NFS
    * Create VM with disks on NFS
    * Create template from this VM
    * Copy template's disk from NFS domain to ISCSI domain
    * Create new VM from template that resides on NFS and choose thin copy in
    Resource Allocation
    """
    __test__ = True
    polarion_test_case = '4551'
    vm_name = "vm_%s" % polarion_test_case
    template_name = "template_%s" % polarion_test_case
    vm_cloned_name = "vm_cloned_%s" % polarion_test_case

    def setUp(self):
        """
        Create a vm in nfs storage and create a template
        """
        super(TestCase4551, self).setUp()
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.nfs

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove.append(self.vm_name)
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
        )
        self.templates_to_remove.append(self.template_name)

    @polarion("RHEVM3-4551")
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


@attr(tier=2)
class TestCase4553(IscsiNfsSD):
    """
    * Create shared DC
    * Create ISCSI and NFS domains
    * Create VM with disks on different domains (iscsi and nfs)
    * Export this VM
    * Import VM and choose disk location on different SD
    """
    __test__ = True
    polarion_test_case = '4553'
    storagedomains = [config.ISCSI_DOMAIN_0, config.NFS_DOMAIN,
                      config.EXPORT_DOMAIN]

    export_domain = config.EXPORT_DOMAIN['name']

    vm_name = "vm_%s" % polarion_test_case
    vm_imported = "vm_imported_%s" % polarion_test_case

    @polarion("RHEVM3-4553")
    def test_export_import(self):
        """
        Import VM and choose disk location on different SD
        """
        vm_args = VM_ARGS.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.iscsi
        vm_args['installation'] = False

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        self.vms_to_remove.append(self.vm_name)
        helpers.add_disk_to_sd("vm_second_disk", self.nfs, self.vm_name)

        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        self.vms_to_remove_from_export_domain.append(self.vm_name)
        assert ll_vms.importVm(True, self.vm_name, self.export_domain,
                               self.nfs, self.cluster_name,
                               self.vm_imported)
        self.vms_to_remove.append(self.vm_imported)
