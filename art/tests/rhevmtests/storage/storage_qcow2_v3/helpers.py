"""
4.1 Feature: qcow2 v3 test helpers functions
"""

import logging
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms, disks as ll_disks
)
import config

snapshot_disks_qcow_list = []

logger = logging.getLogger(__name__)


def get_qcow_snapshot_disks_list_one_snapshot(vm_name, snapshot):
    """
    Get qcow snapshot disks list for one snapshot

    Args:
        snapshot(str)- snapshot description
        vm_name(str) - name of the VM
.
    Returns:
       snapshot_disks_qcow_list(list) - snapshot disks qcow version on one
       snapshot
    """

    snapshot_disks_qcow_list.append(
        ll_vms.get_qcow_version_disks_snapshot(vm_name, snapshot)
    )
    return snapshot_disks_qcow_list


def verify_qcow_version_vm_disks(vm_name, qcow_ver=config.QCOW_V3):
    """
    Get qcow version from disks attached to a VM

    Args:
        vm_name(str) - name of the VM
        qcow_ver(str) - expected qcow version v2 or v3
.
    """

    disk_objects_list = ll_vms.getVmDisks(vm_name)
    for disk_obj in disk_objects_list:
        disk_alias = disk_obj.get_alias()
        qcow_version = disk_obj.get_qcow_version()
        assert qcow_version == qcow_ver, (
            "disk %s has unexpected cow version %s" % (
                disk_alias, qcow_version
            )
        )
        logger.info("disk %s was updated to %s" % (disk_alias, qcow_ver))


# Due to bug 1430447 checking qcow_version return wrong value from VM API
def verify_qcow_snapshot_disks_version(
        vm_name, snapshot_list, expected_qcow_version=config.QCOW_V3
):
    """
    Verify disk snapshot qcow version is v2 or v3 on all snapshot disks via
    VM API

    Args:
        vm_name(str) - name of the VM
        snapshot_list(list) - snapshots description on a VM
        expected_qcow_version(str) - qcow version v2 or v3

    """
    for snap in snapshot_list:
        for actual_qcow_version in get_qcow_snapshot_disks_list_one_snapshot(
                vm_name, snap
        ):
            assert expected_qcow_version == actual_qcow_version, (
                "Snapshot disk %s has unexpected cow ver %s" % (
                    snap, expected_qcow_version
                )
            )


def verify_qcow_disks_snapshots_version_sd(
        storage_domain, expected_qcow_version=config.QCOW_V3
):
    """
    Verify disk snapshot qcow version is v2 or v3 on all disks snapshots via
    storage domain API

     Args:
        storage_domain(str) - storage_domain name where snapshot disks reside
        expected_qcow_version(str) - qcow version v2 or v3

    """
    storage_domain_diskssnapshots_objects = (
        ll_disks.get_storage_domain_diskssnapshots_objects(storage_domain)
    )

    for sd_diskssnapshot_object in storage_domain_diskssnapshots_objects:
        actual_qcow_version = sd_diskssnapshot_object.get_qcow_version()
        assert expected_qcow_version == actual_qcow_version, (
            "Snapshot disk %s has unexpected cow ver %s" % (
                sd_diskssnapshot_object.get_alias(), expected_qcow_version
            )
        )
        logger.info(
            "Snapshot disk %s was upgraded to qcow version %s" % (
                sd_diskssnapshot_object.get_alias(), expected_qcow_version
            )
        )


def amend_disk_attachment_api(
        vm_name, disk_name, qcow_ver=config.QCOW_V3, wait=True
):
    """
    Amend disk & disk snapshots in its chain to qcow v2 or v3 via disk
    attachment API

     Args:
        vm_name(str) - name of the VM
        disk_name(str) - name of the disk
        qcow_ver(str) - qcow version v2 or v3
        wait(bool) - wait for disk status to be 'OK'
.
    """
    assert ll_vms.updateDisk(
        True, vmName=vm_name, alias=disk_name,
        qcow_version=qcow_ver
    ), "Failed to update disk %s on VM %s to qcow version %s" % (
        disk_name, vm_name, qcow_ver
    )


def amend_disk_disk_api(disk_name, qcow_version=config.QCOW_V3, wait=True):
    """
    Amend disk & disk snapshots in its chain to qcow v2 or v3 via disk API

    Args:
        disk_name(str) - name of the disk
        qcow_version(str) - target qcow version v2 or v3 of disk/disksnapshot
        wait(bool) - wait for disk status to be 'OK'
.
    """
    # Changed updateDisk function to update_disk_from_disk_api
    # to support new update directly DISK API and to enable amend tests
    # Currently due to bug 1429437 we can not amend disk with updateDisk

    assert ll_disks.update_disk_from_disk_api(
        True, disk_name,
        qcow_version=qcow_version, compare=False
    ), "Failed to update disk %s to qcow version %s" % (
        disk_name, qcow_version
    )
    if wait:
        ll_disks.wait_for_disks_status([disk_name])
