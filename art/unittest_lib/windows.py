#!/usr/bin/python

import os
import logging

from contextlib import contextmanager
from tempfile import mkstemp
from utilities import machine  # TODO: get rid of utilities dependency
from utilities.timeout import TimeoutingSampler, TimeoutExpiredError

# Those are default user/pass I use in windows images located at glance
USER = 'Administrator'
PASSWORD = 'Heslo123'
DEFAULT_TIMEOUT = 300
DEFAULT_INTERVAL = 10
GT_ID = '{042CD13C-735D-4140-B146-D3F8263D7E4C}'


@contextmanager
def temp_data_file(data):
    """
    Description: Create a temp file and write data, tempfile is removed
                 when function finishes, use it with 'with statement'
    :param data: data to be written into tempfile
    :type data: str
    :returns: path to tempfile with data
    :rtype: str
    """
    fd, path = mkstemp()
    try:
        os.write(fd, data)
        yield path
    finally:
        os.close(fd)


def gt_install_answer_file(apps, platf):
    """
    Description: Create an aswer file for guest tools installation
    :param apps: application list to be installed
    :type apps: list of str
    :returns: installshiled answer file to unattended gt installation
    :rtype: str
    """
    return (
        '[InstallShield Silent]\n'
        'Version=v7.00\n'
        'File=Response File\n'
        '[File Transfer]\n'
        'OverwrittenReadOnly=NoToAll\n'
        '[{guest_tools_id}-DlgOrder]\n'
        'Dlg0={guest_tools_id}-SdWelcome-0\n'
        'Count=4\n'
        'Dlg1={guest_tools_id}-SdComponentTree-0\n'
        'Dlg2={guest_tools_id}-SdStartCopy2-0\n'
        'Dlg3={guest_tools_id}-SdFinishReboot-0\n'
        '[{guest_tools_id}-SdWelcome-0]\n'
        'Result=1\n'
        '[{guest_tools_id}-SdComponentTree-0]\n'
        'szDir=C:\\Program Files{platf}\\Redhat\\RHEV\\Tools\n'
        'Component-type=string\n'
        'Component-count={componentCount}\n'
        '{components}\n'
        'Result=1\n'
        '[{guest_tools_id}-SdStartCopy2-0]\n'
        'Result=1\n'
        '[{guest_tools_id}-SdFinishReboot-0]\n'
        'Result=1\n'
        'BootOption=0'
    ).format(
        componentCount=len(apps),
        guest_tools_id=GT_ID,
        platf=' (x86)' if platf == '64' else '',
        components='\n'.join([
            'Component-%s=%s' % (i, app) for i, app in enumerate(apps)
        ]),
    )


def gt_uninstall_answer_file():
    """
    Description: Create an aswer file for guest tools uninstallation
    :returns: installshiled answer file to unattended gt uninstallation
    :rtype: str
    """
    return (
        '[InstallShield Silent]\n'
        'Version=v7.00\n'
        'File=Response File\n'
        '[File Transfer]\n'
        'OverwrittenReadOnly=NoToAll\n'
        '[{guest_tools_id}-DlgOrder]\n'
        'Dlg0={guest_tools_id}-SdWelcomeMaint-0\n'
        'Count=3\n'
        'Dlg1={guest_tools_id}-MessageBox-0\n'
        'Dlg2={guest_tools_id}-SdFinishReboot-0\n'
        '[{guest_tools_id}-SdWelcomeMaint-0]\n'
        'Result=303\n'
        '[{guest_tools_id}-MessageBox-0]\n'
        'Result=6\n'
        '[{guest_tools_id}-SdFinishReboot-0]\n'
        'Result=1\n'
        'BootOption=0'
    ).format(
        guest_tools_id=GT_ID
    )


class WindowsGuest(object):
    """ Class for working with Guest Tools """
    APPS = [
        'Vioserial',
        'Spice_Agent',
        'Spice_Driver',
        'Network_Driver',
        'Agent_Driver',
        'USB_Driver',
        'SSO_Driver',
        'Viostor',
        'icon',
        'Balloon',
        'Vioscsi',
        'QemuGA',
    ]
    # TODO: change these when proper API of WinRM and wmi will be in ART
    TOOLS_CD_PATH = 'D:\\'
    WINDOWS_PATH = 'C:\\Windows\\'
    TOOLS_TMP_PATH = 'C:\\Windows\\Temp\\'
    INSTALL_LOG = '%sgt.log' % WINDOWS_PATH
    ANSWER_FILE = '%ssetup.iss' % WINDOWS_PATH
    TOOLS_EXE = 'RHEV-toolsSetup.exe'
    logger = logging.getLogger('guest')

    @property
    def platf(self):
        """ Get windows platf 64/86 """
        if self._platf is None:
            self._platf = self.vm.getSystemArchitecture()[1]
        return self._platf

    def __init__(self, ip, user=USER, password=PASSWORD):
        """
        Description: setup windows guest resources
        :param ip: ip of the windows guest
        :type ip: str
        :param user: windows user to login with
        :type user: str
        :param password: password of user
        :type password: str
        """
        super(WindowsGuest, self).__init__()
        self._platf = None
        self.user = user
        self.password = password
        self.ip = ip
        self.vm = machine.Machine(
            host=ip,
            user=user,
            password=password
        ).util('windows')

    def __wait_for_proccess(self, name):
        """
        Description: Wait until process finish
        :param name: proccess name
        :type name: str
        :returns: True if proccess was finished in timeout, False otherwise
        :rtype: boolean
        :raises: TimeoutExpiredError
        """
        for statusOk, _ in TimeoutingSampler(
            DEFAULT_TIMEOUT, DEFAULT_INTERVAL, self.vm.getPidByName, name
        ):
            if not statusOk:
                return True
        return False

    def get_all_products(self):
        """
        Description: return list of all products installed on windows machine
        :returns: list of installed products
        :rtype: list of str
        """
        return [product['Name'] for product in self.vm.getAllProducts()]

    def get_all_services(self):
        """
        Description: return dic of all services on windows machine
        :returns: dict of services info
        :rtype: dict of services info
        """
        return dict(
            (service['Name'], service) for service in self.vm.getAllServices()
        )

    def is_product_installed(self, product):
        """
        Description: Searches for product installed on guest.
        :param product: product name
        :type product: str
        :returns: True if product is installed, False otherwise
        :rtype: boolean
        """
        return self.vm.checkProductExist(product)

    def is_service_running(self, service):
        """
        Description: Check if service is running
        :param service: name of service
        :type service: str
        :returns: True if service is running False otherwise
        :rtype: boolean
        """
        serviceStat = self.vm.checkServiceRunningAndEnabled(service)
        return serviceStat['State'] == 'Running'

    def is_service_enabled(self, service):
        """
        Description: Check if service is enabled (autostarted)
        :param service: name of service
        :type service: str
        :returns: True if service is enabled False otherwise
        :rtype: boolean
        """
        serviceStat = self.vm.checkServiceRunningAndEnabled(service)
        return serviceStat['StartMode'] == 'Auto'

    def __run_setup_tool(self, answer_file):
        """
        Description: run setup tools with answer_file
        :returns: True if tools ran successfull, False otherwise
        :rtype: boolean
        """

        try:
            # Create answer file and copy it to windows machine
            with temp_data_file(answer_file) as tmp_file:
                ret = self.vm.copyFileTo(
                    tmp_file,
                    self.WINDOWS_PATH,
                    toFile='setup.iss'
                )
                self.logger.debug('Answer file content: %s', answer_file)
            # Copy installation program to disk C:
            ret, out = self.vm.runCmd(
                cmd='copy %s%s %s' % (
                    self.TOOLS_CD_PATH, self.TOOLS_EXE, self.TOOLS_TMP_PATH,
                ),
                wait=True,
            )
            # Run setup tool silently with answer file and wait to finish
            ret, out = self.vm.runCmd(
                cmd='%s%s /sms /s /f1%s /f2%s' % (
                    self.TOOLS_TMP_PATH,  self.TOOLS_EXE,
                    self.ANSWER_FILE, self.INSTALL_LOG
                ),
                wait=True,
            )
            self.__wait_for_proccess(self.TOOLS_EXE)
            self.logger.info("Setup tool successfully finished")
        except (IOError, TimeoutExpiredError) as e:
            self.logger.error("Setup tool failed: %s", e)
            self.logger.debug('Error', exc_info=True)
            return False
        finally:
            self.logger.debug(
                "Install shiled log file content: %s",
                self.vm.getFile(self.INSTALL_LOG)
            )
            # TODO: obtain log of win GT installetion

        return True

    def uninstall_guest_tools(self):
        """
        Description: silently uninstall guest tools
        :rtype: boolean
        """
        return self.__run_setup_tool(
            answer_file=gt_uninstall_answer_file()
        )

    def install_guest_tools(self, apps=APPS):
        """
        Description: silently install guest tools apps
        :param apps: list of names of apps to be installed, default ALL
        :type apps: list of str
        :returns: True if installation was successfull, False otherwise
        :rtype: boolean
        """
        return self.__run_setup_tool(
            answer_file=gt_install_answer_file(apps, self.platf)
        )

    def reboot_guest(self, wait=True):
        """
        Description: reboot guest
        :param wait: wait for host to reboot
        :type wait: boolean
        :returns: True if rebooting succeed and guest up and running
                  False if failed during rebooting proccess.
        :rtype: boolean
        """
        self.logger.info('Guest %s is going down for reboot', self.ip)
        self.vm.shutdown('-r -t 5')
        if not wait:
            return True

        try:
            for statusOk in TimeoutingSampler(
                DEFAULT_TIMEOUT, DEFAULT_INTERVAL, self.vm.isAlive, 1
            ):
                if not statusOk:
                    break
        except TimeoutExpiredError:
            self.logger.error(
                "Timeout expired while waiting for machine to reboot"
            )
            return False
        self.logger.info("Guest %s is down", self.ip)
        return self.wait_for_machine_ready()

    def wait_for_machine_ready(self):
        """
        Description: Wait for machine to be ready for work
        :returns: True if machine is ready, False if timeout expired
        :rtype: boolean
        """
        try:
            for statusOk in TimeoutingSampler(
                DEFAULT_TIMEOUT, DEFAULT_INTERVAL, self.vm.isAlive
            ):
                if statusOk:
                    break
            self.logger.debug("Machine is alive")
            for statusOk in TimeoutingSampler(
                DEFAULT_TIMEOUT, DEFAULT_INTERVAL, self.vm.isConnective
            ):
                if statusOk:
                    break
            self.logger.debug("WinRM is alive")
        except TimeoutExpiredError:
            self.logger.error(
                "Timeout expired while waiting for machine to be ready"
            )
            return False
        return True

if __name__ == '__main__':
    import sys
    w = WindowsGuest(sys.argv[1])
    print w.install_guest_tools()
