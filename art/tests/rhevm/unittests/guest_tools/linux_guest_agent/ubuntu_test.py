'''
Ubuntu guest agent test
'''
import config
import logging
import common
from nose.tools import istest
from art.test_handler.tools import tcms

eOS = config.eOS
package_manager = '/usr/bin/apt-get'
config_manager = '/usr/bin/add-apt-repository'
LOGGER = logging.getLogger(__name__)
NAME = config.AGENT_SERVICE_NAME


def setup_module():
    for os in [eOS.UBUNTU_14_04_64b]:
        machine = common.MyLinuxMachine(config.TEMPLATES[os]['ip'])
        repo_cmd = ['echo', "deb %s ./" % config.UBUNTU_REPOSITORY, '>>',
                    '/etc/apt/sources.list']
        res, out = machine.runCmd(repo_cmd, timeout=config.TIMEOUT)
        LOGGER.info('Guest agent repo enabled.')
        if not res:
            LOGGER.error("Fail to run cmd %s: %s", repo_cmd, out)
        gpg_cmd1 = ['gpg', '-v', '-a', '--keyserver',
                    '%sRelease.key' % config.UBUNTU_REPOSITORY,
                    '--recv-keys', 'D5C7F7C373A1A299']
        gpg_cmd2 = ['gpg', '--export', '--armor', '73A1A299', '|', 'apt-key',
                    'add', '-']
        res, out = machine.runCmd(gpg_cmd1, timeout=config.TIMEOUT)
        LOGGER.info('Gpg keys exported.')
        if not res:
            LOGGER.error("Fail to run cmd %s: %s", gpg_cmd1, out)
        res, out = machine.runCmd(gpg_cmd2, timeout=config.TIMEOUT)
        if not res:
            LOGGER.error("Fail to run cmd %s: %s", gpg_cmd2, out)

        LOGGER.info('Updating system...')
        assert common.runPackagerCommand(machine, package_manager, 'update')
        assert common.runPackagerCommand(machine, package_manager,
                                         'install', NAME)
        LOGGER.info('%s is istalled', NAME)
        LOGGER.info('Service started %s', machine.startService(NAME))
        config.TEMPLATES[os]['machine'] = machine


class UbuntuPostInstall(common.BasePostInstall):
    """ Ubuntu post install """
    __test__ = True
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343363)
    def post_install(self):
        """ Ubuntu rhevm-guest-agent post-install """
        super(UbuntuPostInstall, self).post_install()


class UbuntuInstallGA(common.BaseInstallGA):
    """ Ubuntu post install """
    __test__ = True
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343362)
    def install_guest_agent(self):
        """ Ubuntu rhevm-guest-agent install """
        super(UbuntuInstallGA, self).install_guest_agent()


class UbuntuUninstallGA(common.BaseUninstallGA):
    """ Ubuntu post install """
    __test__ = True
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343365)
    def uninstall_guest_agent(self):
        """ Ubuntu rhevm-guest-agent uninstall """
        self.package_manager = package_manager
        self.remove_command = 'purge'
        self.uninstall()


class UbuntuServiceTest(common.BaseServiceTest):
    """ Ubuntu post install """
    __test__ = True
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343364)
    def service_test(self):
        """ Ubuntu rhevm-guest-agent start-stop-restart-status """
        super(UbuntuServiceTest, self).service_test()


class UbuntuAgentData(common.BaseAgentData):
    """ Ubuntu post install """
    __test__ = True
    os = eOS.UBUNTU_14_04_64b
    list_app = ['dpkg', '--list']
    application_list = ['ovirt-guest-agent', 'linux-image',
                        'xserver-xorg-video-qxl']

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343359)
    def agent_data(self):
        """ Ubuntu rhevm-guest-agent data """
        super(UbuntuAgentData, self).agent_data()


class UbuntuAgentDataUpdate(common.BaseAgentDataUpdate):
    """ Ubuntu post install """
    __test__ = False
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343360)
    def agent_data_update(self):
        """ Ubuntu rhevm-guest-agent data update """
        super(UbuntuAgentDataUpdate, self).agent_data_update()


class UbuntuFunctionContinuity(common.BaseFunctionContinuity):
    """ Ubuntu post install """
    __test__ = False
    os = eOS.UBUNTU_14_04_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343361)
    def function_continuity(self):
        """ Ubuntu rhevm-guest-agent function continuity """
        super(UbuntuFunctionContinuity, self).function_continuity()
