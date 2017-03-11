import logging
import random
import shlex
import os

from art.rhevm_api import resources
from art.rhevm_api.tests_lib.low_level import hosts


logger = logging.getLogger(__name__)

LV_CHANGE_CMD = 'lvchange -a {active} {vg_name}/{lv_name}'
PVSCAN_CACHE_CMD = 'pvscan --cache'
PVSCAN_CMD = 'pvscan'
DEFAULT_MNT_DIR = "/tmp/mnt_point"
VDC_ROOT_USER = "root"
VDC_ROOT_PASS = "qum5net"


def get_host_resource(host_name):
    """
    Takes the host name and returns the Host resource on which commands can be
    executed

    :param host_name: Name of the host
    :type host_name: str
    :return: Host resource on which commands can be executed
    :rtype: Host resource
    """
    host_obj = hosts.get_host_object(host_name)
    host = resources.Host(host_obj.get_address())
    host.users.append(resources.User(VDC_ROOT_USER, VDC_ROOT_PASS))
    return host


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
    if target is None:
        target = '%s_%s' % (DEFAULT_MNT_DIR, random.randint(1, 1000))

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


def clean_mount_point(host, src_ip, src_path, opts=None):
    """
    Clean the directory of mount_point
    __author__ = khakimi
    :param host: Host name to use for mount and umount operations
    :type host: str
    :param src_ip: source ip address
    :type src_ip: str
    :param src_path: path to source.
                    to use them both such as: "src_ip:src_path"
    :type src_path: str
    :param opts: List of mount options such as: ['-tnfs', '-o', 'vers=3', '-v']
                 or in case of gluster storage: ['-tglusterfs', '-v']
    :type opts: list
    :return: True if clean mount point succeeded, False otherwise
    :rtype: bool
    """
    source = '%s:%s' % (src_ip, src_path)
    mnt_dir = mount(host, source, opts=opts)
    if mnt_dir:
        rm_cmd = ['rm', '-rfv', os.path.join(mnt_dir, '*')]
        host_machine = get_host_resource(host)
        logger.info('Clean the mount point %s', source)
        rc, out, _ = host_machine.run_command(rm_cmd)
        if out:
            logger.warning("The following files and folders deleted:\n%s", out)
        umount(host, mnt_dir)
    if not mnt_dir or rc:
        logger.error('Failed to clean the mount point %s', source)
        return False
    return True
