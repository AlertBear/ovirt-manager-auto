"""
Test installation and uninstallation of guest agent on RHEL 5 32b/64b
"""
import logging

from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

from nose.tools import istest


LOGGER = logging.getLogger(__name__)
NAME = config.GA_NAME
RHEL5_APP_LIST = ['kernel', 'rhevm-guest-agent']
RHEL_CMD_LIST_APP = ['rpm', '-qa']
DISKx64_NAME = 'rhel5_x64_Disk1'
DISKx86_NAME = 'rhel5_x86_Disk1'


def setup_module():
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


def teardown_module():
    for image in [DISKx64_NAME, DISKx86_NAME]:
        vms.removeVm(True, image, stopVM='true')


class RHEL5x64Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7407")
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL5x64Install, self).install_guest_agent()


class RHEL5x64Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    package = NAME

    @istest
    @polarion("RHEVM3-7408")
    def uninstall_guest_agent(self):
        """ RHEL5_64b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package,
                                  '-x', 'rhevm-guest-agent-common')


class RHEL5x64PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @polarion("RHEVM3-7431")
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL5x64PostInstall, self).post_install()


class RHEL5x64ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7432")
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5x64ServiceTest, self).service_test()


class RHEL5x64AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL5_APP_LIST

    @istest
    @polarion("RHEVM3-7433")
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL5x64AgentData, self).agent_data()


class RHEL5x64AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7434")
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL5x64AgentData, self).agent_data_update()


class RHEL5x64FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL5_APP_LIST

    @istest
    @polarion("RHEVM3-7435")
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL5x64FunctionContinuity, self).function_continuity()


class RHEL5x86Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 5 32b '''
    __test__ = True
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7377")
    def install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        super(RHEL5x86Install, self).install_guest_agent()


class RHEL5x86Uninstall(common.BaseUninstallGA):
    ''' RHEL5_32b uninstall_guest_agent '''
    __test__ = True
    disk_name = DISKx86_NAME
    package = NAME

    @istest
    @polarion("RHEVM3-7406")
    def uninstall_guest_agent(self):
        """ RHEL5_32b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package,
                                  '-x', 'rhevm-guest-agent-common')


class RHEL5x86PostInstall(common.BasePostInstall):
    ''' RHEL5_32b rhevm-guest-agent post-install '''
    __test__ = True
    disk_name = DISKx86_NAME
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @polarion("RHEVM3-7425")
    def post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        super(RHEL5x86PostInstall, self).post_install()


class RHEL5x86ServiceTest(common.BaseServiceTest):
    ''' RHEL5_32b rhevm-guest-agent start-stop-restart-status '''
    __test__ = True
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7426")
    def service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5x86ServiceTest, self).service_test()


class RHEL5x86AgentData(common.BaseAgentData):
    ''' RHEL5_32b rhevm-guest-agent data '''
    __test__ = True
    disk_name = DISKx86_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL5_APP_LIST

    @istest
    @polarion("RHEVM3-7427")
    def agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        super(RHEL5x86AgentData, self).agent_data()


class RHEL5x86AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' RHEL5_32b, rhevm-guest-agent data update '''
    __test__ = False
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7428")
    def agent_data_update(self):
        """ RHEL5_32b, rhevm-guest-agent data update """
        super(RHEL5x86AgentData, self).agent_data_update()


class RHEL5x86FunctionContinuity(common.BaseFunctionContinuity):
    ''' RHEL5_32b, rhevm-guest-agent function continuity '''
    __test__ = True
    disk_name = DISKx86_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL5_APP_LIST

    @istest
    @polarion("RHEVM3-7429")
    def function_continuity(self):
        """ RHEL5_32b, rhevm-guest-agent function continuity """
        super(RHEL5x86FunctionContinuity, self).function_continuity()
