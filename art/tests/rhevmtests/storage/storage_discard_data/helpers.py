"""
Helpers module for storage_domain discard data
"""
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks,
    jobs as ll_jobs
)


def start_vm(vm_name):
    """
    Start VM

    Args:
        vm_name: The name of the VM

    Raises:
        AssertionError: In case of start VM failure
    """
    testflow.step("Starting VM %s", vm_name)
    ll_vms.start_vms([vm_name], 1, wait_for_ip=True)


def power_off_vm(vm_name):
    """
    Power off VM

    Args:
        vm_name (str): The VM name

    Raises:
        AssertionError: In case of an error to start the VM
    """
    testflow.step("Power off VM %s", vm_name)
    assert ll_vms.stop_vms_safely([vm_name]), (
        "Failed to power off VM %s" % vm_name
    )


def create_snapshot(vm_name, description, persist_memory=None):
    """
    Create a snapshot

    Args:
        vm_name (str): The name of the VM
        description (str): Snapshot description
        persist_memory (bool): Snapshot persistent memory

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step("Creating snapshot %s of VM %s", description, vm_name)
    assert ll_vms.addSnapshot(
        True, vm_name, description, persist_memory=persist_memory
    ), "Failed to create snapshot of VM %s" % vm_name
    ll_vms.wait_for_vm_snapshots(vm_name, [config.SNAPSHOT_OK], description)
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])


def preview_snapshot(vm_name, description):
    """
    Preview snapshot

    Args:
        vm_name (str): The name of the VM
        description (str): Snapshot description

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step("Previewing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.preview_snapshot(True, vm_name, description), (
        "Failed to preview snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])


def remove_snapshot(vm_name, description):
    """
    Remove snapshot

    Args:
        vm_name (str): The name of the VM
        description (str): Snapshot description

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step(
        "Removing snapshot '%s' of vm %s", description, vm_name
    )
    assert ll_vms.removeSnapshot(True, vm_name, description), (
        "Failed to live delete snapshot %s" % description
    )
    ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


def delete_disk_flow(disk_name):
    """
    Perform delete disk basic flow

    Args:
        disk_name (str): The name of the disk

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step("Deleting disk %s", disk_name)
    assert ll_disks.deleteDisk(True, disk_name), (
        "Failed to delete disk %s" % disk_name
    )
    ll_jobs.wait_for_jobs([config.DELETE_DISK])


def cold_move_flow(vm_name, disk_name, target_sd):
    """
    Perform cold disk move basic flow

    Args:
        disk_name (str): The name of the disk
        vm_name (str): The name of the VM
        target_sd (str): The name of the target storage domain

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step(
        "Moving disk %s of VM %s to storage domain %s", disk_name, vm_name,
        target_sd
    )
    assert ll_disks.move_disk(disk_name=disk_name, target_domain=target_sd), (
        "Failed to cold move disk %s to domain %s" % (disk_name, target_sd)
    )
    ll_jobs.wait_for_jobs([config.COLD_MOVE])


def live_storage_migration_flow(vm_name, disk_name, target_sd):
    """
    Perform live storage migration basic flow

    Args:
        disk_name (str): The name of the disk
        vm_name (str): The name of the VM
        target_sd (str): The name of the target storage domain

    Raises:
        DiskException: When disk live migration fails
        APITimeout: If waiting for snapshot was longer than 20 seconds
    """
    start_vm(vm_name)
    testflow.step(
        "Live migrate VM %s disk %s to storage domain %s",
        vm_name, disk_name, target_sd
    )
    ll_vms.migrate_vm_disk(vm_name, disk_name, target_sd)
    ll_jobs.wait_for_jobs([config.LIVE_STORAGE_MIGRATION])


def live_merge_flow(vm_name):
    """
    Perform live snapshot merge basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.LIVE_MERGE
    create_snapshot(vm_name, description)
    start_vm(vm_name)
    remove_snapshot(vm_name, description)


def cold_merge_flow(vm_name):
    """
    Perform cold snapshot merge basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.COLD_MERGE
    create_snapshot(vm_name, description)
    remove_snapshot(vm_name, description)


def cold_merge_with_memory_flow(vm_name):
    """
    Perform cold snapshot merge with memory basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.COLD_MERGE_WITH_MEMORY
    start_vm(vm_name)
    create_snapshot(vm_name, description, True)
    power_off_vm(vm_name)
    remove_snapshot(vm_name, description)


def restore_snapshot_flow(vm_name):
    """
    Perform restore snapshot without memory basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.RESTORE_SNAPSHOT
    create_snapshot(vm_name, description)
    preview_snapshot(vm_name, description)
    testflow.step("Committing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.commit_snapshot(True, vm_name), (
        "Failed to commit snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])


def undo_previewed_snapshot_flow(vm_name):
    """
    Perform undo to a previewed snapshot basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.PREVIEW_UNDO_SNAPSHOT
    create_snapshot(vm_name, description)
    preview_snapshot(vm_name, description)
    testflow.step("Undoing snapshot of VM %s", vm_name)
    assert ll_vms.undo_snapshot_preview(True, vm_name), (
        "Failed to undo previewed snapshot %s" % description
    )
    ll_vms.wait_for_vm_snapshots(vm_name, [config.SNAPSHOT_OK])


def restore_snapshot_with_memory_flow(vm_name):
    """
    Perform restore snapshot with memory basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.RESTORE_SNAPSHOT_WITH_MEMORY
    start_vm(vm_name)
    create_snapshot(vm_name, description, True)
    power_off_vm(vm_name)
    preview_snapshot(vm_name, description)
    testflow.step("Committing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.commit_snapshot(True, vm_name, restore_memory=True), (
        "Failed to commit snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])


def remove_snspshot_single_disk_flow(vm_name):
    """
    Perform remove snapshot single disk basic flow

    Args:
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    description = config.REMOVE_SNAPSHOT_SINGLE_DISK
    create_snapshot(vm_name, description)
    snapshot_disks_before = ll_vms.get_snapshot_disks(vm_name, description)
    disk_ids_before = [disk.get_id() for disk in snapshot_disks_before]
    vm_disk = ll_vms.getVmDisks(vm_name)[-1]
    assert vm_disk.get_id() in disk_ids_before, (
        "Disk %s is not part of the snapshot's disks" % vm_disk.get_alias()
    )
    testflow.step("Deleting snapshot %s disks", description)
    assert ll_vms.delete_snapshot_disks(
        vm_name, description, vm_disk.get_id()
    ), "Failed to remove snapshots disk %s" % vm_disk.get_alias()
    ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOTS_DISK])

    snapshot_disks_after = ll_vms.get_snapshot_disks(vm_name, description)
    disk_ids_after = [disk.get_id() for disk in snapshot_disks_after]
    assert vm_disk.get_id() not in disk_ids_after, (
        "Disk %s is part of the snapshot's disks" % vm_disk.get_alias()
    )
