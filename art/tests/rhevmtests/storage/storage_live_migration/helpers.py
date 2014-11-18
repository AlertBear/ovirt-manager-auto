"""
Live Storage Migration test helpers functions
"""
import config
import logging
from art.rhevm_api.tests_lib.low_level.disks import (
    wait_for_disks_status, addDisk, get_all_disk_permutation,
)
from art.test_handler import exceptions
from rhevmtests.storage.helpers import prepare_disks_for_vm

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS

DISK_NAMES = dict()
DISK_TIMEOUT = 250

DD_TIMEOUT = 1500
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
FILTER = '[sv]d'
READ_ONLY = 'Read-only'
NOT_PERMITTED = 'Operation not permitted'


def add_new_disk(sd_name, permutation, sd_type, shared=False):
    """
    Add a new disk

    :param sd_name: storage domain where a new disk will be added
    :type sd_name: str
    :param permutations:
            * interface - VIRTIO or VIRTIO_SCSI
            * sparse - True if thin, False if preallocated
            * disk_format - 'cow' or 'raw'
    :type permutations: dict
    :param sd_type: type of the storage domain (nfs, iscsi, ...)
    :type sd_type: str
    :param shared: True if the disk should be shared
    :type shared: bool
    :returns: Nothing
    :rtype: None
    """
    if permutation.get('alias'):
        alias = permutation['alias']
    else:
        alias = "%s_%s_%s_%s_disk" % (
            permutation['interface'], permutation['format'],
            permutation['sparse'], sd_type
        )

    disk_args = {
        # Fixed arguments
        'provisioned_size': config.DISK_SIZE,
        'wipe_after_delete': sd_type in config.BLOCK_TYPES,
        'storagedomain': sd_name,
        'bootable': False,
        'shareable': shared,
        'active': True,
        'size': config.DISK_SIZE,
        # Custom arguments - change for each disk
        'format': permutation['format'],
        'interface': permutation['interface'],
        'sparse': permutation['sparse'],
        'alias': alias,
    }

    assert addDisk(True, **disk_args)
    DISK_NAMES[sd_type].append(alias)


def start_creating_disks_for_test(shared=False, sd_name=None,
                                  sd_type=None):
    """
    Begins asynchronous creation of disks of all permutations of disk
    interfaces, formats and allocation policies

    :param shared: Specifies whether disks should be shared
    :type shared: bool
    :param sd_name: name of the storage domain where the disks will be created
    :type sd_name: str
    :param sd_type: storage type of the domain where the disks will be created
    :type sd_type: str
    :returns: Nothing
    :rtype: None
    """
    global DISK_NAMES
    DISK_NAMES[sd_type] = list()
    logger.info("Disks: %s", DISK_NAMES)
    logger.info("Creating all disks")
    DISK_PERMUTATIONS = get_all_disk_permutation(
        block=sd_type in config.BLOCK_TYPES, shared=shared)
    for permutation in DISK_PERMUTATIONS:
        add_new_disk(sd_name=sd_name, permutation=permutation, shared=shared,
                     sd_type=sd_type)


def add_new_disk_for_test(vm_name, alias, provisioned_size=(1 * config.GB),
                          sparse=False, disk_format=config.RAW_DISK,
                          wipe_after_delete=False, attach=False,
                          sd_name=None):
            """
            Prepares disk for given vm
            """
            disk_params = {
                'alias': alias,
                'active': False,
                'provisioned_size': provisioned_size,
                'interface': config.VIRTIO,
                'format': disk_format,
                'sparse': sparse,
                'wipe_after_delete': wipe_after_delete,
                'storagedomain': sd_name,
            }

            if not addDisk(True, **disk_params):
                raise exceptions.DiskException(
                    "Can't create disk with params: %s" % disk_params)
            logger.info("Waiting for disk %s to be ok", alias)
            wait_for_disks_status([alias])
            if attach:
                prepare_disks_for_vm(vm_name, [alias])
