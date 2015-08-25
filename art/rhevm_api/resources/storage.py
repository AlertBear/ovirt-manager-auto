import logging
import shlex

from art.rhevm_api import resources
from art.rhevm_api.tests_lib.low_level import hosts

logger = logging.getLogger(__name__)

LV_CHANGE_CMD = 'lvchange -a {active} {vg_name}/{lv_name}'
PVSCAN_CACHE_CMD = 'pvscan --cache'
PVSCAN_CMD = 'pvscan'


def get_host_resource(host_name):
    """
    Takes the host name and returns the Host resource on which commands can be
    executed

    __author__ = "glazarov"
    :param host_name: Name of the host
    :type host_name: str
    :return: host resource on which commands can be executed
    :rtype: Host resource
    """
    host_obj = hosts.get_host_object(host_name)
    return resources.Host.get(host_obj.get_address())


def lv_change(host_name, vg_name, lv_name, activate=True):
    """
    Set the LV attribute 'active' (active or inactive)

    __author__ = "ratamir, glazarov"
    :param host_name: The host to use for setting the Logical volume state
    :type host_name: str
    :param vg_name: The name of the Volume group under which LV is contained
    :type vg_name: str
    :param lv_name: The name of the logical volume which needs to be
    activated or deactivated
    :type lv_name: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    active = 'y' if activate else 'n'
    host = get_host_resource(host_name)

    logger.info("Setting the logical volume 'active=%s' attribute", activate)
    rc, output, error = host.executor().run_cmd(
        shlex.split(LV_CHANGE_CMD.format(
            active=active, vg_name=vg_name, lv_name=lv_name)
        )
    )
    if rc:
        logger.error(
            "Error while setting the logical volume 'active=%s' attribute. "
            "Output is '%s', error is '%s'", activate, output, error
        )
        return False
    return True


def run_pvscan_command(host_name):
    """
    Executes pvscan on the input host

    __author__ = "ratamir, glazarov"
    :param host_name: The host to use for executing the pvscan command
    :type host_name: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    # Execute 'pvscan --cache' in order to get the latest list of volumes.
    # In case no data is returned (equivalent to no changes), run 'pvscan' by
    # itself. This combination appears to correctly retrieve the latest
    # volume listing
    host = get_host_resource(host_name)

    logger.info("Executing '%s' command", PVSCAN_CACHE_CMD)
    rc, output, error = host.executor().run_cmd(shlex.split(PVSCAN_CACHE_CMD))
    if rc:
        logger.error(
            "Error while executing the '%s' command, output is '%s', "
            "error is '%s'", PVSCAN_CACHE_CMD, output, error
        )
        return False

    if output == '':
        logger.info("Executing '%s' command", PVSCAN_CMD)
        rc, output, error = host.executor().run_cmd(shlex.split(PVSCAN_CMD))
        if rc:
            logger.error(
                "Error while executing the '%s' command, output is '%s', "
                "error is '%s'", PVSCAN_CMD, output, error
            )
            return False
    return True
