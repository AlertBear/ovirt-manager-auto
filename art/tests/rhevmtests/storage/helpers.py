"""
Storage helper functions
"""
import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState,
    attachDisk,
    addDisk)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import activateVmDisk
from art.test_handler import exceptions
from rhevmtests.storage.storage_single_disk_snapshot import config

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 250

disk_args = {
    # Fixed arguments
    'provisioned_size': config.DISK_SIZE,
    'wipe_after_delete': config.BLOCK_FS,
    'storagedomain': config.SD_NAME,
    'bootable': False,
    'shareable': False,
    'active': True,
    'interface': config.VIRTIO,
    # Custom arguments - change for each disk
    'format': config.COW_DISK,
    'sparse': True,
    'alias': '',
}


def prepare_disks_for_vm(vm_name, disks_to_prepare, read_only=False):
    """
    Adding disks, Attach disks to vm, and activate them
    Parameters:
        * vm_name - name of vm which disk should attach to
        * disks_to_prepare - list of disks aliases
        * read_only - if the disks should attach as RO disks
    Return: True if ok, or raise DiskException otherwise
    """
    is_ro = 'Read Only' if read_only else 'Read Write'
    for disk in disks_to_prepare:
        disk_args['alias'] = disk
        assert addDisk(positive=True, **disk_args)
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