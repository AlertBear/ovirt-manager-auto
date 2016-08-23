"""
3.6 copy disk feature
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Create_Disk_From_Existing_Disk
"""

import config
import logging
import pytest
import helpers
from art.unittest_lib import (
    tier1,
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest as BaseTestCase, testflow
from art.test_handler.tools import bz, polarion
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.test_handler import exceptions
from concurrent.futures import ThreadPoolExecutor
from rhevmtests.networking.helper import seal_vm
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (
    initialize_storage_domains
)
from rhevmtests.storage.storage_copy_disk.fixtures import (
    initialize_vm, create_disks, remove_disks,
    create_test_vm, remove_template, remove_vm
)

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

CMD_CREATE_FILE = 'touch %s/test_file_copy_disk'
POLL_TIMEOUT = 20
COPY_DISK_TIMEOUT = 600
REMOVE_TEMPLATE_TIMEOUT = 300
CREATE_TEMPLATE_TIMEOUT = 1800
CLONE_FROM_TEMPLATE = 1200

disk_args = {
    'positive': True,
    'provisioned_size': config.DISK_SIZE,
    'bootable': False,
    'interface': config.VIRTIO,
    'sparse': True,
    'format': config.COW_DISK,
}

copy_args = {
    'target_domain': None,
    'disk_id': None,
    'timeout': COPY_DISK_TIMEOUT,
    'wait': False,
    'new_disk_alias': None,
}


@pytest.fixture(scope='module', autouse=True)
def create_vms_per_storage(request):
    """
    Prepares environment
    """
    def finalizer_module():
        """
        Remove vm
        """
        testflow.teardown(
            "Removing VMs %s", ', '.join(config.VM_NAMES.values())
        )
        ll_vms.safely_remove_vms(config.VM_NAMES.values())
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])

    request.addfinalizer(finalizer_module)
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = config.VM_NAME % storage_type
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['vmDescription'] = vm_name

        testflow.setup("Creating base VM %s", vm_name)
        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        config.VM_NAMES[storage_type] = vm_name
        helpers.prepare_disks_for_test(vm_name, storage_type, storage_domain)
        ll_vms.stop_vms_safely([vm_name])


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    initialize_vm.__name__,
)
class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    new_alias = "new_copy_disk_alias"
    disks_after_copy = list()
    new_disks = []


@pytest.mark.usefixtures(
    create_disks.__name__,
    remove_disks.__name__,
)
class CopyDiskWithoutContent(BasicEnvironment):
    """
    A base class for cases that require floating disks
    """
    @classmethod
    def basic_copy(cls, positive=True, same_domain=True, new_alias=None):
        """
        Copy disk to target storage domain

        :param same_domain: Determines whether the disk will be copied to
        the same domain
        :type same_domain: bool
        :param new_alias: Determines the new copied disks' alias
        :type new_alias: str
        """
        executors = []
        copy_args = {
            'target_domain': None,
            'disk_id': None,
            'timeout': COPY_DISK_TIMEOUT,
            'wait': False,
            'positive': positive,
            'new_disk_alias': new_alias
        }

        disk_objects = [
            d for d in ll_disks.DISKS_API.get(abs_link=False)
            if d.get_id() in config.FLOATING_DISKS
        ]
        testflow.step(
            "Copy disks %s", ', '.join([d.get_alias() for d in disk_objects])
        )
        with ThreadPoolExecutor(max_workers=len(disk_objects)) as executor:
            for disk_obj in disk_objects:
                if same_domain:
                    target_sd = helpers.get_disk_storage_domain_name(disk_obj)
                else:
                    target_sd = ll_disks.get_other_storage_domain(
                        disk_obj.get_alias()
                    )
                copy_args['target_domain'] = target_sd
                copy_args['disk_id'] = disk_obj.get_id()

                executors.append(
                    executor.submit(ll_disks.copy_disk, **copy_args)
                )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        cls.disks_after_copy = ll_disks.get_non_ovf_disks()
        cls.new_disks = helpers.get_new_disks(
            config.DISKS_BEFORE_COPY, cls.disks_after_copy
        )
        ll_disks.wait_for_disks_status(
            cls.new_disks, key='id', timeout=COPY_DISK_TIMEOUT
        )


@pytest.mark.usefixtures(
    create_test_vm.__name__,
)
class CopyDiskWithContent(BasicEnvironment):
    """
    A base class for cases that require data on vm's disks
    """
    test_vm_name = "copy_disk_test_vm"

    def basic_copy(self, vm_name, same_domain=True, new_alias=None):
        """
        Copy disk to target storage domain

        :param vm_name: Name of the VM which disks will be copied from
        :type vm_name: str
        :param same_domain: Determines whether the disk will be copied to
        the same domain
        :type same_domain: bool
        :param new_alias: Determines the new copied disks' alias
        :type new_alias: str
        """
        executors = []
        vm_disks = ll_vms.getVmDisks(vm_name)
        ll_vms.stop_vms_safely([vm_name])
        sealed = seal_vm(vm_name, config.VM_PASSWORD)
        if not sealed:
            logger.error("Failed to seal vm %s", vm_name)
        testflow.step(
            "Copying disks %s", ', '.join([d.get_alias() for d in vm_disks])
        )
        with ThreadPoolExecutor(max_workers=len(vm_disks)) as executor:
            for disk_obj in vm_disks:
                copy_disk_args = copy_args.copy()
                copy_disk_args['new_disk_alias'] = new_alias
                if same_domain:
                    target_sd = helpers.get_disk_storage_domain_name(disk_obj)
                else:
                    target_sd = ll_disks.get_other_storage_domain(
                        disk_obj.get_alias()
                    )
                copy_disk_args['target_domain'] = target_sd
                copy_disk_args['disk_id'] = disk_obj.get_id()
                if ll_vms.is_bootable_disk(vm_name, disk_obj.get_id()):
                    copy_disk_args['new_disk_alias'] = 'bootable_copy_disk'
                executors.append(
                    executor.submit(ll_disks.copy_disk, **copy_disk_args)
                )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
        self.disks_after_copy = ll_disks.get_non_ovf_disks()
        self.new_disks = helpers.get_new_disks(
            config.DISKS_BEFORE_COPY, self.disks_after_copy
        )
        ll_disks.wait_for_disks_status(
            self.new_disks, key='id', timeout=COPY_DISK_TIMEOUT
        )

    def copy_with_template(self, storage, clone=True):
        """
        Copy disks from a VM that was created from a template
        """
        ll_vms.stop_vms_safely([self.vm_name])
        assert seal_vm(self.vm_name, config.VM_PASSWORD), (
            "Failed to seal vm %s" % self.vm_name
        )
        testflow.step("Creating template from VM %s", self.vm_name)
        assert ll_templates.createTemplate(
            positive=True, timeout=CREATE_TEMPLATE_TIMEOUT,
            vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain
        ), ("Failed to create template from vm %s" % self.vm_name)

        args_for_clone = {
            'positive': True,
            'name': self.cloned_vm,
            'cluster': config.CLUSTER_NAME,
            'template': self.template_name,
            'timeout': CLONE_FROM_TEMPLATE,
            'clone': clone,
            'vol_sparse': True,
            'vol_format': config.COW_DISK,
            'storagedomain': self.storage_domain,
            'virtio_scsi': True,
        }
        testflow.step("Cloning VM from template %s", self.template_name)
        assert ll_vms.cloneVmFromTemplate(**args_for_clone), (
            "Failed to clone vm %s from template %s" % (
                self.cloned_vm, self.template_name
            )
        )
        config.VMS_TO_REMOVE.append(self.cloned_vm)
        config.DISKS_BEFORE_COPY = ll_disks.get_non_ovf_disks()
        self.basic_copy(self.cloned_vm)
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )


class TestCaseCopyAttachedDisk(CopyDiskWithContent):
    """
    Copy disk - basic flow
    """
    __test__ = True

    @polarion("RHEVM3-11246")
    @bz({'1334726': {'ppc': config.PPC_ARCH}})
    @tier1
    def test_same_domain_same_alias(self, storage):
        """
        Copy existing disk to the same storage domain with the same alias
        """
        self.basic_copy(self.vm_name)
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )

    @polarion("RHEVM3-11247")
    @tier2
    def test_different_domain_different_alias(self, storage):
        """
        Copy existing disk to different storage domain with different alias
        """
        self.basic_copy(
            self.vm_name, same_domain=False, new_alias=self.new_alias
        )
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )

    @polarion("RHEVM3-11242")
    @tier3
    def test_different_domain_same_alias(self, storage):
        """
        Copy existing disk to different storage domain with the same alias
        """
        self.basic_copy(self.vm_name, same_domain=False)
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )

    @polarion("RHEVM3-11248")
    @tier3
    def test_same_domain_different_alias(self, storage):
        """
        Copy existing disk to the same storage domain with different alias
        """
        self.basic_copy(self.vm_name, new_alias=self.new_alias)
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )


class TestCaseCopyFloatingDisk(CopyDiskWithoutContent):
    """
    Copy floating disk - basic flow
    """
    __test__ = True
    new_disks = list()

    @polarion("RHEVM3-11252")
    @tier2
    @bz({'1334726': {'ppc': config.PPC_ARCH}})
    def test_same_domain_same_alias(self):
        """
        Copy existing disk to the same storage domain with the same alias
        """
        self.basic_copy()

    @polarion("RHEVM3-11253")
    @tier2
    def test_different_domain_different_alias(self):
        """
        Copy existing disk to different storage domain with different alias
        """
        self.basic_copy(same_domain=False, new_alias=self.new_alias)

    @polarion("RHEVM3-11254")
    @tier3
    def test_same_domain_different_alias(self):
        """
        Copy existing disk to the same storage domain with different alias
        """
        self.basic_copy(new_alias=self.new_alias)

    @polarion("RHEVM3-11251")
    @tier3
    def test_different_domain_same_alias(self):
        """
        Copy existing disk to different storage domain with the same alias
        """
        self.basic_copy(same_domain=False)


class TestCaseCopyDiskNoSpaceLeft(CopyDiskWithoutContent):
    """
    Copy floating disk -  Not enough space on target domain
    """
    __test__ = False

    # TODO: Implement setup when ticket
    # https://projects.engineering.redhat.com/browse/RHEVM-2415
    # is resolved

    @polarion("RHEVM3-11262")
    @tier4
    def test_no_space_left_same_domain(self):
        """
        Copy existing disk to the same storage domain
        """
        self.basic_copy(positive=False)

    @polarion("RHEVM3-11263")
    @tier4
    def test_no_space_left_different_domain(self):
        """
        Copy existing disk to different storage domain
        """
        self.basic_copy(positive=False, same_domain=False)


class TestCase11264(CopyDiskWithContent):
    """
    Copy disk - VM in various states
    """
    __test__ = True

    @polarion("RHEVM3-11246")
    @tier3
    def test_copy_when_vm_in_various_states(self, storage):
        """
        Copy existing disk to the same storage when vm in different states
        """
        disk_objects = [
            d for d in ll_disks.DISKS_API.get(abs_link=False)
            if d.get_id() in config.DISKS_FOR_TEST[storage]
        ]
        copy_disk_args = copy_args.copy()
        copy_disk_args['new_disk_alias'] = self.new_alias
        copy_disk_args['positive'] = False
        logger.info(
            "Starting vm %s before performing copy disk, this should fail",
            self.vm_name
        )
        ll_vms.start_vms([self.vm_name], wait_for_ip=False)
        for disk_obj in disk_objects:
            target_sd = helpers.get_disk_storage_domain_name(disk_obj)
            copy_disk_args['target_domain'] = target_sd
            copy_disk_args['disk_id'] = disk_obj.get_id()
            assert ll_disks.copy_disk(**copy_disk_args), (
                "Succeeded to copy disk of powering up VM %s" % self.vm_name
            )
        ll_vms.waitForVMState(self.vm_name)
        for disk_obj in disk_objects:
            target_sd = helpers.get_disk_storage_domain_name(disk_obj)
            copy_disk_args['target_domain'] = target_sd
            copy_disk_args['disk_id'] = disk_obj.get_id()
            assert ll_disks.copy_disk(**copy_disk_args), (
                "Succeeded to copy disk of running VM %s" % self.vm_name
            )


class TestCase11339(CopyDiskWithContent):
    """
    Copy disk - Vm with snapshot
    """
    __test__ = True
    snapshot_description = "snapshot_11339"
    # Bugzilla history:
    # 1292196 - Deleting disk that was copied from a disk containing a
    # snapshot, will cause the original disk to remove

    @polarion("RHEVM3-11339")
    @tier3
    def test_copy_vm_disks_with_snapshot(self, storage):
        """
        Copy existing disk when vm is with snapshot
        """
        testflow.step("Taking snapshot of VM %s", self.vm_name)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        ), ("Failed to create snapshot for vm %s" % self.vm_name)
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        self.basic_copy(self.vm_name)
        helpers.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        assert helpers.check_file_existence(
            self.test_vm_name, storage_type=storage
        )


@pytest.mark.usefixtures(
    remove_template.__name__,
    remove_vm.__name__,
)
class TestCase11140(CopyDiskWithContent):
    """
    Copy disk - Vm cloned from template as clone
    """
    __test__ = True
    template_name = "template_copy_disk_11140"
    cloned_vm = 'cloned_vm_copy_disk_11140'

    @polarion("RHEVM3-11340")
    @tier3
    def test_copy_vm_disks_after_cloned_as_clone(self):
        """
        Copy existing disk when vm cloned from snapshot as clone
        """
        self.copy_with_template()


@pytest.mark.usefixtures(
    remove_template.__name__,
    remove_vm.__name__,
)
class TestCase11141(CopyDiskWithContent):
    """
    Copy disk - Vm cloned from template as thin
    """
    __test__ = True
    template_name = "template_copy_disk_11141"
    cloned_vm = 'cloned_vm_copy_disk_11141'

    @polarion("RHEVM3-11341")
    @tier3
    def test_copy_vm_disks_after_cloned_as_thin(self):
        """
        Copy existing disk when vm cloned from snapshot as thin
        """
        self.copy_with_template(clone=False)
