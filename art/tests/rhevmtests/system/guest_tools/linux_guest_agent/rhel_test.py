"""
Test installation and uninstallation of guest agent on RHEL 5/6 32b/64b
"""
import os
from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common
import logging
from nose.tools import istest
from art.test_handler.tools import tcms  # pylint: disable=E0611

package_manager = '/usr/bin/yum'
repo_path = '/etc/yum.repos.d/'
LOGGER = logging.getLogger(__name__)
eOS = config.eOS
NAME = 'rhevm-guest-agent'
repo_name = 'latest_rhel'


def setup_module():
    for vm_os in [eOS.RHEL_5_64b, eOS.RHEL_5_32b,
                  eOS.RHEL_6_64b, eOS.RHEL_6_32b]:
        machine = common.MyLinuxMachine(config.TEMPLATES[vm_os]['ip'])
        path = os.path.join(repo_path, 'latest_rhevm.repo')
        lines = ['[%s]' % repo_name, 'name=%s' % repo_name,
                 'baseurl=%s' % config.RHEL_REPOSITORY, 'enabled=1',
                 'gpgcheck=0']
        for line in lines:
            repo_cmd = ['echo', line, '>>', path]
            res, out = machine.runCmd(repo_cmd, timeout=config.TIMEOUT)
            if not res:
                LOGGER.error("Fail to run cmd %s: %s", repo_cmd, out)

        if vm_os in (eOS.RHEL_5_64b, eOS.RHEL_5_32b):
            common.runPackagerCommand(machine, package_manager, 'install',
                                      '--disablerepo=rhevm', NAME, '-x',
                                      'rhevm-guest-agent-common')
        else:
            common.runPackagerCommand(machine, package_manager, 'install',
                                      '--disablerepo=rhevm33', NAME)
        LOGGER.info('Service started %s',
                    machine.startService(config.AGENT_SERVICE_NAME))
        config.TEMPLATES[vm_os]['machine'] = machine


class RHEL64b6Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    os = eOS.RHEL_6_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325219)
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL64b6Install, self).install_guest_agent()


class RHEL64b6Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_64b
    package = '%s-*' % NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325292)
    def uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', '--disablerepo=rhevm33',
                                  self.package)


class RHEL64b6PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_64b
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325446)
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL64b6PostInstall, self).post_install()
        stat = ['stat', '-L', '/dev/virtio-ports/*rhevm*', '|', 'grep', 'Uid',
                '|', 'grep', '660']
        tuned_cmd = ['tuned-adm', 'list', '|', 'grep', '^Current', '|', 'grep',
                     '-i', 'virtual']
        self.assertTrue(self.machine.runCmd(tuned_cmd)[0])
        self.assertTrue(self.machine.runCmd(stat)[0])


class RHEL64b6ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325497)
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL64b6ServiceTest, self).service_test()


class RHEL64b6AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_64b
    list_app = ['rpm', '-qa']
    application_list = ['kernel', 'rhevm-guest-agent-common']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325504)
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL64b6AgentData, self).agent_data()


class RHEL64b6AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    os = eOS.RHEL_6_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325498)
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL64b6AgentData, self).agent_data_update()


class RHEL64b6FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    os = eOS.RHEL_6_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325532)
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL64b6FunctionContinuity, self).function_continuity()


class RHEL32b6Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 32b '''
    __test__ = True
    os = eOS.RHEL_6_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325218)
    def install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        super(RHEL32b6Install, self).install_guest_agent()


class RHEL32b6Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_32b
    package = '%s-*' % NAME

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325291)
    def uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package,
                                  '--disablerepo=rhevm33')


class RHEL32b6PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_32b
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 175514)
    def post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
        super(RHEL32b6PostInstall, self).post_install()
        stat = ['stat', '-L', '/dev/virtio-ports/*rhevm*', '|', 'grep', 'Uid',
                '|', 'grep', '660']
        tuned_cmd = ['tuned-adm', 'list', '|', 'grep', '^Current', '|', 'grep',
                     '-i', 'virtual']
        self.assertTrue(self.machine.runCmd(tuned_cmd)[0])
        self.assertTrue(self.machine.runCmd(stat)[0])


class RHEL32b6ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325496)
    def service_test(self):
        """ RHEL6_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL32b6ServiceTest, self).service_test()


class RHEL32b6AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    os = eOS.RHEL_6_32b
    application_list = ['kernel', 'rhevm-guest-agent-common']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 69880)
    def agent_data(self):
        """ RHEL6_32b rhevm-guest-agent data """
        super(RHEL32b6AgentData, self).agent_data()


class RHEL32b6AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    os = eOS.RHEL_6_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325503)
    def agent_data_update(self):
        """ RHEL6_32b, rhevm-guest-agent data update """
        super(RHEL32b6AgentData, self).agent_data_update()


class RHEL32b6FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    os = eOS.RHEL_6_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325530)
    def function_continuity(self):
        """ RHEL6_32b, rhevm-guest-agent function continuity """
        super(RHEL32b6FunctionContinuity, self).function_continuity()


class RHEL64b5Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    os = eOS.RHEL_5_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325217)
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL64b5Install, self).install_guest_agent()


class RHEL64b5Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    os = eOS.RHEL_5_64b
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
                                  '--disablerepo=rhevm', '-x',
                                  'rhevm-guest-agent-common')


class RHEL64b5PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    os = eOS.RHEL_5_64b
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325493)
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL64b5PostInstall, self).post_install()


class RHEL64b5ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    os = eOS.RHEL_5_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325495)
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL64b5ServiceTest, self).service_test()


class RHEL64b5AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    os = eOS.RHEL_5_64b
    application_list = ['kernel', 'rhevm-guest-agent']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325502)
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL64b5AgentData, self).agent_data()


class RHEL64b5AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' '''
    __test__ = False
    os = eOS.RHEL_5_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325499)
    def agent_data_update(self):
        """ RHEL6_64b, rhevm-guest-agent data update """
        super(RHEL64b5AgentData, self).agent_data_update()


class RHEL64b5FunctionContinuity(common.BaseFunctionContinuity):
    ''' '''
    __test__ = False
    os = eOS.RHEL_5_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325529)
    def function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        super(RHEL64b5FunctionContinuity, self).function_continuity()


class RHEL32b5Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 5 32b '''
    __test__ = True
    os = eOS.RHEL_5_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325215)
    def install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        super(RHEL32b5Install, self).install_guest_agent()


class RHEL32b5Uninstall(common.BaseUninstallGA):
    ''' RHEL5_32b uninstall_guest_agent '''
    __test__ = True
    os = eOS.RHEL_5_32b
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
                                  '--disablerepo=rhevm', '-x',
                                  'rhevm-guest-agent-common')


class RHEL32b5PostInstall(common.BasePostInstall):
    ''' RHEL5_32b rhevm-guest-agent post-install '''
    __test__ = True
    os = eOS.RHEL_5_32b
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325492)
    def post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        super(RHEL32b5PostInstall, self).post_install()


class RHEL32b5ServiceTest(common.BaseServiceTest):
    ''' RHEL5_32b rhevm-guest-agent start-stop-restart-status '''
    __test__ = True
    os = eOS.RHEL_5_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325494)
    def service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL32b5ServiceTest, self).service_test()


class RHEL32b5AgentData(common.BaseAgentData):
    ''' RHEL5_32b rhevm-guest-agent data '''
    __test__ = True
    os = eOS.RHEL_5_32b
    application_list = ['kernel', 'rhevm-guest-agent']
    list_app = ['rpm', '-qa']

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325500)
    def agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        super(RHEL32b5AgentData, self).agent_data()


class RHEL32b5AgentDataUpdate(common.BaseAgentDataUpdate):
    ''' RHEL5_32b, rhevm-guest-agent data update '''
    __test__ = False
    os = eOS.RHEL_5_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 325501)
    def agent_data_update(self):
        """ RHEL5_32b, rhevm-guest-agent data update """
        super(RHEL32b5AgentData, self).agent_data_update()


class RHEL32b5FunctionContinuity(common.BaseFunctionContinuity):
    ''' RHEL5_32b, rhevm-guest-agent function continuity '''
    __test__ = False
    os = eOS.RHEL_5_32b

    @istest
    @tcms(config.TCMS_PLAN_ID_RHEL, 69882)
    def function_continuity(self):
        """ RHEL5_32b, rhevm-guest-agent function continuity """
        super(RHEL32b5FunctionContinuity, self).function_continuity()
