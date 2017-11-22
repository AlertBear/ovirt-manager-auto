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
        if disk.get_storage_type() == config.DISK_TYPE_LUN:
            disk_id = disk.get_lun_storage().get_id()
        else:
            disk_id = disk.get_id()
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
        status, out = helpers.perform_dd_to_disk(vm_name, disk_id, key='id')
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
            sd_args['lun'] = config.ISCSI_DOMAINS_KWARGS[0]['lun']
            sd_args['lun_address'] = (
                config.ISCSI_DOMAINS_KWARGS[0]['lun_address']
            )
            sd_args['lun_target'] = (
                config.ISCSI_DOMAINS_KWARGS[0]['lun_target']
            )
            sd_args['lun_port'] = config.LUN_PORT
        elif storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.NFS_DOMAINS_KWARGS[0]['address']
            sd_args['path'] = config.NFS_DOMAINS_KWARGS[0]['path']
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_args['address'] = config.GLUSTER_DOMAINS_KWARGS[0]['address']
            sd_args['path'] = config.GLUSTER_DOMAINS_KWARGS[0]['path']
    else:
        if storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.ISCSI_DOMAINS_KWARGS[2]['lun']
            sd_args['lun_address'] = (
                config.ISCSI_DOMAINS_KWARGS[2]['lun_address']
            )
            sd_args['lun_target'] = (
                config.ISCSI_DOMAINS_KWARGS[2]['lun_target']
            )
            sd_args['lun_port'] = config.LUN_PORT
        elif storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.NFS_DOMAINS_KWARGS[2]['address']
            sd_args['path'] = config.NFS_DOMAINS_KWARGS[2]['path']
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_args['address'] = config.GLUSTER_DOMAINS_KWARGS[2]['address']
            sd_args['path'] = config.GLUSTER_DOMAINS_KWARGS[2]['path']

    logger.info('Creating storage domain with parameters: %s', sd_args)
    status = ll_sd.addStorageDomain(True, **sd_args)

    return status
