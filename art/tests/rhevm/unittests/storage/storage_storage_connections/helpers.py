import logging

from utilities.machine import Machine
import config


LOGGER = logging.getLogger(__name__)


class ChangeVdsmPermissions(object):
    def __init__(self, machine, password):
        self.machine = machine
        self.password = password

    def __enter__(self):
        ecode, out = self.machine.runCmd(
            ['echo', self.password, '|', 'passwd', 'vdsm', '--stdin'])
        LOGGER.debug(out)
        assert ecode
        ecode, out = self.machine.runCmd(
            ['usermod', '--shell', '/bin/bash', 'vdsm'])
        LOGGER.debug(out)
        assert ecode

    def __exit__(self, type, value, traceback):
        ecode, out = self.machine.runCmd(
            ['usermod', '--shell', '/sbin/nologin', 'vdsm'])
        LOGGER.debug(out)
        assert ecode


def get_user_and_passwd_for_host(host):
    for (tmp_host, password) in zip(
            config.HOSTS, config.PASSWORDS):
        if tmp_host == host:
            return 'root', password
    return None, None


def copy_nfs_sd(addr_from, path_from, addr_to, path_to, host, user, passwd):
    copy_posix_sd(
        addr_from, path_from, addr_to, path_to, host, user, passwd, 'nfs')


def copy_posix_sd(
        addr_from, path_from, addr_to, path_to, host, user, passwd, vfs_type):
    machine = Machine(host=host, user=user, password=passwd).util('linux')
    password = 'sth_random'
    src_from = "%s:%s" % (addr_from, path_from)
    src_to = "%s:%s" % (addr_to, path_to)
    opts = ['-t', vfs_type]

    with machine.mount(src_from, opts=opts) as mnt_point_1:
        with machine.mount(src_to, opts=opts) as mnt_point_2:
            with ChangeVdsmPermissions(machine, password) as vdsm:
                LOGGER.info("Copying data")
                vdsm_conn = Machine(
                    host=host, user='vdsm',
                    password=password).util('linux')
                rc, out = vdsm_conn.runCmd(
                    ['cp', '-r', "%s/*" % mnt_point_1, mnt_point_2])
                LOGGER.debug(out)
                assert rc


def copy_local_sd(dir_from, dir_to, machine):
    ecode, out = machine.runCmd(["cp", "-r", "%s/*" % dir_from, dir_to])
    LOGGER.debug(out)
    assert ecode

    ecode, out = machine.runCmd(["chown", "-R", "36:36", dir_to])
    LOGGER.debug(out)
    assert ecode


def clean_posix_domain(addr, path, sd_id, host, user, passwd, vfs_type):
    machine = Machine(host=host, user=user, password=passwd).util('linux')
    password = 'sth_random'
    src = "%s:%s" % (addr, path)
    opts = ['-t', vfs_type]

    with machine.mount(src, opts=opts) as mnt_point:
        with ChangeVdsmPermissions(machine, password) as vdsm:
            LOGGER.info("Copying data")
            vdsm_conn = Machine(
                host=host, user='vdsm', password=password).util('linux')
            rc, out = vdsm_conn.runCmd(
                ['rm', '-rf', "%s/%s" % (mnt_point, sd_id)])
            LOGGER.info(out)
            assert rc


def clean_nfs_domain(addr, path, sd_id, host, user, passwd):
    clean_posix_domain(addr, path, sd_id, host, user, passwd, 'nfs')
