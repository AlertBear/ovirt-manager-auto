"""
Read Only Disk test helpers functions
"""
import logging

import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.test_handler import exceptions
from rhevmtests.storage import helpers

logger = logging.getLogger(__name__)

DISK_NAMES = dict()  # dictionary with storage type as key

READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'

not_bootable = lambda disk: not disk.get_bootable() and disk.get_active()


def write_on_vms_ro_disks(vm_name, storage_type, imported_vm=False):
    """
    Check that vm's disks are all visible and write operations to RO are
    impossible
    Parameters:
        * vm_name - name of vm
        * storage_type - storage domain type
        * imported_vm - True if the vm is imported
    """
    vm_disks = filter(not_bootable, ll_vms.getVmDisks(vm_name))
    if imported_vm:
        global DISK_NAMES
        DISK_NAMES[storage_type] = [disk.get_alias() for disk in vm_disks]
        logger.info("Disks: %s", DISK_NAMES[storage_type])
    logger.info("VM %s disks %s", vm_name, vm_disks)

    for disk, is_ro_vm_disk in zip(DISK_NAMES[storage_type], vm_disks):
        logger.info("Checking if disk %s visible to %s", disk, vm_name)
        is_visible = ll_disks.check_disk_visibility(disk, vm_disks)
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
            raise exceptions.DiskException(
                "Write operation to RO disk succeeded"
            )
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
        'type': config.TYPE_DATA,
        'storage_type': storage_type,
        'host': host_name
    }

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
    status = ll_sd.addStorageDomain(True, **sd_args)

    return status
