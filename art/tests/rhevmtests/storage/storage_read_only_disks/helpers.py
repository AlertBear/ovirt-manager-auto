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

READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'


def write_on_vms_ro_disks(vm_name):
    """
    Check that vm's disks are all visible and write operations to RO are
    impossible
    Parameters:
        * vm_name - name of vm
    """
    vm_disks = [
        disk for disk in ll_vms.getVmDisks(vm_name) if not
        ll_vms.is_bootable_disk(vm_name, disk.get_id()) and
        ll_vms.is_active_disk(vm_name, disk.get_id())
    ]

    for disk in vm_disks:
        disk_alias = disk.get_alias()
        logger.info(
            "Checking if disk %s visible to %s", disk_alias, vm_name
        )
        is_visible = ll_disks.check_disk_visibility(disk_alias, vm_disks)
        if not is_visible:
            raise exceptions.DiskException(
                "Disk '%s' is not visible to vm '%s'", disk_alias, vm_name
            )
        logger.info("disk %s is visible to %s", disk_alias, vm_name)
        logger.info("Checking if disk '%s' is readonly", disk_alias)
        if not ll_disks.get_read_only(vm_name, disk.get_id()):
            raise exceptions.DiskException(
                "Disk '%s' is not read only, aborting test", disk_alias
            )

        logger.info("Trying to write to read only disk...")
        status, out = helpers.perform_dd_to_disk(vm_name, disk_alias)
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
