"""
Storage Disk Image Format
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_2_Storage_Disk_Image_Format
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import config
import pytest
from art.test_handler.tools import bz, polarion
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    templates as ll_templates,
    vms as ll_vms,
)
from art.unittest_lib import (
    StorageTest as TestCase,
    testflow,
    tier2,
    tier3,
)
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage.fixtures import (
    initialize_storage_domains, create_vm, create_template, remove_vm,
    remove_vms, clean_export_domain, remove_template, add_disk, attach_disk,
)  # flake8: noqa
from rhevmtests.storage.storage_disk_image_format.fixtures import (
    initialize_params, create_test_vms, remove_vm_setup, remove_test_templates,
    initialize_template_name
)

ENUMS = config.ENUMS

logger = logging.getLogger(__name__)
MOVE_DISK_TIMEOUT = 600


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    initialize_params.__name__,
)
class BaseTestDiskImage(TestCase):
    """
    Base Test Class for test plan:
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Disk_Image_Format
    """
    default_disks = {}

    __test__ = False

    def check_disks(self, disks_dict={}):
        """
        Make sure the vm's disks have the expected values. If the parameter
        disks_dict is passed in,  the default dictionary is updated. Also make
        sure there's at least one disk in the vm

        :param disks_dict: dictionary str/bool with disk identifier and sparse
        value
        :type disks_dict: dict
        """
        check_disks = self.default_disks.copy()
        check_disks.update(disks_dict)

        for key, sparse in check_disks.iteritems():
            testflow.step("Checking disks format for %s", key)
            vm_disks = config.retrieve_disk_obj(key)
            # Make sure there's at least one disk
            assert vm_disks
            for disk in vm_disks:
                assert disk.get_sparse() == sparse, (
                    "Wrong sparse value for disk %s (disk id: %s) expected %s"
                    % (disk.get_alias(), disk.get_id(), str(sparse))
                )


@pytest.mark.usefixtures(
    create_test_vms.__name__,
)
class BaseTestDiskImageVms(BaseTestDiskImage):
    """
    Base Test Case with two vms created, with thin and pre-allocated disks
    """
    polarion_test_id = None

    def execute_concurrent_vms(self, fn):
        """
        Concurrent execute function for self.vm_names

        :param fn: function to submit to ThreadPoolExecutor. The function must
        accept only one parameter, the name of the vm
        :type fn: function
        """
        executions = list()
        with ThreadPoolExecutor(max_workers=2) as executor:
            for vm in self.vm_names:
                executions.append(executor.submit(fn, **{"vm": vm}))

        for execution in executions:
            if not execution.result():
                if execution.exception():
                    raise execution.exception()
                else:
                    raise Exception("Error executing %s" % execution)

    def add_snapshots(self):
        """
        Create a snapshot for each vm in parallel
        """
        testflow.step("Adding snapshots for %s", ", ".join(self.vm_names))

        def addsnapshot(vm):
            return ll_vms.addSnapshot(True, vm, self.snapshot_desc)

        self.execute_concurrent_vms(addsnapshot)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    def export_vms(self, discard_snapshots=False):
        """
        Export vms in parallel
        """
        def exportVm(vm):
            status = ll_vms.exportVm(
                True, vm, config.EXPORT_DOMAIN_NAME,
                discard_snapshots=discard_snapshots
            )
            return status

        testflow.step("Export vms %s", ", ".join(self.vm_names))
        self.execute_concurrent_vms(exportVm)

    def import_vms(self, collapse=False):
        """
        Import vms in parallel
        """
        testflow.step("Import vms %s", ", ".join(self.vm_names))

        def importVm(vm):
            return ll_vms.importVm(
                True, vm, config.EXPORT_DOMAIN_NAME, self.storage_domain,
                config.CLUSTER_NAME, collapse=collapse
            )

        self.execute_concurrent_vms(importVm)

    def check_snapshots_collapsed(self):
        """
        Ensure that the snapshots are removed after the import process
        """
        vm_thin_snapshots = [
            snapshot.get_description() for snapshot in
            ll_vms.get_vm_snapshots(self.vm_thin)
        ]
        vm_prealloc_snapshots = [
            snapshot.get_description() for snapshot in
            ll_vms.get_vm_snapshots(self.vm_prealloc)
        ]
        assert self.snapshot_desc not in vm_thin_snapshots
        assert self.snapshot_desc not in vm_prealloc_snapshots


class TestCase11604(BaseTestDiskImageVms):
    """
    Polarion case 11604
    """
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with
    # id' after live migrate a Virtio RAW disk, job stays in status STARTED
    __test__ = True
    polarion_test_id = '11604'

    @polarion("RHEVM3-11604")
    @tier2
    def test_format_and_snapshots(self):
        """
        Create a snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.check_disks()
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})


# Bugzilla 1403183 is a duplicate of 1405822 that was openned for this
# test with more info about the cause of failure.
@bz({'1403183': {}})
class TestCase11621(BaseTestDiskImageVms):
    """
    Polarion case 11621
    """
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with
    # id' after live migrate a Virtio RAW disk, job stays in status STARTED
    __test__ = True
    polarion_test_id = '11621'

    @rhevm_helpers.wait_for_jobs_deco([config.JOB_MOVE_COPY_DISK])
    @polarion("RHEVM3-11621")
    @tier2
    def test_move_disk_offline(self):
        """
        Move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert ll_disks.move_disk(
            disk_id=self.disk_thin, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        assert ll_disks.move_disk(
            disk_id=self.disk_prealloc, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        self.check_disks()


class TestCase11620(BaseTestDiskImageVms):
    """
    Polarion case 11620
    """
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with
    # id' after live migrate a Virtio RAW disk, job stays in status STARTED
    __test__ = True
    polarion_test_id = '11620'

    @polarion("RHEVM3-11620")
    @tier3
    def test_add_snapshot_and_move_disk(self):
        """
        Create a snapshot and move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})
        assert ll_disks.move_disk(
            disk_id=self.disk_thin, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        assert ll_disks.move_disk(
            disk_id=self.disk_prealloc, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        self.check_disks({self.vm_prealloc: True})


class TestCase11619(BaseTestDiskImageVms):
    """
    Polarion case 11619
    """
    # Bugzilla history:
    # 1251956: Live storage migration is broken
    # 1259785: Error 'Unable to find org.ovirt.engine.core.common.job.Step with
    # id' after live migrate a Virtio RAW disk, job stays in status STARTED
    __test__ = True
    polarion_test_id = '11619'

    @polarion("RHEVM3-11619")
    @tier2
    def test_live_move_disk(self):
        """
        Start a live disk migration
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        ll_vms.start_vms(
            [self.vm_prealloc, self.vm_thin], max_workers=2,
            wait_for_status=config.VM_UP, wait_for_ip=False
        )
        testflow.step(
            "Moving disk %s to storage domain %s",
            self.disk_thin, self.storage_domain_1
        )
        assert ll_disks.move_disk(
            disk_id=self.disk_thin, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        testflow.step(
            "Moving disk %s to storage domain %s",
            self.disk_prealloc, self.storage_domain_1
        )
        assert ll_disks.move_disk(
            disk_id=self.disk_prealloc, target_domain=self.storage_domain_1,
            timeout=MOVE_DISK_TIMEOUT
        )
        ll_vms.wait_for_disks_status(
            [self.disk_thin, self.disk_prealloc], key='id',
            timeout=MOVE_DISK_TIMEOUT
        )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        ll_vms.wait_for_vm_snapshots(self.vm_prealloc, config.SNAPSHOT_OK)
        ll_vms.wait_for_vm_snapshots(self.vm_thin, config.SNAPSHOT_OK)
        self.check_disks({self.vm_prealloc: False})


@pytest.mark.usefixtures(
    clean_export_domain.__name__,
)
class ExportVms(BaseTestDiskImageVms):
    """
    Common class for export related cases
    """
    pass


@bz({'1409238': {}})
class TestCase11618(ExportVms):
    """
    Polarion case 11618
    """
    __test__ = True
    polarion_test_id = '11618'

    @polarion("RHEVM3-11618")
    @tier2
    def test_export_vm(self):
        """
        Export a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()

        config.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=config.EXPORT_DOMAIN_NAME
        )
        self.check_disks()


@bz({'1409238': {}})
class TestCase11617(ExportVms):
    """
    Polarion case 11617
    """
    __test__ = True
    polarion_test_id = '11617'

    @polarion("RHEVM3-11617")
    @tier2
    def test_add_snapshot_and_export_vm(self):
        """
        Create a snapshot and export the vm
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should change to thin
        provision
        """
        self.add_snapshots()
        self.export_vms()

        config.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=config.EXPORT_DOMAIN_NAME
        )
        self.check_disks({self.vm_prealloc: True})


@bz({'1409238': {}})
class TestCase11616(ExportVms):
    """
    Polarion case 11616
    """
    __test__ = True
    polarion_test_id = '11616'

    @polarion("RHEVM3-11616")
    @tier2
    def test_add_snapshot_export_vm_with_discard_snapshots(self):
        """
        Create a snapshot and export the vm choosing to discard the existing
        snapshots.
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should remain the same
        """
        self.add_snapshots()
        self.export_vms(discard_snapshots=True)

        config.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=config.EXPORT_DOMAIN_NAME
        )
        self.check_disks()


class TestCase11615(ExportVms):
    """
    Polarion case 11615
    """
    __test__ = True
    polarion_test_id = '11615'

    @polarion("RHEVM3-11615")
    @tier2
    def test_import_vm(self):
        """
        Export a vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        self.import_vms()
        self.check_disks()


class TestCase11614(ExportVms):
    """
    Polarion case 11614
    """
    __test__ = True
    polarion_test_id = '11614'

    @polarion("RHEVM3-11614")
    @tier3
    def test_export_vm_after_snapshot_and_import(self):
        """
        Create snapshot on vm, export the vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        self.import_vms()
        self.check_disks({self.vm_prealloc: True})


class TestCase11613(ExportVms):
    """
    Polarion case 11613
    """
    __test__ = True
    polarion_test_id = '11613'

    @polarion("RHEVM3-11613")
    @tier2
    def test_export_vm_with_collapse(self):
        """
        Polarion case id: 11613
        Create a snapshot to a vm, export the vm and import choosing to
        collapse the existing snapshots
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        self.import_vms(collapse=True)
        self.check_snapshots_collapsed()
        self.check_disks({self.vm_prealloc: True})


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_template.__name__,
    clean_export_domain.__name__,
    remove_vm_setup.__name__,
    remove_vms.__name__,
)
class TestCasesImportVmLinked(BaseTestDiskImage):
    """
    Collection for test cases with one vm imported
    """
    config.retrieve_disk_obj = lambda x: ll_vms.getVmDisks(x)


class TestCase11612(TestCasesImportVmLinked):
    """
    Polarion case 11612
    """
    __test__ = True
    polarion_test_id = '11612'

    @polarion("RHEVM3-11612")
    @tier3
    def test_import_link_to_template(self):
        """
        Create a vm from a thin provisioned template, export the vm and
        re-import it back
        * Thin provisioned disk should remain the same
        """
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert ll_vms.exportVm(True, self.vm_name, config.EXPORT_DOMAIN_NAME)
        assert ll_vms.removeVm(True, self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        assert ll_vms.importVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME, self.storage_domain,
            config.CLUSTER_NAME
        )
        self.vm_names.append(self.vm_name)
        self.check_disks()


class TestCase11611(TestCasesImportVmLinked):
    """
    Polarion case 11611
    """
    __test__ = True
    polarion_test_id = '11611'

    @polarion("RHEVM3-11611")
    @tier3
    def test_import_link_to_template_collapse(self):
        """
        Create a vm from a thin provisioned template, export the vm and the
        template, remove both of them and import the vm back
        * Thin provisioned disk should remain the same
        """
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, config.EXPORT_DOMAIN_NAME, wait=True
        )
        self.remove_exported_template = True
        assert ll_vms.exportVm(True, self.vm_name, config.EXPORT_DOMAIN_NAME)

        assert ll_vms.removeVm(True, self.vm_name)
        ll_jobs.wait_for_jobs([ENUMS['job_remove_vm']])
        assert ll_templates.remove_template(True, self.template_name)

        assert ll_vms.importVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME, self.storage_domain,
            config.CLUSTER_NAME, collapse=True
        )

        self.check_disks()


@pytest.mark.usefixtures(
    remove_vms.__name__,
    clean_export_domain.__name__,
)
class TestCasesImportVmWithNewName(BaseTestDiskImageVms):
    """
    Check disk images' format after importing the vm without removing the
    original vm used in the export process
    """

    def import_vm_with_new_name(self):
        """
        Export the thin provisioned and preallocated disk vms, then import them
        with a new name
        """
        self.new_vm_thin = "new_%s" % self.vm_thin
        self.new_vm_prealloc = "new_%s" % self.vm_prealloc

        self.export_vms()
        assert ll_vms.importVm(
            True, self.vm_thin, config.EXPORT_DOMAIN_NAME, self.storage_domain,
            config.CLUSTER_NAME, name=self.new_vm_thin
        )
        self.vm_names.append(self.new_vm_thin)
        assert ll_vms.importVm(
            True, self.vm_prealloc, config.EXPORT_DOMAIN_NAME,
            self.storage_domain, config.CLUSTER_NAME, name=self.new_vm_prealloc
        )
        self.vm_names.append(self.new_vm_prealloc)


class TestCase11610(TestCasesImportVmWithNewName):
    """
    Polarion case 11610
    """
    __test__ = True
    polarion_test_id = '11610'

    @polarion("RHEVM3-11610")
    @tier2
    def test_import_vm_without_removing_old_vm(self):
        """
        Import a vm without removing the original vm used in the export
        process
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.import_vm_with_new_name()


class TestCase11609(TestCasesImportVmWithNewName):
    """
    Polarion case 11609
    """
    __test__ = True
    polarion_test_id = '11609'

    @polarion("RHEVM3-11609")
    @tier3
    def test_import_vm_without_removing_old_vm_with_snapshot(self):
        """
        Create a snapshot to a vm, export the vm and import without removing
        the original vm used in the export process
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.import_vm_with_new_name()
        self.check_disks({self.vm_prealloc: True})


@pytest.mark.usefixtures(
    remove_test_templates.__name__,
)
class TestCasesCreateTemplate(BaseTestDiskImageVms):
    """
    Verify the disk images' format of a template
    """
    template_thin_name = "%s_template_thin"
    template_preallocated_name = "%s_template_preallocated"
    # Bugzilla history:
    # 1257240: Template's disk format is wrong

    def create_template_from_vm(self):
        """
        Create one template from a vm with a thin provisioned disk and one from
        a vm with a preallocated disk. Check templates' disks image format
        """
        assert ll_templates.createTemplate(
            True, vm=self.vm_thin, name=self.template_thin,
            cluster=config.CLUSTER_NAME
        )

        assert ll_templates.createTemplate(
            True, vm=self.vm_prealloc, name=self.template_preallocated,
            cluster=config.CLUSTER_NAME
        )

        config.retrieve_disk_obj = ll_templates.getTemplateDisks
        self.default_disks = {
            self.template_thin: True,
            self.template_preallocated: False,
        }
        self.check_disks()


class TestCase11608(TestCasesCreateTemplate):
    """
    Polarion case 11608
    """
    __test__ = True
    polarion_test_id = '11608'

    @polarion("RHEVM3-11608")
    @tier2
    def test_create_template_from_vm(self):
        """
        Create a template from a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.create_template_from_vm()


class TestCase11607(TestCasesCreateTemplate):
    """
    Polarion case 11607
    """
    __test__ = True
    polarion_test_id = '11607'

    @polarion("RHEVM3-11607")
    @tier3
    def test_create_template_from_vm_with_snapshots(self):
        """
        Create a snapshot to the vm and create a template
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.add_snapshots()
        self.create_template_from_vm()


@pytest.mark.usefixtures(
    remove_template.__name__,
    create_vm.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    clean_export_domain.__name__,
    initialize_template_name.__name__,
)
class TestCase11606(BaseTestDiskImage):
    """
    Test vm with both disk formats
    """
    add_disk_params = {
        'bootable': False,
        'format': config.RAW_DISK,
        'sparse': False
    }
    get_thin_disk = lambda self, x: [
        d.get_alias() for d in ll_vms.getVmDisks(x) if d.get_sparse()
        ][0]

    def check_disks(self):
        """
        Verify the vm and template disks' format
        """
        self.thin_disk_alias = self.get_thin_disk(self.vm_name)
        for function, object_name in [
            (ll_disks.getTemplateDisk, self.template_name),
            (ll_disks.getVmDisk, self.vm_name)
        ]:
            thin_disk = function(object_name, self.thin_disk_alias)
            preallocated_disk = function(
                object_name, self.disk_name,
            )
            assert thin_disk.get_sparse(), (
                "%s disk %s should be thin provisioned" %
                (object_name, thin_disk.get_alias())
            )
            assert not preallocated_disk.get_sparse(), (
                "%s disk %s should be preallocated" %
                (object_name, preallocated_disk.get_alias())
            )

    def action_test(self, collapse=False):
        """
        Export the vm, import it and create a template
        """
        assert ll_vms.exportVm(True, self.vm_name, config.EXPORT_DOMAIN_NAME)
        assert ll_vms.removeVm(True, self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
        assert ll_vms.importVm(
            True, self.vm_name, config.EXPORT_DOMAIN_NAME, self.storage_domain,
            config.CLUSTER_NAME, collapse=collapse
        )

        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        )


class TestCase11606A(TestCase11606):
    """
    No snapshot on vm
    """
    __test__ = True
    polarion_test_id = '11606'

    @polarion("RHEVM3-11606")
    @tier3
    def test_different_format_same_vm(self):
        """
        Polarion case id: 11606 - no snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.action_test()
        self.check_disks()


class TestCase11606B(TestCase11606):
    """
    Snapshot on vm
    """
    __test__ = True
    polarion_test_id = '11606'
    deep_copy = True

    @polarion("RHEVM3-11606")
    @tier3
    def test_different_format_same_vm_with_snapshot(self):
        """
        Polarion case id: 11606 - with snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert ll_vms.addSnapshot(True, self.vm_name, "another snapshot")
        self.action_test(collapse=True)
