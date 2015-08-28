'''
Ubuntu guest agent test
'''
import logging

from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import common, config

from nose.tools import istest

LOGGER = logging.getLogger(__name__)
NAME = 'ovirt-guest-agent'
DISK_NAME = 'ubuntu-12.04_Disk1'
package_manager = '/usr/bin/apt-get'


def setup_module():
    if config.TEST_IMAGES[DISK_NAME]['image']._is_import_success():
        machine = common.createMachine(DISK_NAME)
        config.TEST_IMAGES[DISK_NAME]['machine'] = machine
        res, out = machine.runCmd(
            cmd=[
                'echo',
                "deb %s ./" % config.UBUNTU_REPOSITORY, '>>',
                '/etc/apt/sources.list',
            ],
            timeout=config.TIMEOUT
        )
        assert res, out
        LOGGER.info('Guest agent repo enabled.')
        gpg_cmd1 = [
            'gpg', '-v', '-a', '--keyserver',
            '%sRelease.key' % config.UBUNTU_REPOSITORY,
            '--recv-keys', 'D5C7F7C373A1A299'
        ]
        gpg_cmd2 = [
            'gpg', '--export', '--armor', '73A1A299',
            '|', 'apt-key', 'add', '-'
        ]
        res, out = machine.runCmd(gpg_cmd1, timeout=config.TIMEOUT)
        assert res, "Fail to run cmd %s: %s" % (gpg_cmd1, out)
        LOGGER.info('Gpg keys exported.')
        res, out = machine.runCmd(gpg_cmd2, timeout=config.TIMEOUT)
        assert res, "Fail to run cmd %s: %s" % (gpg_cmd2, out)

        LOGGER.info('Updating system...')
        package_manager = config.TEST_IMAGES[DISK_NAME]['manager']
        assert common.runPackagerCommand(machine, package_manager, 'update')
        assert common.runPackagerCommand(
            machine, package_manager, 'install', NAME
        )
        LOGGER.info('%s is installed', NAME)
        LOGGER.info('Service started %s', machine.startService(NAME))


def teardown_module():
    ll_vms.removeVm(True, DISK_NAME, stopVM='true')


class UbuntuPostInstall(common.BasePostInstall):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9333")
    def post_install(self):
        """ Ubuntu rhevm-guest-agent post-install """
        super(UbuntuPostInstall, self).post_install()


class UbuntuInstallGA(common.BaseInstallGA):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9331")
    def install_guest_agent(self):
        """ Ubuntu rhevm-guest-agent install """
        super(UbuntuInstallGA, self).install_guest_agent()


class UbuntuUninstallGA(common.BaseUninstallGA):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9337")
    def uninstall_guest_agent(self):
        """ Ubuntu rhevm-guest-agent uninstall """
        self.remove_command = 'purge'
        self.uninstall()


class UbuntuServiceTest(common.BaseServiceTest):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9335")
    def service_test(self):
        """ Ubuntu rhevm-guest-agent start-stop-restart-status """
        super(UbuntuServiceTest, self).service_test()


class UbuntuAgentData(common.BaseAgentData):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'
    list_app = ['dpkg', '--list']
    application_list = ['ovirt-guest-agent', 'linux-image',
                        'xserver-xorg-video-qxl']

    @istest
    @polarion("RHEVM3-9325")
    def agent_data(self):
        """ Ubuntu rhevm-guest-agent data """
        super(UbuntuAgentData, self).agent_data()


class UbuntuAgentDataUpdate(common.BaseAgentDataUpdate):
    """ Ubuntu post install """
    __test__ = False
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9328")
    def agent_data_update(self):
        """ Ubuntu rhevm-guest-agent data update """
        super(UbuntuAgentDataUpdate, self).agent_data_update()


class UbuntuFunctionContinuity(common.BaseFunctionContinuity):
    """ Ubuntu post install """
    __test__ = False
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @polarion("RHEVM3-9330")
    def function_continuity(self):
        """ Ubuntu rhevm-guest-agent function continuity """
        super(UbuntuFunctionContinuity, self).function_continuity()
