"""
Test installation and uninstallation of guest agent on RHEL 6 32b/64b
"""
import logging

from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

from nose.tools import istest


LOGGER = logging.getLogger(__name__)
NAME = config.GA_NAME
RHEL6_APP_LIST = ['kernel', 'rhevm-guest-agent-common']
RHEL_CMD_LIST_APP = ['rpm', '-qa']
DISKx64_NAME = 'rhel6_x64_Disk1'
DISKx86_NAME = 'rhel6_x86_Disk1'


def setup_module():
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


def teardown_module():
    for image in [DISKx64_NAME, DISKx86_NAME]:
        vms.removeVm(True, image, stopVM='true')


class RHEL6x64Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7422")
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL6x64Install, self).install_guest_agent()


class RHEL6x64Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    package = '%s-*' % NAME

    @istest
    @polarion("RHEVM3-7423")
    def uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package)


class RHEL6x64PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @polarion("RHEVM3-7437")
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL6x64PostInstall, self).post_install()
        stat = ['stat', '-L', '/dev/virtio-ports/*rhevm*', '|', 'grep', 'Uid',
                '|', 'grep', '660']
        self.assertTrue(self.machine.runCmd(stat)[0])
        if not config.UPSTREAM:
            tuned_cmd = [
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual'
            ]
            self.assertTrue(self.machine.runCmd(tuned_cmd)[0])


class RHEL6x64ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7438")
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6x64ServiceTest, self).service_test()


class RHEL6x64AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL6_APP_LIST

    @istest
    @polarion("RHEVM3-7439")
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL6x64AgentData, self).agent_data()


class RHEL6x64AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = DISKx64_NAME

    @istest
    @polarion("RHEVM3-7440")
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL6x64AgentData, self).agent_data_update()


class RHEL6x64FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = True
    disk_name = DISKx64_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL6_APP_LIST

    @istest
    @polarion("RHEVM3-7441")
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL6x64FunctionContinuity, self).function_continuity()


class RHEL6x86Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 32b '''
    __test__ = True
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7420")
    def install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        super(RHEL6x86Install, self).install_guest_agent()


class RHEL6x86Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = DISKx86_NAME
    package = '%s-*' % NAME

    @istest
    @polarion("RHEVM3-7419")
    def uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package)


class RHEL6x86PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    disk_name = DISKx86_NAME
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @polarion("RHEVM3-7410")
    def post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
        super(RHEL6x86PostInstall, self).post_install()
        stat = ['stat', '-L', '/dev/virtio-ports/*rhevm*', '|', 'grep', 'Uid',
                '|', 'grep', '660']
        self.assertTrue(self.machine.runCmd(stat)[0])
        if not config.UPSTREAM:
            tuned_cmd = [
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual'
            ]
            self.assertTrue(self.machine.runCmd(tuned_cmd)[0])


class RHEL6x86ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7411")
    def service_test(self):
        """ RHEL6_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6x86ServiceTest, self).service_test()


class RHEL6x86AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = DISKx86_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL6_APP_LIST

    @istest
    @polarion("RHEVM3-7412")
    def agent_data(self):
        """ RHEL6_32b rhevm-guest-agent data """
        super(RHEL6x86AgentData, self).agent_data()


class RHEL6x86AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = DISKx86_NAME

    @istest
    @polarion("RHEVM3-7413")
    def agent_data_update(self):
        """ RHEL6_32b, rhevm-guest-agent data update """
        super(RHEL6x86AgentData, self).agent_data_update()


class RHEL6x86FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = True
    disk_name = DISKx86_NAME
    list_app = RHEL_CMD_LIST_APP
    application_list = RHEL6_APP_LIST

    @istest
    @polarion("RHEVM3-7414")
    def function_continuity(self):
        """ RHEL6_32b, rhevm-guest-agent function continuity """
        super(RHEL6x86FunctionContinuity, self).function_continuity()
