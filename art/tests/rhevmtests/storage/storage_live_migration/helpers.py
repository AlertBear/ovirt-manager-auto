"""
Live Storage Migration test helpers functions
"""

import logging
from utilities.machine import Machine
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState, addDisk, get_all_disk_permutation, attachDisk,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import (
    activateVmDisk, waitForVMState, start_vms,
)
from rhevmtests.storage.helpers import get_vm_ip

from art.test_handler import exceptions
import shlex

import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISKS_NAMES = list()
DISK_TIMEOUT = 250

DD_TIMEOUT = 1500
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
FILTER = '[sv]d'
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'


def add_new_disk(sd_name, permutation, shared=False):
    """
    Add a new disk
    Parameters:
        * sd_name - disk wil added to this sd
        * shared - True if the disk should e shared
        * permutations:
            * interface - VIRTIO or VIRTIO_SCSI
            * sparse - True if thin, False preallocated
            * disk_format - 'cow' or 'raw'
    """
    disk_args = {
        # Fixed arguments
        'provisioned_size': config.DISK_SIZE,
        'wipe_after_delete': config.BLOCK_FS,
        'storagedomain': sd_name,
        'bootable': False,
        'shareable': shared,
        'active': True,
        'size': config.DISK_SIZE,
        # Custom arguments - change for each disk
        'format': permutation['format'],
        'interface': permutation['interface'],
        'sparse': permutation['sparse'],
        'alias': "%s_%s_%s_disk" %
                 (permutation['interface'],
                  permutation['format'],
                  permutation['sparse'])}

    assert addDisk(True, **disk_args)
    DISKS_NAMES.append(disk_args['alias'])


def start_creating_disks_for_test(shared=False, sd_name=config.SD_NAME_0):
    """
    Begins asynchronous creation of disks of all permutations of disk
    interfaces, formats and allocation policies
    """
    global DISKS_NAMES
    DISKS_NAMES = []
    logger.info("Disks: %s", DISKS_NAMES)
    logger.info("Creating all disks")
    DISK_PERMUTATIONS = get_all_disk_permutation(
        block=config.BLOCK_FS, shared=shared)
    for permutation in DISK_PERMUTATIONS:
        add_new_disk(sd_name=sd_name, permutation=permutation, shared=shared)


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
        wait_for_jobs()
    return True


def add_new_disk_for_test(vm_name, alias, provisioned_size=(1 * config.GB),
                          sparse=False, disk_format=config.RAW_DISK,
                          wipe_after_delete=False, attach=False):
            """
            Prepares disk for given vm
            """
            disk_params = {
                'alias': alias,
                'active': False,
                'provisioned_size': provisioned_size,
                'interface': config.VIRTIO,
                'format': disk_format,
                'sparse': sparse,
                'wipe_after_delete': wipe_after_delete,
                'storagedomain': config.SD_NAME_0
            }

            if not addDisk(True, **disk_params):
                raise exceptions.DiskException(
                    "Can't create disk with params: %s" % disk_params)
            logger.info("Waiting for disk %s to be ok", disk_params['alias'])
            waitForDisksState(disk_params['alias'])
            if attach:
                prepare_disks_for_vm(vm_name, [disk_params['alias']])


def verify_write_operation_to_disk(vm_name, disk_number=0, ensure_vm_on=False):
    """
    Function that perform dd command to disk
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * disk_number - disk number from devices list
    Return: ecode and output, or raise EntityNotFound if error occurs
    """
    if ensure_vm_on:
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')
    vm_devices = vm_machine.get_storage_devices(filter=FILTER)
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'
    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")

    vm_devices = [device for device in vm_devices if device != boot_disk]
    command = DD_COMMAND % (boot_disk, vm_devices[disk_number])
    logger.info("Verifying write operation to disk %s",
                vm_devices[disk_number])
    ecode, out = vm_machine.runCmd(shlex.split(command), timeout=DD_TIMEOUT)
    return ecode, out
