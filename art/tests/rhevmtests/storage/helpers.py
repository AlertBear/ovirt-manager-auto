"""
Storage helper functions
"""
import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState, attachDisk, addDisk,
    get_all_disk_permutation,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainObj,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    stop_vms_safely, get_vm_snapshots, removeSnapshot, activateVmDisk,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler import exceptions
from rhevmtests.storage import config

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 250
SNAPSHOT_TIMEOUT = 15 * 60

disk_args = {
    # Fixed arguments
    'provisioned_size': config.DISK_SIZE,
    'wipe_after_delete': config.BLOCK_FS,
    'storagedomain': config.SD_NAMES_LIST[0],
    'bootable': False,
    'shareable': False,
    'active': True,
    'interface': config.VIRTIO,
    # Custom arguments - change for each disk
    'format': config.COW_DISK,
    'sparse': True,
    'alias': '',
    'description': '',
}


def prepare_disks_for_vm(vm_name, disks_to_prepare, read_only=False):
    """
    Adding disks, Attach disks to vm, and activate them
    Parameters:
        * vm_name - name of vm which disk should attach to
        * disks_to_prepare - list of disks aliases
        * read_only - if the disks should attach as RO disks
    Return: True if ok, or raise DiskException otherwise
    """
    is_ro = 'Read Only' if read_only else 'Read Write'
    for disk in disks_to_prepare:
        disk_args['alias'] = disk
        disk_args['description'] = '%s_description' % disk
        assert addDisk(positive=True, **disk_args)
        waitForDisksState(disk, timeout=DISK_TIMEOUT)
        logger.info("Attaching disk %s as %s disk to vm %s",
                    disk, is_ro, vm_name)
        status = attachDisk(True, disk, vm_name, active=False,
                            read_only=read_only)
        if not status:
            raise exceptions.DiskException("Failed to attach disk %s to"
                                           " vm %s"
                                           % (disk, vm_name))

        logger.info("Plugging disk %s", disk)
        status = activateVmDisk(True, vm_name, disk)
        if not status:
            raise exceptions.DiskException("Failed to plug disk %s "
                                           "to vm %s"
                                           % (disk, vm_name))
        wait_for_jobs()
    return True


def remove_all_vm_test_snapshots(vm_name, description):
    """
    Description: Removes all snapshots with given description from a given VM
    Author: ratamir
    Parameters:
    * vm_name - name of the vm that should be cleaned out of snapshots
    * description - snapshot description
    Raise: AssertionError if something went wrong
    """
    logger.info("Removing all '%s'", description)
    stop_vms_safely([vm_name])
    snapshots = get_vm_snapshots(vm_name)
    results = [removeSnapshot(True, vm_name, description, SNAPSHOT_TIMEOUT)
               for snapshot in snapshots
               if snapshot.get_description() == description]
    wait_for_jobs(timeout=SNAPSHOT_TIMEOUT)
    assert False not in results


def create_disks_from_requested_permutations(domain_to_use,
                                             interfaces=(config.VIRTIO,
                                                         config.VIRTIO_SCSI),
                                             size=config.DISK_SIZE):
    """
    Generates a list of permutations for disks using virtio, virtio-scsi and
    ide using thin-provisioning and pre-allocated options

    :param domain_to_use: the storage domain on which to create the disks
    :type domain_to_use: str
    :param interfaces: list of interfaces to use in generating the disks.
    Default is (VIRTIO, VIRTIO_SCSI)
    :type interfaces: list
    :param size: the disk size (in bytes) to create, uses config.DISK_SIZE as a
    default
    :type size: str
    :returns: list of the disk aliases and descriptions
    :rtype: list
    """
    logger.info("Generating a list of disk permutations")
    # Get the storage domain object and its type, use this to ascertain
    # whether the storage is of a block or file type
    storage_domain_object = getStorageDomainObj(domain_to_use)
    storage_type = storage_domain_object.get_storage().get_type()
    is_block = storage_type in config.BLOCK_TYPES
    disk_permutations = get_all_disk_permutation(block=is_block,
                                                 shared=False,
                                                 interfaces=interfaces)
    # Provide a warning in the logs when the total number of disk
    # permutations is 0
    if len(disk_permutations) == 0:
        logger.warn("The number of disk permutations is 0")
    # List of the disk aliases and descriptions that will be returned when
    # the function completes execution
    lst_aliases_and_descriptions = []

    logger.info("Create disks for all permutations generated previously")
    for index, disk_permutation in enumerate(disk_permutations):
        disk_alias = "%s_%s_sparse-%s_alias" % (disk_permutation['interface'],
                                                disk_permutation['format'],
                                                disk_permutation['sparse'])
        disk_description = disk_alias.replace("_alias", "_description")
        lst_aliases_and_descriptions.append({
            "alias": disk_alias,
            "description": disk_description
        })
        assert addDisk(True, alias=disk_alias, description=disk_description,
                       size=size, interface=disk_permutation['interface'],
                       sparse=disk_permutation['sparse'],
                       format=disk_permutation['format'],
                       storagedomain=domain_to_use, bootable=False)
        assert waitForDisksState(disk_alias)
    return lst_aliases_and_descriptions
