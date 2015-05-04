"""
Read Only Disk test helpers functions
"""
import config
import logging
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.low_level.disks import (
    addDisk, get_all_disk_permutation,
    check_disk_visibility, checkDiskExists, deleteDisk,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import addStorageDomain
from art.rhevm_api.tests_lib.low_level.vms import getVmDisks
from rhevmtests.storage import helpers

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISKS_NAMES = dict()  # dictionary with storage type as key
DISK_TIMEOUT = 250
DD_TIMEOUT = 1500
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
FILTER = '[sv]d'
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'

not_bootable = lambda disk: not disk.get_bootable() and disk.get_active()


def add_new_disk(sd_name, storage_type, permutation, shared=False,
                 force_create=True):
    """
    Add a new disk
    Parameters:
        * sd_name - disk wil added to this sd
        * storage_type - storage domain type
        * shared - True if the disk should e shared
        * permutations:
            * interface - VIRTIO or VIRTIO_SCSI
            * sparse - True if thin, False preallocated
            * disk_format - 'cow' or 'raw'
        * force_create: Remove any existing disk in the system with the same
                        alias
    """
    disk_alias = "%s_%s_%s_%s_disk" % (
        permutation['interface'],
        permutation['format'],
        permutation['sparse'],
        storage_type)
    disk_args = {
        # Fixed arguments
        'provisioned_size': config.DISK_SIZE,
        'wipe_after_delete': storage_type in config.BLOCK_TYPES,
        'storagedomain': sd_name,
        'bootable': False,
        'shareable': shared,
        'active': True,
        'size': config.DISK_SIZE,
        # Custom arguments - change for each disk
        'format': permutation['format'],
        'interface': permutation['interface'],
        'sparse': permutation['sparse'],
        'alias': disk_alias,
    }

    if force_create:
        # Remove any existing disk in the system with the same alias
        if checkDiskExists(True, disk_alias):
            logger.info("Found disk with alias %s need for test. Removing...",
                        disk_alias)
            assert deleteDisk(True, disk_alias)

    assert addDisk(True, **disk_args)
    if storage_type not in DISKS_NAMES.keys():
        DISKS_NAMES[storage_type] = list()

    DISKS_NAMES[storage_type].append(disk_args['alias'])


def start_creating_disks_for_test(sd_name, storage_type, shared=False):
    """
    Begins asynchronous creation of disks of all permutations of disk
    interfaces, formats and allocation policies
    """
    global DISKS_NAMES
    DISKS_NAMES[storage_type] = list()
    logger.info("Disks: %s", DISKS_NAMES[storage_type])
    logger.info("Creating all disks")
    DISK_PERMUTATIONS = get_all_disk_permutation(
        block=storage_type in config.BLOCK_TYPES, shared=shared)
    for permutation in DISK_PERMUTATIONS:
        add_new_disk(sd_name, storage_type,
                     permutation=permutation, shared=shared)


def write_on_vms_ro_disks(vm_name, storage_type, imported_vm=False):
    """
    Check that vm's disks are all visible and write operations to RO are
    impossible
    Parameters:
        * vm_name - name of vm
        * storage_type - storage domain type
        * imported_vm - True if the vm is imported
    """
    vm_disks = filter(not_bootable, getVmDisks(vm_name))
    if imported_vm:
        global DISKS_NAMES
        DISKS_NAMES[storage_type] = [disk.get_alias() for disk in vm_disks]
        logger.info("Disks: %s", DISKS_NAMES[storage_type])
    logger.info("VM %s disks %s", vm_name, vm_disks)

    for disk, is_ro_vm_disk in zip(DISKS_NAMES[storage_type], vm_disks):
        logger.info("Checking if disk %s visible to %s", disk, vm_name)
        is_visible = check_disk_visibility(disk, vm_disks)
        if not is_visible:
            raise exceptions.DiskException(
                "Disk '%s' is not visible to vm '%s'", disk, vm_name
            )
        logger.info("disk %s is visible to %s" % (disk, vm_name))

        logger.info("Checking if disk '%s' is readonly", disk)
        if not is_ro_vm_disk.get_read_only():
            raise exceptions.DiskException(
                "Disk '%s' is not read only, aborting test", disk
            )

        logger.info("Trying to write to read only disk...")
        status, out = helpers.perform_dd_to_disk(vm_name, disk)
        status = (not status) and (READ_ONLY in out or NOT_PERMITTED in out)
        if not status:
            raise exceptions.DiskException("Write operation to RO disk "
                                           "succeeded")
        logger.info("Failed to write to read only disk")


def create_third_sd(sd_name, host_name, storage_type):
    """
    Helper function for creating SD
    Params:
        * sd_name - name of the storage domain
        * host_name - name of the host use to create the sd
        * storage_type - storage domain type
    Return: False if storage domain was not created,
            True otherwise
    """
    sd_args = {
        'type': ENUMS['storage_dom_type_data'],
        # storage_type should be always passed in
        'storage_type': storage_type,
        'host': host_name}

    sd_args['name'] = sd_name
    if config.GOLDEN_ENV:
        if storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.UNUSED_LUNS[0]
            sd_args['lun_address'] = config.UNUSED_LUN_ADDRESSES[0]
            sd_args['lun_target'] = config.UNUSED_LUN_TARGETS[0]
            sd_args['lun_port'] = config.LUN_PORT
        elif storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
            sd_args['path'] = config.UNUSED_DATA_DOMAIN_PATHS[0]
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_args['address'] = config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0]
            sd_args['path'] = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
    else:
        if storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.LUNS[2]
            sd_args['lun_address'] = config.LUN_ADDRESS[2]
            sd_args['lun_target'] = config.LUN_TARGET[2]
            sd_args['lun_port'] = config.LUN_PORT
        elif storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.ADDRESS[2]
            sd_args['path'] = config.PATH[2]
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_args['address'] = config.GLUSTER_ADDRESS[2]
            sd_args['path'] = config.GLUSTER_PATH[2]

    logger.info('Creating storage domain with parameters: %s', sd_args)
    status = addStorageDomain(True, **sd_args)

    return status
