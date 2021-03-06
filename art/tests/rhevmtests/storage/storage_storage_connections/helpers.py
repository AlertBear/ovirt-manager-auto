import logging
import config
from art.test_handler import exceptions
import rhevmtests.helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers
logger = logging.getLogger(__name__)
MNT_POINT1 = '/tmp/mnt_point1'
MNT_POINT2 = '/tmp/mnt_point2'


def copy_posix_sd(
    addr_from, path_from, addr_to, path_to, host, user, passwd, vfs_type
):
    machine = rhevm_helpers.get_host_resource(host, passwd, user)
    src_from = "%s:%s" % (addr_from, path_from)
    src_to = "%s:%s" % (addr_to, path_to)
    opts = ['-t', vfs_type]

    mnt_point_1 = machine.nfs.mount(src_from, MNT_POINT1, opts=opts)
    mnt_point_2 = machine.nfs.mount(src_to, MNT_POINT2, opts=opts)
    logger.info("Copying data")
    rc, out, err = machine.run_command(
        ['cp', '-r', '-p', "%s/*" % mnt_point_1, mnt_point_2]
    )

    logger.debug(out)
    try:
        if rc:
            raise exceptions.StorageDomainException(
                "Failed to copy storage domain content to new location"
            )
    finally:
        machine.nfs.umount(MNT_POINT1)
        machine.nfs.umount(MNT_POINT2)


def logout_from_all_iscsi_targets():
    """
    Logout from all the targets used in the test
    """
    executor = rhevm_helpers.get_host_executor(
        ip=config.HOST_FOR_MOUNT_IP, password=config.HOSTS_PW
    )
    storage_helpers.logout_iscsi_sessions(executor)
