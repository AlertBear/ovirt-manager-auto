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
from sys import modules
import config
from art.rhevm_api.utils import test_utils
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

from fixtures import (
    init_hsm_host, create_one_or_more_storage_domains_same_type_for_upgrade,
    remove_unattached_domain, initialize_dc_parameters_for_upgrade,
    init_spm_host, init_test_vm_name, init_base_params,
    deactivate_and_remove_non_master_domains, init_test_template_name,
)

from rhevmtests.storage.fixtures import (
    clean_dc, create_vm, add_disk, export_vm,
    remove_template, attach_disk, create_export_domain, remove_export_domain,
    create_several_snapshots, import_image_from_glance, remove_vms, create_dc
)

from art.unittest_lib import attr, StorageTest as TestCase


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


__THIS_MODULE = modules[__name__]


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


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_several_snapshots.__name__,
)
class BaseTestCase2(BaseTestCase):
    pass


@pytest.mark.usefixtures(
    import_image_from_glance.__name__,
    create_vm.__name__,
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


class TestCase18303(TestCase):
    """
    * Verify existing storage Domain is in version 4
    """
    __test__ = True
    storage_format = 'v4'

    @polarion("RHEVM3-18303")
    @attr(tier=1)
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
        testflow.step("kill vdsmd on host %s", self.host_name)
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


class TestCase18336(BaseTestCase2):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and 2 snapshots
    3. Upgrade cluster &DC to version 4
    4. Amend the snapshot images to version 1.0 & restart engine
    5. Re-ammend the snapshot images to version 1.0
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
        test_utils.restart_engine(config.ENGINE, 5, 30)
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)
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
            "Re-amend qcow disk %s to v3 after engine restart" % self.disk_name
        )
        helpers.amend_disk_attachment_api(
            self.vm_name, self.disk_name, qcow_ver=config.QCOW_V3
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


@bz({'1431619': {}})
class TestCase18337(BaseTestCase2):

    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and create 5 snapshots
    3. Upgrade cluster &DC to version 4
    4. Amend the snapshot images to version 1.0 & kill vdsmd on SPM
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

        testflow.step("kill vdsmd on host %s", self.spm_host)
        self.host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=self.host_name
        )
        assert ll_hosts.kill_vdsmd(self.host_resource), (
            "Failed to kill vdsmd on host %s" % self.spm_host
        )
        testflow.step("Check DC is up %s", self.host_name)
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)
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

        testflow.step(
            "Check qcow version was upgraded to %s" % config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )
        # TODO: Due to bug 1430447 checking qcow_version return wrong value
        # helpers.verify_qcow_snapdisks_version(
        #     self.vm_name, self.snapshot_list,
        #     expected_qcow_version=config.QCOW_V3
        # )


@pytest.mark.usefixtures(
    create_export_domain.__name__,
    export_vm.__name__,
    remove_export_domain.__name__,
)
@bz({'1432493': {}})
class TestCase18338(BaseTestCase3):
    """
    1. Create DC + cluster on v3
    2. Create a VM with thin disk and create 5 snapshots
    3. Create export domain on v3 DC
    4. Export VM to export domain
    5. Upgrade cluster &DC to version 4
    6. Import the VM and verify snapshot images version 1.0
    7. Create a new snapshot and verify that the images are version 1.0
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
            "remove vm %s to v4.1" % self.vm_name
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
            "verify disk and snapshots on storage domain %s has version 1.0"
            % self.storage_domain
        )
        helpers.verify_qcow_version_vm_disks(
            self.vm_name, qcow_ver=config.QCOW_V3
        )
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )

        testflow.step(
            "Create a new snapshot %s" % self.new_snap_description
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.new_snap_description
        ), "Failed to create snapshot of VM %s" % self.vm_name
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.new_snap_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        self.snapshot_list.append(self.new_snap_description)
        testflow.step(
            "Verify the new snapshot %s disks are in version 1.0" % (
                self.new_snap_description
            )
        )
        testflow.step(
            "Check qcow version was upgraded to %s" % config.QCOW_V3
        )
        helpers.verify_qcow_version_vm_disks(self.vm_name)
        helpers.verify_qcow_disks_snapshots_version_sd(
            self.storage_domain, expected_qcow_version=config.QCOW_V3
        )
        # TODO: Due to bug 1430447 checking qcow_version return wrong value
        # helpers.verify_qcow_snapdisks_version(
        #     self.vm_name, self.snapshot_list, qcow_ver=config.QCOW_V3
        # )


@bz({'1433052': {}})
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
    6. Create a snapshot and verify that the images are qcow version 1.0
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
            % self.vm_name
        )
        ll_vms.startVm(True, self.new_vm_name)
        ll_vms.waitForVMState(self.new_vm_name)

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
        # TODO: Due to bug 1430447 checking qcow_version return wrong value
        # helpers.verify_qcow_snapdisks_version(
        #     self.new_vm_name, self.snapshot_list, qcow_ver=config.QCOW_V3
        # )


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
        test_utils.restart_engine(config.ENGINE, 5, 30)
        hl_dc.ensure_data_center_and_sd_are_active(self.new_dc_name)

        testflow.step(
            "Checking that cluster %s is indeed on v4" % self.cluster_name
        )
        assert ll_hosts.get_cluster_compatibility_version(
            self.cluster_name
        ) == self.cluster_upgraded_version, (
            "cluster %s is not on version %s" % self.cluster_upgraded_version
        )


@polarion("RHEVM3-18334")
@attr(tier=3)
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
    @attr(tier=1)
    def test_restart_engine_during_upgrade_dc(self):
        self.data_center_upgrade_without_verification()
        testflow.step("Restarting ovirt-engine")
        test_utils.restart_engine(config.ENGINE, 5, 30)
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
