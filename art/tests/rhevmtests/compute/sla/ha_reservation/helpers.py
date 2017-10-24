"""
HA Reservation Test Helpers
"""
import logging
import shlex
from time import sleep

from rhevmtests.compute.sla.ha_reservation import config

logger = logging.getLogger(__name__)


def is_cluster_ha_safe():
    """
    Check if cluster is HA safe

    Returns:
        bool: True, if cluster is HA safe, otherwise False
    """
    fail_status = "fail to pass HA reservation check"
    command = "grep -c \"{0}\" {1}".format(
        fail_status, config.ENGINE_LOG
    )
    logger.info(
        "Check number of strings \"%s\" under engine log", fail_status
    )
    old_out = config.ENGINE_HOST.run_command(
        command=shlex.split(command)
    )[1]
    if not old_out:
        return False
    logger.info(
        "Waiting %d seconds until engine will update log",
        config.RESERVATION_TIMEOUT
    )
    sleep(config.RESERVATION_TIMEOUT)
    logger.info(
        "Check number of strings \"%s\" under engine log", fail_status
    )
    new_out = config.ENGINE_HOST.run_command(
        command=shlex.split(command)
    )[1]
    if not new_out:
        return False
    return int(old_out) == int(new_out)
