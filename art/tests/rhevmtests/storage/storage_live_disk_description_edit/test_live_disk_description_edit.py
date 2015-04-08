"""
3.5 Live Disk Description Edit
https://tcms.engineering.redhat.com/plan/14844
"""

import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    deleteDisk, updateDisk, addDisk, attachDisk, wait_for_disks_status,
    detachDisk, get_other_storage_domain,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as BaseTestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, startVm, removeVm,
    remove_all_vm_lsm_snapshots, live_migrate_vm_disk,
)
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.test_handler import exceptions
from rhevmtests.storage.helpers import (
    create_disks_from_requested_permutations, create_vm_or_clone,
)
from rhevmtests.storage.storage_live_disk_description_edit import config
from rhevmtests.storage.storage_live_disk_description_edit.helpers import (
    verify_vm_disk_description,
)

logger = logging.getLogger(__name__)

TEST_PLAN_ID = '14844'

VM1_NAME = "vm1_" + config.TESTNAME
VM2_NAME = "vm2_" + config.TESTNAME
VM2_DISK1_ALIAS = VM2_NAME + "_disk1_alias"
VM2_DISK1_DESCRIPTION = VM2_NAME + "_disk1_initial_description"

VM_INITIAL_DESCRIPTION = "disk_description_initial_state"
VM_POWERED_ON_DESCRIPTION = "vm_powered_on_disk_description"
VM_SUSPENDED_DESCRIPTION = "vm_suspended_on_disk_description"

ALIAS = "alias"
DESCRIPTION = "description"
DESCRIPTION_ORIG = "description_orig"

vm_main_arguments = {
    'positive': True, 'vmName': VM1_NAME,
    'vmDescription': VM1_NAME + "_description", 'cluster': config.CLUSTER_NAME,
    'installation': False, 'nic': 'nic1', 'network': config.MGMT_BRIDGE,
    'start': 'false'
}


def setup_module():
    """
    Prepares environment, setting up the Data center and creating one VM
    """
    if not config.GOLDEN_ENV:
        logger.info("Preparing Data Center %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    logger.info('Creating a VM')
    if not create_vm_or_clone(**vm_main_arguments):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % VM1_NAME)


def teardown_module():
    """
    Cleanup VM created for test and the Data Center (when not running on GE)
    """
    logger.info('Removing created VM')
    # Wait for all jobs in case a failure happened in one of the cases and a
    # task is still in progress
    wait_for_jobs()
    stop_vms_safely([VM1_NAME])
    waitForVMState(VM1_NAME, config.VM_DOWN)
    assert removeVm(True, VM1_NAME)

    if not config.GOLDEN_ENV:
        logger.info('Cleaning Data Center')
        datacenters.clean_datacenter(
            True,
            config.DATA_CENTER_NAME,
            vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False

    def setup_with_disks(self, disk_interfaces=(config.VIRTIO,
                                                config.VIRTIO_SCSI)):
        """
        Creates a set of disks to be used with all the Live disk
        description edit tests, and saves a dictionary with the aliases
        and descriptions of the created disks
        """
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.disk_aliases_and_descriptions = \
            create_disks_from_requested_permutations(
                self.storage_domain, disk_interfaces, config.DISK_SIZE)

    def tearDown(self):
        """
        Remove the disks created as part of the initial setup, this is to
        ensure no conflict between runs including Rest API and SDK
        """
        for disk_dict in self.disk_aliases_and_descriptions:
            deleteDisk(True, disk_dict['alias'])


class BaseClassEditDescription(BasicEnvironment):
    """
    Base class to be used by test cases 396316 and 396321
    """
    __test__ = False

    def setUp(self):
        """
        Pass in all disk interfaces (including IDE) for the 2 basic sanity
        cases
        """
        disk_interfaces = (config.IDE, config.VIRTIO, config.VIRTIO_SCSI)
        self.setup_with_disks(disk_interfaces)

    def basic_positive_flow(self):
        for disk_dict in self.disk_aliases_and_descriptions:
            logger.info("Attaching disk '%s' to VM", disk_dict[ALIAS])
            attachDisk(True, disk_dict[ALIAS], VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])

            disk_dict[DESCRIPTION] += "_update"
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
        logger.info("Starting VM")
        assert startVm(True, VM1_NAME, config.VM_UP)
        for disk_dict in self.disk_aliases_and_descriptions:
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
            disk_dict[DESCRIPTION] = VM_POWERED_ON_DESCRIPTION
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
        logger.info("Stopping VM safely")
        stop_vms_safely([VM1_NAME])
        waitForVMState(VM1_NAME, config.VM_DOWN)
        for disk_dict in self.disk_aliases_and_descriptions:
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
            disk_dict[DESCRIPTION] = disk_dict[DESCRIPTION_ORIG]
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)
            detachDisk(True, disk_dict[ALIAS], VM1_NAME)


@attr(tier=0)
class TestCase396316(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a block domain
    https://tcms.engineering.redhat.com/case/396316/?from_plan=14844 (block)
    """
    __test__ = BaseClassEditDescription.storage in config.BLOCK_TYPES
    tcms_test_case = '396316'
    bz = ({'1206911': {'engine': ['java'], 'version': ['3.5']},
           '1211314': {'engine': ['cli'], 'version': ['3.5', '3.6']}})

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_edit_description_on_block_or_file_domain(self):
        """
        1. Add VM with a block based disk, add a description and run the VM,
        verify description
        2. Edit description while the VM is up
        3. Power off the VM, run the VM and verify that the description
        hasn't changed
        4. Suspend the VM, edit description, power off the VM and verify the
        description
        """
        self.basic_positive_flow()


@attr(tier=0)
class TestCase396321(BaseClassEditDescription):
    """
    Edit Disk description for a machine on a file domain
    https://tcms.engineering.redhat.com/case/396321/?from_plan=14844
    """
    __test__ = BaseClassEditDescription.storage not in config.BLOCK_TYPES
    tcms_test_case = '396321'
    bz = ({'1206911': {'engine': ['java'], 'version': ['3.5']},
           '1211314': {'engine': ['cli'], 'version': ['3.5', '3.6']}})

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_edit_description_on_block_or_file_domain(self):
        """
        1. Add VM with a file based disk, add a description and run the VM,
        verify description
        2. Edit description while the VM is up
        3. Power off the VM, run the VM and verify that the description
        hasn't changed
        4. Suspend the VM, edit description, power off the VM and verify the
        description
        """
        self.basic_positive_flow()


@attr(tier=1)
class TestCase396320(BasicEnvironment):
    """
    Hot plug disk from one running VM to another, ensuring that the
    description does not change
    https://tcms.engineering.redhat.com/case/396320/?from_plan=14844
    """
    __test__ = True
    tcms_test_case = '396320'

    def setUp(self):
        self.setup_with_disks()

        vm_arguments = vm_main_arguments.copy()
        vm_arguments['vmName'] = VM2_NAME
        vm_arguments['vmDescription'] = VM2_NAME + "_description"

        logger.info('Creating 2nd VM needed for the test')
        if not create_vm_or_clone(**vm_arguments):
            raise exceptions.VMException('Unable to create vm %s for test'
                                         % VM2_NAME)
        addDisk(True, alias=VM2_DISK1_ALIAS,
                description=VM2_DISK1_DESCRIPTION,
                size=config.DISK_SIZE, interface=config.INTERFACE_VIRTIO,
                sparse=True, format=config.DISK_FORMAT_COW,
                storagedomain=self.storage_domain, bootable=False)
        wait_for_disks_status(VM2_DISK1_ALIAS)
        attachDisk(True, VM2_DISK1_ALIAS, VM2_NAME)

    def tearDown(self):
        super(TestCase396320, self).tearDown()
        stop_vms_safely([VM2_NAME])
        waitForVMState(VM2_NAME, config.VM_DOWN)
        removeVm(True, VM2_NAME)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_verify_disk_description_edit_works_across_hot_plug(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Remove the Disk
        3. Hot plug the disk into a new VM, verify that the description is
        still valid
        """
        for disk_dict in self.disk_aliases_and_descriptions:
            attachDisk(True, disk_dict[ALIAS], VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])

            disk_dict[DESCRIPTION] = VM_INITIAL_DESCRIPTION
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)

        assert startVm(True, VM1_NAME, config.VM_UP)
        assert startVm(True, VM2_NAME, config.VM_UP)
        for disk_dict in self.disk_aliases_and_descriptions:
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])

            disk_dict[DESCRIPTION] = VM_POWERED_ON_DESCRIPTION
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
            detachDisk(True, disk_dict[ALIAS], VM1_NAME)
            attachDisk(True, disk_dict[ALIAS], VM2_NAME)
            assert verify_vm_disk_description(VM2_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])

        # Detach disk that was attached into the 2nd VM from the 1st
        stop_vms_safely([VM1_NAME, VM2_NAME])
        waitForVMState(VM1_NAME, config.VM_DOWN)
        waitForVMState(VM2_NAME, config.VM_DOWN)
        for disk_dict in self.disk_aliases_and_descriptions:
            disk_dict[DESCRIPTION] = disk_dict[DESCRIPTION_ORIG]
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM2_NAME)
            detachDisk(True, disk_dict[ALIAS], VM2_NAME)


@attr(tier=1)
class TestCase396322(BasicEnvironment):
    """
    Attempt to edit a disk's description on a running VM while running a
    Live storage migration
    https://tcms.engineering.redhat.com/case/396322/?from_plan=14844
    """
    __test__ = True
    tcms_test_case = '396322'

    def setUp(self):
        self.setup_with_disks()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_ensure_disk_description_is_locked_during_lsm(self):
        """
        1. Add VM with a disk, run the VM and add a description while the VM
        is powered on
        2. Start a Live Storage migration, and ensure that the disk
        description cannot happen while this operation is running
        """
        for disk_dict in self.disk_aliases_and_descriptions:
            attachDisk(True, disk_dict[ALIAS], VM1_NAME)
        assert startVm(True, VM1_NAME, config.VM_UP)

        for disk_dict in self.disk_aliases_and_descriptions:
            disk_dict[DESCRIPTION] = VM_POWERED_ON_DESCRIPTION
            assert updateDisk(True, alias=disk_dict[ALIAS],
                              description=disk_dict[DESCRIPTION],
                              vmName=VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])
        # Find a storage domain of the same type to migrate the disk into
        target_sd = get_other_storage_domain(disk_dict[ALIAS], VM1_NAME,
                                             self.storage)
        live_migrate_vm_disk(VM1_NAME, disk_dict[ALIAS], target_sd,
                             wait=False)
        disk_description_expected_to_fail = \
            "LSM_disk_description_will_not_work_at_all"
        logger.info('Waiting until disk is locked, expected to be the'
                    'case when the Snapshot operation commences')
        assert wait_for_disks_status(
            disk_dict[ALIAS],
            status=config.DISK_LOCKED
        )

        for disk_dict in self.disk_aliases_and_descriptions:
            assert updateDisk(False, alias=disk_dict[ALIAS],
                              description=disk_description_expected_to_fail,
                              vmName=VM1_NAME)
            assert verify_vm_disk_description(VM1_NAME, disk_dict[ALIAS],
                                              disk_dict[DESCRIPTION])

    def tearDown(self):
        """
        Ensure that the snapshot created is removed and all disks are detached
        """
        # Power off VM, remove snapshot created during Live storage
        # migration and then delete each disk
        logger.info(
            'Wait until all jobs have completed and the disk is no longer '
            'locked, this will be the case once Live storage migration has '
            'completed'
        )

        wait_for_jobs()
        for disk_dict in self.disk_aliases_and_descriptions:
            wait_for_disks_status(disk_dict[ALIAS], timeout=900, sleep=5)

        stop_vms_safely([VM1_NAME])
        waitForVMState(VM1_NAME, config.VM_DOWN)
        remove_all_vm_lsm_snapshots(VM1_NAME)
        super(TestCase396322, self).tearDown()
