"""
3.6 Feature: Resize data domain LUNs:
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/3_6_Storage_Resizing_Data_Domain_Luns
"""
import config
import helpers
import logging
import pytest
import os
import shlex
import rhevmtests.storage.helpers as storage_helpers
import art.test_handler.exceptions as errors
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    disks as ll_disks,
    vms as ll_vms,
    jobs as ll_jobs,
    templates as ll_templates
)
from art.rhevm_api.tests_lib.high_level import (
    vmpools as hl_vmpools
)
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib.common import StorageTest as TestCase, testflow
from rhevmtests.fixtures import (
    init_storage_manager, create_lun_on_storage_server,
    remove_lun_from_storage_server
)
from rhevmtests.storage.fixtures import (
    create_storage_domain, skip_invalid_storage_type,
    create_vm, add_disk, init_vm_executor, start_vm, create_fs_on_disk,
    attach_disk, copy_template_disk, create_second_vm, extend_storage_domain,
    remove_vms_pool,
)
from fixtures import (
    set_disk_params, init_domain_disk_param, attach_disk_to_second_vm,
    set_shared_disk_params, poweroff_vms, append_to_luns_to_resize,
    create_second_lun, remove_second_lun
)

from rhevmtests.storage.fixtures import remove_vm  # noqa

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    skip_invalid_storage_type.__name__,
    init_storage_manager.__name__,
)
class BaseTestCase(TestCase):
    """
    Common class for all tests with some common methods
    """
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_FCP])
    new_lun_size = '15'
    extended_size = 20
    file_name = None
    checksum_before = None

    def resize_luns(self):
        """
        Resize LUNs on storage server
        """
        self.size_before = ll_sd.get_total_size(
            storagedomain=self.new_storage_domain,
            data_center=config.DATA_CENTER_NAME
        )
        testflow.step(
            "Storage domain %s total size before LUNs %s resize is %s",
            self.new_storage_domain, config.LUNS_TO_RESIZE, self.size_before
        )
        testflow.step(
            "Resizing LUNs %s of storage domain %s from %s to %s",
            config.LUNS_TO_RESIZE, self.new_storage_domain, self.new_lun_size,
            self.extended_size
        )

        for lun_id, identifier in zip(
            config.LUNS_TO_RESIZE, config.LUNS_IDENTIFIERS
        ):
            self.storage_manager.resize_lun(
                lun=lun_id, new_size=self.extended_size
            )

        for lun_id in config.LUNS_TO_RESIZE:
            for lun_info in TimeoutingSampler(
                config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
                self.storage_manager.getLun, lun_id
            ):
                logger.info("LUN %s size is %s", lun_id, lun_info['size'])
                lun_size = lun_info['size'].replace('G', '').replace('B', '')
                if int(lun_size[:2]) == self.extended_size:
                    break

    def refresh_luns(self):
        """
        Refresh size of storage domain LUNs
        """
        testflow.step(
            "Refreshing LUNs %s size of storage domain %s",
            config.LUNS_TO_RESIZE, self.new_storage_domain
        )
        assert ll_sd.refresh_storage_domain_luns(
            storage_domain=self.new_storage_domain,
            logical_unit_ids=config.LUNS_IDENTIFIERS
        ), "Failed to refresh storage domain %s LUNs %s" % (
            self.new_storage_domain, config.LUNS_TO_RESIZE
        )

        assert ll_sd.wait_for_change_total_size(
            storage_domain=self.new_storage_domain,
            data_center=config.DATA_CENTER_NAME,
            original_size=self.size_before
        ), "Storage domain %s size hasn't been changed" % (
            self.new_storage_domain
        )

        size_after = ll_sd.get_total_size(
            storagedomain=self.new_storage_domain,
            data_center=config.DATA_CENTER_NAME
        )
        testflow.step(
            "Storage domain %s total size after LUNs %s resize is %s",
            self.new_storage_domain, config.LUNS_TO_RESIZE, size_after
        )
        assert size_after == (
            len(config.LUNS_TO_RESIZE) * self.extended_size - 1
        ) * config.GB, (
                "Storage domain %s total size after LUNs %s resize hasn't "
                "been changed" % (
                    self.new_storage_domain, config.LUNS_TO_RESIZE
                )
            )

    def full_resize(self):
        self.resize_luns()
        self.refresh_luns()


@pytest.mark.usefixtures(
    create_lun_on_storage_server.__name__,
    remove_lun_from_storage_server.__name__,
    append_to_luns_to_resize.__name__,
    create_storage_domain.__name__,
)
class ResizeSingleLun(BaseTestCase):
    """
    Basic class for single LUN resize
    """


@pytest.mark.usefixtures(
    copy_template_disk.__name__,
    init_domain_disk_param.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__
)
class ResizeVmOperations(ResizeSingleLun):
    """
    Basic class for LUN resize with VM operations
    """
    new_lun_size = '35'
    extended_size = 40
    file_name = None
    checksum_before = None
    template = config.TEMPLATE_NAME[0]


@pytest.mark.usefixtures(
    set_disk_params.__name__,
    add_disk.__name__,
    attach_disk.__name__,
)
class ResizeVmDiskOperations(ResizeVmOperations):
    """
    Base class for LUN resize with VM and disk operations
    """


class TestCase9854(ResizeSingleLun):
    """
    RHEVM3-9854 Basic LUN extend
    """
    __test__ = True

    @polarion("RHEVM3-9854")
    @tier2
    def test_basic_lun_extend(self):
        self.full_resize()


class TestCase10139(ResizeVmOperations):
    """
    RHEVM3-10139 Creating a snapshot after extending LUN
    """
    __test__ = True

    @polarion("RHEVM3-10139")
    @tier2
    def test_create_snapshot_after_lun_extend(self):
        self.file_name, self.checksum_before = (
            helpers.write_content_and_get_checksum(
                vm_name=self.vm_name, vm_executor=self.vm_executor
             )
        )

        helpers.power_off_vm(self.vm_name)

        self.full_resize()

        description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        helpers.create_and_restore_snapshot(self.vm_name, description)
        helpers.start_vm(self.vm_name)
        helpers.verify_data_integrity(
            vm_name=self.vm_name, file_name=self.file_name,
            vm_executor=self.vm_executor, checksum_before=self.checksum_before
        )


class TestCase10140(ResizeVmDiskOperations):
    """
    RHEVM3-10140 Live merge after extending LUN
    """
    __test__ = True
    size_diff = 6

    @polarion("RHEVM3-10140")
    @tier3
    def test_live_merge_after_lun_extend(self):
        description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        helpers.create_snapshot(self.vm_name, description)

        # Trying to remove the snapshot with positive=False to see that it
        # fails because there is not enough space in the domain for live merge.
        # Then, resize the LUN and try again with positive=True.
        helpers.delete_snapshot(False, description, self.vm_name)
        self.full_resize()
        helpers.delete_snapshot(True, description, self.vm_name)


class TestCase10141(ResizeSingleLun):
    """
    RHEVM3-10141 Adding disk after extending LUN
    """
    __test__ = True

    @polarion("RHEVM3-10141")
    @tier3
    def test_add_disk_after_lun_extend(self):
        self.resize_luns()
        helpers.create_second_disk(self.new_storage_domain)


@pytest.mark.usefixtures(
    create_second_vm.__name__,
    set_shared_disk_params.__name__,
    add_disk.__name__,
    attach_disk.__name__,
    attach_disk_to_second_vm.__name__,
    create_fs_on_disk.__name__,
    poweroff_vms.__name__
)
class TestCase10142(ResizeVmOperations):
    """
    RHEVM3-10142 Extend LUN with shared disk attached to 2 VMs
    """
    __test__ = True
    vm_executor_2 = None

    @polarion("RHEVM3-10142")
    @tier3
    def test_extend_lun_shared_disk(self):
        helpers.start_vm(self.vm_name_2)
        self.vm_executor_2 = storage_helpers.get_vm_executor(self.vm_name_2)
        helpers.mount_fs_on_second_vm(
            vm_name=self.vm_name_2, disk_name=self.disk_name,
            mount_point=self.mount_point, vm_executor=self.vm_executor_2
        )
        config.FILE_PATH = self.mount_point
        self.file_name, self.checksum_before = (
            helpers.write_content_and_get_checksum(
                vm_name=self.vm_name, vm_executor=self.vm_executor
             )
        )

        self.full_resize()

        # powering off and starting the VMs so the shared disk's file system
        # will get refreshed on both VMs (start VMs in verify_data_integrity())
        helpers.power_off_vm(vm_name=self.vm_name)
        helpers.power_off_vm(vm_name=self.vm_name_2)

        testflow.step("Verifying data integrity for VM %s", self.vm_name)
        helpers.verify_data_integrity(
            vm_name=self.vm_name, file_name=self.file_name,
            vm_executor=self.vm_executor, checksum_before=self.checksum_before
        )
        testflow.step("Verifying data integrity for VM %s", self.vm_name_2)
        helpers.verify_data_integrity(
            vm_name=self.vm_name_2, file_name=self.file_name,
            vm_executor=self.vm_executor_2,
            checksum_before=self.checksum_before
        )


class TestCase10143(ResizeVmOperations):
    """
    RHEVM3-10143 Attaching a direct LUN to VM after extending LUN
    """
    __test__ = True

    @polarion("RHEVM3-10143")
    @tier3
    def test_attach_lun_after_extend_lun(self):
        self.full_resize()
        dev_count_before = storage_helpers.get_storage_devices(
            vm_name=self.vm_name
        )
        direct_lun_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DIRECT_LUN
        )
        lun_kwargs = config.disk_args.copy()
        lun_kwargs['alias'] = direct_lun_name
        lun_kwargs['lun_id'] = config.UNUSED_LUNS[1]
        lun_kwargs['lun_address'] = config.UNUSED_LUN_ADDRESSES[1]
        lun_kwargs['lun_target'] = config.UNUSED_LUN_TARGETS[1]
        lun_kwargs.update({'type_': config.STORAGE_TYPE_ISCSI})
        testflow.step("Adding direct LUN %s", direct_lun_name)
        assert ll_disks.addDisk(True, **lun_kwargs), (
            "Failed to add direct lun %s" % direct_lun_name
        )
        testflow.step(
            "Attaching direct LUN %s to VM", direct_lun_name, self.vm_name
        )
        assert ll_disks.attachDisk(
            positive=True, alias=direct_lun_name, vm_name=self.vm_name
        ), "Failed to attach direct lun %s to vm %s" % (
            self.direct_lun_name, self.vm_name
        )
        dev_count_after = storage_helpers.get_storage_devices(
            vm_name=self.vm_name
        )
        assert dev_count_before < dev_count_after, (
            "Direct LUN %s is not seen by VM %s" % (
                direct_lun_name, self.vm_name
            )
        )


class TestCase10144(ResizeVmDiskOperations):
    """
    RHEVM3-10144 Live storage migration after extending LUN
    """
    __test__ = True
    existing_domain = None
    new_lun_size = '20'
    extended_size = 25
    size_diff = -2

    @polarion("RHEVM3-10144")
    @tier3
    def test_live_storage_migration_after_extending_lun(self):
        testflow.step(
            "Live migrating VM %s disk %s to storage domain %s. Operation "
            "should fail", self.vm_name, self.disk_name,
            self.new_storage_domain
        )
        pytest.raises(
            errors.DiskException, ll_vms.migrate_vm_disk, vm_name=self.vm_name,
            disk_name=self.disk_name, target_sd=self.new_storage_domain
        )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])

        self.full_resize()

        testflow.step(
            "Live migrating VM %s disk %s to storage domain %s. Operation "
            "should succeed", self.vm_name, self.disk_name,
            self.new_storage_domain
        )
        ll_vms.migrate_vm_disk(
            vm_name=self.vm_name, disk_name=self.disk_name,
            target_sd=self.new_storage_domain
        )


@pytest.mark.usefixtures(
    copy_template_disk.__name__,
    init_domain_disk_param.__name__,
    create_vm.__name__,
)
class ResizeCreateTemplate(ResizeSingleLun):
    """
    Base class for TCs 10145 and 10146
    """
    new_lun_size = '35'
    extended_size = 40
    template = config.TEMPLATE_NAME[0]
    new_template_name = None

    def create_template_after_extending_lun(self):
        self.full_resize()
        helpers.power_off_vm(vm_name=self.vm_name)
        testflow.setup("Creating template %s", self.new_template_name)
        self.new_template_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_TEMPLATE
        )
        assert ll_templates.createTemplate(
            positive=True, vm=self.vm_name, name=self.new_template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.new_storage_domain
        ), (
            "Failed to create template %s from VM %s" % (
                self.new_template_name, self.vm_name
            )
        )


class TestCase10145(ResizeCreateTemplate):
    """
    RHEVM3-10145 Creating a template after extending LUN
    """
    __test__ = True

    @polarion("RHEVM3-10145")
    @tier3
    def test_create_template_after_extending_lun(self):
        self.create_template_after_extending_lun()

        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = self.new_storage_domain
        second_vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM + 'second'
        )
        vm_args['vmName'] = second_vm_name
        vm_args['clone_from_template'] = True
        vm_args['template_name'] = self.new_template_name
        testflow.setup("Creating VM %s", second_vm_name)
        assert storage_helpers.create_vm_or_clone(**vm_args), (
            "Failed to create VM %s" % second_vm_name
        )


@pytest.mark.usefixtures(
    remove_vms_pool.__name__
)
class TestCase10146(ResizeCreateTemplate):
    """
    RHEVM3-10146 Creating a VMs pool after extending LUN
    """
    __test__ = True
    pool_name = None

    @bz({'1454821': {}})
    @polarion("RHEVM3-10146")
    @tier3
    def test_create_vms_pool_after_extending_lun(self):
        self.create_template_after_extending_lun()

        self.pool_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_POOL
        )
        pool_params = {
            'size': 3,
            'template': self.new_template_name,
            'cluster': config.CLUSTER_NAME,
            'max_user_vms': 1,
            'prestarted_vms': 0,
        }
        testflow.setup(
            "Creating VMs pool from template %s", self.new_template_name
        )
        hl_vmpools.create_vm_pool(
            positive=True, pool_name=self.pool_name, pool_params=pool_params
        )


@pytest.mark.usefixtures(
    create_fs_on_disk.__name__
)
class TestCase10147(ResizeVmDiskOperations):
    """
    RHEVM3-10147 Extend LUN while writing to disk
    """
    __test__ = True
    target_dir = None

    def copy_file_to_new_disk(self):
        self.target_dir = os.path.join(self.mount_point, 'target')
        mkdir_cmd = 'mkdir %s' % self.target_dir
        rc, out, error = self.vm_executor.run_cmd(
            cmd=shlex.split(mkdir_cmd)
        )
        assert not rc, (
            "Failed to create directory %s on VM %s filesystem %s with "
            "error: %s" % (
                self.target_dir, self.vm_name, self.mount_point, error
            )
        )

        testflow.step(
            "Copying file %s to target path %s on VM %s", self.file_name,
            self.target_dir, self.vm_name
        )

        assert storage_helpers.copy_file(
            vm_name=self.vm_name, file_name=self.file_name,
            target_path=self.target_dir, vm_executor=self.vm_executor,
            run_in_background=True
        ), "Failed to copy file %s to target path %s" % (
            self.file_name, self.target_dir
        )

    @polarion("RHEVM3-10147")
    @tier3
    def test_extend_lun_while_writing_to_disk(self):
        self.file_name, checksum_before = (
            helpers.write_content_and_get_checksum(
                vm_name=self.vm_name, vm_executor=self.vm_executor,
                write_with_dd=True, disk_name=self.disk_name
            )
        )

        self.resize_luns()
        self.copy_file_to_new_disk()
        self.refresh_luns()

        assert storage_helpers.wait_for_background_process_state(
            vm_executor=self.vm_executor, process_state=config.PROCESS_DONE
        ), "File %s copy operation failed to complete" % self.file_name

        copied_file = os.path.join(
            self.target_dir, os.path.split(self.file_name)[-1]
        )

        checksum_after = shlex.split(
            storage_helpers.checksum_file(
                vm_name=self.vm_name, file_name=copied_file,
                vm_executor=self.vm_executor
            )
        )[0]

        testflow.step("Checksum of file %s is %s", copied_file, checksum_after)
        assert checksum_before == checksum_after, (
            "VM %s file %s got corrupted" % (self.vm_name, copied_file)
        )


@pytest.mark.usefixtures(
    create_lun_on_storage_server.__name__,
    remove_lun_from_storage_server.__name__,
    append_to_luns_to_resize.__name__,
    remove_second_lun.__name__,
    create_storage_domain.__name__,
    create_second_lun.__name__,
    extend_storage_domain.__name__
)
class TestCase10148(BaseTestCase):
    """
    RHEVM3-10148 Extend several LUNs
    """
    __test__ = True
    extend_indices = [4]

    @polarion("RHEVM3-10148")
    @tier3
    def test_extend_several_luns(self):
        self.full_resize()
