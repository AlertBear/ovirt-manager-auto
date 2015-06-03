'''
Ubuntu guest agent test
'''
import logging
from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common
from nose.tools import istest
from art.test_handler.tools import tcms  # pylint: disable=E0611

LOGGER = logging.getLogger(__name__)
NAME = 'ovirt-guest-agent'


class UbuntuPostInstall(common.BasePostInstall):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343363)
    def post_install(self):
        """ Ubuntu rhevm-guest-agent post-install """
        super(UbuntuPostInstall, self).post_install()


class UbuntuInstallGA(common.BaseInstallGA):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343362)
    def install_guest_agent(self):
        """ Ubuntu rhevm-guest-agent install """
        super(UbuntuInstallGA, self).install_guest_agent()


class UbuntuUninstallGA(common.BaseUninstallGA):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343365)
    def uninstall_guest_agent(self):
        """ Ubuntu rhevm-guest-agent uninstall """
        self.remove_command = 'purge'
        self.uninstall()


class UbuntuServiceTest(common.BaseServiceTest):
    """ Ubuntu post install """
    __test__ = True
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343364)
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
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343359)
    def agent_data(self):
        """ Ubuntu rhevm-guest-agent data """
        super(UbuntuAgentData, self).agent_data()


class UbuntuAgentDataUpdate(common.BaseAgentDataUpdate):
    """ Ubuntu post install """
    __test__ = False
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343360)
    def agent_data_update(self):
        """ Ubuntu rhevm-guest-agent data update """
        super(UbuntuAgentDataUpdate, self).agent_data_update()


class UbuntuFunctionContinuity(common.BaseFunctionContinuity):
    """ Ubuntu post install """
    __test__ = False
    disk_name = 'ubuntu-12.04_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_UBUNTU, 343361)
    def function_continuity(self):
        """ Ubuntu rhevm-guest-agent function continuity """
        super(UbuntuFunctionContinuity, self).function_continuity()
