"""
3.4 Feature: Single Disk Snapshot helpers functions
"""

import logging
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, get_vm_snapshots, removeSnapshot,
)

logger = logging.getLogger(__name__)

SNAPSHOT_TIMEOUT = 15 * 60


def remove_all_vm_snapshots(vm_name, description):
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
