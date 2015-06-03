"""
Test installation and uninstallation of guest agent on RHEL 5/6 32b/64b
"""
import logging

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common
from nose.tools import istest
from art.test_handler.tools import tcms  # pylint: disable=E0611


LOGGER = logging.getLogger(__name__)
NAME = config.GA_NAME


class RHEL6x64Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = 'rhel6_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325219)
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL6x64Install, self).install_guest_agent()


class RHEL6x64Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = 'rhel6_x64_Disk1'
    package = '%s-*' % NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325292)
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
    disk_name = 'rhel6_x64_Disk1'
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325446)
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
    disk_name = 'rhel6_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325497)
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6x64ServiceTest, self).service_test()


class RHEL6x64AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = 'rhel6_x64_Disk1'
    list_app = ['rpm', '-qa']
    application_list = ['kernel', 'rhevm-guest-agent-common']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325504)
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL6x64AgentData, self).agent_data()


class RHEL6x64AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = 'rhel6_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325498)
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL6x64AgentData, self).agent_data_update()


class RHEL6x64FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    disk_name = 'rhel6_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325532)
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL6x64FunctionContinuity, self).function_continuity()


class RHEL6x86Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 32b '''
    __test__ = True
    disk_name = 'rhel6_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325218)
    def install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        super(RHEL6x86Install, self).install_guest_agent()


class RHEL6x86Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = 'rhel6_x86_Disk1'
    package = '%s-*' % NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325291)
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
    disk_name = 'rhel6_x86_Disk1'
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 175514)
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
    disk_name = 'rhel6_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325496)
    def service_test(self):
        """ RHEL6_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6x86ServiceTest, self).service_test()


class RHEL6x86AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = 'rhel6_x86_Disk1'
    application_list = ['kernel', 'rhevm-guest-agent-common']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 69880)
    def agent_data(self):
        """ RHEL6_32b rhevm-guest-agent data """
        super(RHEL6x86AgentData, self).agent_data()


class RHEL6x86AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = 'rhel6_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325503)
    def agent_data_update(self):
        """ RHEL6_32b, rhevm-guest-agent data update """
        super(RHEL6x86AgentData, self).agent_data_update()


class RHEL6x86FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    disk_name = 'rhel6_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325530)
    def function_continuity(self):
        """ RHEL6_32b, rhevm-guest-agent function continuity """
        super(RHEL6x86FunctionContinuity, self).function_continuity()


class RHEL5x64Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = 'rhel5_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325217)
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL5x64Install, self).install_guest_agent()


class RHEL5x64Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = 'rhel5_x64_Disk1'
    package = NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325290)
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
    disk_name = 'rhel5_x64_Disk1'
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325493)
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL5x64PostInstall, self).post_install()


class RHEL5x64ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    disk_name = 'rhel5_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325495)
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5x64ServiceTest, self).service_test()


class RHEL5x64AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = 'rhel5_x64_Disk1'
    application_list = ['kernel', 'rhevm-guest-agent']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325502)
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL5x64AgentData, self).agent_data()


class RHEL5x64AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    disk_name = 'rhel5_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325499)
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL5x64AgentData, self).agent_data_update()


class RHEL5x64FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    disk_name = 'rhel5_x64_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325529)
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL5x64FunctionContinuity, self).function_continuity()


class RHEL5x86Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 5 32b '''
    __test__ = True
    disk_name = 'rhel5_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325215)
    def install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        super(RHEL5x86Install, self).install_guest_agent()


class RHEL5x86Uninstall(common.BaseUninstallGA):
    ''' RHEL5_32b uninstall_guest_agent '''
    __test__ = True
    disk_name = 'rhel5_x86_Disk1'
    package = NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325289)
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
    disk_name = 'rhel5_x86_Disk1'
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325492)
    def post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        super(RHEL5x86PostInstall, self).post_install()


class RHEL5x86ServiceTest(common.BaseServiceTest):
    ''' RHEL5_32b rhevm-guest-agent start-stop-restart-status '''
    __test__ = True
    disk_name = 'rhel5_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325494)
    def service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5x86ServiceTest, self).service_test()


class RHEL5x86AgentData(common.BaseAgentData):
    ''' RHEL5_32b rhevm-guest-agent data '''
    __test__ = True
    disk_name = 'rhel5_x86_Disk1'
    application_list = ['kernel', 'rhevm-guest-agent']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325500)
    def agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        super(RHEL5x86AgentData, self).agent_data()


class RHEL5x86AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' RHEL5_32b, rhevm-guest-agent data update '''
    __test__ = False
    disk_name = 'rhel5_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325501)
    def agent_data_update(self):
        """ RHEL5_32b, rhevm-guest-agent data update """
        super(RHEL5x86AgentData, self).agent_data_update()


class RHEL5x86FunctionContinuity(common.BaseFunctionContinuity):
    ''' RHEL5_32b, rhevm-guest-agent function continuity '''
    __test__ = False
    disk_name = 'rhel5_x86_Disk1'

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 69882)
    def function_continuity(self):
        """ RHEL5_32b, rhevm-guest-agent function continuity """
        super(RHEL5x86FunctionContinuity, self).function_continuity()
