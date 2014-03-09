"""
3.4 Feature: Single Disk Snapshot helpers functions
"""

import logging
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely,
    get_vm_snapshots,
    removeSnapshot,
)

from rhevmtests.storage.helpers import *  # flake8: noqa
from rhevmtests.storage.storage_single_disk_snapshot import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISK_NAME_FORMAT = '%s_%s_%s_disk'
DISKS_NAMES = list()

DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'

DD_TIMEOUT = 1500
SNAPSHOT_TIMEOUT = 15 * 60


def remove_all_vm_test_snapshots(vm_name, description):
    """
    Description: Removes all snapshots of given VM which were created during
    live storage migration (according to snapshot description)
    Author: ratamir
    Parameters:
    * vm_name - name of the vm that should be cleaned out of snapshots
    * description - snapshot description
    created during live migration
    Raise: AssertionError if something went wrong
    """
    logger.info("Removing all '%s'", description)
    stop_vms_safely([vm_name])
    snapshots = get_vm_snapshots(vm_name)
    results = [removeSnapshot(True, vm_name, description, SNAPSHOT_TIMEOUT)
               for snapshot in snapshots
               if snapshot.description == description]
    wait_for_jobs(timeout=SNAPSHOT_TIMEOUT)
    assert False not in results
