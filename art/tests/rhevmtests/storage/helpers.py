"""
Storage helper functions
"""
import logging
import shlex
from utilities.machine import Machine
from art.rhevm_api.tests_lib.low_level.disks import (
    waitForDisksState, attachDisk, addDisk, get_all_disk_permutation,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    getStorageDomainObj,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    get_vm_disk_logical_name, stop_vms_safely, get_vm_snapshots,
    removeSnapshot, activateVmDisk, waitForIP,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler import exceptions
from rhevmtests.storage import config

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 250
SNAPSHOT_TIMEOUT = 15 * 60
DD_TIMEOUT = 30
DD_COMMAND = 'dd if=/dev/urandom of=%s'

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

    __author__ = "glazarov"
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
            "description": disk_description,
            "description_orig": disk_description
        })
        assert addDisk(True, alias=disk_alias, description=disk_description,
                       size=size, interface=disk_permutation['interface'],
                       sparse=disk_permutation['sparse'],
                       format=disk_permutation['format'],
                       storagedomain=domain_to_use, bootable=False)
        assert waitForDisksState(disk_alias)
    return lst_aliases_and_descriptions


def perform_dd_to_disk(vm_name, disk_alias, protect_boot_device=True):
    """
    Function that performs dd command from urandom to the requested disk (by
    alias)
    **** Important note: Guest Agent must be installed in the OS for this
    function to work ****

    __author__ = "glazarov"
    :param vm_name: name of the vm which which contains the disk on which
    the dd should be performed
    :type: str
    :param disk_alias: The alias of the disk on which the dd operations will
    occur
    :type disk_alias: str
    :param protect_boot_device: True if boot device should be protected and
    writing to this device ignored, False if boot device should be
    overwritten (use with caution!)
    : type protect_boot_device: bool
    :returns: ecode and output
    :rtype: int, str
    """
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=config.VM_USER,
                         password=config.VM_PASSWORD).util('linux')
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'

    disk_logical_volume_name = get_vm_disk_logical_name(vm_name, disk_alias)
    logger.info("The logical volume name for the requested disk is: '%s'",
                disk_logical_volume_name)
    if protect_boot_device:
        if disk_logical_volume_name == boot_disk:
            logger.warn("perform_dd_to_disk function aborted since the "
                        "requested disk alias translates into the boot "
                        "device, this would overwrite the OS")
            # TODO: Need to return an error code here
            return

    command = DD_COMMAND % disk_logical_volume_name
    logger.info("Performing command '%s'", command)

    ecode, out = vm_machine.runCmd(shlex.split(command), timeout=DD_TIMEOUT)

    return ecode, out


def get_vm_ip(vm_name):
    """
    Get vm ip by name

    __author__ = "ratamir"
    :param vm_name: vm name
    :type: str
    :return: ip address of a vm, or raise EntityNotFound exception
    :rtype: str or EntityNotFound exception
    """
    return waitForIP(vm_name)[1]['ip']
