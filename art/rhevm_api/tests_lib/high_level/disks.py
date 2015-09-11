import logging
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level.disks import get_all_disk_permutation,\
    addDisk

logger = logging.getLogger(__name__)

# Polling interval
SLEEP_TIME = 10
# Waiting timeout
DEFAULT_TIMEOUT = 180
GB = 1024 ** 3
DISK_SIZE = 6 * GB


def delete_disks(disks_names, timeout=DEFAULT_TIMEOUT, sleep=SLEEP_TIME):
    """
    Wait until disks states is OK, delete disks and wait until all disks gone

    :param disks_names: list of disk names
    :type disks_names: list
    :param timeout: how long it should wait(by default 180 seconds)
    :type timeout: int
    :param sleep: how often it should poll the state(by default 10 seconds)
    :type sleep: int
    :returns : True, if method was succeeded, else False
    :rtype: bool
    """
    if not disks_names:
        return False
    logger.info("Wait until disks state is OK")
    if not disks.wait_for_disks_status(
            disks_names, timeout=timeout, sleep=sleep
    ):
        return False
    for disk in disks_names:
        logger.info("Delete disk %s", disk)
        if not disks.deleteDisk(True, disk):
            logging.error("Delete disk %s failed", disk)
            return False
    return disks.waitForDisksGone(True, disks_names, timeout, sleep)


def add_new_disk(sd_name, size, block, shared=False, **kwargs):
    """
    Add a new disk
    Parameters:
        * sd_name - disk wil added to this sd
        * shared - True if the disk should e shared
        * kwargs:
            * interface - ENUMS['interface_virtio'] or
                          ENUMS['interface_virtio_scsi']
            * sparse - True if thin, False preallocated
            * disk_format - 'cow' or 'raw'
    """
    disk_args = {
        # Fixed arguments
        'provisioned_size': size,
        'wipe_after_delete': block,
        'storagedomain': sd_name,
        'bootable': False,
        'shareable': shared,
        'active': True,
        'size': size,
        # Custom arguments - change for each disk
        'format': kwargs['format'],
        'interface': kwargs['interface'],
        'sparse': kwargs['sparse'],
        'alias': "%s_%s_%s_disk" %
                 (kwargs['interface'],
                  kwargs['format'],
                  kwargs['sparse'])}

    assert addDisk(True, **disk_args)
    return disk_args['alias']


def create_all_legal_disk_permutations(
        sd_name, shared=False, block=False, size=DISK_SIZE,
        interfaces=None
):
    """
    Begins asynchronous creation of disks of all permutations
    interfaces, formats and allocation policies

    __author__ = "ratamir"
    :param sd_name: Name of storage domain under which the disks should created
    :type sd_name: str
    :param shared: Determines whether the disks should be created as Shareable
    (if True)
    :type shared: bool
    :param block: Use block storage type (if True), use File based storage
    (if False)
    :type block: bool
    :param size: The disk size to be used (for all disks created)
    :type size: int
    :param interfaces: List of interfaces to be used in generating the disks
    permutations
    :type interfaces: list
    :returns: List of the disk aliases created
    :rtype: list
    """
    disks_names = []
    logger.info("Creating all disks")
    disk_permutations = get_all_disk_permutation(
        block=block, shared=shared, interfaces=interfaces
    )
    for permutation in disk_permutations:
        name = add_new_disk(
            sd_name, size, block, shared=shared, **permutation
        )
        disks_names.append(name)
    return disks_names
