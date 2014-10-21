"""
Read Only Disk test helpers functions
"""

import logging
from utilities.machine import Machine
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState, addDisk, get_all_disk_permutation, attachDisk,
    check_disk_visibility, checkDiskExists, deleteDisk,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import addStorageDomain
from art.rhevm_api.tests_lib.low_level.vms import (
    activateVmDisk, getVmDisks, waitForVMState, start_vms,
)
from art.test_handler import exceptions

from rhevmtests.storage.helpers import get_vm_ip

import shlex
import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISKS_NAMES = dict()  # dictionary with storage type as key
DISK_TIMEOUT = 250

DD_TIMEOUT = 1500
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
FILTER = '[sv]d'
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'


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


def verify_write_operation_to_disk(vm_name, disk_number):
    """
    Function that perform dd command to disk
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * disk_number - disk number from devices list
    Return: ecode and output, or raise EntityNotFound if error occurs
    """
    start_vms([vm_name], max_workers=1, wait_for_ip=False)
    waitForVMState(vm_name)
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'

    vm_devices = vm_machine.get_storage_devices(filter=FILTER)
    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")

    vm_devices = [device for device in vm_devices if device != boot_disk]

    command = DD_COMMAND % (boot_disk, vm_devices[disk_number])

    ecode, out = vm_machine.runCmd(shlex.split(command), timeout=DD_TIMEOUT)

    return ecode, out


def prepare_disks_for_vm(vm_name, disks_to_prepare, read_only=False):
    """
    Attach disks to vm
    Parameters:
        * vm_name - name of vm which disk should attach to
        * disks_to_prepare - list of disks aliases
        * read_only - if the disks should attach as RO disks
    Return: True if ok, or raise DiskException otherwise
    """
    is_ro = 'Read Only' if read_only else 'Read Write'
    for disk in disks_to_prepare:
        waitForDisksState(disk, timeout=DISK_TIMEOUT)
        logger.info("Attaching disk %s as %s disk to vm %s",
                    disk, is_ro, vm_name)
        status = attachDisk(True, disk, vm_name, active=False,
                            read_only=read_only)
        if not status:
            raise exceptions.DiskException("Failed to attach disk %s to"
                                           " vm %s"
                                           % (disk, vm_name))

        logger.info("Plugging disk %s", disk)
        status = activateVmDisk(True, vm_name, disk)
        if not status:
            raise exceptions.DiskException("Failed to plug disk %s "
                                           "to vm %s"
                                           % (disk, vm_name))
    return True


def write_on_vms_ro_disks(vm_name, storage_type, imported_vm=False):
    """
    Check that vm's disks are all visible and write operations to RO are
    impossible
    Parameters:
        * vm_name - name of vm
        * storage_type - storage domain type
        * imported_vm - True if the vm is imported
    """
    vm_disks = getVmDisks(vm_name)
    if imported_vm:
        global DISKS_NAMES
        DISKS_NAMES[storage_type] = [disk.get_alias() for disk in vm_disks if
                                     not disk.get_bootable()]
        logger.info("Disks: %s", DISKS_NAMES[storage_type])
    logger.info("VM %s disks %s", vm_name, vm_disks)

    for index, disk in enumerate(DISKS_NAMES[storage_type]):
        logger.info("Checking if disk %s visible to %s", disk, vm_name)
        is_visible = check_disk_visibility(disk, vm_disks)

        if not is_visible:
            raise exceptions.DiskException("Disk %s is not visible to vm %s",
                                           disk, vm_name)
        logger.info("disk %s is visible to %s" % (disk, vm_name))
        state, out = verify_write_operation_to_disk(
            vm_name, disk_number=index)
        logger.info("Trying to write to read only disk...")
        status = (not state) and (READ_ONLY in out or NOT_PERMITTED in out)
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
        if storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
            sd_args['path'] = config.UNUSED_DATA_DOMAIN_PATHS[0]
        elif storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.UNUSED_LUNS[0]
            sd_args['lun_address'] = config.UNUSED_LUN_ADDRESSES[0]
            sd_args['lun_target'] = config.UNUSED_LUN_TARGETS[0]
            sd_args['lun_port'] = config.LUN_PORT
    else:
        if storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.ADDRESS[2]
            sd_args['path'] = config.PATH[2]
        elif storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.LUNS[2]
            sd_args['lun_address'] = config.LUN_ADDRESS[2]
            sd_args['lun_target'] = config.LUN_TARGET[2]
            sd_args['lun_port'] = config.LUN_PORT

    logger.info('Creating storage domain with parameters: %s', sd_args)
    status = addStorageDomain(True, **sd_args)

    return status
