#!/usr/bin/python

"""
Windows helper
"""

import os
import logging
import winrm
from tempfile import mkstemp
from winremote import winremote
from contextlib import contextmanager
from winremote.modules import (
    devices,
    files,
    products,
    services,
    system
)
import config

logger = logging.getLogger(__name__)


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
    def __init__(self, ip, user=config.WIN_USER, password=config.WIN_PASSWORD):
        """
        Connect to windows machine,
        Initialize: windows session, power shell

        Args:
            ip (str): ip of the windows guest
            user (str): windows user to login with
            password (str): password of user
        """
        super(WindowsGuest, self).__init__()
        self.user = user
        self.password = password
        self.ip = ip
        _session = winrm.Session(
            target=ip,
            auth=(user, password),
        )
        self.win = winremote.Windows(_session, winremote.WMI(_session))
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
        status, std_out, std_err = self.win.run_cmd(cmd=cmd, params=params)
        if status:
            return ""
        logging.info("Output:\n", std_out)
        return std_out

    def seal_vm(self):
        """
        Run seal command on VM, the VM will be down after sealing done

        Returns:
            bool: True if seal success, else False
        """
        status, _, std_err = self.run_command(config.SEAL_COMMAND)
        if status:
            logging.error(std_err)
            return False
        return True

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
