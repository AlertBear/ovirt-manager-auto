"""
4.1 Feature: qcow2 v3 test helpers functions
"""
import logging
import config
from rhevmtests.storage import helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    disks as ll_disks,
)
logger = logging.getLogger(__name__)


def verify_qcow_version_vm_disks(vm_name, qcow_ver=config.QCOW_V3):
    """
    Get qcow version from disks attached to a VM

    Args:
        vm_name (str): name of the VM
        qcow_ver (str): expected qcow version v2 or v3

    Raises:
        AssertionError: if disk has unexpected qcow version
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


def verify_qcow_disks_snapshots_version_sd(
    storage_domain, expected_qcow_version=config.QCOW_V3
):
    """
    Verify disk snapshot qcow version is v2 or v3 on all disks snapshots via
    storage domain API

     Args:
        storage_domain (str): storage_domain name where snapshot disks reside
        expected_qcow_version (str): qcow version v2 or v3

    Raises:
        AssertionError: if snapshot disk has unexpected qcow version

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
        vm_name (str): name of the VM
        disk_name (str): name of the disk
        qcow_ver (str): qcow version v2 or v3
        wait (bool): wait for disk status to be 'OK'

    Raises:
        AssertionError: if update qcow version on disk fails
.
    """
    assert ll_vms.updateDisk(
        True, vmName=vm_name, alias=disk_name,
        qcow_version=qcow_ver
    ), "Failed to update disk %s on VM %s to qcow version %s" % (
        disk_name, vm_name, qcow_ver
    )


def verify_qcow_specific_snapshot(
    vm_name, snapshot_description, storage_domain, expected_qcow=config.QCOW_V3
):
    """
    Verify qcow version of a specific snapshot related disks

    Args:
        vm_name (str): name of the VM
        snapshot_description (str): description of the snapshot
        storage_domain (str): storage domain name
        expected_qcow (str): expected qcow_version of the snapshot disk

    Raises:
        AssertionError: if qcow versions of a specific snapshot related disks
                        are not as expected
    """
    snapshot_id = [
        object.get_snapshot().get_id() for object in ll_vms.get_snapshot_disks(
            vm_name, snapshot_description
        )
    ]
    storage_domain_diskssnapshots_objects = (
        ll_disks.get_storage_domain_diskssnapshots_objects(storage_domain)
    )

    for disk_snapshot_object in storage_domain_diskssnapshots_objects:
        if disk_snapshot_object.get_snapshot().get_id() == snapshot_id[0]:
            assert disk_snapshot_object.get_qcow_version() == expected_qcow, (
                "Snapshot disk %s does not have expected cow version %s" % (
                    disk_snapshot_object.get_alias(), expected_qcow
                )
            )


def verify_test_files_checksum(
    vm_name, checksum_file_list, full_path_list, vm_executor=None
):
    """
    Verify test files checksum

    Args:
        vm_name (str): name of the VM
        checksum_file_list (list): list of checksum for files
        full_path_list (list): list for full path of files

    Raises:
        AssertionError: if file exists but it's content changed
    """
    if not vm_executor:
        vm_executor = storage_helpers.get_vm_executor(vm_name)
    for prior_checksum, full_path in zip(full_path_list, checksum_file_list):
        new_checksum = storage_helpers.checksum_file(
            vm_name, full_path, vm_executor
        )
        assert prior_checksum != new_checksum, (
            "File %s exists but it's content changed since it's creation"
        ) % full_path
