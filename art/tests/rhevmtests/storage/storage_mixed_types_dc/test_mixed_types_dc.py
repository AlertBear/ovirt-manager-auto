"""
Test mixed types DC suite
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Mixed_Types_Data_Center]
"""

import config
import helpers
import pytest

from art.unittest_lib import (
    StorageTest as TestCase,
    tier2,
    tier3,
    tier4,
    testflow,
    storages,
)
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates

from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion, bz
import rhevmtests.storage.helpers as storage_helpers
from art.test_handler.settings import ART_CONFIG
from rhevmtests.storage.fixtures import (
    remove_vms, delete_disks, unblock_connectivity_storage_domain_teardown,
    delete_disk, clean_export_domain, create_template,
    put_all_hsm_hosts_to_maintenance
)
from fixtures import (
    init_storage_domains, add_disk_to_vm_on_iscsi, init_parameters,
    create_vm_on_nfs, create_disks_on_selected_storage_domains,
    remove_cloned_vm
)


@storages((config.NOT_APPLICABLE,))
@pytest.mark.usefixtures(
    init_storage_domains.__name__,
    clean_export_domain.__name__,
    remove_vms.__name__
)
class BaseCaseDCMixed(TestCase):
    """
    Base Case for building an environment with specific storage domains and
    versions. The environment is cleaned up after the run.
    """

    __test__ = False
    vol_type = True


class IscsiNfsSD(BaseCaseDCMixed):
    """
    Base case with ISCSI (master) and NFS domain
    """

    __test__ = config.NFS in '\t'.join(
        config.STORAGE_NAME
    ) and config.ISCSI in '\t'.join(
        config.STORAGE_NAME
    )
    storage_domains = {
        config.NFS: None,
        config.ISCSI: None
    }


@pytest.mark.usefixtures(
    create_disks_on_selected_storage_domains.__name__
)
# TODO: doesn't work - need verification when FC is available
class TestCase4558(BaseCaseDCMixed):
    """
    * Create FC and iSCSI Storage Domains
    * Create disks on each domain
    * Move disk (offline movement) between domains (FC to iSCSI and iSCSI to
    FC)
    """
    polarion_test_case = '4558'
    __test__ = False  # No host with HBA port in broker
    storage_domains = {
        config.ISCSI: None,
        config.FCP: None
    }
    domains_to_create_disks_on = [config.ISCSI, config.FCP]
    disks = list()

    @polarion("RHEVM3-4558")
    @tier2
    def test_move_disks(self):
        """
        Move disk (offline movement) between domains
        (FC to iSCSI and iSCSI to FC).
        """
        # Skipping until supports move of disks

        testflow.step("Moving disks between domains")
        assert ll_disks.move_disk(
            disk_name=self.disks[0],
            target_domain=self.storage_domains[config.FCP]
        ), (
            "Failed to move disk %s to storage domain %s" % (
                self.disks[0], self.storage_domains[config.FCP]
            )
        )
        assert ll_disks.move_disk(
            disk_name=self.disks[1],
            target_domain=self.storage_domains[config.ISCSI]
        ), (
            "Failed to move disk %s to storage domain %s" % (
                self.disks[1], self.storage_domains[config.ISCSI]
            )
        )


@pytest.mark.usefixtures(
    remove_vms.__name__,
    clean_export_domain.__name__
)
class TestCase4561(IscsiNfsSD):
    """
    * Create VMs with disks on the same domain type
    * Export/Import VM
    * Create VM with disks on different domain types
    * Export/Import VM
    """

    polarion_test_case = '4561'
    vms_to_remove_from_export_domain = list()

    @polarion("RHEVM3-4561")
    @tier2
    def test_export_import_vm(self):
        """
        Export-import VMs
        """
        vm = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = vm
        vm_args['storageDomainName'] = self.storage_domains[config.ISCSI]
        vm_args['installation'] = False
        testflow.step(
            "Creating VM %s with disk on storage domain %s",
            vm, self.storage_domains[config.ISCSI]
        )
        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s on storage domain %s" % (
                vm, self.storage_domains[config.ISCSI]
            )
        )
        testflow.step("Exporting VM %s to export domain %s" % (
            vm, config.EXPORT_DOMAIN_NAME
        )
        )
        assert ll_vms.exportVm(True, vm, config.EXPORT_DOMAIN_NAME), (
            "Failed to export VM %s to export domain %s" % (
                vm, config.EXPORT_DOMAIN_NAME
            )
        )
        self.vms_to_remove_from_export_domain.append(vm)
        assert ll_vms.removeVm(True, vm), "Failed to remove VM %s" % vm
        imported_vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM)
        assert ll_vms.importVm(
            True, vm, config.EXPORT_DOMAIN_NAME,
            self.storage_domains[config.ISCSI],
            config.CLUSTER_NAME, imported_vm_name
        ), (
            "Failed to import VM %s from export domain %s" % (
                vm, config.EXPORT_DOMAIN_NAME
            )
        )
        self.vm_names.append(imported_vm_name)
        self.vms_to_remove_from_export_domain.remove(vm)
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        testflow.step(
            "Creating VM %s with disks in different domains", self.vm_name
        )
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = self.storage_domains[config.ISCSI]
        vm_args['installation'] = False

        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s" % self.vm_name
        )
        self.vm_names.append(self.vm_name)
        second_disk = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
        testflow.step(
            "Creating and attaching second disk %s to VM %s", second_disk,
            self.vm_name
        )
        helpers.add_disk_to_sd(
            second_disk, self.storage_domains[config.NFS],
            attach_to_vm=self.vm_name
        )
        testflow.step(
            "Trying export/import for VM %s with multiple disks ", self.vm_name
        )
        assert ll_vms.exportVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME
        ), (
            "Failed to export VM %s to export domain %s" % (
                self.vm_name, config.EXPORT_DOMAIN_NAME
            )
        )
        self.vms_to_remove_from_export_domain.append(self.vm_name)

        assert ll_vms.removeVm(True, self.vm_name), (
            "Failed to remove VM %s" % self.vm_name
        )
        self.vm_names.remove(self.vm_name)
        assert ll_vms.importVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME,
            self.storage_domains[config.NFS], config.CLUSTER_NAME
        ), (
            "Failed to import VM %s from export domain %s to storage domain %s"
            % (
                self.vm_name, config.EXPORT_DOMAIN_NAME,
                self.storage_domains[config.NFS]
            )
        )
        self.vms_to_remove_from_export_domain.remove(self.vm_name)
        self.vm_names.append(self.vm_name)


@pytest.mark.usefixtures(
    create_vm_on_nfs.__name__,
    add_disk_to_vm_on_iscsi.__name__
)
class TestCase4562(IscsiNfsSD):
    """
    * Create VM
    * Attach disks to VM from different storage domains
    * Create a snapshot
    * Clone VM from snapshot
    """

    polarion_test_case = '4562'

    @polarion("RHEVM3-4562")
    @tier3
    @bz({'1435967': {}})
    def test_clone_from_snapshot(self):
        """
        Creates a new snapshots and clones VM from it for both VMS
        """
        def get_sd_id(w):
            return w.get_storage_domains().get_storage_domain()[0].get_id()

        def add_snapshot_and_clone(vm_name):
            snapshot_name = "%s_snapshot" % vm_name
            cloned_vm_name = "%s_cloned" % vm_name
            assert ll_vms.addSnapshot(True, vm_name, snapshot_name), (
                "Failed to add snapshot %s to VM %s" % (
                    snapshot_name, snapshot_name
                )
            )
            assert ll_vms.cloneVmFromSnapshot(
                True, cloned_vm_name, cluster=config.CLUSTER_NAME,
                vm=vm_name, snapshot=snapshot_name,
            ), "Failed to clone VM from snapshot %s" % snapshot_name

            self.vm_names.append(cloned_vm_name)
            disks = ll_vms.getVmDisks(cloned_vm_name)
            assert get_sd_id(disks[0]) != get_sd_id(
                disks[1]
            ), "Disks are not in different storage domains"
            testflow.step(
                "Starting up VM %s to make sure is operational", cloned_vm_name
            )
            assert ll_vms.startVm(
                True, cloned_vm_name, config.VM_UP
            ), "Failed to start VM %s" % cloned_vm_name

        add_snapshot_and_clone(self.vm_name)


@pytest.mark.usefixtures(
    create_vm_on_nfs.__name__,
    create_template.__name__,
    remove_vms.__name__,
)
class TestCase4563(IscsiNfsSD):
    """
    * Create VM with disks on NFS
    * Make template from this VM
    * Copy template disk's from NFS domain to ISCSI domain
    * Clone a new VM from the template with its disk located on the iSCSI
    domain
    """

    polarion_test_case = '4563'

    @polarion("RHEVM3-4563")
    @tier3
    def test_copy_template(self):
        """
        Copy a template's disk from NFS to ISCSI domain and clone a new VM
        from the template with the disk residing on NFS ISCSI domain
        """

        disk = ll_templates.getTemplateDisks(self.template_name)[0]
        testflow.step(
            "Copy template disk %s to %s storage domain",
            disk.get_alias(), self.storage_domains[config.ISCSI]
        )
        assert ll_disks.copy_disk(
            disk_id=disk.get_id(),
            target_domain=self.storage_domains[config.ISCSI]
        ), (
            "Failed to copy disk %s to storage domain %s" % (
                disk.get_alias(), self.storage_domains[config.ISCSI]
            )
        )
        assert ll_disks.wait_for_disks_status(
            disk.get_id(), timeout=240
        ), (
            "Disk %s was not in the expected state 'OK'" %
            self.disks_to_remove[0]
        )

        def clone_and_verify(storagedomain):
            testflow.step(
                "Clone a VM from template to storage domain %s",
                storagedomain
            )
            vm_name = "vm_cloned_%s_%s" % (self.polarion_test_case,
                                           storagedomain)
            assert ll_vms.cloneVmFromTemplate(
                True, vm_name, self.template_name, config.CLUSTER_NAME,
                timeout=config.CLONE_FROM_TEMPLATE_TIMEOUT,
                storagedomain=storagedomain, clone=True
            ), "Failed to clone VM from template %s" % self.template_name
            self.vm_names.append(vm_name)

            disk_id = ll_vms.getVmDisks(vm_name)[0].get_id()
            testflow.step(
                "Verify disk %s is in storage domain %s", disk_id,
                storagedomain
            )
            assert disk_id in map(
                lambda w: w.get_id(),
                ll_disks.getStorageDomainDisks(storagedomain, False)
            ), "Failed to get storage domain for disk id %s" % disk_id

        clone_and_verify(self.storage_domains[config.ISCSI])
        clone_and_verify(self.storage_domains[config.NFS])


@pytest.mark.usefixtures(
    create_vm_on_nfs.__name__,
    add_disk_to_vm_on_iscsi.__name__
)
class TestCase4565(IscsiNfsSD):
    """
    * Create VM with two disks - one on NFS and the second on ISCSI
    * Perform basic snapshot sanity (create, preview, commit, undo, delete)
    """
    polarion_test_case = '4565'

    @polarion("RHEVM3-4565")
    @tier2
    def test_snapshot_operations(self):
        """
        Perform basic snapshot sanity (create, preview, commit, undo, delete)
        """
        snap_name = "%s_snap_1" % self.vm_name

        testflow.step("Create a snapshot %s", snap_name)
        assert ll_vms.addSnapshot(True, self.vm_name, snap_name), (
            "Failed to create snapshot %s to VM %s" % (
                snap_name, self.vm_name
            )
        )
        testflow.step("Preview a snapshot %s", snap_name)
        assert ll_vms.preview_snapshot(
            True, self.vm_name, snap_name, ensure_vm_down=True
        ), (
            "Failed to preview snapshot %s VM name %s" % (
                snap_name, self.vm_name
            )
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_IN_PREVIEW], [snap_name]
        )
        testflow.step("Commit a snapshot")
        assert ll_vms.commit_snapshot(
            True, self.vm_name, ensure_vm_down=True
        ), "Failed to commit snapshot %s" % snap_name

        testflow.step("Preview snapshot %s", snap_name)
        assert ll_vms.preview_snapshot(
            True, self.vm_name, snap_name, ensure_vm_down=True
        ), "Failed to preview snapshot %s" % snap_name
        assert ll_vms.undo_snapshot_preview(
            True, self.vm_name, ensure_vm_down=True
        ), "Failed to undo snapshot preview %s" % snap_name
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])

        testflow.step("Restore a snapshot %s", snap_name)
        assert ll_vms.restore_snapshot(
            True, self.vm_name, snap_name, ensure_vm_down=True
        ), "Failed to restore snapshot %s" % snap_name

        testflow.step("Delete a snapshot %s", snap_name)
        assert ll_vms.removeSnapshot(True, self.vm_name, snap_name), (
            "Failed to delete snapshot %s" % snap_name
        )


class TestCase4557(IscsiNfsSD):
    """
    * Choose Active Domain and switch it to maintenance
    * After reconstruct is finished, perform operations in the storage pool
    like disk creation, removal and move
    """
    polarion_test_case = '4557'

    @bz({'1422508': {}})
    @polarion("RHEVM3-4557")
    @tier2
    def test_basic_operations_reconstruct(self):
        """
        Perform basic disk sanity after reconstruct
        """
        testflow.step(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME,
        )
        assert found, (
            "Unable to find master storage domain for data center %s" %
            config.DATA_CENTER_NAME
        )
        self.master_domain = master_domain['masterDomain']
        testflow.step("Maintenance master domain %s", self.master_domain)
        assert ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.master_domain), (
            "Failed to deactivate storage domain %s" % self.master_domain
        )
        testflow.step(
            "Waiting for Data center %s to reconstruct",
            config.DATA_CENTER_NAME
        )
        assert ll_dc.waitForDataCenterState(config.DATA_CENTER_NAME), (
            "Waiting for Data center %s to reconstruct has reached timeout"
        )
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME,
        )
        assert found, (
            "Failed to find master storage domain for data center %s" %
            config.DATA_CENTER_NAME
        )
        new_master_domain = master_domain['masterDomain']
        assert new_master_domain != self.master_domain, (
            "Failed to reconstruct - master storage domain is still %s" %
            self.master_domain
        )
        ll_sd.wait_for_storage_domain_available_size(
            config.DATA_CENTER_NAME, new_master_domain
        )
        disk_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
        testflow.step("Add disk %s", disk_name)
        helpers.add_disk_to_sd(disk_name, new_master_domain)

        testflow.step("Activate non master domain %s", self.master_domain)
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.master_domain
        ), "Failed to activate non master domain %s" % self.master_domain

        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)

        ll_sd.wait_for_storage_domain_available_size(
            config.DATA_CENTER_NAME, self.master_domain
        )
        testflow.step("Move disk %s", disk_name)
        assert ll_disks.move_disk(
            disk_name=disk_name, target_domain=self.master_domain,
            positive=True, wait=True
        ), ("Failed moving disk %s to storage domain %s" % (
            disk_name, self.master_domain
        )
        )
        testflow.step("Delete disk %s", disk_name)
        assert ll_disks.deleteDisk(True, disk_name, async=False), (
            "Failed to delete disk %s" % disk_name
        )
        assert ll_disks.waitForDisksGone(True, [disk_name]), (
            "Disk timeout has been reached - disk is still in the system" %
            disk_name

        )


# TODO: doesn't work - wait until reinitialize is on rest
# RFE https://bugzilla.redhat.com/show_bug.cgi?id=1092374
# Issue 1092374 is in status won't fix
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

    @polarion("RHEVM3-4556")
    @tier2
    def test_reinitialize(self):
        """
        Reinitialize from unattached storage domain
        """
        testflow.step(
            "Waiting for tasks before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        testflow.step(
            "Deactivate iSCSI storage domain %s", self.iscsi_storage_doamin
        )
        ll_sd.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.iscsi_storage_domain
        )

        testflow.step("Wait for DC state not operational")
        ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME, state=config.ENUMS[
                'data_center_state_not_operational'
            ]
        )

        testflow.step("Create unattached NFS storage domain")
        assert ll_sd.addStorageDomain(
            True, host=self.host, **config.NFS_DOMAIN
        ), "Failed to create NFS storage domain"

        # TODO: Reinitialize - needs implementation


# TODO: doesn't work, need FC
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

    @polarion("RHEVM3-4555")
    @tier2
    def test_move_between_types(self):
        """
        Move disk (offline movement) between domains (file to block and
        block to file).
        """
        testflow.step("Moving disks")
        # Make matrix...


@pytest.mark.usefixtures(
    init_storage_domains.__name__,
    delete_disks.__name__
)
class TestCase4554(BaseCaseDCMixed):
    """
    * Create disks on NFS and GlusterFS Storage Domains
    * Move disk (offline movement) between domains (NFS to Gluster and
    Gluster to NFS)
    """

    __test__ = (config.NFS in ART_CONFIG['RUN']['storages'] and
                config.GLUSTERFS in ART_CONFIG['RUN']['storages'])

    polarion_test_case = '4554'

    storage_domains = {
        config.NFS: None,
        config.GLUSTERFS: None
    }

    @polarion("RHEVM3-4554")
    @tier3
    def test_move_nfs_to_glusterfs_and_vice_verca(self):
        """
        Move disks from one NFS storage to GlusterFS and vice versa
        """
        gluster_disk = storage_helpers.create_unique_object_name(
            "gluster_disk", config.OBJECT_TYPE_DISK
        )
        nfs_disk = storage_helpers.create_unique_object_name(
            "nfs_disk", config.OBJECT_TYPE_DISK
        )
        helpers.add_disk_to_sd(
            nfs_disk, self.storage_domains[config.NFS]
        )
        helpers.add_disk_to_sd(
            gluster_disk, self.storage_domains[config.GLUSTERFS]

        )
        assert ll_disks.move_disk(
            disk_name=nfs_disk,
            target_domain=self.storage_domains[config.GLUSTERFS],
        ), (
            "Failed moving disk %s to storage domain %s" % (
                nfs_disk, self.storage_domains[config.GLUSTERFS]
            )
        )
        self.disks_to_remove.append(nfs_disk)
        assert ll_disks.move_disk(
            disk_name=gluster_disk,
            target_domain=self.storage_domains[config.NFS]
        ), (
            "Failed moving disk %s to storage domain %s" % (
                gluster_disk, self.storage_domains[config.NFS]
            )
        )
        self.disks_to_remove.append(gluster_disk)


@pytest.mark.usefixtures(
    init_parameters.__name__,
    put_all_hsm_hosts_to_maintenance.__name__,
    delete_disk.__name__,
    unblock_connectivity_storage_domain_teardown.__name__
)
class TestCase4566(IscsiNfsSD):
    """
    * Block connectivity from all hosts to storage server which master domain
    is located on
    * After reconstruct is finished, perform operations in the storage pool
    like disk creation, removal and move
    """

    polarion_test_case = '4566'

    @bz({'1455273': {}})
    @polarion("RHEVM3-4566")
    @tier4
    def test_reconstruct_master(self):
        """
        Block connectivity from the host to the storage.
        Wait until DC is up.
        Create a disk and remove it.
        """

        # Make sure non master domain is active
        assert ll_sd.wait_for_storage_domain_status(
            True, config.DATA_CENTER_NAME, self.non_master[0],
            expected_status=config.ENUMS['storage_domain_state_active']
        ), (
            "Non-master storage domain %s is not in active state" %
            self.non_master[0]
        )

        testflow.step(
            "Blocking outgoing connection from %s to %s", self.host_ip,
            self.storage_domain_ip,
        )
        assert storage_helpers.blockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        ), (
            "Failed to block outgoing connection from host %s to storage"
            "domain %s" % (self.non_master, self.master_domain)
        )

        testflow.step("Waiting for the data center to be non responsive")
        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME,
            config.ENUMS['data_center_state_non_responsive'],
            timeout=config.TIMEOUT_DATA_CENTER_NON_RESPONSIVE
        ), (
            "Data center %s failed to become unresponsive" %
            config.DATA_CENTER_NAME
        )

        testflow.step("... and be up again")
        assert ll_dc.waitForDataCenterState(
            config.DATA_CENTER_NAME,
            timeout=config.TIMEOUT_DATA_CENTER_RECONSTRUCT
        ), "Data center %s failed to reconstruct" % config.DATA_CENTER_NAME

        testflow.step("Add a disk")
        disk_args = config.disk_args.copy()
        disk_args['provisioned_size'] = config.GB
        disk_args['storagedomain'] = self.non_master[0]
        disk_args['format'] = config.DISK_FORMAT_RAW
        disk_args['sparse'] = False
        disk_args['alias'] = self.disk_name

        assert ll_disks.addDisk(True, **disk_args)
        ll_disks.wait_for_disks_status([self.disk_name]), (
            "Failed to add disk %s" % self.disk_name
        )

        testflow.step("Deleting disk %s", self.disk_name)
        assert ll_disks.deleteDisk(True, self.disk_name), (
            "Failed to delete disk %s" % self.disk_name
        )


class TestCase4564(IscsiNfsSD):
    """
    * Create VM with 2 disks - on ISCSI domain and the other in NFS domain
    * Install OS and make file system on both disks
    """

    __test__ = (config.ISCSI in ART_CONFIG['RUN']['storages'] or
                config.NFS in ART_CONFIG['RUN']['storages'])

    polarion_test_case = '4564'

    # Bugzilla history:
    # 1265672: [SCALE] Disk performance is really slow

    @polarion("RHEVM3-4564")
    @tier2
    def test_vm_disk_two_domain_types(self):
        """
        Test having two disks in two different storage domain types
        """
        second_disk_alias = storage_helpers.create_unique_object_name(
            "vm_second_disk", config.OBJECT_TYPE_DISK
        )
        vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        testflow.step("Cloning VM %s from template", vm_name)
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = vm_name
        vm_args['storageDomainName'] = self.storage_domains[config.NFS]

        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s for test %s" % (
                vm_name, self.polarion_test_case
            )
        )
        self.vm_names.append(vm_name)
        testflow.step(
            "Creating disk %s on storage domain %s",
            second_disk_alias, self.storage_domains[config.ISCSI]
        )
        helpers.add_disk_to_sd(
            second_disk_alias, self.storage_domains[config.ISCSI],
            attach_to_vm=vm_name
        )
        ll_vms.startVm(True, vm_name, config.VM_UP, True)
        linux_machine = storage_helpers.get_vm_executor(vm_name)
        device_name = ll_vms.get_vm_disk_logical_name(
            vm_name, second_disk_alias
        )
        testflow.step("Create a partition in newly attached disk")
        partition_cmd = config.PARTITION_CREATE_CMD % device_name
        assert storage_helpers._run_cmd_on_remote_machine(
            vm_name, partition_cmd, linux_machine
        ), "Failed to create partition"
        mkfs_cmd = storage_helpers.CREATE_FILESYSTEM_CMD % (
            'ext4', device_name
        )
        testflow.step("Creating a filesystem on the partition")
        assert storage_helpers._run_cmd_on_remote_machine(
            vm_name, mkfs_cmd, linux_machine
        ), "Failed to create filesystem"


@pytest.mark.usefixtures(
    create_vm_on_nfs.__name__,
    create_template.__name__,
    remove_cloned_vm.__name__
)
class TestCase4551(IscsiNfsSD):
    """
    * Create VM with disks on NFS
    * Create template from this VM
    * Copy template's disk from NFS domain to ISCSI domain
    * Create new VM from template that resides on NFS and choose thin copy in
    Resource Allocation
    """

    polarion_test_case = '4551'
    cloned_vm = storage_helpers.create_unique_object_name(
        "cloned_vm", config.OBJECT_TYPE_VM
    )

    @polarion("RHEVM3-4551")
    @tier3
    def test_thin_provision_on_block(self):
        """
        Thin provision disk on block form template that resides on NFS

        """
        disk_id = ll_templates.getTemplateDisks(self.template_name)[0].get_id()

        assert ll_disks.copy_disk(
            disk_id=disk_id, target_domain=self.storage_domains[config.ISCSI]
        ), (
            "Failed to copy disk %s to storage domain %s" % (
                disk_id, self.storage_domains[config.ISCSI]
            )
        )
        ll_disks.wait_for_disks_status(disk_id, key='id')

        testflow.step("Cloning VM from template with thin provisioning")
        assert ll_vms.cloneVmFromTemplate(
            True, self.cloned_vm, self.template_name,
            config.CLUSTER_NAME,
            storagedomain=self.storage_domains[config.NFS],
            clone=False
        ), (
            "Failed to clone VM from template %s (deep copy)" %
            self.template_name
        )
        disk = ll_vms.getVmDisks(self.cloned_vm)[0]
        assert disk.get_sparse(), (
            "Disk %s should be Thin Provision" % disk.get_alias()
        )


class TestCase4553(IscsiNfsSD):
    """
    * Create VM with disks on different domains (ISCSI and NFS)
    * Export this VM
    * Import VM and choose disk location on different SD
    """

    polarion_test_case = '4553'

    @polarion("RHEVM3-4553")
    @tier2
    def test_export_import(self):
        """
        Import VM and choose disk location on different SD
        """
        imported_vm = storage_helpers.create_unique_object_name(
            'imported_vm', config.OBJECT_TYPE_VM
        )
        vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        vm_args = config.create_vm_args.copy()
        vm_args['vmName'] = vm_name
        vm_args['storageDomainName'] = self.storage_domains[config.ISCSI]
        vm_args['installation'] = False

        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s for test" %
            (vm_name, self.polarion_test_case)
        )
        self.vm_names.append(vm_name)
        helpers.add_disk_to_sd(
            "vm_second_disk", self.storage_domains[config.ISCSI], vm_name
        )
        assert ll_vms.exportVm(True, vm_name, config.EXPORT_DOMAIN_NAME), (
            "Failed to export VM % to export domain %s" % (
                vm_name, config.EXPORT_DOMAIN_NAME
            )
        )
        assert ll_vms.importVm(
            True, vm_name, config.EXPORT_DOMAIN_NAME,
            self.storage_domains[config.NFS], config.CLUSTER_NAME, imported_vm
        ), (
            "Failed to import VM %s from export domain %s" % (
                vm_name, config.EXPORT_DOMAIN_NAME
            )
        )
        self.vm_names.append(imported_vm)
