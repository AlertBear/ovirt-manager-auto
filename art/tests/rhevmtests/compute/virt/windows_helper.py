#!/usr/bin/python

"""
Windows helper
"""
import logging
import os
import shlex
from contextlib import contextmanager
from tempfile import mkstemp

import winrm
from winremote import winremote
from winremote.modules import (
    devices,
    files,
    products,
    services,
    system
)

import config
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler

logger = logging.getLogger(__name__)

USER_LIST_COMMAND = 'WMIC USERACCOUNT LIST BRIEF'


@contextmanager
def temp_data_file(data):
    """
    Create a temp file and write data, tempfile is removed
    when function finishes, use it with 'with statement'

    Args:
        data (str): data to be written into tempfile

    Returns:
        path (str): path to tempfile with data
    """
    fd, path = mkstemp()
    try:
        os.write(fd, data)
        yield path
    finally:
        os.close(fd)


class WindowsGuest(object):
    def __init__(
            self, ip, user=config.WIN_ADMIN_USER, password=config.WIN_PASSWORD,
            connectivity_check=False
    ):
        """
        Connect to windows machine,
        Initialize: windows session, power shell

        Args:
            ip (str): ip of the windows guest
            user (str): Windows user to login with
            password (str): Password of user
            connectivity_check (bool): Run command on remote server to check
                if connection establish.
        """
        super(WindowsGuest, self).__init__()
        self.user = user
        self.password = password
        self.ip = ip
        self.timeout = 600
        self.sleep = 30
        logger.info(
            "Create session to windows vm. IP:%s User name:%s, Password:%s",
            ip, user, password
        )
        _session = winrm.Session(target=ip, auth=(user, password))
        self.win = winremote.Windows(_session, winremote.WMI(_session))
        if connectivity_check:
            def check_connection():
                """
                Run command on remote vm to check if connection established
                and WinRM service is running
                """
                try:
                    _session.protocol.open_shell()
                    output = self.win.run_cmd(cmd="echo 'test'")
                except Exception, err:
                    logger.warning("Failed to connect: %s", err)
                    return None
                return output
            try:
                for check in TimeoutingSampler(
                    self.timeout, self.sleep, check_connection
                ):
                    if check:
                        logger.info("Connectivity check pass")
                        break
            except APITimeout:
                logger.error("Failed to connect to VM: %s", ip)
        self.shell_id = _session.protocol.open_shell()

    def run_command(self, cmd, params=list()):
        """
        Run command on windows

        Args:
            cmd (str): Command to run
            params (list): List of parameters for command

        Returns:
            str: Command output
        """
        logger.info("cmd: %s, params: %s", cmd, params)
        status, std_out, std_err = self.win.run_cmd(cmd=cmd, params=params)
        if not status:
            logging.error("ERR:%s\n", std_err)
            return ""
        logging.info("Output:%s\n", std_out)
        return std_out

    def seal_vm(self):
        """
        Run seal command on VM, the VM will be down after sealing done
        Connection to VM should drop after running command
        After running the command we should check the VM status
        """
        logger.info("Seal VM")
        try:
            _, _, err = self.win.run_cmd(cmd=config.SEAL_COMMAND, params=[])
        except Exception, err:
            logger.info("Connection to VM drop since sealing disconnect nic")
            logger.info("ERR: %s", err)

    def get_all_products(self):
        """
        Return list of all products installed on windows machine

        Returns:
            list: List of installed products
        """
        return [
            product['Name'] for product in products.list(self.win)
            ]

    def get_all_services(self):
        """
        Return dic of all services on windows machine

        Returns:
            dict: directory of services info
        """
        return dict(
            (service['Name'], service)
            for service in services.list(self.win)
        )

    def get_device_info(self, name):
        """
        Fetch info from device manager about driver

        Args:
            name (str): name of driver to fetch info about

        Returns:
            dict: dictionary with device driver information
        """
        return devices.get(self.win, name, attributes='*')

    def reboot(self):
        """
        Reboot VM
        """
        system.reboot(self.win)

    def copy_file(
        self,
        file_content=config.DEFAULT_FILE_CONTENT,
        file_name=config.DEFAULT_FILE_NAME,
        dest_path=config.TMP_PATH
    ):
        """
        Copy file to windows, create local tmp file and copy it to remote VM

        Args:
            file_content(str): File content
            file_name (str): File name
            dest_path (str): Target destination to copy file

        Returns:
            bool: True is file copied Else False
        """
        try:
            target_file = '%s%s' % (dest_path, file_name)
            logging.info("Copy file to %s", target_file)
            with temp_data_file(file_content) as tmp_file:
                files.copy_remote(
                    session=self.win, src_path=tmp_file, dest_path=target_file
                )
        except IOError as e:
            logger.error("Failed to copy file: %s", e)
            return False
        return True

    def exist(self, path):
        """
        Check if file/directory exists

        Args:
            path (str): Path to file/directory

        Returns:
            bool: True if file/dir exists False otherwise
        """

        return files.exists(self.win, path=path)

    def get_system_info(self):
        """
        Return directory with system info

        Returns:
            dict: System info directory
        """
        system_info = {}
        system_info_data = self.run_command(cmd='systeminfo')
        lines = system_info_data.splitlines(False)
        for line in lines:
            if len(line) > 1:
                tmp = line.split(':', 1)
                if tmp[0].strip() in config.SYSTEM_INFO_NAMES:
                    system_info[tmp[0].strip()] = tmp[1].strip()
        logging.info("system info: %s", system_info)
        return system_info

    def get_users_list(self):
        """
        Get users list

        Returns:
            list: users list
        """

        user_list = []
        user_info = self.run_command(cmd=USER_LIST_COMMAND)
        lines = user_info.splitlines(False)
        for line in lines[2:]:
            if len(line) > 1:
                user_list.append(shlex.split(line)[3])
        logger.info("Users list: %s", user_list)
        return user_list
