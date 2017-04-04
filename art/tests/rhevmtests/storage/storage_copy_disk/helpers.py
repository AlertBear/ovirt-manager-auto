import config
import logging
import shlex
import os
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from rhevmtests.storage import helpers as storage_helpers
from art.test_handler import exceptions

logger = logging.getLogger(__name__)


def clean_all_copied_disks(disks_to_clean):
    """
    Delete all newly created disks
    """
    testflow.teardown("Deleting disks %s", ', '.join(disks_to_clean))
    results = []
    for disk in disks_to_clean:
        results.append(ll_disks.deleteDisk(
            True, disk_id=disk
        ))
    ll_jobs.wait_for_jobs([config.JOB_REMOVE_DISK])
    if False in results:
        raise exceptions.DiskException("Failed to delete disk")


def get_disk_storage_domain_name(disk_object):
    """
    Get the disk's storage domain name

    :param disk_object: Disk object
    :type disk_object: Disk object
    :return: Storage domain name
    :rtype: str
    """
    storage_id = (
        disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    )
    storage_domain_object = ll_sd.get_storage_domain_obj(
        storage_domain=storage_id, key='id'
    )
    return storage_domain_object.get_name()


def get_new_disks(disks_before_copy, disks_after_copy):
    """
    Get new disks copied during the test

    :param disks_before_copy: List of disks before the test starts
    :type disks_before_copy: list
    :param disks_after_copy: List of disks after the test finishes
    :type disks_after_copy: list
    :return: List of newly created disks
    :rtype: list
    """
    return list(set(disks_after_copy) - set(disks_before_copy))


def attach_new_disks_to_vm(vm_name, disks_to_attach):
    """
    Attach newly copied disks to test vm

    :param vm_name: Name of the VM into which disks will be attached
    :type vm_name: str
    :param disks_to_attach: List of the disks to be attached to the
    specified VM
    :type disks_to_attach: list
    """
    testflow.step("Attach copied disks to VM %s", vm_name)
    for disk in disks_to_attach:
        disk_obj = ll_disks.get_disk_obj(disk, 'id')
        bootable = True if 'boot' in disk_obj.get_alias() else False
        ll_disks.attachDisk(
            True, disk, vm_name, disk_id=disk, bootable=bootable
        )


def prepare_disks_for_test(vm_name, storage_type, storage_domain):
    """
    Prepare disks with FS to VM
    """

    testflow.setup("Creating FS on VM's %s disks", vm_name)
    config.DISKS_FOR_TEST[storage_type], config.MOUNT_POINTS[storage_type] = (
        storage_helpers.prepare_disks_with_fs_for_vm(
            storage_domain, storage_type, vm_name
        )
    )
    disk_objects = ll_vms.getVmDisks(vm_name)
    for disk in disk_objects:
        new_vm_disk_name = (
            "%s_%s" % (disk.get_alias(), config.TESTNAME)
        )
        ll_disks.updateDisk(
            True, vmName=vm_name, id=disk.get_id(),
            alias=new_vm_disk_name
        )
    testflow.setup("Creating files on disks")
    assert create_files_on_vm_disks(vm_name, storage_type), (
        "Failed to create files on vm's disks"
    )
    config.DISKS_BEFORE_COPY = ll_disks.get_non_ovf_disks()


def create_files_on_vm_disks(vm_name, storage_type):
    """
    Files will be created on vm's disks with name:
    'test_file_<iteration_number>'
    """
    if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
        assert ll_vms.startVm(
            True, vm_name, config.VM_UP, wait_for_ip=True
        )
    config.CHECKSUM_FILES[storage_type] = dict()
    vm_executor = storage_helpers.get_vm_executor(vm_name)
    for mount_dir in config.MOUNT_POINTS[storage_type]:
        logger.info("Creating file in %s", mount_dir)
        full_path = os.path.join(mount_dir, config.TEST_FILE_TEMPLATE)
        rc = storage_helpers.create_file_on_vm(
            vm_name, config.TEST_FILE_TEMPLATE, mount_dir, vm_executor
        )
        if not rc:
            logger.error(
                "Failed to create file test_file_%s under %s on vm %s",
                mount_dir, vm_name
            )
            return False
        if not storage_helpers.write_content_to_file(
            vm_name, full_path, vm_executor=vm_executor
        ):
            logger.error(
                "Failed to write content to file %s on vm %s",
                full_path, vm_name
            )
            return False
        config.CHECKSUM_FILES[storage_type][full_path] = (
            storage_helpers.checksum_file(
                vm_name, full_path, vm_executor
            )
        )
    vm_executor.run_cmd(shlex.split(config.SYNC_CMD))
    return True


def check_file_existence(
    vm_name, file_name=config.TEST_FILE_TEMPLATE, should_exist=True,
    storage_type=None
):
    """
    Determines whether file exists on mounts
    """
    ll_vms.start_vms(
        [vm_name], 1, wait_for_status=config.VM_UP, wait_for_ip=True
    )
    result_list = []
    state = not should_exist
    vm_executor = storage_helpers.get_vm_executor(vm_name)
    # For each mount point, check if the corresponding file exists
    for mount_dir in config.MOUNT_POINTS[storage_type]:
        full_path = os.path.join(mount_dir, file_name)
        testflow.step("Checking if file %s exists", full_path)
        result = storage_helpers.does_file_exist(
            vm_name, full_path, vm_executor
        )
        logger.info(
            "File %s %s",
            file_name, 'exists' if result else 'does not exist'
        )
        if should_exist and not result:
            return False
        if result:
            checksum = storage_helpers.checksum_file(
                vm_name, full_path, vm_executor
            )
            if checksum != config.CHECKSUM_FILES[storage_type][full_path]:
                logger.error(
                    "File exists but it's content changed since it's "
                    "creation!"
                )
                result = False
        result_list.append(result)

    if state in result_list:
        return False
    return True
