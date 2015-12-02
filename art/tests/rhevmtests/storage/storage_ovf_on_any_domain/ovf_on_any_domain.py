"""
3.5 Storage OVF on any Domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_OVF_On_Any_Domain
"""
import logging
import os

import config
import helpers
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.high_level import datacenters as hl_datacenters
from art.rhevm_api.tests_lib.high_level import hosts as hl_hosts
from art.rhevm_api.tests_lib.low_level import (
    clusters, datacenters, disks, hosts, jobs, storagedomains, templates,
    vmpools, vms,
)
from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as BaseTestCase
from rhevmtests.storage.helpers import (
    create_vm_or_clone, get_spuuid, get_sduuid, get_imguuid, get_voluuid,
    host_to_use,
)

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

POLARION_PROJECT = "RHEVM3-"
UPDATE_OVF_INTERVAL_CMD = "OvfUpdateIntervalInMinutes=%(minutes)s"
UPDATE_OVF_NUM_OVF_STORES_CMD = "StorageDomainOvfStoreCount=%(num_ovf_stores)s"
VM1_NAME, VM2_NAME, VM3_NAME = (config.VM_NAME_1, config.VM_NAME_2,
                                config.VM_NAME_3)
TEMPLATE_NAME = config.TEMPLATE_NAME
VM_ARGS = {
    'positive': True,
    'vmName': '',
    'vmDescription': '',
    'cluster': config.CLUSTER_NAME,
    'installation': False,
    'nic': config.NIC_NAME[0],
    'network': config.MGMT_BRIDGE,
}
ANY_DOMAIN = 0
MASTER_DOMAIN = 1
ANY_NON_MASTER_DOMAIN = 2
OVF_STORE_DISK_NAME = "OVF_STORE"
ENGINE_REGEX_VM_NAME = (
    "START, SetVolumeDescriptionVDSCommand("".|\n)*"
    "imageGroupGUID=%s(.|\n)*"
    "description={""\"Updated\":true(.|\n)*"
    "FINISH, SetVolumeDescriptionVDSCommand"
)
OBJECT_NAME_IN_OVF = "<Name>%s</Name>"
OVF_LOCAL_FILE_LOCATION = "/tmp/%s.ovf"
ISCSI = config.STORAGE_TYPE_ISCSI
NFS = config.STORAGE_TYPE_NFS
GLUSTERFS = config.STORAGE_TYPE_GLUSTER
SD_ID_DISK_ON_DOMAIN = None
DEFAULT_NUM_OVF_STORES_PER_SD = 2
UPDATED_NUM_OVF_STORES_PER_SD = 4
FIND_OVF_DISKS_TIMEOUT = 75
FIND_OVF_DISKS_SLEEP = 5
FIND_OVF_INFO_TIMEOUT = 90
FIND_OVF_INFO_SLEEP = 5


def setup_module():
    """
    Set the OvfUpdateIntervalInMinutes to 1 minute and create VMs needed by
    this test suite
    """
    logger.info("Changing the ovirt-engine service with "
                "OvfUpdateIntervalInMinutes to 1 minute, restarting engine")
    if not test_utils.set_engine_properties(
            config.ENGINE, [UPDATE_OVF_INTERVAL_CMD % {'minutes': 1}]
    ):
        raise exceptions.UnkownConfigurationException(
            "Update OVF interval failed to execute on '%s'" % config.VDC
        )

    # TODO: As a workaround for bug
    # https://bugzilla.redhat.com/show_bug.cgi?id=1275174 where storage
    # domains are coming up in Unknown state after engine restart
    helpers.ensure_data_center_and_sd_are_active()

    vm1_args = VM_ARGS.copy()
    vm1_args['vmName'] = VM1_NAME
    vm2_args = VM_ARGS.copy()
    vm2_args['vmName'] = VM2_NAME
    master_domain = helpers.get_master_storage_domain_name()
    if master_domain is None:
        raise exceptions.StorageDomainException("Unable to retrieve the master"
                                                " storage domain name")
    ovf_store_id = helpers.get_first_ovf_store_id_and_obj(master_domain)['id']
    vdsm_host = host_to_use()
    for vm_args in (vm1_args, vm2_args):
        vm_args_and_function = vm_args.copy()
        vm_args_and_function['function_name'] = create_vm_or_clone
        logger.info("Create a VM and watch the engine log for OVF processing")
        create_vm_success = helpers.watch_engine_log_for_ovf_store(
            ENGINE_REGEX_VM_NAME % ovf_store_id, vdsm_host,
            **vm_args_and_function
        )
        if not create_vm_success:
            raise exceptions.VMException(
                "Unable to create or clone VM '%s'" % vm_args['vmName']
            )


def teardown_module():
    """
    Remove the VMs created for this test suite, restore the
    OvfUpdateIntervalInMinutes to default of 60 minutes
    """
    test_failed = False
    if not vms.safely_remove_vms([VM1_NAME, VM2_NAME]):
        logger.error("Failed to remove vms %s", [VM1_NAME, VM2_NAME])
        test_failed = True
    jobs.wait_for_jobs([ENUMS['job_remove_vm']])
    logger.info("Changing the ovirt-engine service with "
                "OvfUpdateIntervalInMinutes to 60 minutes, restarting engine")
    if not test_utils.set_engine_properties(
            config.ENGINE, [UPDATE_OVF_INTERVAL_CMD % {'minutes': 60}]
    ):
        raise exceptions.HostException("Update OVF interval failed to "
                                       "execute on '%s'" % config.VDC)
    if test_failed:
        raise exceptions.TearDownException("Test failed while executing "
                                           "teardown_module")


class BasicEnvironment(BaseTestCase):
    """
    This class implements the common functions including the setUp and
    tearDown for this feature
    """
    __test__ = False
    domain_to_use = ANY_DOMAIN
    storage_domain_0 = None
    storage_domain_1 = None

    def setUp(self):
        """
        General setup function that picks a storage domain to use (matching
        the current storage type) depending on the domain_to_use choice:
        1. ANY_DOMAIN (any domain within the current storage type)
        2. MASTER_DOMAIN (the current master domain, regardless of current
        storage type)
        3. ANY_NON_MASTER_DOMAIN (any non-master domain matching the current
        storage type)
        """
        # Determine whether storage type if block or file, this is needed for
        # building the path to the OVF store and its data. Note that in the
        # case of a master storage domain, the input storage type may be
        # incorrect, will use the actual type observed
        self.is_block_storage = self.storage in config.BLOCK_TYPES
        self.sds_in_current_storage_type = (
            storagedomains.getStorageDomainNamesForType(
                config.DATA_CENTER_NAME, self.storage
            ))

        # Choose the storage domain to be used for disk creations
        self.select_storage_domain()

        # Pick a VDSM host to use for both the Block and File level OVF
        # verifications (will run machine commands on this host)
        self.host_machine = host_to_use()

        # The name of the SPM host in the default Data center and cluster
        self.host = hosts.getSPMHost(config.HOSTS)

        # Initialize variables to be used across all tests
        self.initialize_variables()

    def initialize_variables(self):
        """
        Initialize variables the OVF data dictionary, the Storage Pool ID
        and the total number of disks created. These are then used
        throughout the tests and their supporting functions
        """
        self.vms_and_disks_dict = {VM1_NAME: dict(), VM2_NAME: dict(),
                                   VM3_NAME: dict()}
        self.vm_with_no_disks_dict = dict()
        self.template_dict = dict()
        self.sp_id = None
        self.total_disks_created = 0

    def select_storage_domain(self):
        """
        Select a storage domain to be used for the disk creations based on
        requested domain type input
        """
        if self.domain_to_use == ANY_DOMAIN:
            self.storage_domain_0 = self.sds_in_current_storage_type[0]
        elif self.domain_to_use == MASTER_DOMAIN:
            found, master_domain = storagedomains.findMasterStorageDomain(
                True, config.DATA_CENTER_NAME,
            )
            if not found:
                self.error("Master storage domain not found")
            self.storage_domain_0 = master_domain['masterDomain']
            # Use the storage domain to determine whether the storage type
            # to use is block (True) or File (False)
            sd_obj = storagedomains.getStorageDomainObj(self.storage_domain_0)
            storage_type = sd_obj.get_storage().get_type()
            self.is_block_storage = storage_type in config.BLOCK_TYPES
        elif self.domain_to_use == ANY_NON_MASTER_DOMAIN:
            found, master_domain = storagedomains.findMasterStorageDomain(
                True, config.DATA_CENTER_NAME,
            )
            if not found:
                self.error("Master storage domain not found")
            master_storage_domain = master_domain['masterDomain']
            for storage_domain in self.sds_in_current_storage_type:
                if storage_domain != master_storage_domain:
                    self.storage_domain_0 = storage_domain
                    break

    def initialize_vm_ovf_store_params(self):
        """
        Initialize the OVF store parameters for the specified vm
        """
        vm = self.vm_with_no_disks_dict
        logger.info("The storage from which the OVF store will be extracted "
                    "is '%s", self.storage_domain_0)
        ovf_store = helpers.get_first_ovf_store_id_and_obj(
            self.storage_domain_0
        )
        vm['sd_id'] = get_sduuid(ovf_store['disk'])
        logger.info("The Storage Domain ID is: '%s'", vm['sd_id'])
        vm['ovf_store_id'] = ovf_store['id']
        vm['ovf_store_img_id'] = ovf_store['img_id']
        logger.info("The OVF store ID is: '%s'", vm['ovf_store_id'])
        logger.info("The OVF Image ID is: '%s'", vm['ovf_store_img_id'])

    def initialize_vm_params(self, vm_name):
        """
        Initialize the parameters for the specified vm (which has no
        attached disks)
        """
        vm = self.vm_with_no_disks_dict
        if not self.sp_id:
            data_center_obj = datacenters.get_data_center(
                config.DATA_CENTER_NAME
            )
            self.sp_id = get_spuuid(data_center_obj)
        logger.info("The Storage Pool ID is: '%s'", self.sp_id)
        vm['name'] = vm_name
        vm['vm_id'] = vms.get_vm_obj(vm_name).get_id()
        logger.info("The VM ID of the VM being used is: '%s'", vm['vm_id'])

    def initialize_template_ovf_store_params(self):
        """
        Initialize the OVF store parameters for the template
        """
        template = self.template_dict
        logger.info("The storage from which the OVF store will be extracted "
                    "is '%s", self.storage_domain_0)
        ovf_store = helpers.get_first_ovf_store_id_and_obj(
            self.storage_domain_0
        )
        template['sd_id'] = get_sduuid(ovf_store['disk'])
        logger.info("The Storage Domain ID is: '%s'", template['sd_id'])
        template['ovf_store_id'] = ovf_store['id']
        template['ovf_store_img_id'] = ovf_store['img_id']
        logger.info("The OVF store ID is: '%s'", template['ovf_store_id'])
        logger.info("The OVF Image ID is: '%s'", template['ovf_store_img_id'])

    def initialize_template_params(self, template_name):
        """
        Initialize the parameters for the specified template
        """
        template = self.template_dict
        if not self.sp_id:
            data_center_obj = datacenters.get_data_center(
                config.DATA_CENTER_NAME
            )
            self.sp_id = get_spuuid(data_center_obj)
        logger.info("The Storage Pool ID is: '%s'", self.sp_id)
        template['name'] = template_name
        template['template_id'] = (
            templates.get_template_obj(template_name).get_id()
        )
        logger.info("The Template ID of the Template being used is: '%s'",
                    template['template_id'])

    def initialize_disk_params(self, vm_name, disk_alias, raw_lun=False,
                               data_center=config.DATA_CENTER_NAME):
        """
        Initialize the disk parameters for the specified disk attached to
        the vm inputted
        """
        global SD_ID_DISK_ON_DOMAIN
        # Assign the dictionary to disk in order to improve readability
        disk = self.vms_and_disks_dict[vm_name][disk_alias]
        # Retrieve the required parameters for retrieving the OVF of each disk:
        # Storage Pool ID, Storage domain ID, Image ID and Volume ID.
        # The Storage Pool ID is unique across the entire data center,
        # only retrieve it once
        if self.sp_id is None:
            data_center_obj = datacenters.get_data_center(data_center)
            self.sp_id = get_spuuid(data_center_obj)
        logger.info("The Storage Pool ID is: '%s'", self.sp_id)
        disk_obj = disks.get_disk_obj(disk_alias)
        if not raw_lun:
            disk['sd_id'] = get_sduuid(disk_obj)
            SD_ID_DISK_ON_DOMAIN = disk['sd_id']
            logger.info("The Storage Domain ID is: '%s'", disk['sd_id'])
        else:
            disk['sd_id'] = SD_ID_DISK_ON_DOMAIN
        disk['img_id'] = get_imguuid(disk_obj)
        logger.info("The Image ID is: '%s'", disk['img_id'])
        disk['vol_id'] = get_voluuid(disk_obj)
        logger.info("The Volume ID is: '%s'", disk['vol_id'])
        logger.info("Retrieve the OVF store info for the current storage "
                    "domain, store info with current disk dictionary")
        disk_id_and_image_id = (
            helpers.get_first_ovf_store_id_and_obj(disk['sd_name'])
        )
        disk['ovf_store_id'] = disk_id_and_image_id['id']
        disk['ovf_store_img_id'] = disk_id_and_image_id['img_id']
        logger.info("The OVF store ID is: '%s'", disk['ovf_store_id'])
        logger.info("The OVF Image ID is: '%s'", disk['ovf_store_img_id'])

    def create_and_attach_disk(self, vm_name, storage_domain, bootable=True,
                               shareable=False, raw_lun=False,
                               wait_on_engine_log=True,
                               ovf_store_supported=True):
        """
        Creates and attaches a disk using the specified VM, storage domain,
        bootable flag and also allows setting a shared disk or a raw lun
        """
        # Store each disk alias created in a list to be used in subsequent
        # functions including tearDown
        disk_alias = "disk_%s_%s_%s_alias" % (
            self.total_disks_created, self.polarion_test_case, storage_domain
        )
        # Set Sparse as True by default, in the case of shareable disks set
        # it to False (which will work on both iSCSI and NFS)
        disk_format = config.DISK_FORMAT_COW
        sparse = True
        if shareable:
            disk_format = config.DISK_FORMAT_RAW
            sparse = False
        lun_address = config.EXTEND_LUN_ADDRESS[0] if raw_lun else None
        lun_target = config.EXTEND_LUN_TARGET[0] if raw_lun else None
        lun_id = config.EXTEND_LUN[0] if raw_lun else None
        self.assertTrue(
            disks.addDisk(
                True, alias=disk_alias, size=config.DISK_SIZE, sparse=sparse,
                storagedomain=storage_domain, format=disk_format,
                interface=config.VIRTIO, wipe_after_delete=False,
                bootable=bootable, shareable=shareable,
                lun_address=lun_address, lun_target=lun_target, lun_id=lun_id,
                type_=config.STORAGE_TYPE_ISCSI
            ), "Failed to add disk %s" % disk_alias
        )
        if not raw_lun:
            disks.wait_for_disks_status([disk_alias])
        self.total_disks_created += 1

        # Use the storage domain of the disk to determine whether the storage
        # type to use is block (True) or File (False)
        sd_obj = storagedomains.getStorageDomainObj(storage_domain)
        storage_type = sd_obj.get_storage().get_type()
        is_block_storage = storage_type in config.BLOCK_TYPES

        self.vms_and_disks_dict[vm_name][disk_alias] = {
            'alias': disk_alias,
            'sd_name': storage_domain,
            'is_block_storage': is_block_storage,
            'sd_id': '',
            'img_id': '',
            'vol_id': '',
            'ovf_store_id': '',
            'ovf_store_img_id': '',
        }

        # Assign the dictionaries to disk and vm to improve readability
        disk = self.vms_and_disks_dict[vm_name][disk_alias]
        vm = self.vms_and_disks_dict[vm_name]

        vm['vm_id'] = vms.get_vm_obj(vm_name).get_id()
        logger.info("The VM ID for the VM which the disk will be attached to "
                    "is: '%s'", vm['vm_id'])

        # Exit function when OVF stores are not supported (this is the
        # case when the Data center version is < 3.5)
        if not ovf_store_supported:
            return

        # Retrieve the required parameters for retrieving the OVF of each disk
        self.initialize_disk_params(vm_name, disk_alias, raw_lun)

        if wait_on_engine_log:
            logger.info("Attach disk '%s' to VM '%s' and watch the engine log "
                        "for OVF processing", disk_alias, vm_name)
            attach_disk_function_and_args = {
                'function_name': disks.attachDisk,
                'positive': True,
                'alias': disk_alias,
                'vmName': vm_name
            }
            attach_disk_success = helpers.watch_engine_log_for_ovf_store(
                ENGINE_REGEX_VM_NAME % disk['ovf_store_id'], self.host_machine,
                **attach_disk_function_and_args
            )
        else:
            attach_disk_success = disks.attachDisk(True, disk_alias, vm_name)

        self.assertTrue(attach_disk_success, "Failed to attach disk '%s' to "
                                             "VM '%s'" % (disk_alias, vm_name))
        self.assertTrue(vms.waitForVmDiskStatus(vm_name, True, disk_alias),
                        "Disk '%s' did not reach the active status while "
                        "being attached to VM '%s'" % (disk_alias, vm_name))

    def get_ovf_contents_or_num_ovf_files(
            self, disk, vm, template, ovf_should_exist=True, get_content=True
    ):
        """
        Extract and return the OVF contents for the VM or Template, or the
        number of OVF files within OVF store provided
        """
        ovf_store_args = {
            'host': self.host,
            'is_block': self.is_block_storage,
            'disk_or_template_or_vm_name': '',
            'vm_or_template_id': '',
            'sd_id': '',
            'ovf_id': '',
            'sp_id': '',
            'ovf_filename': ''
        }
        if disk:
            # Base arguments that are applicable to both the block and file
            # storage domain types
            ovf_store_args['disk_or_template_or_vm_name'] = disk['alias']
            ovf_store_args['vm_or_template_id'] = vm['vm_id']
            ovf_store_args['sd_id'] = disk['sd_id']

            # The Block and File storage type differ in the parameters and
            # order which make up their OVF storage data
            if disk['is_block_storage']:
                ovf_store_args['is_block'] = True
                ovf_store_args['ovf_id'] = disk['ovf_store_img_id']
            else:
                ovf_store_args['is_block'] = False
                ovf_store_args['ovf_id'] = disk['ovf_store_id']
                ovf_store_args['sp_id'] = self.sp_id
                ovf_store_args['ovf_filename'] = disk['ovf_store_img_id']
        elif vm:
            ovf_store_args['disk_or_template_or_vm_name'] = vm['name']
            ovf_store_args['vm_or_template_id'] = vm['vm_id']
            ovf_store_args['sd_id'] = vm['sd_id']
            # The Block and File storage type differ in the parameters and
            # order which make up their OVF storage data
            if self.is_block_storage:
                ovf_store_args['ovf_id'] = vm['ovf_store_img_id']
            else:
                ovf_store_args['ovf_id'] = vm['ovf_store_id']
                ovf_store_args['sp_id'] = self.sp_id
                ovf_store_args['ovf_filename'] = vm['ovf_store_img_id']
        elif template:
            ovf_store_args['disk_or_template_or_vm_name'] = template['name']
            ovf_store_args['vm_or_template_id'] = template['template_id']
            ovf_store_args['sd_id'] = template['sd_id']
            if self.is_block_storage:
                ovf_store_args['ovf_id'] = template['ovf_store_img_id']
            else:
                ovf_store_args['ovf_id'] = template['ovf_store_id']
                ovf_store_args['sp_id'] = self.sp_id
                ovf_store_args['ovf_filename'] = template['ovf_store_img_id']

        for ovf_remote_full_path_num_ovf_files in TimeoutingSampler(
                timeout=FIND_OVF_INFO_TIMEOUT, sleep=FIND_OVF_INFO_SLEEP,
                func=helpers.get_ovf_file_path_and_num_ovf_files,
                **ovf_store_args
        ):
            if ovf_remote_full_path_num_ovf_files or not ovf_should_exist:
                break

        if not ovf_remote_full_path_num_ovf_files and ovf_should_exist:
            assert False, ("The OVF file for the VM still doesn't exist, "
                           "aborting run")

        ovf_remote_full_path = (
            ovf_remote_full_path_num_ovf_files['ovf_file_path']
        )
        number_of_ovf_files = (
            ovf_remote_full_path_num_ovf_files['number_of_ovf_files']
        )

        if not ovf_should_exist:
            assert not self.host_machine.isFileExists(ovf_remote_full_path)
            return None

        if not self.host_machine.isFileExists(ovf_remote_full_path):
            logger.info("The OVF file for the VM still doesn't exist, return")
            return None

        if vm:
            local_ovf_file = OVF_LOCAL_FILE_LOCATION % vm['vm_id']
        else:
            local_ovf_file = OVF_LOCAL_FILE_LOCATION % template['template_id']
        assert self.host_machine.copyFrom(ovf_remote_full_path, local_ovf_file)
        with open(local_ovf_file, 'r') as file_read_contents:
            ovf_file_content = file_read_contents.read()
        os.remove(local_ovf_file)

        if get_content:
            return ovf_file_content
        else:
            return number_of_ovf_files

    def validate_ovf_contents(
            self, vm_name=None, template_name=None, positive=True,
            should_ovf_exist=True
    ):
        """
        Validate the OVF contents for the requested VM, ensuring each
        attached disk is checked for
        """
        if self.is_block_storage:
            logger.info("Block based storage, will use LVM methods to extract "
                        "OVF store")
            self.host_machine.run_pvscan_command()
        else:
            logger.info("File based storage, will use file system methods to "
                        "extract OVF store")
        if vm_name:
            # Retrieve all keys from the input VM's dictionary excluding
            # 'vm_id'
            disk_aliases = self.vms_and_disks_dict[vm_name].keys()
            for disk_alias in disk_aliases:
                if disk_alias == 'vm_id':
                    continue
                # Assign the dictionaries to disk and vm to improve readability
                disk = self.vms_and_disks_dict[vm_name][disk_alias]
                vm = self.vms_and_disks_dict[vm_name]
                return_value = False

                for ovf_file_content in TimeoutingSampler(
                    timeout=FIND_OVF_INFO_TIMEOUT, sleep=FIND_OVF_INFO_SLEEP,
                    func=self.get_ovf_contents_or_num_ovf_files,
                    disk=disk, vm=vm, template=None,
                    ovf_should_exist=should_ovf_exist, get_content=True
                ):
                    logger.info("Removing the extracted OVF store for disk "
                                "'%s'", disk_alias)
                    helpers.remove_ovf_store_extracted(self.host, disk_alias)

                    if not should_ovf_exist:
                        logger.info(
                            "VM OVF was not expected to exist, validated as "
                            "part of the "
                            "self.get_ovf_contents_or_num_ovf_files call"
                        )
                        break

                    if not ovf_file_content:
                        logger.info("No OVF content retrieved, try again")
                        continue

                    if positive:
                        if disk_alias in ovf_file_content:
                            return_value = True
                            break
                    else:
                        if disk_alias not in ovf_file_content:
                            return_value = True
                            break

                if should_ovf_exist:
                    if positive:
                        self.assertTrue(
                            return_value,
                            "Disk alias '%s' was not found in the OVF file, "
                            "contents '%s'" % (disk_alias, ovf_file_content)
                        )
                    else:
                        self.assertTrue(
                            return_value,
                            "Disk alias '%s' was found in the OVF file, "
                            "contents '%s'" % (disk_alias, ovf_file_content)
                        )
        elif template_name:
            template = self.template_dict
            ovf_file_content = self.get_ovf_contents_or_num_ovf_files(
                disk=None, vm=None, template=template,
                ovf_should_exist=should_ovf_exist, get_content=True
            )
            logger.info("Removing the extracted OVF store for template "
                        "'%s'", template_name)
            helpers.remove_ovf_store_extracted(self.host, template_name)
            if should_ovf_exist:
                if positive:
                    self.assertTrue(
                        OBJECT_NAME_IN_OVF % template_name in ovf_file_content,
                        "Template name '%s' was not found in the OVF file "
                        "contents '%s'" % (template_name, ovf_file_content)
                    )
                    self.assertTrue(
                        template['disk_name'] in ovf_file_content,
                        "Disk alias '%s' was not found in the OVF file "
                        "contents '%s'" % (template['disk_name'],
                                           ovf_file_content)
                    )
                else:
                    self.assertTrue(
                        OBJECT_NAME_IN_OVF % template_name not in
                        ovf_file_content,
                        "Template name '%s' was found in the OVF file "
                        "contents '%s'" % (template_name, ovf_file_content)
                    )
            else:
                logger.info(
                    "Template OVF was not expected to exist, validated as "
                    "part of the self.get_ovf_contents_or_num_ovf_files call"
                )
        else:
            self.assertTrue(False, "vm_name or template_name must be passed "
                                   "in to validate_ovf_contents")

    def retrieve_number_of_ovf_files_from_ovf_store(
            self, vm_name=None, template_name=None
    ):
        """
        Return the number of OVF files found in the OVF store of the VM or
        Template.  Note that in the case of a VM, it is assumed that there
        is only one disk attached
        """
        number_of_ovf_files = -1
        if self.is_block_storage:
            logger.info("Block based storage, will use LVM methods to extract "
                        "OVF store")
            self.host_machine.run_pvscan_command()
        else:
            logger.info("File based storage, will use file system methods to "
                        "extract OVF store")
        if vm_name:
            # Retrieve all keys from the input VM's dictionary excluding
            # 'vm_id'
            disk_aliases = self.vms_and_disks_dict[vm_name].keys()
            for disk_alias in disk_aliases:
                if disk_alias == 'vm_id':
                    continue
                # Assign the dictionaries to disk and vm to improve readability
                disk = self.vms_and_disks_dict[vm_name][disk_alias]
                vm = self.vms_and_disks_dict[vm_name]
                number_of_ovf_files = \
                    self.get_ovf_contents_or_num_ovf_files(
                        disk=disk, vm=vm, template=None,
                        ovf_should_exist=True, get_content=False
                    )
                logger.info("Removing the extracted OVF store for disk '%s'",
                            disk_alias)
                helpers.remove_ovf_store_extracted(self.host, disk_alias)
                break
        elif template_name:
            template = self.template_dict
            number_of_ovf_files = self.get_ovf_contents_or_num_ovf_files(
                disk=None, vm=None, template=template,
                ovf_should_exist=True, get_content=False
            )
            logger.info("Removing the extracted OVF store for template "
                        "'%s'", template_name)
            helpers.remove_ovf_store_extracted(self.host, template_name)
        return number_of_ovf_files

    def find_second_storage_domain(self):
        """
        Find a second storage domain from the current storage type, ensuring
        that it's different than the first storage domain being used
        """
        second_storage_domain = filter(lambda w: w != self.storage_domain_0,
                                       self.sds_in_current_storage_type)
        assert len(second_storage_domain) > 0
        self.storage_domain_1 = second_storage_domain[0]

    def create_and_initialize_standalone_vm_params(
            self, ovf_store_supported=True, cluster_name=config.CLUSTER_NAME
    ):
        """
        Create a new VM, which will be used by a test and deleted at the end of
        its run
        """
        vm_args_and_function = VM_ARGS.copy()
        vm_args_and_function['vmName'] = VM3_NAME
        vm_args_and_function['cluster'] = cluster_name
        if ovf_store_supported:
            self.initialize_vm_ovf_store_params()
        vm = self.vm_with_no_disks_dict

        if ovf_store_supported:
            logger.info("Create a VM and watch the engine log for OVF "
                        "processing")
            vm_args_and_function['function_name'] = create_vm_or_clone
            create_vm_success = helpers.watch_engine_log_for_ovf_store(
                ENGINE_REGEX_VM_NAME % vm['ovf_store_id'], self.host_machine,
                **vm_args_and_function
            )
            self.assertTrue(create_vm_success, "Failed to create VM '%s'" %
                            VM3_NAME)
            self.initialize_vm_params(VM3_NAME)
        else:
            self.assertTrue(create_vm_or_clone(**vm_args_and_function),
                            "Failed to create VM '%s'" % VM3_NAME)

    def create_and_initialize_template_and_its_params(self):
        """
        Create a new Template, which will be used by a test and deleted at the
        end of its run
        """
        self.initialize_template_ovf_store_params()
        logger.info("Creating template '%s' from vm '%s'", VM3_NAME,
                    TEMPLATE_NAME)
        template_function_and_args = {
            'function_name': templates.createTemplate,
            'positive': True,
            'name': TEMPLATE_NAME,
            'vm': VM3_NAME,
            'storagedomains': self.storage_domain_0
        }
        # Retrieve all keys from the input VM's dictionary excluding 'vm_id'
        disk_aliases = self.vms_and_disks_dict[VM3_NAME].keys()
        for disk_alias in disk_aliases:
            if disk_alias == 'vm_id':
                disk_aliases.remove(disk_alias)

        self.assertTrue(len(disk_aliases) == 1,
                        "Did not retrieve the expected number of disks")
        # Retrieve the tuple contents for the current disk, wait for the
        # OVF store to be updated
        disk = self.vms_and_disks_dict[VM3_NAME][disk_aliases[0]]

        logger.info("Create a Template and watch the engine log for OVF "
                    "processing")
        create_template_success = helpers.watch_engine_log_for_ovf_store(
            ENGINE_REGEX_VM_NAME % disk['ovf_store_id'], self.host_machine,
            **template_function_and_args
        )
        self.assertTrue(create_template_success, "Failed to create Template "
                                                 "'%s'" % VM3_NAME)
        self.template_created = True
        # Store the disk alias added into the template dict
        self.template_dict['disk_name'] = disk_aliases[0]
        self.initialize_template_params(TEMPLATE_NAME)

    def tearDown(self):
        """
        Detach and remove the disks created as part of the initial setup,
        this is to ensure no conflict exists between runs including Rest API
        and SDK
        """
        vms.stop_vms_safely([VM1_NAME, VM2_NAME])
        for vm_name in [VM1_NAME, VM2_NAME]:
            for disk_obj in vms.getVmDisks(vm_name):
                if not disks.deleteDisk(True, disk_obj.alias):
                    self.test_failed = True
                    logger.error("Cannot delete disk %s", disk_obj.alias)

        jobs.wait_for_jobs([config.ENUMS['job_remove_disk']])
        if self.test_failed:
            raise exceptions.TestException("Test failed during tearDown")


class EnvironmentWithNewVm(BasicEnvironment):
    """
    This class implements the common functions for tests that require a
    standalone VM created
    """
    __test__ = False
    domain_to_use = ANY_DOMAIN
    template_created = False
    storage_domain_0 = None
    storage_domain_1 = None

    def setUp(self):
        super(EnvironmentWithNewVm, self).setUp()
        self.create_and_initialize_standalone_vm_params()

    def tearDown(self):
        vms.safely_remove_vms([VM3_NAME])
        jobs.wait_for_jobs([ENUMS['job_remove_vm']])
        if self.template_created:
            templates.removeTemplate(True, TEMPLATE_NAME)


@attr(tier=1)
class TestCase6247(BasicEnvironment):
    """
    Disk on master domain attached to VM

    1. Create a VM with a disk on master storage domain, ensure the OVF is
    created on this storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6247
    """
    __test__ = True
    # TODO: Disable Java while attachDisk function isn't activating the disk as
    # expected, see ticket:
    # https://projects.engineering.redhat.com/browse/RHEVM-2374
    apis = BasicEnvironment.apis - set(['java'])
    polarion_test_case = '6247'
    domain_to_use = MASTER_DOMAIN

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_disk_on_master_domain(self):
        """ Polarion case 6247 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM1_NAME)


@attr(tier=2)
class TestCase6248(BasicEnvironment):
    """
    Disk on non-master domain attached to VM

    1. Create a VM with a disk on a non-master storage domain, ensure the
    OVF is created on this storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6248
    """
    __test__ = True
    polarion_test_case = '6248'
    domain_to_use = ANY_NON_MASTER_DOMAIN

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_disk_on_non_master_domain(self):
        """ Polarion case 6248 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM1_NAME)


@attr(tier=2)
class TestCase6249(EnvironmentWithNewVm):
    """
    Disks on 3.4 Cluster

    1. Create a new Data Center with a 3.4 Compatibility version
    2. Create a new Cluster with a 3.4 Compatibility version
    3. Move an existing host into the new Data Center (maintenance, remove
    and then add)
    4. Create 2 new storage domains using the 3.4 host
    5. Create a VM with 2 disks (on different storage domains) using the
    Cluster with the 3.4 compatibility
    6. Upgrade the cluster and ensure that the OVFs are created on each of
    the storage domains

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6249
    """
    __test__ = True
    polarion_test_case = '6249'
    data_center_name = "test_6249_data_center"
    cluster_name = "test_6249_cluster"
    new_domain_1 = "test_6249_sd_1"
    new_domain_2 = "test_6249_sd_2"
    bz = {'1279788': {'engine': None, 'version': ['3.6']}}

    def setUp(self):
        # Determine whether storage type is block
        self.is_block_storage = self.storage in config.BLOCK_TYPES

        # Initialize the storage domains to be used in this test
        self.storage_domain_0 = self.new_domain_1
        self.storage_domain_1 = self.new_domain_2

        # Initialize the variables for this test
        self.initialize_variables()

        logger.info("Retrieve the first host from the 2nd cluster (in "
                    "original Data center")
        self.original_cluster = config.CLUSTERS[1]['name']
        self.host_being_moved = config.CLUSTERS[1]['hosts'][0]['name']
        self.host = self.host_being_moved

        logger.info("Creating a 3.4 Data center")
        datacenters.addDataCenter(
            True, name=self.data_center_name, storage_type=self.storage,
            version=config.DC_6249_INITIAL_VERSION
        )

        logger.info("Creating a Cluster with a 3.6 compatibility version for "
                    "the 3.4 Data center")
        clusters.addCluster(
            True, name=self.cluster_name, cpu=config.CPU_NAME,
            data_center=self.data_center_name, version=config.COMP_VERSION
        )
        logger.info("Move the host into the newly created cluster")
        hl_hosts.move_host_to_another_cluster(self.host_being_moved,
                                              self.cluster_name)

        # Use the moved VDSM host for both the Block and File level OVF
        # verifications
        self.host_being_moved_ip = hosts.getHostIP(self.host_being_moved)
        self.host_machine = helpers.machine_to_use(self.host_being_moved_ip)

        logger.info("Creating 2 storage domains and attaching them to the "
                    "host sitting on the new cluster and Data center")
        sd_1_args = {'type': ENUMS['storage_dom_type_data'],
                     'storage_type': self.storage,
                     'host': self.host_being_moved,
                     'name': self.storage_domain_0}
        sd_2_args = sd_1_args.copy()
        sd_2_args['name'] = self.storage_domain_1

        if self.storage == config.STORAGE_TYPE_ISCSI:
            sd_1_args['lun'] = config.UNUSED_LUNS[0]
            sd_2_args['lun'] = config.UNUSED_LUNS[1]
            sd_1_args['lun_address'] = config.UNUSED_LUN_ADDRESSES[0]
            sd_2_args['lun_address'] = config.UNUSED_LUN_ADDRESSES[1]
            sd_1_args['lun_target'] = config.UNUSED_LUN_TARGETS[0]
            sd_2_args['lun_target'] = config.UNUSED_LUN_TARGETS[1]
            sd_1_args['lun_port'] = config.LUN_PORT
            sd_2_args['lun_port'] = config.LUN_PORT
        elif self.storage == config.STORAGE_TYPE_NFS:
            sd_1_args['address'] = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
            sd_2_args['address'] = config.UNUSED_DATA_DOMAIN_ADDRESSES[1]
            sd_1_args['path'] = config.UNUSED_DATA_DOMAIN_PATHS[0]
            sd_2_args['path'] = config.UNUSED_DATA_DOMAIN_PATHS[1]
        elif self.storage == config.STORAGE_TYPE_GLUSTER:
            sd_1_args['address'] = (
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0]
            )
            sd_2_args['address'] = (
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[1]
            )
            sd_1_args['path'] = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
            sd_2_args['path'] = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[1]

        for sd_args in [sd_1_args, sd_2_args]:
            logger.info('Creating storage domain with parameters: %s', sd_args)
            storagedomains.addStorageDomain(True, wait=True, **sd_args)
            storagedomains.attachStorageDomain(True, self.data_center_name,
                                               sd_args['name'])

        logger.info("Creating a standalone disk on new cluster")
        self.create_and_initialize_standalone_vm_params(
            ovf_store_supported=False, cluster_name=self.cluster_name
        )

    def tearDown(self):
        if not vms.safely_remove_vms([VM3_NAME]):
            self.test_failed = True
            logger.error("Could not remove VM'%s'", VM3_NAME)

        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  self.data_center_name)
        status = hl_datacenters.clean_datacenter(
            True, self.data_center_name, formatExpStorage='true',
            vdc=config.VDC, vdc_password=config.VDC_PASSWORD
        )
        if not status:
            self.test_failed = True
            logger.info("Failed to clean Data center '%s'",
                        self.data_center_name)

        logger.info("Re-add the moved host back into its original "
                    "cluster/data center")
        if not hosts.addHost(True, self.host_being_moved,
                             address=self.host_being_moved_ip, wait=True,
                             reboot=False, cluster=self.original_cluster,
                             root_password=config.VDC_ROOT_PASSWORD):
            self.test_failed = True
            logger.error("Could not add host '%s' back into cluster '%s'",
                         self.host_being_moved, self.original_cluster)

        if self.test_failed:
            raise exceptions.TestException("Test failed during tearDown")

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_disks_on_34_cluster_with_upgrade(self):
        """ Polarion case 6249 """
        logger.info("Ensure that storage domains created on a 3.4 Data "
                    "center have no OVF stores")
        ovf_stores_domain_0 = storagedomains.get_number_of_ovf_store_disks(
            self.storage_domain_0)
        ovf_stores_domain_1 = storagedomains.get_number_of_ovf_store_disks(
            self.storage_domain_1)
        self.assertTrue(ovf_stores_domain_0 == 0, "The number of OVF stores "
                                                  "was expected to be zero")
        self.assertTrue(ovf_stores_domain_1 == 0, "The number of OVF stores "
                                                  "was expected to be zero")
        logger.info("Attaching a disk to each of the storage domains created")
        self.create_and_attach_disk(VM3_NAME, self.storage_domain_0,
                                    bootable=True, wait_on_engine_log=False,
                                    ovf_store_supported=False)
        self.create_and_attach_disk(VM3_NAME, self.storage_domain_1,
                                    bootable=False, wait_on_engine_log=False,
                                    ovf_store_supported=False)
        # Retrieve all keys from the input VM's dictionary excluding 'vm_id'
        logger.info("Attach each of the disks created to VM '%s'", VM3_NAME)
        disk_aliases = self.vms_and_disks_dict[VM3_NAME].keys()
        for disk_alias in disk_aliases:
            if disk_alias == 'vm_id':
                continue
            self.assertTrue(disks.attachDisk(True, disk_alias, VM3_NAME),
                            "Failed to attach disk '%s' to VM '%s'" % (
                                disk_alias, VM3_NAME))

        # Upgrade the Data Center (Cluster is already at the latest version)
        logger.info(
            "Upgrading Data center '%s' to version '%s'",
            self.data_center_name, config.DC_TEST_VERSION
        )
        self.assertTrue(
            datacenters.updateDataCenter(True, self.data_center_name,
                                         version=config.DC_TEST_VERSION),
            "Data center '%s' was not updated" % self.data_center_name
        )
        logger.info("Ensure that OVF store count is 2 after the Data center "
                    "upgrade, allowing about a minute")
        for num_ovf_store_disks_sd_0 in TimeoutingSampler(
            timeout=FIND_OVF_DISKS_TIMEOUT, sleep=FIND_OVF_DISKS_SLEEP,
            func=storagedomains.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain_0
        ):
            if num_ovf_store_disks_sd_0 == DEFAULT_NUM_OVF_STORES_PER_SD:
                break
        self.assertTrue(num_ovf_store_disks_sd_0 ==
                        DEFAULT_NUM_OVF_STORES_PER_SD,
                        "The number of OVF stores in domain '%s' isn't %s "
                        "after the Data center upgrade" %
                        (self.storage_domain_0, DEFAULT_NUM_OVF_STORES_PER_SD))

        for num_ovf_store_disks_sd_1 in TimeoutingSampler(
            timeout=FIND_OVF_DISKS_TIMEOUT, sleep=FIND_OVF_DISKS_SLEEP,
            func=storagedomains.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain_1
        ):
            if num_ovf_store_disks_sd_1 == DEFAULT_NUM_OVF_STORES_PER_SD:
                break
        self.assertTrue(num_ovf_store_disks_sd_1 ==
                        DEFAULT_NUM_OVF_STORES_PER_SD,
                        "The number of OVF stores in domain '%s' isn't %s "
                        "after the Data center upgrade" %
                        (self.storage_domain_1, DEFAULT_NUM_OVF_STORES_PER_SD))

        logger.info("Update the disks dict with the OVF store related data "
                    "now that Data center version is 3.5 or higher")
        # Retrieve all keys from the input VM's dictionary excluding 'vm_id'
        disk_aliases = self.vms_and_disks_dict[VM3_NAME].keys()
        for disk_alias in disk_aliases:
            if disk_alias == 'vm_id':
                continue
            self.initialize_disk_params(VM3_NAME, disk_alias, raw_lun=False,
                                        data_center=self.data_center_name)

        self.validate_ovf_contents(vm_name=VM3_NAME)


@attr(tier=2)
class TestCase6250(BasicEnvironment):
    """
    Several Disks from several VMs on one storage domain

    1. Create 2 VMs, each with a disk, ensure that OVFs are created on this
    storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6250
    """
    __test__ = True
    polarion_test_case = '6250'

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_multiple_disks_on_single_domain(self):
        """ Polarion case 6250 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.create_and_attach_disk(VM2_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM1_NAME)
        self.validate_ovf_contents(vm_name=VM2_NAME)


@attr(tier=2)
class TestCase6251(BasicEnvironment):
    """
    VM with disks on 2 storage domains

    1. Create 1 VM with 2 disks (each on a different storage domain), ensure
    that OVFs are created on each of the storage domains

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6251
    """
    __test__ = True
    polarion_test_case = '6251'

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_one_vm_with_disks_on_multiple_domains(self):
        """ Polarion case 6251 """
        self.find_second_storage_domain()
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_1,
                                    bootable=False)
        self.validate_ovf_contents(vm_name=VM1_NAME)


@attr(tier=2)
class TestCase6252(BasicEnvironment):
    """
    Actions on OVF store

    1. Create a VM
    2. Create a disk on the master domain and attach it to the VM
    3. Create a disk on the non-master domain and attach it to the VM
    4. Ensure that OVF files are created containing info for both disks
    5. Try moving the OVF store for each disk into a different storage
    domain - this should fail
    6. Try to export the OVF store for each disk into a glance domain -
    this should fail
    7. Try to remove the OVF store for each disk - this should fail

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6252
    """
    __test__ = True
    polarion_test_case = '6252'

    def move_ovf_stores(self, vm_name):
        """
        Attempt to move one OVF stores for each disk, failure is expected
        """
        disk_aliases = [disk.get_name() for disk in vms.getVmDisks(vm_name)]
        for disk_alias in disk_aliases:
            # Assign the dictionary to disk in order to improve readability
            disk = self.vms_and_disks_dict[vm_name][disk_alias]
            new_sd = disks.get_other_storage_domain(disk_alias, vm_name)
            self.assertTrue(disks.move_disk(
                target_domain=new_sd, disk_id=disk['ovf_store_id'],
                positive=False), "Move disk succeeded for an OVF store"
            )

    def delete_ovf_stores(self, vm_name):
        """
        Attempt to delete one OVF stores for each disk, failure is expected
        """
        disk_aliases = [disk.get_name() for disk in vms.getVmDisks(vm_name)]
        for disk_alias in disk_aliases:
            # Assign the dictionary to disk in order to improve readability
            disk = self.vms_and_disks_dict[vm_name][disk_alias]
            self.assertTrue(
                disks.deleteDisk(
                    positive=False, alias=OVF_STORE_DISK_NAME,
                    disk_id=disk['ovf_store_id']
                ), "Delete disk succeeded for an OVF store"
            )

    def setUp(self):
        self.domain_to_use = MASTER_DOMAIN
        super(TestCase6252, self).setUp()
        self.find_second_storage_domain()

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_actions_on_ovf_store(self):
        """ Polarion case 6252 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_1,
                                    bootable=False)
        self.validate_ovf_contents(vm_name=VM1_NAME)
        self.move_ovf_stores(VM1_NAME)
        # TODO: Not implemented, export disk into glance - tracking ticket:
        # https://projects.engineering.redhat.com/browse/RHEVM-2345)
        self.delete_ovf_stores(VM1_NAME)


@attr(tier=2)
class TestCase6253File(BasicEnvironment):
    """
    VM with an attached shareable disk

    1. Create 1 VM with no disks
    2. Attach a shared disk to this VM
    OVF should be created, but the disk alias for the shared disk should not
    be part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6253
    """
    __test__ = NFS in opts['storages'] or GLUSTERFS in opts['storages']
    storages = set([NFS, GLUSTERFS])
    polarion_test_case = '6253'
    # Bug 1273376: OVF file is removed for any given VM when only a direct
    # LUN disk is attached to it
    bz = {'1273376': {'engine': None, 'version': ['3.6']}}

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_one_vm_with_shared_disk(self):
        """ Polarion case 6253 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True, shareable=True)
        self.validate_ovf_contents(vm_name=VM1_NAME, positive=False)


@attr(tier=2)
class TestCase6253Block(BasicEnvironment):
    """
    VM with attached disks: shared disk and direct LUN

    1. Create 1 VM with no disks
    2. Attach a shared disk to this VM
    3. Attach a direct LUN to this VM
    OVF should be created, but the disk aliases for the shared disk and the
    direct LUN should not be part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6253
    """
    # Direct LUN is only possible on Block devices
    __test__ = ISCSI in opts['storages']
    storages = set([ISCSI])
    polarion_test_case = '6253'
    bz = {'1273376': {'engine': None, 'version': ['3.6']}}

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_one_vm_with_shared_disk_and_direct_LUN(self):
        """ Polarion case 6253 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True, shareable=True)
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=False, shareable=False,
                                    raw_lun=True)
        self.validate_ovf_contents(vm_name=VM1_NAME, positive=False)


@attr(tier=2)
class TestCase6254(BasicEnvironment):
    """
    Delete a disk from a VM

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Delete the disk from the VM, ensure that the OVF remains for this VM
    but the disk alias no longer exists as part of the OVF file contents

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6254
    """
    __test__ = True
    polarion_test_case = '6254'

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_delete_disk_from_vm(self):
        """ Polarion case 6254 """
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM1_NAME)

        # Retrieve all keys from the input VM's dictionary
        disk_aliases = self.vms_and_disks_dict[VM1_NAME].keys()

        delete_disk_function_and_args = {
            'function_name': disks.deleteDisk,
            'positive': True,
            'alias': ''
        }
        for disk_alias in disk_aliases:
            # Exclude the 'vm_id' from the retrieved keys
            if disk_alias == 'vm_id':
                continue
            delete_disk_function_and_args['alias'] = disk_alias
            disk = self.vms_and_disks_dict[VM1_NAME][disk_alias]
            logger.info("Delete disk from VM and watch the engine log for OVF "
                        "processing")
            delete_disk_success = helpers.watch_engine_log_for_ovf_store(
                ENGINE_REGEX_VM_NAME % disk['ovf_store_id'], self.host_machine,
                **delete_disk_function_and_args
            )
            self.assertTrue(delete_disk_success,
                            "Deleting disk '%s' failed" % disk_alias)

        self.validate_ovf_contents(vm_name=VM1_NAME, positive=False)


@attr(tier=1)
class TestCase6255(EnvironmentWithNewVm):
    """
    Remove a VM

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Remove the VM, ensure the OVF is removed for this VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6255
    """
    __test__ = True
    # TODO: Disable Java while attachDisk function isn't activating the disk as
    # expected, see ticket:
    # https://projects.engineering.redhat.com/browse/RHEVM-2374
    apis = BasicEnvironment.apis - set(['java'])
    polarion_test_case = '6255'

    def tearDown(self):
        logger.info("VM '%s' removed as part of the test case", VM3_NAME)

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_remove_vm(self):
        """ Polarion case 6255 """
        self.create_and_attach_disk(VM3_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM3_NAME)

        # Retrieve all keys from the input VM's dictionary excluding 'vm_id'
        disk_aliases = self.vms_and_disks_dict[VM3_NAME].keys()
        for disk_alias in disk_aliases:
            if disk_alias == 'vm_id':
                disk_aliases.remove(disk_alias)

        self.assertTrue(len(disk_aliases) == 1,
                        "Did not retrieve the expected number of disks")
        # Retrieve the tuple contents for the current disk, wait for the
        # OVF store to be updated
        disk = self.vms_and_disks_dict[VM3_NAME][disk_aliases[0]]

        logger.info("Remove VM and watch the engine log for OVF processing")
        remove_vm_function_and_args = {
            'function_name': vms.safely_remove_vms,
            'vms': [VM3_NAME]
        }
        remove_vm_success = helpers.watch_engine_log_for_ovf_store(
            ENGINE_REGEX_VM_NAME % disk['ovf_store_id'], self.host_machine,
            **remove_vm_function_and_args
        )
        self.assertTrue(remove_vm_success,
                        "Failed to remove VM '%s'" % VM3_NAME)
        self.validate_ovf_contents(vm_name=VM3_NAME, template_name=None,
                                   positive=False, should_ovf_exist=False)


@attr(tier=2)
class TestCase6256(EnvironmentWithNewVm):
    """
    Diskless VM

    1. Create a VM with no disks, ensure that the OVF is created on all
    storage domains (pick any domain within the current storage type,
    no need to check across all storage domains)

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6256
    """
    __test__ = True
    polarion_test_case = '6256'

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_diskless_vm(self):
        """ Polarion case 6256 """
        vm = self.vm_with_no_disks_dict
        logger.info("Extract and return the contents of the OVF store "
                    "containing the disk")

        for ovf_file_content in TimeoutingSampler(
                timeout=FIND_OVF_INFO_TIMEOUT, sleep=FIND_OVF_INFO_SLEEP,
                func=self.get_ovf_contents_or_num_ovf_files, disk=None, vm=vm,
                template=None, ovf_should_exist=True, get_content=True
        ):
            if ovf_file_content:
                break

        logger.info("Ensure that the VM's OVF file contains the VM name")
        self.assertTrue(OBJECT_NAME_IN_OVF % VM3_NAME in ovf_file_content)


@attr(tier=2)
class TestCase6257(EnvironmentWithNewVm):
    """
    Check tar file after VM name change

    1. Create a VM with no disks
    2. Modify the VM's name and ensure that the OVF is updated reflecting
    this change

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6257
    """
    __test__ = True
    polarion_test_case = '6257'
    vm_name_updated = False
    updated_vm_name = 'storage_ovf_renamed_vm'

    def tearDown(self):
        if self.vm_name_updated:
            vms.safely_remove_vms([self.updated_vm_name])
            jobs.wait_for_jobs([ENUMS['job_remove_vm']])
        else:
            super(TestCase6257, self).tearDown()

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_tar_file_on_vdsm_for_vm_name_change(self):
        """ Polarion case 6257 """
        vm = self.vm_with_no_disks_dict
        logger.info("Extract and return the contents of the OVF store "
                    "containing the VM")
        for ovf_file_content in TimeoutingSampler(
                timeout=FIND_OVF_INFO_TIMEOUT, sleep=FIND_OVF_INFO_SLEEP,
                func=self.get_ovf_contents_or_num_ovf_files, disk=None,
                vm=vm, template=None, ovf_should_exist=True, get_content=True
        ):
            if ovf_file_content:
                break

        logger.info("Ensure that the VM's OVF file contains the VM name")
        self.assertTrue(OBJECT_NAME_IN_OVF % VM3_NAME in ovf_file_content)
        new_vm_name = "storage_ovf_renamed_vm"

        logger.info("Create a VM and watch the engine log for OVF processing")
        update_vm_function_and_args = {
            'function_name': vms.updateVm,
            'positive': True,
            'vm': VM3_NAME,
            'name': new_vm_name
        }
        update_vm_success = helpers.watch_engine_log_for_ovf_store(
            ENGINE_REGEX_VM_NAME % vm['ovf_store_id'], self.host_machine,
            **update_vm_function_and_args
        )
        self.assertTrue(update_vm_success,
                        "Failed to update the VM '%s'" % VM3_NAME)
        # VM name updated successfully, update the specified boolean so that
        # the tearDown will remove the VM with this new name
        self.vm_name_updated = True
        logger.info("Extract and return the contents of the OVF store "
                    "containing the disk")
        ovf_file_content = self.get_ovf_contents_or_num_ovf_files(
            disk=None, vm=vm, template=None, ovf_should_exist=True,
            get_content=True
        )
        logger.info("Ensure that the VM's OVF file contains the VM name")
        self.assertTrue(OBJECT_NAME_IN_OVF % VM3_NAME not in ovf_file_content)
        self.assertTrue(OBJECT_NAME_IN_OVF % new_vm_name in ovf_file_content)


@attr(tier=2)
class TestCase6259(BasicEnvironment):
    """
    Restore a VM from configuration

    1. Create a VM with a single disk, ensure that the OVF is created on the
    disk's storage domain
    2. Remove VM, ensuring that its OVF file is removed
    3. Create a new VM with a single disk
    4. Attach the OVF_store where the previous VM originally resided
    5. Attempt to run RestoreVmFromConfiguration which should restore the
    original VM

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6259
    """
    # TODO: Mounting the OVF store as a disk isn't supported until version 4.0
    __test__ = False
    polarion_test_case = '6259'

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_restore_vm_from_ovf_store(self):
        """ Polarion case 6259 """
        # TODO: Add code once support for mounting OVF store exists


@attr(tier=1)
class TestCase6260(EnvironmentWithNewVm):
    """
    OVF of a template

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Create a template from this VM, ensure that a new OVF is created
    reflecting the Template created

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6260
    """
    __test__ = True
    # TODO: Disable Java while attachDisk function isn't activating the disk as
    # expected, see ticket:
    # https://projects.engineering.redhat.com/browse/RHEVM-2374
    apis = BasicEnvironment.apis - set(['java'])
    polarion_test_case = '6260'
    template_created = False

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_ovf_for_a_template(self):
        """ Polarion case 6260 """
        self.create_and_attach_disk(VM3_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM3_NAME)
        self.create_and_initialize_template_and_its_params()
        logger.info("Validate the OVF store contents for template '%s'",
                    TEMPLATE_NAME)
        self.validate_ovf_contents(template_name=TEMPLATE_NAME)


@attr(tier=2)
class TestCase6261(BasicEnvironment):
    """
    Change the number of OVF_STORE disks

    1. Update the number of the OVF_STORE disks
    2. Create a VM with a disk, ensure the OVF is created on each of the
    OVF stores that are assigned to the storage domain, matching the updated
    number specified

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6261
    """
    __test__ = True
    polarion_test_case = '6261'

    def setUp(self):
        super(TestCase6261, self).setUp()
        self.find_second_storage_domain()
        logger.info("Changing the ovirt-engine service with "
                    "StorageDomainOvfStoreCount set to %s, restarting "
                    "engine", UPDATED_NUM_OVF_STORES_PER_SD)
        if not test_utils.set_engine_properties(
                config.ENGINE,
                [UPDATE_OVF_NUM_OVF_STORES_CMD % {
                    'num_ovf_stores': UPDATED_NUM_OVF_STORES_PER_SD}]
        ):
            raise exceptions.UnkownConfigurationException(
                "Update number of OVF stores failed to execute on '%s'" %
                config.VDC
            )

        # TODO: As a workaround for bug
        # https://bugzilla.redhat.com/show_bug.cgi?id=1275174 where storage
        # domains are coming up in Unknown state after engine restart
        helpers.ensure_data_center_and_sd_are_active()

    def tearDown(self):
        super(TestCase6261, self).tearDown()
        logger.info("Restoring the ovirt-engine service with "
                    "StorageDomainOvfStoreCount set to %s, restarting "
                    "engine", DEFAULT_NUM_OVF_STORES_PER_SD)
        if not test_utils.set_engine_properties(
                config.ENGINE,
                [UPDATE_OVF_NUM_OVF_STORES_CMD % {
                    'num_ovf_stores': DEFAULT_NUM_OVF_STORES_PER_SD}]
        ):
            raise exceptions.UnkownConfigurationException(
                "Update number of OVF stores failed to execute on '%s'" %
                config.VDC
            )

        # TODO: As a workaround for bug
        # https://bugzilla.redhat.com/show_bug.cgi?id=1275174 where storage
        # domains are coming up in Unknown state after engine restart
        helpers.ensure_data_center_and_sd_are_active()

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_change_ovf_store_count(self):
        """ Polarion case 6261 """
        logger.info("Ensure that OVF store count is %s after the engine "
                    "configuration change", UPDATED_NUM_OVF_STORES_PER_SD)
        for num_ovf_store_disks_sd_0 in TimeoutingSampler(
            timeout=FIND_OVF_DISKS_TIMEOUT, sleep=FIND_OVF_DISKS_SLEEP,
            func=storagedomains.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain_0
        ):
            if num_ovf_store_disks_sd_0 == UPDATED_NUM_OVF_STORES_PER_SD:
                break
        self.assertTrue(num_ovf_store_disks_sd_0 ==
                        UPDATED_NUM_OVF_STORES_PER_SD,
                        "The number of OVF stores in domain '%s' isn't %s "
                        "after the engine configuration change" %
                        (self.storage_domain_0, UPDATED_NUM_OVF_STORES_PER_SD))

        for num_ovf_store_disks_sd_1 in TimeoutingSampler(
            timeout=FIND_OVF_DISKS_TIMEOUT, sleep=FIND_OVF_DISKS_SLEEP,
            func=storagedomains.get_number_of_ovf_store_disks,
            storage_domain=self.storage_domain_1
        ):
            if num_ovf_store_disks_sd_1 == UPDATED_NUM_OVF_STORES_PER_SD:
                break
        self.assertTrue(num_ovf_store_disks_sd_1 ==
                        UPDATED_NUM_OVF_STORES_PER_SD,
                        "The number of OVF stores in domain '%s' isn't %s "
                        "after the engine configuration change" %
                        (self.storage_domain_1, UPDATED_NUM_OVF_STORES_PER_SD))

        self.create_and_attach_disk(VM1_NAME, self.storage_domain_0,
                                    bootable=True)
        self.create_and_attach_disk(VM1_NAME, self.storage_domain_1,
                                    bootable=False)
        self.validate_ovf_contents(vm_name=VM1_NAME)


@attr(tier=2)
class TestCase6262(EnvironmentWithNewVm):
    """
    Large number of OVFs

    1. Create a VM with a disk, ensure the OVF is created on this storage
    domain
    2. Create a template from this VM, ensure that a new OVF is created
    reflecting the Template created
    3. Create a pool of 5 from this template, ensure that the OVF counts
    reflect this newly created pool

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
    workitem?id=RHEVM3-6262
    """
    __test__ = True
    polarion_test_case = '6262'
    template_created = False

    def tearDown(self):
        vmpools.removeVmPool(True, config.POOL_NAME)
        super(TestCase6262, self).tearDown()

    @polarion(POLARION_PROJECT + polarion_test_case)
    def test_ovf_for_a_template(self):
        """ Polarion case 6262 """
        self.create_and_attach_disk(VM3_NAME, self.storage_domain_0,
                                    bootable=True)
        self.validate_ovf_contents(vm_name=VM3_NAME)

        self.create_and_initialize_template_and_its_params()
        logger.info("Validate the OVF store contents for template '%s'",
                    TEMPLATE_NAME)
        self.validate_ovf_contents(template_name=TEMPLATE_NAME)
        num_ovf_files_with_template = (
            self.retrieve_number_of_ovf_files_from_ovf_store(
                template_name=TEMPLATE_NAME
            )
        )

        logger.info("Create a VM pool with 5 VMs from the created template")
        self. assertTrue(vmpools.addVmPool(
            True, name=config.POOL_NAME, size=config.POOL_SIZE,
            cluster=config.CLUSTER_NAME, template=TEMPLATE_NAME,
            description=config.POOL_DESCRIPTION
        ), "Failed to add VM pool '%s' using template '%s'" % (
            config.POOL_NAME, TEMPLATE_NAME
        ))
        logger.info("Wait until all VMs in the pool have been created "
                    "successfully")
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)
        logger.info("Allow a bit over a minute for all the VMs created from "
                    "the pool to be written into the OVF store")
        for num_ovf_files_with_vm_pool in TimeoutingSampler(
            timeout=FIND_OVF_DISKS_TIMEOUT, sleep=FIND_OVF_DISKS_SLEEP,
            func=self.retrieve_number_of_ovf_files_from_ovf_store,
            template_name=TEMPLATE_NAME
        ):
            if num_ovf_files_with_vm_pool == (
                num_ovf_files_with_template + config.POOL_SIZE
            ):
                break
        self.assertTrue(
            num_ovf_files_with_vm_pool ==
            num_ovf_files_with_template + config.POOL_SIZE,
            "The number of OVF stores in domain '%s' hasn't increased by the "
            "%s VMs added in the VM pool after the Data center upgrade" %
            (self.storage_domain_0, config.POOL_SIZE)
        )