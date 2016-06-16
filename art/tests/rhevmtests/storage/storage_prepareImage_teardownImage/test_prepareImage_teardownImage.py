"""
3.5 prepareImage and teardownImage
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
"""
# TODO: All tests have been marked with tier=config.DO_NOT_RUN #17
# (which means they won't be executed),
# because vdsClient isn't supported
import config
import logging
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, attachDisk, wait_for_disks_status, get_disk_obj, detachDisk,
    deleteDisk, move_disk,
)
from art.rhevm_api.tests_lib.low_level import jobs as ll_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainNamesForType,
)
from art.rhevm_api.tests_lib.low_level.templates import (
    createTemplate, removeTemplate,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, waitForVMState, startVm, removeVm,
    waitForVmDiskStatus, addSnapshot, removeSnapshot, cloneVmFromTemplate,
    removeVms, safely_remove_vms,
)
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import StorageTest as BaseTestCase
from art.unittest_lib import attr
from rhevmtests.storage.helpers import (
    create_vm_or_clone, perform_dd_to_disk, host_to_use, get_spuuid,
    get_sduuid, get_imguuid, get_voluuid,
)
logger = logging.getLogger(__name__)
VM1_NAME = "vm_%s" % config.TESTNAME
VM1_SNAPSHOT1_DESCRIPTION = "vm1_snap1_description"
VM2_NAME = "case_4602_wipe_after_delete"
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
            'os_type': config.OS_TYPE,
            'user': config.VM_USER,
            'password': config.VM_PASSWORD,
            'network': config.MGMT_BRIDGE,
            'display_type': config.DISPLAY_TYPE,
            }

CMD_ERROR_INCORRECT_NUM_PARAMS_PART_1 = \
    "Error using command: Wrong number of parameters"
CMD_ERROR_INCORRECT_NUM_PARAMS_PART_2 = \
    "<spUUID> <sdUUID> <imgUUID> <volUUID>"
CMD_ERROR_INCORRECT_NUM_PARAMS_PART_3 = \
    "Prepare an image, making the needed volumes available."

CMD_OK = "OK"
CMD_INCORRECT_PARAMETER = "incorrect"
CMD_ERROR_INVALID_SP_UUID = "Storage pool does not exist: ('incorrect',)"
CMD_ERROR_INVALID_SD_UUID = "Storage domain does not exist: ('incorrect',)"
CMD_ERROR_INVALID_IMG_UUID = "Image does not exist: ('incorrect',)"
CMD_ERROR_INVALID_VOL_UUID = "Volume does not exist: ('incorrect',)"

CMD_ERROR_NO_SPACE_LEFT = "No space left on device"
CMD_ERROR_VOLUME_DOES_NOT_EXIST = "Volume does not exist"
ENUMS = config.ENUMS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
TIMEOUT_IMAGE_OPERATION = 120


def setup_module():
    """
    Prepares environment, setting up the Data center and creating one VM
    """
    logger.info('Creating VM to be used for all tests except for case 4602')
    if not create_vm_or_clone(**vm1_args):
        raise exceptions.VMException(
            "Unable to create or clone VM '%s'" % VM1_NAME
        )


def teardown_module():
    """
    Clean Data Center and VM created for test
    """
    test_failed = False
    logger.info('Removing created VM')
    stop_vms_safely([VM1_NAME])
    waitForVMState(VM1_NAME, config.VM_DOWN)
    if not removeVms(True, [VM1_NAME]):
        logger.error("Failed to remove VM %s" % VM1_NAME)
        test_failed = True
    ll_jobs.wait_for_jobs([ENUMS['job_remove_vm']])
    if test_failed:
        raise exceptions.TearDownException(
            "Test failed while executing teardown_module"
        )


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
        stop_vms_safely([self.vm_name])
        for disk_alias in self.disk_aliases:
            detachDisk(True, disk_alias, self.vm_name)
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

        # In the case of a wipe after delete disk (case 4602), only add
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
                                                       self.polarion_test_case,
                                                       self.storage_domain)
            self.disk_aliases.append(self.disk_alias)
            self.assertTrue(addDisk(True, alias=self.disk_alias,
                                    provisioned_size=disk_size,
                                    sparse=disk_sparse,
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
                    self.sp_id, self.sd_ids[i], self.img_ids[i], volume_id,
                    timeout=TIMEOUT_IMAGE_OPERATION
                )
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
                    self.vol_ids[i], timeout=TIMEOUT_IMAGE_OPERATION
                )
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
                      self.vol_ids[i], ""]
            for index in indices:
                params[index] = CMD_INCORRECT_PARAMETER
            if function == "prepareImage":
                function_obj = self.host_machine.execute_prepareImage_command
            else:
                function_obj = self.host_machine.execute_teardownImage_command

            # preapreImage/teardownImage only accepts four parameters, simulate
            # passing an extra one concatenating the extra parameter to the
            # last parameter (volume uuid)
            status, output = function_obj(
                params[0], params[1], params[2],
                "{vol_uuid} {extra_param}".format(
                    vol_uuid=params[3], extra_param=params[4]
                )
            )
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4581(BasicEnvironment):
    """
    Prepare image with all the correct parameters
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages'] or FCP in opts['storages']
    storages = set([ISCSI, FCP])
    polarion_test_case = '4581'
    disk_count = 2

    @polarion("RHEVM3-4581")
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
        self.assertTrue(startVm(True, self.vm_name, config.VM_UP),
                        "Failed to start VM '%s'" % self.vm_name)


@attr(tier=config.DO_NOT_RUN)
class TestCase4595(BasicEnvironment):
    """
    Prepare image with no parameters
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4595'
    disk_count = 2

    @polarion("RHEVM3-4595")
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4596(BasicEnvironment):
    """
    Prepare image with optional flag unset
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4596'
    disk_count = 2
    snapshot_success = False
    # Bugzilla history: 1115556

    def setUp(self):
        super(TestCase4596, self).setUp()
        logger.info("Create a snapshot that includes all attached disks")
        self.snapshot_success = addSnapshot(True, self.vm_name,
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
            removeSnapshot(True, self.vm_name, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase4596, self).tearDown()

    @polarion("RHEVM3-4596")
    @bz({'1254001': {}})
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4597(BasicEnvironment):
    """
    Prepare image with 1 erroneous flag value
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4597'
    disk_count = 1

    @polarion("RHEVM3-4597")
    @bz({'1130995': {}})
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4598(BasicEnvironment):
    """
    Prepare image with several erroneous parameters
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4598'
    disk_count = 2

    @polarion("RHEVM3-4598")
    @bz({'1130995': {}})
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4599(BasicEnvironment):
    """
    Prepare image on VM with multiple disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4599'
    disk_count = 5
    snapshot_success = False

    def tearDown(self):
        logger.info("Remove the snapshot created (if it succeeded), paving "
                    "the way for the disk to be detached and removed")
        if self.snapshot_success:
            removeSnapshot(True, self.vm_name, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase4599, self).tearDown()

    @polarion("RHEVM3-4599")
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
        self.snapshot_success = addSnapshot(True, self.vm_name,
                                            VM1_SNAPSHOT1_DESCRIPTION,
                                            wait=True, persist_memory=False,
                                            disks_lst=self.disk_aliases)
        self.assertTrue(self.snapshot_success, "Taking a snapshot of "
                                               "the VM failed, aborting case")

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks following the snapshot on the powered off"
                    "VM")
        self.basic_positive_flow()


@attr(tier=config.DO_NOT_RUN)
class TestCase4600(BasicEnvironment):
    """
    Prepare image on VM with disks from different Storage Domains
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4600'
    disk_count = 4
    snapshot_success = False

    def setUp(self):
        super(TestCase4600, self).setUp()
        logger.info("Migrate the last two disks added to a secondary storage "
                    "domain")
        target_storage_domain = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[1]
        for index in xrange(2):
            self.assertTrue(
                move_disk(
                    disk_name=self.disk_aliases[self.disk_count - index - 1],
                    target_domain=target_storage_domain
                ), "Migrating disk failed for disk '%s" %
                self.disk_aliases[self.disk_count - index - 1]
            )
            # Update the Storage domain ID for the disk that was migrated
            disk_obj = get_disk_obj(self.disk_aliases[self.disk_count -
                                                      index - 1])
            self.sd_ids[self.disk_count - index - 1] = get_sduuid(disk_obj)

    def tearDown(self):
        logger.info("Remove the snapshot created (if it succeeded), paving "
                    "the way for the disk to be detached and removed")
        if self.snapshot_success:
            removeSnapshot(True, self.vm_name, VM1_SNAPSHOT1_DESCRIPTION)
        super(TestCase4600, self).tearDown()

    @polarion("RHEVM3-4600")
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
        self.snapshot_success = addSnapshot(True, self.vm_name,
                                            VM1_SNAPSHOT1_DESCRIPTION,
                                            wait=True, persist_memory=False,
                                            disks_lst=self.disk_aliases)
        self.assertTrue(self.snapshot_success, "Taking a snapshot of "
                                               "the VM failed, aborting case")

        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks following the snapshot on the powered off"
                    "VM")
        self.basic_positive_flow()


@attr(tier=config.DO_NOT_RUN)
class TestCase4601(BasicEnvironment):
    """
    Prepare image for Disks on a VM created from template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4601'
    disk_count = 3

    def setUp(self):
        super(TestCase4601, self).setUp()
        logger.info("Create a template with 3 disks")
        template_name = "template_%s" % self.polarion_test_case
        self.assertTrue(createTemplate(True, wait=True, vm=self.vm_name,
                                       name=template_name,
                                       cluster=config.CLUSTER_NAME),
                        "Failed to create template '%s'" % template_name)

        logger.info("Remove the original VM created which was used to "
                    "generate the template so that there are no duplicate "
                    "VMs or disk aliases")
        if not removeVm(True, self.vm_name):
            logger.error("Failed to remove VM %s", self.vm_name)
            BaseTestCase.test_failed = True

        logger.info("Create a VM from the template created earlier in the "
                    "test")
        self.assertTrue(cloneVmFromTemplate(True, name=self.vm_name,
                                            template=template_name,
                                            cluster=config.CLUSTER_NAME),
                        "Failed to clone a VM from template '%s'" %
                        template_name)
        waitForVMState(self.vm_name, config.VM_DOWN)

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

    @polarion("RHEVM3-4601")
    def test_prepare_image_from_template(self):
        """
        1. Create a VM from a VM template with 3 disks
        2. Run prepareImage from vdsClient using all parameters, ensuring
        that the disk is activated
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=config.DO_NOT_RUN)
class TestCase4602(BasicEnvironment):
    """
    Prepare image with 1 disk missing/corrupted from VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4602'
    disk_count = 4
    vm_name = VM2_NAME

    def setUp(self):
        logger.info('Creating VM to be used only for case 4602')
        sd_name = getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        vm2_args['storageDomainName'] = sd_name
        if not create_vm_or_clone(**vm2_args):
            raise exceptions.VMException(
                "Unable to create or clone VM '%s'" % self.vm_name
            )
        logger.info('Powering off VM %s', self.vm_name)
        stop_vms_safely([self.vm_name])
        logger.info("Register the %s standard disks", self.disk_count)
        super(TestCase4602, self).setUp()
        # For wipe after delete disks the prepareImage/teardownImage operation
        # takes longer to finish
        logger.info("Create and attach a 5 GB disk with wipe after delete "
                    "marked to existing VM")
        self.create_and_attach_disks(wipe_after_delete=True)
        # Register the UUIDs for the wipe after delete disk
        self.register_required_storage_uuids(wipe_after_delete=True)
        logger.info('Powering on VM %s', self.vm_name)
        if not startVm(True, self.vm_name, config.VM_UP, wait_for_ip=True):
            raise exceptions.VMException(
                "Failed to start VM '%s'" % self.vm_name
            )

    def tearDown(self):
        """ Power off VM, remove its disks and then remove VM """
        if not safely_remove_vms([self.vm_name]):
            logger.error("Failed to power off and remove VM %s", self.vm_name)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()

    @polarion("RHEVM3-4602")
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
        self.assertTrue(CMD_OK in teardown_output,
                        "Did not observe the expected message, '%s', as "
                        "part of the output '%s'" %
                        (CMD_ERROR_VOLUME_DOES_NOT_EXIST, teardown_output))

        # Remove the wipe after delete disk alias so it doesn't get deleted
        # again in the class tearDown
        self.disk_aliases.pop(-1)
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=config.DO_NOT_RUN)
class TestCase4605(BasicEnvironment):
    """
    Prepare image followed by Tear Down, then run Prepare image once more
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4605'
    disk_count = 5

    @polarion("RHEVM3-4605")
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4594(BasicEnvironment):
    """
    Prepare image followed by Tear down
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4594'
    disk_count = 5

    @polarion("RHEVM3-4594")
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4593(BasicEnvironment):
    """
    Tear down image with a powered off VM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4593'
    disk_count = 5

    @polarion("RHEVM3-4593")
    def test_multiple_disks_using_only_teardown_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient run the Tear down image command with all the
        correct parameters
        """
        logger.info("Run prepareImage once more for all disks on the powered "
                    "off VM")
        self.basic_positive_flow_teardown_image_only()


@attr(tier=config.DO_NOT_RUN)
class TestCase4582(BasicEnvironment):
    """
    Tear down image with all flags set
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4582'
    disk_count = 5

    @polarion("RHEVM3-4582")
    def test_multiple_disks_using_prepare_then_teardown_image(self):
        """
        1. Create a VM with 5 disks
        2. From the vdsClient, run prepareImage on each of the disks
        3. From the vdsClient, run teardownImage on all the images
        """
        logger.info("Run through the prepareImage and teardownImage flows "
                    "for all disks on the powered off VM")
        self.basic_positive_flow()


@attr(tier=config.DO_NOT_RUN)
class TestCase4584(BasicEnvironment):
    """
    Tear down image with optional flags unset
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4584'
    disk_count = 5

    @polarion("RHEVM3-4584")
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4585(BasicEnvironment):
    """
    Tear down image with 1 erroneous flag value
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4585'
    disk_count = 1

    @polarion("RHEVM3-4585")
    @bz({'1130995': {}})
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


@attr(tier=config.DO_NOT_RUN)
class TestCase4586(BasicEnvironment):
    """
    Tear down image with several erroneous parameters
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_Expose_PrepareImage_and_TeardownImage
    """
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '4586'
    disk_count = 2

    @polarion("RHEVM3-4586")
    @bz({'1130995': {}})
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
