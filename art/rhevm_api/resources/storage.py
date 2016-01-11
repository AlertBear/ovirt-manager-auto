import logging
import random
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
    :return: Host resource on which commands can be executed
    :rtype: Host resource
    """
    host_obj = hosts.get_host_object(host_name)
    return resources.Host.get(host_obj.get_address())


def lvchange(host_name, vg_name, lv_name, activate=True):
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


def pvscan(host):
    """
    Execute 'pvscan' in order to get the current list of physical volumes

    __author__ = "ratamir"
    :returns: True if the pvscan command succeded, False otherwise
    :rtype: bool
    """
    # Execute 'pvscan --cache' in order to get the latest list of volumes.
    # In case no data is returned (equivalent to no changes), run 'pvscan' by
    # itself. This combination appears to correctly retrieve the latest
    # volume listing
    host_machine = get_host_resource(host)
    logger.info("Executing '%s' command", PVSCAN_CACHE_CMD)
    rc, output, error = host_machine.run_command(shlex.split(PVSCAN_CACHE_CMD))
    if rc:
        logger.error(
            "Error while executing the '%s' command, output is '%s', "
            "error is '%s'", PVSCAN_CACHE_CMD, output, error
        )
        return False

    if output == '':
        logger.info("Executing '%s' command", PVSCAN_CMD)
        rc, output, error = host_machine.run_command(shlex.split(PVSCAN_CMD))
        if rc:
            logger.error(
                "Error while executing the '%s' command, output is '%s', "
                "error is '%s'", PVSCAN_CMD, output, error
            )
            return False
    return True


def mount(host, source, target=None, opts=None):
    """
    Mounts source to target mount point

    __author__ = "ratamir"
    :param host: Host name to use for mount operation
    :type host: str
    :param source: Full path to source
    :type source: str
    :param target: Path to target directory, if omitted, a temporary
    folder is created instead
    :type target: str
    :param opts: List of mount options such as:
    ['-t', 'nfs', '-o', 'vers=3']
    :type opts: list
    :return: Path to mount point if succeeded, None otherwise
    :rtype: str
    """
    host_machine = get_host_resource(host)
    target = (
        '/tmp/mnt_point_%s' % random.randint(1, 1000)
    ) if target is None else target

    cmd = ['mkdir', '-p', target]
    logger.info(
        "Creating directory %s to use as a mount point", target
    )
    rc, out, err = host_machine.run_command(cmd)
    if rc:
        logger.error(
            "Failed to create a directory to be used as a mount point "
            "for %s. Output: %s, Error: %s ", source, out, err
        )
        return None

    cmd = ['mount', source, target]
    if opts:
        cmd.extend(opts)
    rc, out, err = host_machine.run_command(cmd)
    if rc:
        logger.error(
            "Failed to mount source %s to target %s. Output: %s",
            source, target, out
        )
        return None
    return target


def umount(host, mount_point, force=True, remove_mount_point=True):
    """
    Performs an 'umount' on input 'mount_point' directory, and
    optionally removes 'mount_point'

    __author__ = "ratamir"
    :param host: Host name to use for mount operation
    :type host: str
    :param mount_point: Path to directory that should be unmounted
    :type mount_point: str
    :param force: True if the mount point should be forcefully removed
    (such as in the case of an unreachable NFS server)
    :type force: bool
    :param remove_mount_point: True if mount point should be deleted
    after 'umount' operation completes, False otherwise
    :type remove_mount_point: bool
    :return: True if umount operation and mount point removal
    succeeded, False otherwise
    :rtype: bool
    """
    host_machine = get_host_resource(host)
    cmd = ['umount', mount_point, '-v']
    if force:
        cmd.append('-f')
    rc, out, err = host_machine.run_command(cmd)
    if rc:
        logger.error(
            "Failed to umount directory: %s, output: %s, error: %s",
            mount_point, out, err
        )
        return False
    if remove_mount_point:
        rc = host_machine.fs.rmdir(mount_point)
        if not rc:
            logger.error("failed to remove directory %s", mount_point)
            return False
    return True
