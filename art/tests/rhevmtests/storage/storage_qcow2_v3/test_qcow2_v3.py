"""
4.1 qcow2 v3
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_qcow2_v3
"""

import logging
import helpers
from rhevmtests.storage import helpers as storage_helpers
from art.unittest_lib.common import testflow
import pytest
import config
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
)
from art.test_handler.tools import polarion, bz
import rhevmtests.helpers as rhevm_helpers

from rhevmtests.storage.fixtures import remove_vm  # noqa

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    storagedomains as ll_sd,
    clusters as ll_clusters,
    vms as ll_vms,
    disks as ll_disks,
    jobs as ll_jobs,
    hosts as ll_hosts,
    templates as ll_templates,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)

from fixtures import (
    init_hsm_host, create_one_or_more_storage_domains_same_type_for_upgrade,
    remove_unattached_domain, initialize_dc_parameters_for_upgrade,
    init_spm_host, init_test_vm_name, init_base_params,
    deactivate_and_remove_non_master_domains, init_test_template_name,
    get_template_from_cluster,
)

from rhevmtests.storage.fixtures import (
    clean_dc, create_vm, add_disk, export_vm,
    remove_template, attach_disk, create_export_domain, remove_export_domain,
    create_several_snapshots, import_image_from_glance, remove_vms, create_dc,
    add_nic, create_file_than_snapshot_several_times,
)

from art.unittest_lib import attr, StorageTest as TestCase
logger = logging.getLogger(__name__)


@pytest.mark.skipif(True, reason="Due to sporadic bz 1449944 & 1456268")
@pytest.mark.usefixtures(
    init_base_params.__name__,
    init_spm_host.__name__,
    init_hsm_host.__name__,
    initialize_dc_parameters_for_upgrade.__name__,
    create_dc.__name__,
    create_one_or_more_storage_domains_same_type_for_upgrade.__name__,
    remove_unattached_domain.__name__,
    clean_dc.__name__,
    deactivate_and_remove_non_master_domains.__name__,
)
class BaseTestCase(TestCase):
    """
    Implement the common setup for upgrading v3 -> v4

    1. Create DC + cluster + sd's on ver3 first

    Two functions to use by need:
    - DC Upgrade from ver3->ver4 function + verification
    - DC Upgrade from ver3->ver4 function without verification(for engine/vdsm
    restart/kill)
    """

    __test__ = False

    def data_center_upgrade_without_verification(self):
        """
        Upgarde a DC + cluster
        """
        testflow.setup(
            "Upgrading cluster %s from version %s to version %s ",
            self.cluster_name, self.cluster_version,
            self.cluster_upgraded_version
        )
        assert ll_clusters.updateCluster(
            True, self.cluster_name,
            version=self.cluster_upgraded_version,
        ), "Failed to upgrade compatibility version of cluster"
        testflow.setup(
            "Upgrading data center %s from version %s to version %s ",
            self.new_dc_name, self.dc_version, self.dc_upgraded_version
        )
        assert ll_dc.update_datacenter(
            True, datacenter=self.new_dc_name,
            version=self.dc_upgraded_version
        ), "Upgrading data center %s failed" % self.new_dc_name

    def data_center_upgrade(self):
        """
        Upgarde a DC + cluster and verify its upgraded
        """
        self.data_center_upgrade_without_verification()
        sds = ll_sd.getDCStorages(self.new_dc_name, get_href=False)

        for sd_obj in sds:
            if sd_obj.get_type() == config.TYPE_DATA:
                was_upgraded = ll_sd.checkStorageFormatVersion(
                    True, sd_obj.get_name(), self.upgraded_storage_format
                )
                logger.info(
                    "Checking that %s was upgraded: %s", sd_obj.get_name(),
                    was_upgraded
                )
                assert was_upgraded, "SD %s was not upgraded to %s" % (
                    sd_obj.get_name(), self.upgraded_storage_format
                )
            else:
                logger.info(
                     "SD %s is not data type" % sd_obj.get_name()
                 )

    def migration_test(self, live):
        """
        Live/cold migration test flow for TCs 18344/3

        Args:
            live (bool): True if live migration , False if cold migration
        """
        disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert disk_name, "No disks were found on VM %s" % self.vm_name
        testflow.step(
            "Upgrade DC %s to v4 & restart engine ", self.new_dc_name
        )
        self.data_center_upgrade()
        testflow.step(
            "Verify that the snapshot images are version %s", config.QCOW_V2
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.DISK_QCOW_V2
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V2
        )
        if live:
            testflow.step("Start the VM %s", self.vm_name)
            assert ll_vms.startVm(
                True, self.vm_name, config.VM_UP, wait_for_ip=True
            ), "VM %s did not reach %s state" % (self.vm_name, config.VM_UP)
        testflow.step(
            "Copy template disk %s to target SD %s for migration",
            self.template_disk_name, self.sd_names[1]
        )
        ll_templates.copyTemplateDisk(
            self.template_name, self.template_disk_name, self.sd_names[1])
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        ll_disks.wait_for_disks_status(self.template_disk_name)

        testflow.step(
            "Storage migration of VM %s from SD %s to SD %s",
            self.vm_name, self.sd_names[0], self.sd_names[1]
        )
        ll_vms.migrate_vm_disks(
            self.vm_name, target_domain=self.sd_names[1]
        ), "Migration of vm %s to SD %s failed" % (
            self.vm_name, self.sd_names[1]
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert ll_vms.verify_vm_disk_moved(
            self.vm_name, vm_disk, self.sd_names[0],
            self.sd_names[1]
        ), "Failed to migrate disk %s" % vm_disk
        testflow.step(
            "Verify that the snapshot images are version %s", config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.DISK_QCOW_V3
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.sd_names[1], expected_qcow_version=config.QCOW_V3
        )
        if live is True:
            testflow.step(
                "Power off VM %s and preview snapshot %s", self.vm_name,
                self.snapshot_list[0]
            )
            assert ll_vms.stop_vms_safely([self.vm_name]), (
                "Shutdown to vm % failed" % self.vm_name
            )
            ll_vms.waitForVMState(self.vm_name, config.VM_POWER_DOWN)

        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshot_list[0]
        ), "Failed to preview snapshot %s" % self.snapshot_list[0]
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
        testflow.step("Commit snapshot on VM %s", self.vm_name)
        assert ll_vms.commit_snapshot(True, self.vm_name), (
            "Failed restoring a previewed snapshot %s"
            % self.snapshot_description
        )
        testflow.step(
            "Start the VM %s and verify that data can be written to the disk",
            self.vm_name
        )
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        ), "VM %s did not reach %s state" % (self.vm_name, config.VM_UP)
        logger.info("Trying to write to disk %s" % disk_name)
        status, out = storage_helpers.perform_dd_to_disk(
            self.vm_name, disk_name
        )
        assert status, "Error found %s" % out
        snapshot_description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.step(
            "Creating snapshot %s of VM %s",
            snapshot_description, self.new_vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, snapshot_description
        ), "Failed to create snapshot of VM %s" % self.new_vm_name
        ll_vms.wait_for_vm_snapshots(
            self.new_vm_name, [config.SNAPSHOT_OK], snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        testflow.step("Verify all disks & snapshot disks are v1.1")
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.sd_names[1], expected_qcow_version=config.QCOW_V3
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_several_snapshots.__name__,
)
class BaseTestCase2(BaseTestCase):
    pass


@pytest.mark.usefixtures(
    import_image_from_glance.__name__,
    get_template_from_cluster.__name__,
    create_vm.__name__,
    add_nic.__name__,
    create_several_snapshots.__name__,
)
class BaseTestCase3(BaseTestCase):
    pass


class TestCase18215(BaseTestCase):
    """
    1. Create DC + cluster on v3
    2. Upgrade the DC from v3 to v4
    3. Verify that all block Storage Domains  were upgraded to version 4
    4. Verify that all File Storage Domains were upgraded to version 4
    """
    __test__ = True

    @polarion("RHEVM3-18215")
    @attr(tier=2)
    def test_upgrade_dc(self):
        self.data_center_upgrade()


@pytest.mark.skipif(True, reason="Due to sporadic bz 1449944 & 1456268")
class TestCase18303(TestCase):
    """
    * Verify existing storage Domain is in version 4
    """
    __test__ = True
    storage_format = 'v4'

    @polarion("RHEVM3-18303")
    @attr(tier=2)
    def test_verify_new_domain_version(self):
        storage_domain_name = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        sd_is_on_v4 = ll_sd.checkStorageFormatVersion(
            True, storage_domain_name, self.storage_format
        )
        logger.info(
            "Checking that %s is indeed on v4: %s", storage_domain_name,
            sd_is_on_v4
        )
        assert sd_is_on_v4, "SD %s is not on v4" % storage_domain_name
        testflow.step("%s is indeed on v4" % storage_domain_name)


@bz({'1450692': {}})
class TestCase18307(BaseTestCase):
    """
    1. Create DC + cluster on v3
    2. Upgrade the Cluster to ver 4 and kill the SPM during the operation
    3. Upgrade the Cluster again
    """
    __test__ = True

    @polarion("RHEVM3-18307")
    @attr(tier=3)
    def test_verify_new_domain_version(self):
        testflow.step(
            "Upgrade DC %s to v4 & kill vdsmd on SPM %s" % (
                self.new_dc_name, self.spm_host
            )
        )
        self.data_center_upgrade_without_verification()
        testflow.step("Kill vdsmd on host %s", self.host_name)
        self.host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=self.host_name
        )
        assert ll_hosts.kill_vdsmd(self.host_resource), (
            "Failed to kill vdsmd on host %s" % self.host_name
        )

        # As kill vdsm is very quick I want to make sure that the host is
        # effected cause it takes several seconds for it.
        ll_hosts.wait_for_hosts_states(
            True, self.host_name, states='connecting'
        )
        ll_dc.waitForDataCenterState(self.new_dc_name)
        ll_hosts.wait_for_hosts_states(True, self.host_name)
        self.data_center_upgrade()


@bz({'1444120': {}})
class TestCase18336(BaseTestCase2):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and 2 snapshots
    3. Upgrade cluster &DC to version 4
    4. Amend the snapshot images to version 1.1 & restart engine
    5. Re-ammend the snapshot images to version 1.1
    """
    __test__ = True
    snap_count = 2
    installation = False

    @polarion("RHEVM3-18336")
    @attr(tier=3)
    def test_failure_engine_during_amend(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step(
            "Upgrade DC %s to v4 & restart engine " % self.new_dc_name
        )
        self.data_center_upgrade()
        testflow.step(
            "Amend qcow disk %s to v3" % self.disk_name
        )

        helpers.amend_disk_attachment_api(
            self.vm_name, self.disk_name, qcow_ver=config.QCOW_V3
        )

        testflow.step("Restarting ovirt-engine")
        config.ENGINE.restart()
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)
        testflow.step(
            "Check disk and snapshot status, see all OK"
        )
        assert ll_disks.wait_for_disks_status(self.disk_name), (
            "Disk %s did not reach OK state" % self.disk_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_list
        ), "Snapshot %s did not reach OK state" % self.snapshot_list
        testflow.step(
            "Re-amend qcow disk %s to v3 after engine restart" % self.disk_name
        )
        helpers.amend_disk_attachment_api(
            self.vm_name, self.disk_name, qcow_ver=config.QCOW_V3
        )
        assert ll_disks.wait_for_disks_status(self.disk_name), (
            "Disk %s did not reach OK state" % self.disk_name
        )
        testflow.step(
            "Check qcow version was upgraded to %s" % config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )

        # TODO: Due to bug 1430447 checking qcow_version return wrong value
        # helpers.verify_qcow_snapshot_disks_version(
        #     self.vm_name, self.snapshot_list, qcow_ver=config.QCOW_V3
        # )


@bz({'1450692': {}})
class TestCase18337(BaseTestCase2):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and create 5 snapshots
    3. Upgrade cluster &DC to version 4
    4. Amend the snapshot images to version 1.1 & kill vdsmd on SPM
    5. Re-amend the remaining snapshot images once the SPM has recovered
    """
    __test__ = True
    snap_count = 5
    installation = False

    @polarion("RHEVM3-18337")
    @attr(tier=3)
    def test_failure_of_SPM_during_amend(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step(
            "Upgrade DC %s to v4" % self.new_dc_name
        )
        self.data_center_upgrade()
        testflow.step(
            "Amend qcow disk %s to v3" % self.disk_name
        )
        helpers.amend_disk_attachment_api(
            self.vm_name, self.disk_name, qcow_ver=config.QCOW_V3
        )

        testflow.step("Kill vdsmd on host %s", self.spm_host)
        self.host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=self.host_name
        )
        assert ll_hosts.kill_vdsmd(self.host_resource), (
            "Failed to kill vdsmd on host %s" % self.spm_host
        )
        testflow.step("Check DC is up %s", self.host_name)
        assert ll_hosts.wait_for_hosts_states(
            True, self.host_name, states=config.CONNECTING
        ), "Host %s did not reach connecting state" % self.host_name
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)
        assert ll_hosts.wait_for_hosts_states(True, self.host_name), (
            "Host %s did not reach up state" % self.host_name
        )
        testflow.step(
            "check disk and snapshot status, see all OK"
        )
        assert ll_disks.wait_for_disks_status(self.disk_name), (
            "Disk %s did not reach OK state" % self.disk_name
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_list
        ), "Snapshot %s did not reach OK state" % self.snapshot_list
        testflow.step(
            "Re-amend qcow disk %s to v3" % self.disk_name
        )
        helpers.amend_disk_attachment_api(
            self.vm_name, self.disk_name, qcow_ver=config.QCOW_V3
        )
        assert ll_disks.wait_for_disks_status(self.disk_name), (
            "Disk %s did not reach OK state" % self.disk_name
        )
        testflow.step(
            "Check qcow version was upgraded to %s" % config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )


@pytest.mark.usefixtures(
    create_export_domain.__name__,
    export_vm.__name__,
    remove_export_domain.__name__,
)
@bz({'1446640': {}})
class TestCase18338(BaseTestCase3):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and create 5 snapshots
    3. Create export domain on v3 DC
    4. Export VM to export domain
    5. Upgrade cluster &DC to version 4
    6. Import the VM and verify snapshot images version 1.1
    7. Create a new snapshot and verify that the images are version 1.1
    8. Start the VM & verify data can be written to the disks
    """
    __test__ = True
    polarion_test_case = '18338'
    snap_count = 5
    storage_domain_kwargs = {
        'storage_type': config.STORAGE_TYPE_NFS,
        'address': config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
        'path': config.UNUSED_DATA_DOMAIN_PATHS[0]
    }

    @polarion("RHEVM3-18338")
    @attr(tier=2)
    def test_import_vm_with_snapshot_from_export_domain(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step(
            "Upgrade DC %s to v4.1" % self.new_dc_name
        )
        self.data_center_upgrade()
        testflow.step(
            "Remove vm %s to v4.1" % self.vm_name
        )
        assert ll_vms.safely_remove_vms([self.vm_name]), (
            "Failed to power off and remove VM %s" % self.vm_name
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        testflow.step(
            "Import vm %s from export domain %s to SD %s" % (
                self.vm_name, self.export_domain, self.storage_domain
            )
        )
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.storage_domain,
            self.cluster_name
        ), "Import VM %s from export domain %s to data domain %s failed" % (
            self.vm_name, self.export_domain, self.storage_domain
        )
        testflow.step(
            "Verify disk and snapshots on storage domain %s has version 1.1"
            % self.storage_domain
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.QCOW_V3
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )

        snapshot_description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        assert ll_vms.addSnapshot(
            True, self.new_vm_name, snapshot_description, wait=True
        ), "Failed to create snapshot of VM %s" % self.new_vm_name
        ll_vms.wait_for_vm_snapshots(
            self.new_vm_name, [config.SNAPSHOT_OK], snapshot_description
        )
        testflow.step(
            "Check qcow version was upgraded to %s" % config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )
        testflow.step("Start the VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        ), "VM %s did not reach %s state" % (self.vm_name, config.VM_UP)
        status, mount_path = storage_helpers.create_fs_on_disk(
            self.vm_name, self.disk_name
        )
        assert status, (
            "Unable to create a filesystem on disk: %s of VM %s" %
            (self.disk_name, self.vm_name)
        )
        storage_helpers.create_test_file_and_check_existance(
            self.vm_name, mount_path, file_name=config.FILE_NAME
        )


@pytest.mark.skipif(True, reason="Due to sporadic bz 1449944 & 1456268")
@pytest.mark.usefixtures(
    init_test_vm_name.__name__,
    create_vm.__name__,
    init_test_template_name.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    remove_template.__name__,
    remove_vms.__name__,
)
class TestCase18340(TestCase):
    """
    1. Use existing V4 DC & cluster
    2. Create a VM with thin disk
    3. Create a template of the previously created VM
    4. Create a new Thin VM from the Template and verify that all
      the disk images are created as qcow version 1.1
    5. Start the VM and verify that data can be written to the disks
    6. Create a snapshot and verify that the images are qcow version 1.1
    """
    __test__ = True
    new_disks_names = []

    @polarion("RHEVM3-18340")
    @attr(tier=2)
    def test_create_new_thin_vm_from_template(self):
        testflow.step(
            "Create a template of VM %s" % self.vm_name
        )
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, timeout=config.CREATE_TEMPLATE_TIMEOUT
        ), "Failed to create template %s" % self.template_name
        testflow.step(
            "Create a new Thin VM from the Template %s"
            % self.template_name
        )
        assert ll_vms.createVm(
            True, self.new_vm_name,
            template=self.template_name,
            cluster=config.CLUSTER_NAME
        )

        self.new_disks_names = [
            disk_object.get_alias() for disk_object in ll_vms.getVmDisks(
                self.new_vm_name
            )
        ]

        testflow.step(
            "Verify newly created VM %s disks %s is on qcow %s" % (
                self.new_vm_name, self.new_disks_names, config.QCOW_V3
            )
        )
        helpers.verify_qcow_version_vm_disks(self.new_vm_name)
        testflow.step(
            "Start the VM %s and verify that data can be written to the disk"
            % self.new_vm_name
        )
        assert ll_vms.startVm(
            True, self.new_vm_name, config.VM_UP, wait_for_ip=True
        ), "VM %s did not reach %s state" % (self.new_vm_name, config.VM_UP)

        logger.info("Trying to write to disk %s" % self.new_disks_names[0])
        status, out = storage_helpers.perform_dd_to_disk(
            self.new_vm_name, self.new_disks_names[0]
        )
        assert status != 0, "error found %s" % out

        snapshot_description = storage_helpers.create_unique_object_name(
                self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.step(
            "Creating snapshot %s of VM %s",
            snapshot_description, self.new_vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.new_vm_name, snapshot_description
        ), "Failed to create snapshot of VM %s" % self.new_vm_name
        ll_vms.wait_for_vm_snapshots(
            self.new_vm_name, [config.SNAPSHOT_OK], snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        testflow.step("Verify all disks & snapshot disks are v1.1")
        helpers.verify_qcow_version_vm_disks(self.new_vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )


@bz({'1444120': {}})
class TestCase18305(BaseTestCase):
    """
    1. Create DC + cluster on v3
    2. Upgrade the cluster from v3 to v4
    3. restart engine during upgrade cluster
    3. Verify that cluster is upgraded to v4
    """
    __test__ = True

    @polarion("RHEVM3-18305")
    @attr(tier=3)
    def test_restart_engine_during_upgrade_cluster(self):
        testflow.step(
            "Upgrading cluster %s from version %s to version %s ",
            self.cluster_name, self.cluster_version,
            self.cluster_upgraded_version
        )
        assert ll_clusters.updateCluster(
            True, self.cluster_name,
            version=self.cluster_upgraded_version, compare=False
        ), "Failed to upgrade compatibility version of cluster"
        testflow.step("Restarting ovirt-engine")
        config.ENGINE.restart()
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)

        testflow.step(
            "Checking that cluster %s is indeed on v4" % self.cluster_name
        )
        assert ll_hosts.get_cluster_compatibility_version(
            self.cluster_name
        ) == self.cluster_upgraded_version, (
            "Cluster %s is not on version %s" % (
                self.cluster_name, self.cluster_upgraded_version
            )
        )


@bz({'1444120': {}})
class TestCase18334(BaseTestCase):
    """
    1. Create DC + cluster on v3
    2. Upgrade the cluster+DC from v3 to v4
    3. restart engine during upgrade DC
    3. Verify that all block Storage Domains  were upgraded to version 4
    4. Verify that all File Storage Domains were upgraded to version 4
    """
    __test__ = True

    @polarion("RHEVM3-18334")
    @attr(tier=3)
    def test_restart_engine_during_upgrade_dc(self):
        self.data_center_upgrade_without_verification()
        testflow.step("Restarting ovirt-engine")
        config.ENGINE.restart()
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)
        storage_domain_name = ll_sd.getStorageDomainNamesForType(
            self.new_dc_name, self.storage
        )[0]

        testflow.step(
            "Checking that %s is indeed on v4" % storage_domain_name
        )

        assert ll_sd.checkStorageFormatVersion(
            True, storage_domain_name, self.upgraded_storage_format
        ), "SD %s is not on v4" % storage_domain_name


@bz({'1446640': {}})
class TestCase18343(BaseTestCase3):
    """
    1. Create DC + cluster on v3 + 2 new storage domains
    2. Create a VM with thin disk and create 2 snapshots
    3. Upgrade the cluster+DC from v3 to v4
    4. Verify that the snapshot images are version 0.10
    5. Start the VM previously created
    6. Move all the disks of the VM to Version 4 Domain
    7. Verify that the snapshot images have been upgraded to version 1.1
    8. Power off the VM and Preview the Snasphot
    9. Commit the Previewed snapshot
    10. Start the VM and verify that data can be written to all disks
    11. Create a new snapshot and verify that the disk image is version is 1.1

    """
    __test__ = True
    snap_count = 2
    new_storage_domains_count = 2

    @polarion("RHEVM3-18343")
    @attr(tier=2)
    def test_live_migration_old_image(self):
        self.migration_test(live=config.LIVE_MIGRATION)


@bz({'1446640': {}})
class TestCase18344(BaseTestCase3):
    """
    1. Create DC + cluster on v3 + 2 new storage domains
    2. Create a VM with thin disk and create 2 snapshots
    3. Upgrade the cluster+DC from v3 to v4
    4. Verify that the snapshot images are version 0.10
    5. Move all the disks of the VM to Version 4 Domain
    6. Verify that the snapshot images have been upgraded to version 1.1
    7. Preview the snapshot
    8. Commit the Previewed snapshot
    9. Start the VM and verify that data can be written to all disks
    10.  Create a new snapshot and verify that the disk image is version is 1.1

    """
    __test__ = True
    snap_count = 2
    new_storage_domains_count = 2

    @polarion("RHEVM3-18344")
    @attr(tier=2)
    def test_cold_migration_old_image(self):
        self.migration_test(live=config.COLD_MIGRATION)


@pytest.mark.usefixtures(
    import_image_from_glance.__name__,
    get_template_from_cluster.__name__,
    create_vm.__name__,
    add_nic.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    create_file_than_snapshot_several_times.__name__,
)
@bz({'1446640': {}})
class TestCase18346(BaseTestCase):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk & start VM
    3. Write data (file1) and Create snapshots s1
    4. Write data (file2) and Create snapshots s2
    5. Upgrade the cluster+DC from v3 to v4
    4. Verify that the snapshot images are version 0.10
    5. Write data (file3)
    6. Create snapshot s3 & verify the snapshot image is version 0.10
    7. Create snapshot s4 & verify the snapshot image is version 1.1
    8. Deleted snapshot s3 and verify that the live merge is successful
    and that the merged image (s3->s4) is now version 0.10
    9. Power off the VM and Preview the Merged snapshot
    10. Commit the Previewed snapshot
    11. Start the VM, verify existing data and write new data to the disks
    """
    __test__ = True
    write_to_file_than_snapshot_number_of_times = 2
    snapshots_descriptions_list = []
    checksum_file_list = []
    full_path_list = []

    @polarion("RHEVM3-18346")
    @attr(tier=2)
    def test_live_merge_old_version_image_with_new_version_image(self):
        testflow.step(
            "Upgrade DC %s to v4", self.new_dc_name
        )
        self.data_center_upgrade()
        testflow.step(
            "Verify that the snapshot images are version %s", config.QCOW_V2
        )
        sd_disks_objects = ll_vms.get_storage_domain_disks(self.storage_domain)
        logger.info(
            "The following disks exist %s in storage domain %s", [
                sd_disk.get_alias() for sd_disk in sd_disks_objects
            ], self.storage_domain
        )
        logger.info(
            "Qcow version on snapshot %s disks version before merge are: %s",
            self.snapshots_descriptions_list[0],
            ll_vms.get_qcow_version_disks_snapshot(
                self.vm_name, self.snapshots_descriptions_list[0]
            )
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.DISK_QCOW_V2
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V2
        )
        testflow.step("Create file on VM %s", self.vm_name)
        storage_helpers.create_file_on_vm(
            self.vm_name, config.FILE_NAME + '3', self.mount_path,
            vm_executor=self.vm_executor
        )

        for index in range(config.CURRENT_VALUE, config.CURRENT_VALUE+2):
            snapshot_description = storage_helpers.create_unique_object_name(
                self.__name__, config.OBJECT_TYPE_SNAPSHOT
            ) + str(index)

            testflow.step(
                "Create snapshot #%s with description %s ", str(index),
                snapshot_description
            )
            assert ll_vms.addSnapshot(
                True, self.vm_name, snapshot_description, wait=True
            ), "Failed to create snapshot of VM %s" % self.vm_name
            self.snapshots_descriptions_list.append(snapshot_description)
            testflow.step(
                "Verify that qcow version of snapshot %s disks are %s ",
                snapshot_description, config.QCOW_V2
            )
            if index is config.CURRENT_VALUE:
                helpers.verify_qcow_specific_snapshot(
                    self.vm_name, snapshot_description, self.storage_domain,
                    expected_qcow=config.QCOW_V2
                )
            else:
                helpers.verify_qcow_specific_snapshot(
                    self.vm_name, snapshot_description, self.storage_domain,
                    expected_qcow=config.QCOW_V3
                )

        testflow.step(
            "Deleted snapshot s%s named %s and verify that the live merge"
            " is successful", config.CURRENT_VALUE,
            self.snapshots_descriptions_list[2]
        )
        testflow.step(
            "Removing snapshot '%s' of vm %s",
            self.snapshots_descriptions_list[2], self.vm_name
        )
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshots_descriptions_list[2]
        ), (
            "Failed to live merge snapshot %s" %
            self.snapshots_descriptions_list[2]
        )
        testflow.step(
            "Verify merged snapshot s4 named %s is now version 0.1",
            self.snapshots_descriptions_list[3]
        )
        helpers.verify_qcow_specific_snapshot(
            self.vm_name, self.snapshots_descriptions_list[3],
            self.storage_domain, expected_qcow=config.DISK_QCOW_V2
        )
        testflow.step(
            "Power off the VM %s and Preview the Merged snapshot %s",
            self.vm_name, self.snapshots_descriptions_list[3]
        )
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off VM %s" % self.vm_name
        )
        assert ll_vms.preview_snapshot(
            True, self.vm_name, self.snapshots_descriptions_list[3]
        ), ("Failed to preview snapshot %s" % self.snapshot_description)
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
        testflow.step(
            "Commit snapshot %s", self.snapshots_descriptions_list[3]
        )
        assert ll_vms.commit_snapshot(True, self.vm_name), (
            "Failure to commit VM's %s snapshot" % self.vm_name
        )
        testflow.step("Start the VM %s", self.vm_name)
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        ), "VM %s did not reach %s state" % (self.vm_name, config.VM_UP)
        testflow.step("Verify existing data and write new data to the disks")
        helpers.verify_test_files_checksum(
            self.vm_name, self.checksum_file_list, self.full_path_list,
            vm_executor=self.vm_executor
        )
        storage_helpers.create_test_file_and_check_existance(
            self.vm_name, self.mount_path, file_name=config.FILE_NAME + '4',
            vm_executor=self.vm_executor
        )


@bz({'1446878': {}})
class TestCase18339(BaseTestCase3):
    """
    1. Create DC + cluster on v3 + 2 storage domains SD1 & SD2
    2. Create a VM with thin disk and create 5 snapshots on SD1
    3. Detach & remove storage domain SD1
    4. Upgrade cluster &DC to version 4.1
    5. Migrate SD1 back to upgraded DC
    6. Import unregistered VM to SD1
    6. Verify disk & snapshot disk are also upgraded to qcow v1.1.
    7. Start the VM & verify data can be written to the disks
    8. Power off the VM and Preview snapshot with upgraded images
    9. Undo the Preview
    10. Create a new snapshot & verify new snapshot disks are version 1.1
    """
    __test__ = True
    polarion_test_case = '18339'
    snap_count = 5
    new_storage_domains_count = 2

    @polarion("RHEVM3-18339")
    @attr(tier=3)
    def test_storage_migration_old_version_to_new_version_dc(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step(
            "Deactivate,detach & remove storage domain %s", self.storage_domain
        )

        assert hl_sd.remove_storage_domain(
            self.storage_domain, self.new_dc_name, self.spm_host, config.ENGINE
        ), "Failed to remove storage domain %s" % self.storage_domain

        testflow.step("Upgrade DC %s to 4.1", self.new_dc_name)
        self.data_center_upgrade()
        storage_helpers.import_storage_domain(
            self.storage_domain, self.host_name, self.storage
        )
        testflow.step("Attaching storage domain %s", self.storage_domain)
        assert hl_sd.attach_and_activate_domain(
            self.new_dc_name, self.storage_domain
        ), "Failed to attach & activate %s" % self.storage_domain
        ll_jobs.wait_for_jobs([config.JOB_ACTIVATE_DOMAIN])
        storage_helpers.register_vm_from_data_domain(
            self.storage_domain, self.vm_name, self.cluster_name
        )
        testflow.step(
            "Verify registered VM %s disk & snapshot disks qcow version is %s",
            self.vm_name, config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.DISK_QCOW_V3
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )
        testflow.step(
            "Start the VM %s and verify that data can be written to the disk",
            self.vm_name
        )
        assert ll_vms.startVm(
            True, self.vm_name, config.VM_UP, wait_for_ip=True
        ), "VM %s did not reach %s state" % (self.vm_name, config.VM_UP)
        status, out = storage_helpers.perform_dd_to_disk(
            self.vm_name, self.disk_name
        )
        assert status, "Error %s found writing data to disk %s from vm %s" % (
            out, self.disk_name, self.vm_name
        )
        snapshot_description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.step(
            "Creating snapshot %s of VM %s",
            snapshot_description, self.new_vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, snapshot_description
        ), "Failed to create snapshot of VM %s" % self.new_vm_name
        ll_vms.wait_for_vm_snapshots(
            self.new_vm_name, [config.SNAPSHOT_OK], snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        testflow.step("Verify all disks & snapshot disks are v1.1")
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )
        assert ll_vms.preview_snapshot(
            True, self.vm_name, snapshot_description
        ), "Failed to preview snapshot %s" % snapshot_description
        ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
        testflow.step(
            "Undo snapshot %s", self.snapshots_description
        )
        assert ll_vms.undo_snapshot_preview(True, self.vm_name), (
            "Snapshot %s preview undo failed " % snapshot_description
        )


@bz({'1450692': {}})
class TestCase18335(BaseTestCase):
    """
    1. Create DC + cluster on v3 + 2 storage domains master & non master
    2. Move non master storage domain to maintenance
    3. Upgrade Cluster + DC & kill the VDSM on SPM after upgraded
    5. Activate remaining non master domain -> verify all SD's are upgraded to
     4.1 (V4)
    """
    __test__ = True
    polarion_test_case = '18335'
    new_storage_domains_count = 2

    @polarion("RHEVM3-18335")
    @attr(tier=3)
    def test_spm_failure_after_upgrade_dc_and_activate_sd(self):
        testflow.step("Deactivate non master domain %s", self.sd_names[1])
        assert ll_sd.deactivateStorageDomain(
            True, self.new_dc_name, self.sd_names[1]
        )

        testflow.step(
            "Upgrade DC %s to v4 & kill vdsmd on SPM %s afterwards" % (
                self.new_dc_name, self.spm_host
            )
        )
        self.data_center_upgrade_without_verification()
        storage_helpers.kill_vdsm_on_spm_host(self.new_dc_name)

        testflow.step("Activate non master domain %s", self.sd_names[1])
        assert ll_sd.activateStorageDomain(
            True, self.new_dc_name, self.sd_names[1]
        ), "Failed to activate non master domain %s" % self.sd_names[1]

        testflow.step(
            "Check master domain %s & non master domain %s are on v4.1",
            self.sd_names[0], self.sd_names[1]
        )
        for sd in self.sd_names:
            assert ll_sd.checkStorageFormatVersion(
                True, sd, self.upgraded_storage_format
            ), "Storage domain %s is not on expected version %s" % (
                sd, self.upgraded_storage_format
            )


@bz({'1448905': {}})
class TestCase18347(BaseTestCase2):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and one snapshot
    3. Upgrade cluster & DC to version 4
    3. Start the VM
    5. Attempt to amend the disk & snapshot disks -> should fail

    """
    __test__ = True
    snap_count = 1
    installation = False

    @polarion("RHEVM3-18347")
    @attr(tier=3)
    def test_amend_volume_while_vm_up(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        self.data_center_upgrade()
        testflow.step("Start VM %s", self.vm_name)
        assert ll_vms.startVm(True, self.vm_name), (
            "VM %s did not start" % self.vm_name
        )
        testflow.step(
            "Amend qcow disk %s on running VM %s , expected to fail",
            self.disk_name, self.vm_name
        )
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name,
            qcow_version=config.QCOW_V3
        ), "Update disk %s on VM %s to qcow version %s succeeded" % (
            self.disk_name, self.vm_name, config.QCOW_V3
        )


@bz({'1449944': {}})
class TestCase18348(BaseTestCase2):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and one snapshot
    3. Attempt to amend the disk & snapshot disks on old DC-> should fail
    """
    __test__ = True
    snap_count = 1
    installation = False

    @polarion("RHEVM3-18348")
    @attr(tier=3)
    def test_amend_old_dc(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step(
            "Amend qcow disk %s on old DC %s , expected to fail",
            self.disk_name, self.new_dc_name
        )
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name,
            qcow_version=config.QCOW_V3
        ), "Update disk %s on VM %s to qcow version %s succeeded" % (
            self.disk_name, self.vm_name, config.QCOW_V3
        )


@pytest.mark.skipif(True, reason="Due to sporadic bz 1449944 & 1456268")
@pytest.mark.usefixtures(
    create_vm.__name__,
    init_test_template_name.__name__,
    remove_template.__name__,
)
@bz({'1449289': {}})
class TestCase18349(TestCase):
    """
    1. Create DC + cluster on v4
    2. Create a Template of the VM with a RAW disk
    3. Attempt to amend the template disks
    """
    __test__ = True
    snap_count = 1
    installation = False
    volume_format = config.DISK_FORMAT_RAW

    @polarion("RHEVM3-18349")
    @attr(tier=3)
    def test_amend_template_disk(self):
        testflow.step(
            "Create a template of VM %s" % self.vm_name
        )
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, timeout=config.CREATE_TEMPLATE_TIMEOUT
        ), "Failed to create template %s" % self.template_name
        template_disk = ll_templates.getTemplateDisks(
            self.template_name
        )[0].get_alias()
        testflow.step(
            "Amend qcow template disk %s , expected to fail", template_disk
        )
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=template_disk,
            qcow_version=config.QCOW_V3
        ), "Update disk %s on VM %s to qcow version %s succeeded" % (
            template_disk, self.vm_name, config.QCOW_V3
        )


@bz({'1449944': {}})
class TestCase18350(BaseTestCase2):
    """
    1. Create DC + cluster on v3 + storage domain
    2. Create a VM with thin disk and one snapshot
    3. Move storage domain to maintenance
    4. Attempt to amend the disk & snapshot disks on old DC-> should fail
    """
    __test__ = True
    snap_count = 1
    installation = False

    @polarion("RHEVM3-18350")
    @attr(tier=3)
    def test_amend_sd_in_maintenance(self):
        self.disk_name = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        testflow.step("Deactivate storage domain %s", self.storage_domain)
        assert ll_sd.deactivate_master_storage_domain(True, self.new_dc_name)
        testflow.step(
            "Amend disk %s on storage domain  %s in maintenance state"
            ", expected to fail", self.disk_name, self.storage_domain
        )
        assert ll_vms.updateDisk(
            False, vmName=self.vm_name, alias=self.disk_name,
            qcow_version=config.QCOW_V3
        ), "Update disk %s on VM %s to qcow version %s succeeded" % (
            self.disk_name, self.vm_name, config.QCOW_V3
        )
        testflow.step("Activate storage domain %s", self.storage_domain)
        assert ll_sd.activateStorageDomain(
            True, self.new_dc_name, self.storage_domain
        ), "Activating sd %s" % self.storage_domain


@bz({'1449944': {}})
class TestCase18351(BaseTestCase2):
    """
    1. Create DC + cluster on v3 + storage domain
    2. Create a VM with thin disk and one snapshot
    3. Attempt to amend a a non existing disk on a VM  -> should fail
    """
    __test__ = True
    snap_count = 1
    installation = False

    @polarion("RHEVM3-18351")
    @attr(tier=3)
    def test_amend_non_existing_disk(self):
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
        testflow.step(
            "Try to amend non existing disk %s -> expected to fail",
            self.disk_name
        )
        pytest.raises(
            AttributeError, ll_vms.updateDisk, positive=False,
            vmName=self.vm_name, alias=self.disk_name,
            qcow_version=config.QCOW_V3
        )
