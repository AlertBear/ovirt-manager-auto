'''
Suse guest agent test
'''
import logging
from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common
from utilities.machine import eServiceHandlers
from nose.tools import istest
from art.test_handler.tools import tcms  # pylint: disable=E0611

eOS = config.eOS
package_manager = '/usr/bin/zypper'
LOGGER = logging.getLogger(__name__)

# Temporary disabled(stabilization in progress)
__test__ = False


def setup_module():
    for os in [eOS.SUSE_13_1_64b]:
        machine = common.MyLinuxMachine(config.TEMPLATES[os]['ip'],
                                        eServiceHandlers.SYSTEMCTL)
        repo_cmd = [package_manager, 'addrepo', '-f',
                    config.SUSE_REPOSITORY, 'guest_agent']
        res, out = machine.runCmd(repo_cmd, timeout=config.TIMEOUT)
        if not res:
            LOGGER.error("Fail to run cmd %s: %s", repo_cmd, out)
        common.runPackagerCommand(machine, package_manager,
                                  'install', 'ovirt-guest-agent*')
        LOGGER.info('Service started %s',
                    machine.startService('ovirt-guest-agent'))

        config.TEMPLATES[os]['machine'] = machine


class SusePostInstall(common.BasePostInstall):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b
    cmd_chkconf = ['systemctl', 'is-enabled', 'ovirt-guest-agent']

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343356)
    def post_install(self):
        """ Suse rhevm-guest-agent post-install """
        super(SusePostInstall, self).post_install()


class SuseInstallGA(common.BaseInstallGA):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343355)
    def install_guest_agent(self):
        """ Suse rhevm-guest-agent install """
        super(SuseInstallGA, self).install_guest_agent()


class SuseUninstallGA(common.BaseUninstallGA):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343358)
    def uninstall_guest_agent(self):
        """ Suse rhevm-guest-agent uninstall """
        super(SuseUninstallGA, self).zz_uninstall_guest_agent()


class SuseServiceTest(common.BaseServiceTest):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343357)
    def service_test(self):
        """ Suse rhevm-guest-agent start-stop-restart-status """
        super(SuseServiceTest, self).service_test()


class SuseAgentData(common.BaseAgentData):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b
    application_list = ['kernel-desktop', 'ovirt-guest-agent-common',
                        'xf86-video-qxl']

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343353)
    def agent_data(self):
        """ Suse rhevm-guest-agent data """
        super(SuseAgentData, self).agent_data()


class SuseAgentDataUpdate(common.BaseAgentDataUpdate):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343354)
    def agent_data_update(self):
        """ Suse rhevm-guest-agent data update """
        super(SuseAgentDataUpdate, self).agent_data_update()


class SuseFunctionContinuity(common.BaseFunctionContinuity):
    """ Suse post install """
    __test__ = False
    os = eOS.SUSE_13_1_64b
    agent_data = SuseAgentData

    @istest
    @tcms(config.TCMS_PLAN_ID_SUSE, 343352)
    def function_continuity(self):
        """ Suse rhevm-guest-agent function continuity """
        super(SuseFunctionContinuity, self).function_continuity()
