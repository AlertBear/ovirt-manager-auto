"""
Collection of helper functions for auto activate disk tests
"""
import logging

import config
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    vms as ll_vms,
)

logger = logging.getLogger(__name__)

ADDITIONAL_DISK_SIZE = 1 * config.GB


def attach_new_disk(
        polarion_case, vm_name, should_be_active=True, storage_domain=None,
        **permutation
):
    """
    Add a new disk, the disk status should match should_be_active input
    """
    disk_alias = "%s_%s_%s_%s_%s_disk" % (
        polarion_case,
        vm_name,
        permutation["interface"],
        permutation["format"],
        permutation["sparse"]
    )
    disk_args = {
        "interface": permutation["interface"],
        "sparse": permutation["sparse"],
        "alias": disk_alias,
        "format": permutation["format"],
        "active": should_be_active,
        "storagedomain": storage_domain
    }

    assert ll_vms.addDisk(True, vm_name, ADDITIONAL_DISK_SIZE, **disk_args)
    ll_disks.wait_for_disks_status(disk_args["alias"])

    disk_obj = ll_disks.getVmDisk(vm_name, disk_alias)
    active = ll_vms.is_active_disk(vm_name, disk_obj.get_id())
    logger.info("Disk '%s' has status of '%s'", disk_alias, active)
    logger.info(
        "Disk Status is %s, expected disk status is %s",
        active, should_be_active
    )
    # Compare the actual and expected disk status
    if active == should_be_active:
        logger.info("Actual disk status matches the expected disk status")
        return True

    logger.info("Actual disk status does not match the expected disk status")
    return False
