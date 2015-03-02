"""
Live Storage Migration test helpers functions
"""

import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    wait_for_disks_status, addDisk, get_all_disk_permutation, attachDisk,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import activateVmDisk

from art.test_handler import exceptions

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
        wait_for_disks_status(disk, timeout=DISK_TIMEOUT)
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
            wait_for_disks_status(disk_params['alias'])
            if attach:
                prepare_disks_for_vm(vm_name, [disk_params['alias']])
