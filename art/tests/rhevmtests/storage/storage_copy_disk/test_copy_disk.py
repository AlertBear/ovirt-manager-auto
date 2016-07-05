"""
3.6 copy disk feature
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_6_Storage_Create_Disk_From_Existing_Disk
"""
import config
import logging
import os
from art.unittest_lib import attr, StorageTest as BaseTestCase, testflow
from art.test_handler.tools import polarion
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

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

VM_NAMES = dict()
CMD_CREATE_FILE = 'touch %s/test_file_copy_disk'
TEST_FILE_TEMPLATE = 'test_file_copy_disk'
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


def setup_module():
    """
    Prepares environment
    """
    global VM_NAMES
    for storage_type in config.STORAGE_SELECTOR:
        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = config.VM_NAME % storage_type
        vm_args = config.create_vm_args.copy()
        vm_args['storageDomainName'] = storage_domain
        vm_args['vmName'] = vm_name
        vm_args['vmDescription'] = vm_name

        if not storage_helpers.create_vm_or_clone(**vm_args):
            raise exceptions.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        VM_NAMES[storage_type] = vm_name


def teardown_module():
    """
    Remove vm
    """
    ll_vms.safely_remove_vms(VM_NAMES.values())
    ll_jobs.wait_for_jobs([ENUMS['job_remove_vm']])


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    test_case = None
    vm_name = None
    new_alias = "new_copy_disk_alias"
    mount_points = list()
    disks_before_copy = list()
    disks_after_copy = list()
    new_disks = list()
    disks_for_test = list()

    @classmethod
    def setup_class(cls):
        """
        Prepare the environment for testing
        """
        cls.vm_name = VM_NAMES[cls.storage]
        cls.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage
        )[0]

    @classmethod
    def create_files_on_vm_disks(cls, vm_name):
        """
        Files will be created on vm's disks with name:
        'test_file_<iteration_number>'
        """
        if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
            assert ll_vms.startVm(
                True, vm_name, config.VM_UP, wait_for_ip=True
            )
        for mount_dir in cls.mount_points:
            logger.info("Creating file in %s", mount_dir)
            rc = storage_helpers.create_file_on_vm(
                vm_name, TEST_FILE_TEMPLATE, mount_dir
            )
            if not rc:
                logger.error(
                    "Failed to create file test_file_%s under %s on vm %s",
                    mount_dir, vm_name
                )
                return False
        return True

    def check_file_existence(
            self, vm_name, file_name=TEST_FILE_TEMPLATE, should_exist=True
    ):
        """
        Determines whether file exists on mounts
        """
        ll_vms.start_vms([vm_name], 1, wait_for_ip=True)
        result_list = []
        state = not should_exist
        # For each mount point, check if the corresponding file exists
        for mount_dir in self.mount_points:
            full_path = os.path.join(mount_dir, file_name)
            logger.info("Checking if file %s exists", full_path)
            result = storage_helpers.does_file_exist(
                vm_name, full_path
            )
            logger.info(
                "File %s %s",
                file_name, 'exists' if result else 'does not exist'
            )
            result_list.append(result)

        if state in result_list:
            return False
        return True

    def get_disk_storage_domain_name(self, disk_object):
        """
        Get the disk's storage domain name

        :param disk_object: Disk object
        :type disk_object: Disk object
        :return: Storage domain name
        :rtype: str
        """
        storage_id = (
            disk_object.get_storage_domains().get_storage_domain()[0].get_id()
        )
        storage_domain_object = ll_sd.get_storage_domain_obj(
            storage_domain=storage_id, key='id'
        )
        return storage_domain_object.get_name()

    def get_new_disks(self, disks_before_copy, disks_after_copy):
        """
        Get new disks copied during the test

        :param disks_before_copy: List of disks before the test starts
        :type disks_before_copy: list
        :param disks_after_copy: List of disks after the test finishes
        :type disks_after_copy: list
        :return: List of newly created disks
        :rtype: list
        """
        return list(set(disks_after_copy) - set(disks_before_copy))

    @classmethod
    def get_non_ovf_disks(cls):
        """
        :return: List of disks that are not OVF_STORE
        :rtype: list
        """
        return [
            d.get_id() for d in ll_disks.DISKS_API.get(absLink=False) if (
                d.get_alias() != config.OVF_DISK_ALIAS
            )
        ]

    @classmethod
    def clean_all_copied_disks(cls, disks_to_clean):
        """
        Delete all newly created disks
        """
        results = []
        for disk in disks_to_clean:
            results.append(ll_disks.deleteDisk(
                True, disk_id=disk
            ))
        ll_jobs.wait_for_jobs([ENUMS['job_remove_disk']])
        if False in results:
            raise exceptions.DiskException(
                "Failed to delete disk"
            )

    def attach_new_disks_to_vm(self, vm_name, disks_to_attach):
        """
        Attach newly copied disks to test vm

        :param vm_name: Name of the VM into which disks will be attached
        :type vm_name: str
        :param disks_to_attach: List of the disks to be attached to the
        specified VM
        :type disks_to_attach: list
        """
        for disk in disks_to_attach:
            ll_disks.attachDisk(True, disk, vm_name, disk_id=disk)


class CopyDiskWithoutContent(BasicEnvironment):
    """
    A base class for cases that require floating disks
    """

    @classmethod
    def setup_class(cls):
        super(CopyDiskWithoutContent, cls).setup_class()
        cls.disks_for_test = list()
        disk_names = (
            storage_helpers.start_creating_disks_for_test(
                sd_name=cls.storage_domain, sd_type=cls.storage
            )
        )
        ll_disks.wait_for_disks_status(disk_names)
        for disk_alias in disk_names:
            cls.disks_for_test.append(
                ll_disks.get_disk_obj(disk_alias).get_id()
            )
        cls.disks_before_copy = cls.get_non_ovf_disks()

    @classmethod
    def teardown_class(cls):
        cls.clean_all_copied_disks(cls.disks_for_test)

    def tearDown(self):
        self.clean_all_copied_disks(self.new_disks)

    def basic_copy(self, positive=True, same_domain=True, new_alias=None):
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
            d for d in ll_disks.DISKS_API.get(absLink=False)
            if d.get_id() in self.disks_for_test
        ]
        with ThreadPoolExecutor(max_workers=len(disk_objects)) as executor:
            for disk_obj in disk_objects:
                if same_domain:
                    target_sd = self.get_disk_storage_domain_name(disk_obj)
                else:
                    target_sd = ll_disks.get_other_storage_domain(
                        disk_obj.get_alias()
                    )
                copy_args['target_domain'] = target_sd
                copy_args['disk_id'] = disk_obj.get_id()

                executors.append(
                    executor.submit(ll_disks.copy_disk, **copy_args)
                )
        ll_jobs.wait_for_jobs([ENUMS['job_move_or_copy_disk']])
        self.disks_after_copy = self.get_non_ovf_disks()
        self.new_disks = self.get_new_disks(
            self.disks_before_copy, self.disks_after_copy
        )
        ll_disks.wait_for_disks_status(
            self.new_disks, key='id', timeout=COPY_DISK_TIMEOUT
        )


class CopyDiskWithContent(BasicEnvironment):
    """
    A base class for cases that require data on vm's disks
    """
    test_vm_name = "copy_disk_test_vm"

    @classmethod
    def setup_class(cls):
        super(CopyDiskWithContent, cls).setup_class()
        cls.disks_for_test, cls.mount_points = (
            storage_helpers.prepare_disks_with_fs_for_vm(
                cls.storage_domain, cls.storage, cls.vm_name
            )
        )
        disk_objects = ll_vms.getVmDisks(cls.vm_name)
        for disk in disk_objects:
            new_vm_disk_name = (
                "%s_%s" % (disk.get_alias(), config.TESTNAME)
            )
            ll_disks.updateDisk(
                True, vmName=cls.vm_name, id=disk.get_id(),
                alias=new_vm_disk_name
            )
        if not cls.create_files_on_vm_disks(cls.vm_name):
            raise exceptions.DiskException(
                "Failed to create files on vm's disks"
            )
        cls.disks_before_copy = cls.get_non_ovf_disks()

    @classmethod
    def teardown_class(cls):
        ll_vms.stop_vms_safely([cls.vm_name])
        cls.clean_all_copied_disks(cls.disks_for_test)

    def setUp(self):
        """
        Create vm to test the content of copied disks
        """
        ll_vms.createVm(
            True, self.test_vm_name, self.test_vm_name,
            cluster=config.CLUSTER_NAME, nic=config.NIC_NAME[0],
            user=config.VM_USER, password=config.VM_PASSWORD,
            network=config.MGMT_BRIDGE, useAgent=True
        )

    def tearDown(self):
        """
        Remove vm for testing files and all new copied disks
        """
        ll_vms.safely_remove_vms([self.test_vm_name])
        ll_jobs.wait_for_jobs([ENUMS['job_remove_vm']])

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
        copy_disk_args = copy_args.copy()
        copy_disk_args['new_disk_alias'] = new_alias
        vm_disks = ll_vms.getVmDisks(vm_name)
        ll_vms.stop_vms_safely([vm_name])
        seal_vm(vm_name, config.VM_PASSWORD)
        with ThreadPoolExecutor(max_workers=len(vm_disks)) as executor:
            for disk_obj in vm_disks:
                if same_domain:
                    target_sd = self.get_disk_storage_domain_name(disk_obj)
                else:
                    target_sd = ll_disks.get_other_storage_domain(
                        disk_obj.get_alias()
                    )
                copy_disk_args['target_domain'] = target_sd
                copy_disk_args['disk_id'] = disk_obj.get_id()

                executors.append(
                    executor.submit(ll_disks.copy_disk, **copy_disk_args)
                )
        ll_jobs.wait_for_jobs([ENUMS['job_move_or_copy_disk']])
        self.disks_after_copy = self.get_non_ovf_disks()
        self.new_disks = self.get_new_disks(
            self.disks_before_copy, self.disks_after_copy
        )
        ll_disks.wait_for_disks_status(
            self.new_disks, key='id', timeout=COPY_DISK_TIMEOUT
        )

    def copy_with_template(self, clone=True):
        """
        Copy disks from a VM that was created from a template
        """
        ll_vms.stop_vms_safely([self.vm_name])
        if not seal_vm(self.vm_name, config.VM_PASSWORD):
            raise exceptions.VMException(
                "Failed to seal vm %s" % self.vm_name
            )
        if not ll_templates.createTemplate(
                positive=True, timeout=CREATE_TEMPLATE_TIMEOUT,
                vm=self.vm_name, name=self.template_name,
                cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain
        ):
            raise exceptions.TemplateException(
                "Failed to create template from vm %s" % self.vm_name
            )

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
        if not ll_vms.cloneVmFromTemplate(**args_for_clone):
            raise exceptions.VMException(
                "Failed to clone vm %s from template %s" % (
                    self.cloned_vm, self.template_name
                )
            )
        self.disks_before_copy = self.get_non_ovf_disks()
        self.basic_copy(self.cloned_vm)
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)


class CopyDiskClonedFromTemplate(CopyDiskWithContent):
    """
    A base class for cases that require data on vm's disks and create template
    from the vm with the disks
    """
    def tearDown(self):
        """
        Remove vm for testing files and all new copied disks, template
        created during the test and a cloned vm from that template
        """
        if not ll_vms.safely_remove_vms([self.test_vm_name, self.cloned_vm]):
            logger.error("Failed to remove vms")
            self.test_failed = True
        if not ll_templates.removeTemplate(
                True, self.template_name, timeout=REMOVE_TEMPLATE_TIMEOUT
        ):
            logger.error("Failed to remove template %s", self.template_name)
            self.test_failed = True

        if self.test_failed:
            raise exceptions.TearDownException(
                "Test failed during tearDown"
            )


@attr(tier=1)
class TestCaseCopyAttachedDisk(CopyDiskWithContent):
    """
    Copy disk - basic flow
    """
    __test__ = True

    @polarion("RHEVM3-11246")
    def test_same_domain_same_alias(self):
        """
        Copy existing disk to the same storage domain with the same alias
        """
        testflow.step("Copying vm %s disks", self.vm_name)
        self.basic_copy(self.vm_name)
        testflow.step(
            "Attach the newly copied disks to vm %s", self.test_vm_name
        )
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        testflow.step("Check the data exists")
        self.check_file_existence(self.test_vm_name)

    @attr(tier=2)
    @polarion("RHEVM3-11248")
    def test_same_domain_different_alias(self):
        """
        Copy existing disk to the same storage domain with different alias
        """
        self.basic_copy(self.vm_name, new_alias=self.new_alias)
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)

    @attr(tier=2)
    @polarion("RHEVM3-11242")
    def test_different_domain_same_alias(self):
        """
        Copy existing disk to different storage domain with the same alias
        """
        self.basic_copy(self.vm_name, same_domain=False)
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)

    @attr(tier=2)
    @polarion("RHEVM3-11247")
    def test_different_domain_different_alias(self):
        """
        Copy existing disk to different storage domain with different alias
        """
        self.basic_copy(
            self.vm_name, same_domain=False, new_alias=self.new_alias
        )
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)


@attr(tier=1)
class TestCaseCopyFloatingDisk(CopyDiskWithoutContent):
    """
    Copy floating disk - basic flow
    """
    __test__ = True

    @polarion("RHEVM3-11252")
    def test_same_domain_same_alias(self):
        """
        Copy existing disk to the same storage domain with the same alias
        """
        testflow.step("Copying disks %s", self.disks_for_test)
        self.basic_copy()

    @attr(tier=2)
    @polarion("RHEVM3-11254")
    def test_same_domain_different_alias(self):
        """
        Copy existing disk to the same storage domain with different alias
        """
        self.basic_copy(new_alias=self.new_alias)

    @attr(tier=2)
    @polarion("RHEVM3-11251")
    def test_different_domain_same_alias(self):
        """
        Copy existing disk to different storage domain with the same alias
        """
        self.basic_copy(same_domain=False)

    @attr(tier=2)
    @polarion("RHEVM3-11253")
    def test_different_domain_different_alias(self):
        """
        Copy existing disk to different storage domain with different alias
        """
        self.basic_copy(same_domain=False, new_alias=self.new_alias)


@attr(tier=2)
class TestCaseCopyDiskNoSpaceLeft(CopyDiskWithoutContent):
    """
    Copy floating disk -  Not enough space on target domain
    """
    __test__ = False

    def setUp(self):
        """
        Configure the critical space threshold to save time in creating
        large disks
        """
        # TODO: Implement when ticket
        # https://projects.engineering.redhat.com/browse/RHEVM-2415
        # is resolved

    @polarion("RHEVM3-11262")
    def test_no_space_left_same_domain(self):
        """
        Copy existing disk to the same storage domain
        """
        self.basic_copy(positive=False)

    @polarion("RHEVM3-11263")
    def test_no_space_left_different_domain(self):
        """
        Copy existing disk to different storage domain
        """
        self.basic_copy(positive=False, same_domain=False)


@attr(tier=2)
class TestCase11264(CopyDiskWithContent):
    """
    Copy disk - VM in various states
    """
    __test__ = True

    @polarion("RHEVM3-11246")
    def test_copy_when_vm_in_various_states(self):
        """
        Copy existing disk to the same storage when vm in different states
        """
        disk_objects = [
            d for d in ll_disks.DISKS_API.get(absLink=False)
            if d.get_id() in self.disks_for_test
        ]
        copy_disk_args = copy_args.copy()
        copy_disk_args['new_disk_alias'] = self.new_alias
        copy_disk_args['positive'] = False
        logger.info(
            "Starting vm %s before performing copy disk, this should fail",
            self.vm_name
        )
        ll_vms.start_vms([self.vm_name])
        for disk_obj in disk_objects:
            target_sd = self.get_disk_storage_domain_name(disk_obj)
            copy_disk_args['target_domain'] = target_sd
            copy_disk_args['disk_id'] = disk_obj.get_id()
            ll_disks.copy_disk(**copy_disk_args)

        self.basic_copy(self.vm_name)
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)


@attr(tier=2)
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
    def test_copy_vm_disks_with_snapshot(self):
        """
        Copy existing disk when vm is with snapshot
        """
        if not ll_vms.addSnapshot(
                True, self.vm_name, self.snapshot_description
        ):
            raise exceptions.SnapshotException(
                "Failed to create snapshot for vm %s" % self.vm_name
            )
        ll_jobs.wait_for_jobs([ENUMS['job_create_snapshot']])

        self.basic_copy(self.vm_name)
        self.attach_new_disks_to_vm(self.test_vm_name, self.new_disks)
        self.check_file_existence(self.test_vm_name)


@attr(tier=2)
class TestCase11140(CopyDiskClonedFromTemplate):
    """
    Copy disk - Vm cloned from template as clone
    """
    __test__ = True
    template_name = "template_copy_disk_11140"
    cloned_vm = 'cloned_vm_copy_disk_11140'

    @polarion("RHEVM3-11340")
    def test_copy_vm_disks_after_cloned_as_clone(self):
        """
        Copy existing disk when vm cloned from snapshot as clone
        """
        self.copy_with_template()


@attr(tier=2)
class TestCase11141(CopyDiskClonedFromTemplate):
    """
    Copy disk - Vm cloned from template as thin
    """
    __test__ = True
    template_name = "template_copy_disk_11141"
    cloned_vm = 'cloned_vm_copy_disk_11141'

    @polarion("RHEVM3-11341")
    def test_copy_vm_disks_after_cloned_as_thin(self):
        """
        Copy existing disk when vm cloned from snapshot as thin
        """
        self.copy_with_template(clone=False)
