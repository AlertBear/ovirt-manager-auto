import logging
import art.rhevm_api.tests_lib.low_level.disks as disks_api

logger = logging.getLogger(__name__)

# Polling interval
SLEEP_TIME = 10
# Waiting timeout
DEFAULT_TIMEOUT = 180


def delete_disks(disks_names, timeout=DEFAULT_TIMEOUT, sleep=SLEEP_TIME):
    """
    Wait until disks states is OK, delete disks and wait until all disks gone
    **Author**: alukiano

    **Parameters**:
        * *disks_names* - list of disks names(["name1", "name2" ...])
        * *timeout* - how long it should wait(by default 180 seconds)
        * *sleep* - how often it should poll the state(by default 10 seconds)
    **Returns**: True, if method was succeeded, else False
    """
    if not disks_api.waitForDisksState(disks_names, timeout=timeout,
                                       sleep=sleep):
        return False
    for disk in disks_names:
        if not disks_api.deleteDisk(True, disk):
            logging.error("Delete disk %s failed", disk)
            return False
    return disks_api.waitForDisksGone(True, disks_names, timeout, sleep)
