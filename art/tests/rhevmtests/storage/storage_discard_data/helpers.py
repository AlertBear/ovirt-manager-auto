"""
Helpers module for storage_domain discard data
"""

import rhevmtests.helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks,
    jobs as ll_jobs
)


def write_to_disk_and_verify_size_claim(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Write to the VM disk with DD and check the LUN used size for later usage

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    # Write to the disk
    testflow.step("Writing to disk %s of VM %s with 'dd'", disk_name, vm_name)
    assert storage_helpers.perform_dd_to_disk(
        vm_name, disk_name, size=config.DD_SIZE
    ), "Failed to write to disk %s" % disk_name

    # Check storage domain's LUN used size after writing to the disk
    lun_used_size_after_dd = rhevm_helpers.get_lun_actual_size(
        storage_manager, lun_id
    )
    assert lun_used_size_after_dd, (
        "Couldn't get storage domain %s volume size" % storage_domain
    )
    assert lun_used_size_after_dd > config.INITIAL_LUN_USED_SIZE, (
        "SD LUN used size didn't grow after writing to disk %s" % disk_name
    )


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


def create_snapshot_write_to_disk_and_power_off_vm(
    vm_name, disk_name, description, storage_domain, storage_manager,
    lun_id, persist_memory=None
):
    """
    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        description (str): Snapshot description
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID
        persist_memory (bool): Snapshot persistent memory

    Raises:
        AssertionError: In case of any failure
    """
    # Create a snapshot with memory
    testflow.step("Creating snapshot %s of VM %s", description, vm_name)
    assert ll_vms.addSnapshot(
        True, vm_name, description, persist_memory=persist_memory
    ), "Failed to create snapshot of VM %s" % vm_name
    ll_vms.wait_for_vm_snapshots(vm_name, [config.SNAPSHOT_OK], description)
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    # Write to the disk and verify LUN used space is claimed
    write_to_disk_and_verify_size_claim(
        vm_name, disk_name, storage_domain, storage_manager, lun_id
    )

    power_off_vm(vm_name)

    config.USED_SIZE_BEFORE_DELETE = rhevm_helpers.get_lun_actual_size(
        storage_manager, lun_id
    )
    testflow.step(
        "LUN used size before delete operation is %s",
        config.USED_SIZE_BEFORE_DELETE
    )


def delete_disk_flow(disk_name, vm_name):
    """
    Perform delete disk basic flow

    Args:
        disk_name (str): The name of the disk
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of any failure
    """
    power_off_vm(vm_name)

    # Delete the disk
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
    power_off_vm(vm_name)

    # Move disk to the target domain
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
    testflow.step(
        "Live migrate VM %s disk %s to storage domain %s",
        vm_name, disk_name, target_sd
    )
    ll_vms.live_migrate_vm_disk(vm_name, disk_name, target_sd)
    ll_jobs.wait_for_jobs([config.LIVE_STORAGE_MIGRATION])


def live_merge_flow(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform live snapshot merge basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    # Create a snapshot without a memory
    description = config.LIVE_MERGE
    testflow.step("Creating snapshot %s of VM %s", description, vm_name)
    assert ll_vms.addSnapshot(True, vm_name, description), (
        "Failed to create snapshot of VM %s" % vm_name
    )
    ll_vms.wait_for_vm_snapshots(
        vm_name, [config.SNAPSHOT_OK], description
    )
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    # Write to the disk and verify LUN used space is claimed
    write_to_disk_and_verify_size_claim(
        vm_name, disk_name, storage_domain, storage_manager, lun_id
    )
    config.USED_SIZE_BEFORE_DELETE = rhevm_helpers.get_lun_actual_size(
        storage_manager, lun_id
    )
    testflow.step(
        "LUN used size before delete operation is %s",
        config.USED_SIZE_BEFORE_DELETE
    )
    # Delete the snapshot
    testflow.step(
        "Removing snapshot '%s' of vm %s", description, vm_name
    )
    assert ll_vms.removeSnapshot(True, vm_name, description), (
        "Failed to live delete snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


def cold_merge_flow(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform cold snapshot merge basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    description = config.COLD_MERGE
    create_snapshot_write_to_disk_and_power_off_vm(
        vm_name, disk_name, description, storage_domain, storage_manager,
        lun_id
    )

    # Delete the snapshot
    testflow.step("Removing snapshot '%s' of vm %s", description, vm_name)
    assert ll_vms.removeSnapshot(True, vm_name, description), (
        "Failed to delete snapshot %s" % description
    )
    ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


def cold_merge_with_memory_flow(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform cold snapshot merge with memory basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    description = config.COLD_MERGE_WITH_MEMORY
    create_snapshot_write_to_disk_and_power_off_vm(
        vm_name, disk_name, description, storage_domain, storage_manager,
        lun_id, True
    )
    # Delete the snapshot
    testflow.step("Removing snapshot '%s' of vm %s", description, vm_name)
    assert ll_vms.removeSnapshot(True, vm_name, description), (
        "Failed to delete snapshot %s" % description
    )
    ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


def restore_snapshot_flow(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform restore snapshot without memory basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    description = config.RESTORE_SNAPSHOT
    create_snapshot_write_to_disk_and_power_off_vm(
        vm_name, disk_name, description, storage_domain, storage_manager,
        lun_id, True
    )
    # Restore the snapshot
    testflow.step("Previewing snapshot %s on VM %s", description, vm_name)

    assert ll_vms.preview_snapshot(True, vm_name, description), (
        "Failed to preview snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
    testflow.step("Committing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.commit_snapshot(True, vm_name), (
        "Failed to commit snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])


def undo_previewed_snapshot_flow(vm_name, disk_name, storage_manager, lun_id):
    """
    Perform undo to a previewed snapshot basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    power_off_vm(vm_name)

    description = config.PREVIEW_UNDO_SNAPSHOT
    # Create a snapshot
    testflow.step("Creating snapshot %s of VM %s", description, vm_name)
    assert ll_vms.addSnapshot(True, vm_name, description), (
        "Failed to create snapshot of VM %s" % vm_name
    )
    ll_vms.wait_for_vm_snapshots(
        vm_name, [config.SNAPSHOT_OK], description
    )
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

    # Preview the snapshot
    testflow.step("Previewing snapshot %s on VM %s", description, vm_name)

    assert ll_vms.preview_snapshot(True, vm_name, description), (
        "Failed to preview snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

    # Start the VM
    testflow.step("Starting VM %s", vm_name)
    assert ll_vms.startVm(True, vm_name, config.VM_UP), (
        "Failed to start VM %s" % vm_name
    )

    # Write to the disk
    testflow.step("Writing to disk %s of VM %s with 'dd'", disk_name, vm_name)
    assert storage_helpers.perform_dd_to_disk(
        vm_name, disk_name, size=config.DD_SIZE
    ), ("Failed to write to disk %s" % disk_name)

    power_off_vm(vm_name)

    config.USED_SIZE_BEFORE_DELETE = rhevm_helpers.get_lun_actual_size(
        storage_manager, lun_id
    )
    testflow.step(
        "LUN used size before delete operation is %s",
        config.USED_SIZE_BEFORE_DELETE
    )

    # Undo snapshot
    testflow.step("Undoing snapshot of VM %s", vm_name)
    assert ll_vms.undo_snapshot_preview(True, vm_name), (
        "Failed to undo previewed snapshot %s" % description
    )
    ll_vms.wait_for_vm_snapshots(vm_name, [config.SNAPSHOT_OK])


def restore_snapshot_with_memory_flow(
    vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform restore snapshot with memory basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """
    description = config.RESTORE_SNAPSHOT_WITH_MEMORY
    create_snapshot_write_to_disk_and_power_off_vm(
        vm_name, disk_name, description, storage_domain, storage_manager,
        lun_id, True
    )

    # Restore the snapshot
    testflow.step("Previewing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.preview_snapshot(True, vm_name, description), (
        "Failed to preview snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])

    testflow.step("Committing snapshot %s on VM %s", description, vm_name)
    assert ll_vms.commit_snapshot(True, vm_name), (
        "Failed to commit snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])


def remove_snspshot_single_disk_flow(
        vm_name, disk_name, storage_domain, storage_manager, lun_id
):
    """
    Perform remove snapshot single disk basic flow

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        storage_domain (str): The name of the storage domain
        storage_manager (str): The storage manager instance
        lun_id (str): The LUN ID

    Raises:
        AssertionError: In case of any failure
    """

    description = config.REMOVE_SNAPSHOT_SINGLE_DISK
    create_snapshot_write_to_disk_and_power_off_vm(
        vm_name, disk_name, description, storage_domain, storage_manager,
        lun_id
    )

    # Delete the snapshot disk
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
    snapshot_disks_after = ll_vms.get_snapshot_disks(vm_name, description)
    disk_ids_after = [disk.get_id() for disk in snapshot_disks_after]
    assert vm_disk.get_id() not in disk_ids_after, (
        "Disk %s is part of the snapshot's disks" % vm_disk.get_alias()
    )
