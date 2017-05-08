import config
import os
import shlex
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    jobs as ll_jobs,
    disks as ll_disks
)


def write_content_and_get_checksum(
    vm_name, vm_executor, write_with_dd=False, disk_name=None
):
    """
    Create file, write content to it and get checksum for it

    Args:
        vm_name (str): The name of the VM
        vm_executor (Host executor): The executor of the VM
        write_with_dd (bool): If True, the write operation will be done with
            'dd', otherwise will be done with text content
        disk_name (str): The name of the disk to write to. If None, the disk to
            write to will be the VM OS disk

    Raises:
        AssertionError: In case of any failure

    Returns:
        tuple: (file_name (str): The file name, checksum_before (str): The
            checksum taken for later comparison)

    """
    file_name = os.path.join(config.FILE_PATH, config.FILE_NAME)
    if write_with_dd:
        testflow.step(
            "Writing to file %s on disk %s of VM %s", file_name, disk_name,
            vm_name
        )
        assert storage_helpers.perform_dd_to_disk(
            vm_name=vm_name, disk_alias=disk_name, size=config.DD_SIZE,
            write_to_file=True, file_name=file_name, vm_executor=vm_executor
        )
    else:
        testflow.step("Writing to file %s", file_name)
        assert storage_helpers.write_content_to_file(
            vm_name=vm_name, file_name=file_name,
            content=config.TEXT_CONTENT, vm_executor=vm_executor
        )

    testflow.step("Getting checksum for file %s", file_name)
    checksum_before = shlex.split(
        storage_helpers.checksum_file(
            vm_name=vm_name, file_name=file_name, vm_executor=vm_executor
        )
    )[0]
    testflow.step("Checksum of file %s is %s", file_name, checksum_before)
    testflow.step("Syncing VM %s file system", vm_name)
    command = 'sync'
    storage_helpers._run_cmd_on_remote_machine(
        machine_name=vm_name, command=command, vm_executor=vm_executor
    )
    return file_name, checksum_before


def verify_data_integrity(vm_name, file_name, vm_executor, checksum_before):
    """
    Get checksum to the file that a checksum was taken for before
    storage domain resize and compare the checksums

    Args:
        vm_name (str): The name of the VM
        file_name (str): The name of the file to verify data integrity with
        vm_executor (Host resource): The executor of the VM
        checksum_before (str): The checksum that was taken before for
            comparison

    Raises:
        AssertionError: In case of any failure
    """
    testflow.step("Starting VM %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name], max_workers=1,
        wait_for_status=config.VM_UP, wait_for_ip=True
    ), "Failed to start VM %s" % vm_name

    testflow.step("Getting checksum for file %s", file_name)
    checksum_after = shlex.split(
        storage_helpers.checksum_file(
            vm_name=vm_name, file_name=file_name, vm_executor=vm_executor
        )
    )[0]

    testflow.step(
        "Checksum before domain resize: %s."
        "Checksum after domain resize: %s",
        checksum_before, checksum_after
    )
    assert checksum_before == checksum_after, (
        "VM %s file %s got corrupted" % (vm_name, file_name)
    )


def create_snapshot(vm_name, description):
    """
    Create a snapshot
    Args:
        vm_name (str): The name of the VM
        description (str): The description for snapshot creation

    Raises:
        AssertionError: In case of any failure
    """

    assert ll_vms.addSnapshot(
        positive=True, vm=vm_name, description=description
    ), "Failed to create snapshot of VM %s" % vm_name
    ll_vms.wait_for_vm_snapshots(vm_name, [config.SNAPSHOT_OK], description)
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])


def start_vm(vm_name):
    """
    Start VM
    Args:
        vm_name: The name of the VM

    AssertionError: In case of start VM failure

    """
    testflow.step("Starting VM %s", vm_name)
    assert ll_vms.startVm(True, vm_name, config.VM_UP), (
        "Failed to start VM %s" % vm_name
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


def delete_snapshot(positive, description, vm_name):
    """
    Delete a snapshot

    Args:
        positive (bool): True for success, False otherwise
        description (str): The description of the snapshot
        vm_name (str): The name of the VM

    Raises:
        AssertionError: In case of failure for positive=True or success for
            positive=False
    """
    testflow.step(
        "Removing snapshot '%s' of VM %s. Operation should end with "
        "success=%s", description, vm_name, positive
    )
    assert ll_vms.removeSnapshot(positive, vm_name, description), (
        "Snapshot %s deletion has ended with success=%s" % (
            description, not positive
        )
    )
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])


def create_and_restore_snapshot(vm_name, description):
    create_snapshot(vm_name, description)

    testflow.step("Power off VM %s", vm_name)
    assert ll_vms.stop_vms_safely([vm_name]), (
        "Failed to power off VM %s" % vm_name
    )
    testflow.step(
        "Previewing snapshot %s on VM %s", description, vm_name
    )

    assert ll_vms.preview_snapshot(True, vm_name, description), (
        "Failed to preview snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])
    testflow.step(
        "Committing snapshot %s on VM %s", description, vm_name
    )
    assert ll_vms.commit_snapshot(True, vm_name), (
        "Failed to commit snapshot %s" % description
    )
    ll_jobs.wait_for_jobs([config.JOB_RESTORE_SNAPSHOT])


def create_second_disk(storage_domain):
    """
    Create second disk

    Args:
        storage_domain (str): The name of the storage domain for disk creation

    Raises:
        AssertionError: In case of disk creation failure

    """
    disk_params = config.disk_args.copy()
    disk_params['storagedomain'] = storage_domain
    disk_params['provisioned_size'] = config.SECOND_DISK_SIZE
    disk_params['sparse'] = False
    disk_params['format'] = config.DISK_FORMAT_RAW
    second_disk_name = storage_helpers.create_unique_object_name(
        'second', config.OBJECT_TYPE_DISK
    )
    disk_params['alias'] = second_disk_name
    testflow.setup("Creating disk %s", second_disk_name)
    assert ll_disks.addDisk(True, **disk_params), (
        "Failed to create disk %s" % second_disk_name
    )
    ll_disks.wait_for_disks_status([second_disk_name])


def mount_fs_on_second_vm(vm_name, disk_name, mount_point, vm_executor):
    """
    Mount file system on the second VM the shared disk is attached to

    Args:
        vm_name (str): The name of the VM
        disk_name (str): The name of the disk
        mount_point (str): The path to mount the file system on
        vm_executor (Host executor): VM executor

    Raises:
        AssertionError: In case of any failure
        MountError: In case of mount failure
    """
    disk_logical_name = ll_vms.get_vm_disk_logical_name(vm_name, disk_name)
    out = storage_helpers._run_cmd_on_remote_machine(
        vm_name, config.MOUNT_POINT_CREATE_CMD % mount_point, vm_executor
    )
    assert out, "Failed to create target directory %s"
    disk_logical_name += '1'
    storage_helpers.mount_fs_on_dir(
        vm_name=vm_name, device_name=disk_logical_name,
        target_dir=mount_point, fs_type='ext4', executor=vm_executor
    )
