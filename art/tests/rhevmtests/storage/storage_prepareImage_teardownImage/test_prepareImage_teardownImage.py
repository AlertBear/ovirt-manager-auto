"""
3.5 prepareImage and teardownImage
https://tcms.engineering.redhat.com/plan/14466
"""
from concurrent.futures.thread import ThreadPoolExecutor
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)
from art.test_handler.tools import tcms  # pylint: disable=E0611
import config
from helpers import (
    get_spuuid, get_sduuid, get_imguuid, get_voluuid,
)
import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, attachDisk, wait_for_disks_status, get_disk_obj, detachDisk,
    deleteDisk, move_disk,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    cleanDataCenter, getStorageDomainNamesForType,
)
from art.unittest_lib import StorageTest as BaseTestCase
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, startVm, removeVm,
    waitForVmDiskStatus, addSnapshot, removeSnapshot, cloneVmFromTemplate,
    removeVms,
)
from art.unittest_lib import attr
from rhevmtests.storage.helpers import (
    create_vm_or_clone, perform_dd_to_disk, host_to_use,
)

logger = logging.getLogger(__name__)

TEST_PLAN_ID = '14466'

VM1_NAME = "vm_%s" % config.TESTNAME
VM1_SNAPSHOT1_DESCRIPTION = "vm1_snap1_description"
VM2_NAME = "case_389924_wipe_after_delete"

vm1_args = {'positive': True,
            'vmName': VM1_NAME,
            'vmDescription': VM1_NAME + "_description",
            'cluster': config.CLUSTER_NAME,
            'installation': False,
            'nic': config.NIC_NAME[0],
            'network': config.MGMT_BRIDGE
            }

vm2_args = {'positive': True,
            'vmName': VM2_NAME,
            'vmDescription': VM2_NAME + "_description",
            'diskInterface': config.VIRTIO,
            'volumeFormat': config.DISK_FORMAT_COW,
            'cluster': config.CLUSTER_NAME,
            'storageDomainName': "",
            'installation': True,
            'size': 10 * config.GB,
            'nic': config.NIC_NAME[0],
            'image': config.COBBLER_PROFILE,
            'useAgent': True,
            'os_type': config.ENUMS['rhel6'],
            'user': config.VM_USER,
            'password': config.VM_PASSWORD,
            'network': config.MGMT_BRIDGE
            }

CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1 = \
    "Error using command: Wrong number of parameters"
CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2 = \
    "<spUUID> <sdUUID> <imgUUID> [<volUUID>]"
CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3 = \
    "Prepare an image, making the needed volumes available."

CMD_INCORRECT_PARAMETER = "incorrect"
CMD_ERROR_INVALID_SP_UUID = "Storage pool does not exist: ('incorrect',)"
CMD_ERROR_INVALID_SD_UUID = "Storage domain does not exist: ('incorrect',)"
CMD_ERROR_INVALID_IMG_UUID = "Image does not exist: ('incorrect',)"
CMD_ERROR_INVALID_VOL_UUID = "Volume does not exist: ('incorrect',)"

CMD_ERROR_NO_SPACE_LEFT = "No space left on device"
CMD_ERROR_VOLUME_DOES_NOT_EXIST = "Volume does not exist"


def setup_module():
    """
    Prepares environment, setting up the Data center and creating one VM
    """
    if not config.GOLDEN_ENV:
        logger.info("Preparing Data Center %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    # Pick the 1st domain from the current storage type used, this is
    # irrelevant for the test since the disk created here is bootable and
    # will run the OS needed for a single test case (389924)
    sd_name = getStorageDomainNamesForType(config.DATA_CENTER_NAME,
                                           config.STORAGE_SELECTOR[0])[0]
    vm2_args['storageDomainName'] = sd_name

    logger.info('Creating VM to be used for all tests except for case 389924')
    logger.info('Creating VM to be used only for case 389924')
    executions = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for args in [vm1_args, vm2_args]:
            executions.append(executor.submit(create_vm_or_clone, **args))

    # Ensure that all threads have completed execution
    [execution.result() for execution in executions]


def teardown_module():
    """
    Clean Data Center and VM created for test
    """
    logger.info('Removing created VM')
    stop_vms_safely([VM1_NAME, VM2_NAME])
    waitForVMState(VM1_NAME, config.VM_DOWN)
    waitForVMState(VM2_NAME, config.VM_DOWN)
    removeVms(True, [VM1_NAME, VM2_NAME])

    if not config.GOLDEN_ENV:
        logger.info('Cleaning Data Center')
        cleanDataCenter(True, config.DATA_CENTER_NAME, vdc=config.VDC,
                        vdc_password=config.VDC_PASSWORD)


class BasicEnvironment(BaseTestCase):
    """
    This class implements disk creation/setup and basic workflow
    """
    __test__ = False
    disk_count = 0
    vm_name = VM1_NAME
    sp_id = ""

    def setUp(self):
        """
        Creates and attaches the number of disks specified for each test
        case.  In addition, lists are stored that contain the disk aliases,
        storage pool ids, storage domain ids, image ids and volume ids
        """
        self.initialize_variables()
        self.storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.create_and_attach_disks()
        self.register_required_storage_uuids()

    def tearDown(self):
        """
        Remove the disks created as part of the initial setup, this is to
        ensure no conflict between runs including Rest API and SDK
        """
        stop_vms_safely([VM1_NAME])
        for disk_alias in self.disk_aliases:
            detachDisk(True, disk_alias, VM1_NAME)
            deleteDisk(True, disk_alias)

    def initialize_variables(self):
        # Initialize the list of disk aliases, storage pool ids, storage domain
        # ids, image ids and volume ids for use within the test and with the
        # tearDown
        self.disk_aliases = []
        self.sd_ids = []
        self.img_ids = []
        self.vol_ids = []

    def register_required_storage_uuids(self, wipe_after_delete=False):
        # Add the 4 required parameters for prepareImage and teardownImage
        # across the added disks: Storage Pool ID, Storage domain ID,
        # Image ID and Volume ID

        # In the case of a wipe after delete disk (case 389924), only add
        # one disk, starting the name with the last existing index (from
        # prior disk additions)
        if wipe_after_delete:
            count = 1
        else:
            count = self.disk_count

        for i in xrange(count):
            data_center_obj = get_data_center(config.DATA_CENTER_NAME)
            self.sp_id = get_spuuid(data_center_obj)
            logger.info("The Storage Pool ID is: '%s'", self.sp_id)
            if wipe_after_delete:
                disk_obj = get_disk_obj(self.disk_aliases[len(
                    self.disk_aliases) - 1])
            else:
                disk_obj = get_disk_obj(self.disk_aliases[i])
            sd_id = get_sduuid(disk_obj)
            self.sd_ids.append(sd_id)
            logger.info("The Storage Domain ID is: '%s'", sd_id)
            img_id = get_imguuid(disk_obj)
            self.img_ids.append(img_id)
            logger.info("The Image ID is: '%s'", img_id)
            vol_id = get_voluuid(disk_obj)
            self.vol_ids.append(vol_id)
            logger.info("The Volume ID is: '%s'", vol_id)

    def create_and_attach_disks(self, wipe_after_delete=False):
        """
        Creates and attaches a variable number of disks using either one of
        existing storage domains to the existing VM
        """
        if wipe_after_delete:
            disk_size = 5 * config.GB
            disk_format = config.DISK_FORMAT_RAW
            disk_sparse = False
            disk_count = 1
        else:
            disk_size = config.DISK_SIZE
            disk_format = config.DISK_FORMAT_COW
            disk_sparse = True
            disk_count = self.disk_count

        # Store each disk alias created in a list to be used in subsequent
        # functions including tearDown
        for _ in xrange(disk_count):
            self.disk_alias = "disk_%s_%s_%s_alias" % (len(self.disk_aliases),
                                                       self.tcms_test_case,
                                                       self.storage_domain)
            self.disk_aliases.append(self.disk_alias)
            self.assertTrue(addDisk(True, alias=self.disk_alias,
                                    size=disk_size, sparse=disk_sparse,
                                    storagedomain=self.storage_domain,
                                    format=disk_format,
                                    interface=config.VIRTIO,
                                    wipe_after_delete=wipe_after_delete,
                                    bootable=False),
                            "Failed to Add Disk %s" % self.disk_alias)
            wait_for_disks_status(self.disk_alias)
            self.assertTrue(attachDisk(True, self.disk_alias, self.vm_name),
                            "Failed to attach disk '%s' to VM '%s'" % (
                                self.disk_alias, self.vm_name))
            waitForVmDiskStatus(self.vm_name, True, self.disk_alias)

    def basic_positive_flow(self):
        """
        Runs prepareImage and teardownImage calls while the VM is powered off
        """
        self.basic_positive_flow_prepare_image_only()
        self.basic_positive_flow_teardown_image_only()

    def basic_positive_flow_prepare_image_only(self, use_volume_id=True):
        """
        Runs prepareImage call while the VM is powered off, using the volume
        ID if requested
        """
        self.host_machine = host_to_use()
        for i in xrange(self.disk_count):
            logger.info("Ensure that the disk becomes active after running "
                        "prepareImage")
            volume_id = ""
            if use_volume_id:
                volume_id = self.vol_ids[i]
            status, prepare_output = \
                self.host_machine.execute_prepareImage_command(
                    self.sp_id, self.sd_ids[i], self.img_ids[i], volume_id)
            # Ensure that a status of True is returned for the prepareImage
            # execution
            logger.info("The returned status from running prepareImage is: "
                        "'%s'", status)
            logger.info("The returned output from running prepareImage is: "
                        "'%s'", prepare_output)
            self.assertTrue(status, "Status returned for prepareImage "
                                    "command was not True as expected")
            self.assertTrue(self.host_machine.compare_lv_attributes(
                self.sd_ids[i], self.vol_ids[i], "a-"),
                "The disk was not found to be active after running "
                "prepareImage")

    def basic_positive_flow_teardown_image_only(self):
        """
        Runs teardownImage call while the VM is powered off
        """
        self.host_machine = host_to_use()
        for i in xrange(self.disk_count):
            logger.info("Ensure that the disk becomes inactive after running "
                        "teardownImage")
            status, teardown_image_output = \
                self.host_machine.execute_teardownImage_command(
                    self.sp_id, self.sd_ids[i], self.img_ids[i],
                    self.vol_ids[i])
            # Ensure that a status of True is returned for the teardownImage
            # execution
            self.assertTrue(status, "Status returned for teardownImage "
                                    "command was not True as expected")
            logger.info("The returned output from running teardownImage is: "
                        "'%s'", teardown_image_output)
            self.assertTrue(self.host_machine.compare_lv_attributes(
                self.sd_ids[i], self.vol_ids[i], "--"),
                "The disk was not found to be inactive after running "
                "teardownImage")

    def basic_positive_flow_teardown_first(self, num_repetitions):
        """
        Runs teardownImage and prepareImage calls while the VM is powered off
        """
        self.host_machine = host_to_use()
        for r in xrange(num_repetitions):
            for i in xrange(self.disk_count):
                logger.info("Ensure that the initial disk attributes are "
                            "active")
                self.assertTrue(self.host_machine.compare_lv_attributes(
                    self.sd_ids[i], self.vol_ids[i], "a-"),
                    "The initial disk attributes were not found to show the "
                    "disk in an active state")

                logger.info("Ensure that the disk becomes inactive after "
                            "running teardownImage")
                status, teardown_image_output = \
                    self.host_machine.execute_teardownImage_command(
                        self.sp_id, self.sd_ids[i], self.img_ids[i],
                        self.vol_ids[i])
                # Ensure that a status of True is returned for the
                # teardownImage execution
                self.assertTrue(status, "Status returned for teardownImage "
                                        "command was not True as expected")
                logger.info("The returned output from running teardownImage "
                            "is: '%s'", teardown_image_output)
                self.assertTrue(self.host_machine.compare_lv_attributes(
                    self.sd_ids[i], self.vol_ids[i], "--"),
                    "The disk was not found to be inactive after running "
                    "teardownImage")

                logger.info("Ensure that the disk becomes active after "
                            "running prepareImage")
                status, prepare_output = \
                    self.host_machine.execute_prepareImage_command(
                        self.sp_id, self.sd_ids[i], self.img_ids[i],
                        self.vol_ids[i])
                # Ensure that a status of True is returned for the prepareImage
                # execution
                self.assertTrue(status, "Status returned for prepareImage "
                                        "command was not True as expected")
                logger.info("The returned output from running prepareImage "
                            "is: '%s'", prepare_output)
                self.assertTrue(self.host_machine.compare_lv_attributes(
                    self.sd_ids[i], self.vol_ids[i], "a-"),
                    "The disk was not found to be active after running "
                    "prepareImage")

    def basic_positive_flow_only_teardown_image_no_volume_id(self):
        """
        Runs teardownImage call without the optional volume ID while the VM is
        powered off
        """
        self.host_machine = host_to_use()
        for i in xrange(self.disk_count):
            logger.info("Ensure that the disk becomes inactive after running "
                        "teardownImage")
            status, teardown_image_output = \
                self.host_machine.execute_teardownImage_command(
                    self.sp_id, self.sd_ids[i], self.img_ids[i])
            # Ensure that a status of True is returned for the teardownImage
            # execution
            self.assertTrue(status, "Status returned for teardownImage "
                                    "command was not True as expected")
            logger.info("The returned output from running teardownImage is: "
                        "'%s'", teardown_image_output)
            self.assertTrue(self.host_machine.compare_lv_attributes(
                self.sd_ids[i], self.vol_ids[i], "--"),
                "The disk was not found to be inactive after running "
                "teardownImage")

    def basic_negative_flow_erroneous_parameters(self, function, indices,
                                                 errors):
        """
        Runs prepareImage or teardownImage with one or more incorrect
        parameters while the VM is powered off
        """
        self.host_machine = host_to_use()
        for i in xrange(self.disk_count):
            params = [self.sp_id, self.sd_ids[i], self.img_ids[i],
                      self.vol[i], ""]
            for index in indices:
                params[index] = CMD_INCORRECT_PARAMETER
            if function == "prepareImage":
                status, output = \
                    self.host_machine.execute_prepareImage_command(
                        params[0], params[1], params[2], params[3], params[4])
            else:
                status, output = \
                    self.host_machine.execute_teardownImage_command(
                        params[0], params[1], params[2], params[3], params[4])

            # Ensure that status is False, expected when any parameters are
            # missing or incorrect
            self.assertFalse(status, "The status is not False as expected when"
                                     " running with an incorrect parameter")
            logger.info("The returned output from running %s with an "
                        "incorrect parameter is: '%s'" % (function, output))
            for error in errors:
                self.assertTrue(error in output,
                                "Did not observe the expected error, '%s', as "
                                "part of the output" % error)


@attr(tier=0)
class TestCase388747(BasicEnvironment):
    """
    Prepare image with all the correct parameters
    https://tcms.engineering.redhat.com/case/388747/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '388747'
    disk_count = 2

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_all_parameters(self):
        """
        1. Create a VM with 2 disks
        2. Run prepareImage from vdsClient using no parameters, ensure that
        the expected usage is displayed
        3. Run prepareImage from vdsClient and ensure that both disks are
        activated
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()

        logger.info("Ensure that the VM can be powered on successfully")
        self.assertTrue(startVm(True, VM1_NAME, config.VM_UP),
                        "Failed to start VM '%s'" % VM1_NAME)


@attr(tier=1)
class TestCase388748(BasicEnvironment):
    """
    Prepare image with no parameters
    https://tcms.engineering.redhat.com/case/388748/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '388748'
    disk_count = 2

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_no_parameters(self):
        """
        1. Create a VM with 2 disks
        2. Run prepareImage from vdsClient using no parameters
        3. Re-run prepareImage with all parameters including the volume UUID
        """
        # Retrieve the host on which to execute prepareImage commands
        host_machine = host_to_use()
        # Retrieve the status and output from running prepareImage with no
        # parameters
        status, output = host_machine.execute_prepareImage_command()
        # Ensure that status is False, expected when any parameters are
        # missing or incorrect
        self.assertFalse(status, "Running prepareImage with no parameters "
                                 "did not yield a False status as expected")
        logger.info("The returned output from running prepareImage with no "
                    "parameters is: '%s'", output)
        self.assertTrue(CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1 in output,
                        "Did not observe the expected error, '%s', as "
                        "part of the output" %
                        CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1)
        self.assertTrue(CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2 in output,
                        "Did not observe the expected error, '%s', as "
                        "part of the output" %
                        CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2)
        self.assertTrue(CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3 in output,
                        "Did not observe the expected error, '%s', as "
                        "part of the output" %
                        CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3)

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389851(BasicEnvironment):
    """
    Prepare image with optional flag unset
    https://tcms.engineering.redhat.com/case/388851/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389851'
    disk_count = 2
    snapshot_success = False
    bz = {'1115556': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    def setUp(self):
        super(TestCase389851, self).setUp()
        logger.info("Create a snapshot that includes all attached disks")
        self.snapshot_success = addSnapshot(True, VM1_NAME,
                                            VM1_SNAPSHOT1_DESCRIPTION,
                                            wait=True,
                                            persist_memory=False,
                                            disks_lst=self.disk_aliases)
        self.assertTrue(self.snapshot_success, "Taking a snapshot of "
                                               "the VM failed, aborting case")

    def tearDown(self):
        logger.info("Remove the snapshot created (if it succeeded), paving "
                    "the way for the disk to be detached and removed")
        if self.snapshot_success:
            removeSnapshot(True, VM1_NAME, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase389851, self).tearDown()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_without_volume_id(self):
        """
        1. Create a VM with 2 disks
        2. Take a snapshot of the VM
        3. Run prepareImage from vdsClient without the optional
        parameter (volume uuid), ensuring that the disks become active
        """
        logger.info("Execute a basic flow where the Volume ID parameter "
                    "isn't passed in to prepareImage")
        self.basic_positive_flow_prepare_image_only(False)
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389852(BasicEnvironment):
    """
    Prepare image with 1 erroneous flag value
    https://tcms.engineering.redhat.com/case/389852/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389852'
    disk_count = 1
    bz = ({'1130995': {'engine': ['rest', 'sdk'], 'version': ['3.5']},
           '1184718': {'engine': ['rest', 'sdk'], 'version': ['3.5']}})

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_1_invalid_parameter(self):
        """
        1. Create a VM with 1 disk
        2. From vdsClient run the prepareImage command with an incorrect spUUID
        3. Run the prepareImage command again with an incorrect sdUUID
        4. Run the prepareImage command again with an incorrect imgUUID
        5. Run the prepareImage command again with an incorrect volUUID
        6. Run the prepareImage command again with an extra parameter
        following the volUUID
        7. Run the prepareImage command again, this time with all the correct
        parameters
        """
        logger.info("Execute the prepareImage negative flow with one "
                    "erroneous parameter")
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [0], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [1], [CMD_ERROR_INVALID_SD_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [2], [CMD_ERROR_INVALID_IMG_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [3], [CMD_ERROR_INVALID_VOL_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [4], [CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1,
                                  CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2,
                                  CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3])

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389853(BasicEnvironment):
    """
    Prepare image with several erroneous parameters
    https://tcms.engineering.redhat.com/case/389853/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389853'
    disk_count = 2
    bz = {'1130995': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_several_invalid_parameters(self):
        """
        1. Create a VM with 2 disks
        2. From vdsClient run the prepareImage command with an erroneous
        spUUID, sdUUID, volUUID but correct imgUUID
        3. From vdsClient run the prepareImage command with an erroneous
        spUUID, imgUUID, volUUID but correct sdUUID
        4. From vdsClient run the prepareImage command with an erroneous
        sdUUID, imUUID, volUUID but correct spUUID
        5. Run the prepareImage command again, this time with all the correct
        parameters
        """
        logger.info("Execute the negative flow with one multiple erroneous "
                    "parameters")
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [0, 1, 3], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [0, 2, 3], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "prepareImage", [0, 1, 3], [CMD_ERROR_INVALID_SD_UUID])

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389921(BasicEnvironment):
    """
    Prepare image on VM with multiple disks
    https://tcms.engineering.redhat.com/case/389921/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389921'
    disk_count = 5
    snapshot_success = False

    def tearDown(self):
        logger.info("Remove the snapshot created (if it succeeded), paving "
                    "the way for the disk to be detached and removed")
        if self.snapshot_success:
            removeSnapshot(True, VM1_NAME, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase389921, self).tearDown()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_multiple_disks(self):
        """
        1. Create a VM with 5 disks
        2. Run prepareImage on each disk and ensure only this disk is affected
        2. Take a snapshot of the VM
        4. Run prepareImage on each disk and ensure only this disk is affected
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()

        logger.info("Create a snapshot that includes all attached disks")
        self.snapshot_success = addSnapshot(True, VM1_NAME,
                                            VM1_SNAPSHOT1_DESCRIPTION,
                                            wait=True, persist_memory=False,
                                            disks_lst=self.disk_aliases)
        self.assertTrue(self.snapshot_success, "Taking a snapshot of "
                                               "the VM failed, aborting case")

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks following the snapshot on the powered off"
                    "VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389922(BasicEnvironment):
    """
    Prepare image on VM with disks from different Storage Domains
    https://tcms.engineering.redhat.com/case/389922/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389922'
    disk_count = 4
    snapshot_success = False

    def setUp(self):
        super(TestCase389922, self).setUp()
        logger.info("Migrate the last two disks added to a secondary storage "
                    "domain")
        target_storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        for index in xrange(2):
            self.assertTrue(move_disk(disk_name=self.disk_aliases[
                self.disk_count - index - 1],
                target_domain=target_storage_domain),
                "Migrating disk failed for disk '%s" %
                self.disk_aliases[self.disk_count - index - 1])
            # Update the Storage domain ID for the disk that was migrated
            disk_obj = get_disk_obj(self.disk_aliases[self.disk_count -
                                                      index - 1])
            self.sd_ids[self.disk_count - index - 1] = get_sduuid(disk_obj)

    def tearDown(self):
        logger.info("Remove the snapshot created (if it succeeded), paving "
                    "the way for the disk to be detached and removed")
        if self.snapshot_success:
            removeSnapshot(True, VM1_NAME, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase389922, self).tearDown()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_disks_on_multiple_domains(self):
        """
        1. Create a VM with 4 disks from 2 different Storage Domains
        2. Run prepareImage on each disk and ensure only this disk is affected
        3. Take a snapshot of the VM
        4. Run prepareImage on each disk and ensure only this disk is affected
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()

        logger.info("Create a snapshot that includes all attached disks")
        self.snapshot_success = addSnapshot(True, VM1_NAME,
                                            VM1_SNAPSHOT1_DESCRIPTION,
                                            wait=True, persist_memory=False,
                                            disks_lst=self.disk_aliases)
        self.assertTrue(self.snapshot_success, "Taking a snapshot of "
                                               "the VM failed, aborting case")

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks following the snapshot on the powered off"
                    "VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389923(BasicEnvironment):
    """
    Prepare image for Disks on a VM created from template
    https://tcms.engineering.redhat.com/case/389923/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389923'
    disk_count = 3

    def setUp(self):
        super(TestCase389923, self).setUp()
        logger.info("Create a template with 3 disks")
        template_name = "template_%s" % self.tcms_test_case
        self.assertTrue(createTemplate(True, wait=True, vm=VM1_NAME,
                                       name=template_name,
                                       cluster=config.CLUSTER_NAME),
                        "Failed to create template '%s'" % template_name)

        logger.info("Remove the original VM created which was used to "
                    "generate the template so that there are no duplicate "
                    "VMs or disk aliases")
        removeVm(True, VM1_NAME)

        logger.info("Create a VM from the template created earlier in the "
                    "test")
        self.assertTrue(cloneVmFromTemplate(True, name=VM1_NAME,
                                            template=template_name,
                                            cluster=config.CLUSTER_NAME),
                        "Failed to clone a VM from template '%s'" %
                        template_name)
        waitForVMState(VM1_NAME, config.VM_DOWN)

        logger.info("Remove the template so that there are no duplicate disk "
                    "aliases left")
        self.assertTrue(removeTemplate(True, template_name, wait=True),
                        "Failed to remove template '%s'" % template_name)

        # Re-build the list of UUIDs now that we have a new set of
        # disks created from the template
        disk_aliases_backup = self.disk_aliases
        self.initialize_variables()
        self.disk_aliases = disk_aliases_backup
        self.register_required_storage_uuids()

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_from_template(self):
        """
        1. Create a VM from a VM template with 3 disks
        2. Run prepareImage from vdsClient using all parameters, ensuring
        that the disk is activated
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389924(BasicEnvironment):
    """
    Prepare image with 1 disk missing/corrupted from VM
    https://tcms.engineering.redhat.com/case/389924/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389924'
    disk_count = 4
    vm_name = VM2_NAME
    bz = {'1184718': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    def setUp(self):
        logger.info('Powering off VM %s', self.vm_name)
        stop_vms_safely([self.vm_name])
        waitForVMState(self.vm_name, config.VM_DOWN)

        logger.info("Register the %s standard disks", self.disk_count)
        super(TestCase389924, self).setUp()

        logger.info("Create and attach a 5 GB disk with wipe after delete "
                    "marked to existing VM")
        self.create_and_attach_disks(wipe_after_delete=True)
        # Register the UUIDs for the wipe after delete disk
        self.register_required_storage_uuids(wipe_after_delete=True)
        logger.info('Powering on VM %s', self.vm_name)
        self.assertTrue(startVm(True, self.vm_name, config.VM_UP),
                        "Failed to start VM '%s'" % self.vm_name)

    def tearDown(self):
        stop_vms_safely([self.vm_name])
        for disk_alias in self.disk_aliases:
            detachDisk(True, disk_alias, self.vm_name)
            deleteDisk(True, disk_alias)

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_large_disk_marked_for_wipe_after_delete(self):
        """
        1. Create a VM with 5 disks one of 5 GB in size (with wipe after
        delete marked)
        2. Write using dd to the Wipe after delete disk
        3. Select to delete the large disk - this will take a while
        4. While the above disk is being deleted, from vdsClient run the
        prepareImage command with all the correct parameters
        5. While the above disk is being deleted, from vdsClient run the
        teardownImage command with all the correct parameters
        6. Run the prepareImage command on the remaining disks with all the
        correct parameters for each image
        """
        logger.info("Fills up the wipe after delete disk with data written "
                    "using dd urandom ")
        status, out = perform_dd_to_disk(self.vm_name, self.disk_aliases[-1])
        logger.info("The output of the file copy from the boot disk into the "
                    "5 GB disk was '%s'", out)

        logger.info("Power off the VM in order to delete the 5 GB disk and "
                    "attempt to run prepareImage and teardownImage while "
                    "delete is in progress")
        stop_vms_safely([self.vm_name])
        self.host_machine = host_to_use()
        deleteDisk(True, self.disk_aliases[-1])
        _, prepare_output = \
            self.host_machine.execute_prepareImage_command(
                self.sp_id, self.sd_ids[-1],
                self.img_ids[-1], self.vol_ids[-1])
        logger.info("The returned output from running prepareImage on the "
                    "disk being deleted was '%s'", prepare_output)
        self.assertTrue(CMD_ERROR_VOLUME_DOES_NOT_EXIST in prepare_output,
                        "Did not observe the expected error, '%s', as "
                        "part of the output '%s'" %
                        (CMD_ERROR_VOLUME_DOES_NOT_EXIST, prepare_output))

        _, teardown_output = \
            self.host_machine.execute_teardownImage_command(
                self.sp_id, self.sd_ids[-1],
                self.img_ids[-1], self.vol_ids[-1])
        logger.info("The returned output from running teardownImage on the "
                    "disk being deleted was '%s'", teardown_output)
        self.assertTrue(CMD_ERROR_VOLUME_DOES_NOT_EXIST in teardown_output,
                        "Did not observe the expected error, '%s', as "
                        "part of the output '%s'" %
                        (CMD_ERROR_VOLUME_DOES_NOT_EXIST, teardown_output))

        # Remove the wipe after delete disk alias so it doesn't get deleted
        # again in the class tearDown
        self.disk_aliases.pop(-1)

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389927(BasicEnvironment):
    """
    Prepare image followed by Tear Down, then run Prepare image once more
    https://tcms.engineering.redhat.com/case/389927/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389927'
    disk_count = 5

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_using_prepare_teardown_then_prepare_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient run the Prepare image command with all the
        correct parameters
        3.Tear down all the images
        4. Run the Prepare Image command again on each image
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()

        logger.info("Run prepareImage once more for all disks on the powered "
                    "off VM")
        self.basic_positive_flow_prepare_image_only()


@attr(tier=1)
class TestCase389931(BasicEnvironment):
    """
    Prepare image followed by Tear down
    https://tcms.engineering.redhat.com/case/389931/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389931'
    disk_count = 5

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_using_prepare_and_teardown_of_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient run the Prepare image command with all the
        correct parameters
        3.Tear down all the images
        4. Run Prepare Image again on all the images
        5. Run Tear down image followed by Prepare image across all images 5
        times
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()

        logger.info("Run prepareImage once more for all disks on the powered "
                    "off VM")
        self.basic_positive_flow_prepare_image_only()

        logger.info("Run through the teardownImage and prepareImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow_teardown_first(5)


@attr(tier=1)
class TestCase389935(BasicEnvironment):
    """
    Tear down image with a powered off VM
    https://tcms.engineering.redhat.com/case/389935/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389935'
    disk_count = 5

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_using_only_teardown_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient run the Tear down image command with all the
        correct parameters
        """
        logger.info("Run prepareImage once more for all disks on the powered "
                    "off VM")
        self.basic_positive_flow_teardown_image_only()


@attr(tier=1)
class TestCase389936(BasicEnvironment):
    """
    Tear down image with all flags set
    https://tcms.engineering.redhat.com/case/389936/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389936'
    disk_count = 5

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_using_prepare_then_teardown_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient, run prepareImage on each of the disks
        3. From the vdsClient, run teardownImage on all the images
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=1)
class TestCase389939(BasicEnvironment):
    """
    Tear down image with optional flags unset
    https://tcms.engineering.redhat.com/case/389939/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389939'
    disk_count = 5

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_multiple_disks_without_optional_volume_id_on_teardown(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient, run prepareImage on each of the disks
        3. From the vdsClient, run teardownImage on all the images without
        the optional volume ID parameter
        """
        logger.info("Run  prepareImage for all disks on the powered off VM")
        self.basic_positive_flow_prepare_image_only()

        logger.info("Run teardownImage for all disks leaving out the "
                    "optional volume ID")
        self.basic_positive_flow_only_teardown_image_no_volume_id()


@attr(tier=1)
class TestCase389940(BasicEnvironment):
    """
    Tear down image with 1 erroneous flag value
    https://tcms.engineering.redhat.com/case/389940/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389940'
    disk_count = 1
    bz = ({'1130995': {'engine': ['rest', 'sdk'], 'version': ['3.5']},
           '1184718': {'engine': ['rest', 'sdk'], 'version': ['3.5']}})

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_teardown_image_with_1_invalid_parameter(self):
        """
        1. Create a VM with 1 disk
        2. From the vdsClient, run prepareImage on the disk
        3. From vdsClient run the teardownImage command with an incorrect
        spUUID
        4. Run the teardownImage command again with an incorrect sdUUID
        5. Run the teardownImage command again with an incorrect imgUUID
        6. Run the teardownImage command again with an incorrect volUUID
        7. Run the teardownImage command with an extra parameter following
        the volUUID
        """
        logger.info("Run  prepareImage for all disks on the powered off VM")
        self.basic_positive_flow_prepare_image_only()

        logger.info("Execute the teardownImage negative flow with one "
                    "erroneous parameter")
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [0], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [1], [CMD_ERROR_INVALID_SD_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [2], [CMD_ERROR_INVALID_IMG_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [3], [CMD_ERROR_INVALID_VOL_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [4], [CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1,
                                   CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2,
                                   CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3])


@attr(tier=1)
class TestCase389943(BasicEnvironment):
    """
    Tear down image with several erroneous parameters
    https://tcms.engineering.redhat.com/case/389943/?from_plan=14466
    """
    __test__ = BasicEnvironment.storage in config.BLOCK_TYPES
    tcms_test_case = '389943'
    disk_count = 2
    bz = {'1130995': {'engine': ['rest', 'sdk'], 'version': ['3.5']}}

    @tcms(TEST_PLAN_ID, tcms_test_case)
    def test_prepare_image_with_several_invalid_parameters(self):
        """
        1. Create a VM with 1 disk
        2. From the vdsClient, run prepareImage on the disk
        3. From vdsClient run the teardownImage command with an erroneous
        spUUID, sdUUID, volUUID but correct imgUUID
        4. From vdsClient run the teardownImage command with an erroneous
        spUUID, imgUUID, volUUID but correct sdUUID
        5. From vdsClient run the teardownImage command with an erroneous
        sdUUID, imUUID, volUUID but correct spUUID
        """
        logger.info("Run  prepareImage for all disks on the powered off VM")
        self.basic_positive_flow_prepare_image_only()

        logger.info("Execute the negative teardownImage flow with multiple "
                    "erroneous parameters")
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [0, 1, 3], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [0, 2, 3], [CMD_ERROR_INVALID_SP_UUID])
        self.basic_negative_flow_erroneous_parameters(
            "teardownImage", [0, 1, 3], [CMD_ERROR_INVALID_SD_UUID])
