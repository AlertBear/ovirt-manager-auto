import logging
import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.test_handler.settings import ART_CONFIG
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
)

logger = logging.getLogger("art.hl_lib.disks")

# Polling interval
SLEEP_TIME = 10
# Waiting timeout
DEFAULT_TIMEOUT = 180
GB = 1024 ** 3
DISK_SIZE = 6 * GB
RHEVM_UTILS_ENUMS = ART_CONFIG['elements_conf']['RHEVM Utilities']


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
    if not ll_disks.wait_for_disks_status(
            disks_names, timeout=timeout, sleep=sleep
    ):
        return False
    for disk in disks_names:
        logger.info("Delete disk %s", disk)
        if not ll_disks.deleteDisk(True, disk):
            logging.error("Delete disk %s failed", disk)
            return False
    return ll_disks.waitForDisksGone(True, disks_names, timeout, sleep)


def add_new_disk(sd_name, size, block, shared=False, **kwargs):
    """
    Add a new disk
    Parameters:
        * sd_name - disk wil added to this sd
        * size - target device size (GB)
        * block - set whether it is block device True/False
        * shared - True if the disk should e shared
        * kwargs:
            * interface - ENUMS['interface_virtio'] or
                          ENUMS['interface_virtio_scsi']
            * sparse - True if thin, False preallocated
            * format - 'cow' or 'raw'
    """
    # Custom arguments
    disk_args = kwargs.copy()
    disk_args.setdefault('format', 'cow')
    disk_args.setdefault('interface', 'virtio')
    disk_args.setdefault('sparse', True)
    disk_args.setdefault(
        'alias', "%s_%s_%s_disk" % (
            disk_args['interface'],
            disk_args['format'],
            disk_args['sparse'],
        )
    )
    disk_args.update(
        {
            # Fixed arguments
            'provisioned_size': size,
            'wipe_after_delete': block,
            'storagedomain': sd_name,
            'bootable': False,
            'shareable': shared,
            'active': True,
        }
    )

    assert ll_disks.addDisk(True, **disk_args)
    return disk_args['alias']


@ll_general.generate_logs()
def unlock_disks(engine):
    """
    Update locked disks to unlocked, using DB query

    Args:
        engine (Engine) engine host

    Returns:
         str: query output
    """

    query = "update images set imagestatus=1 where imagestatus=2;"
    return engine.db.psql(query)


@ll_general.generate_logs()
def check_no_locked_disks(engine):
    """
    Check there are no disks in locked status, using DB query

    Args:
    engine (Engine): engine host

    Returns:
         bool: True is all disk are not locked, else False
    """
    query = "select imagestatus from images;"
    res = engine.db.psql(query)
    logger.info("images status %s", res)
    return not ['2'] in res
