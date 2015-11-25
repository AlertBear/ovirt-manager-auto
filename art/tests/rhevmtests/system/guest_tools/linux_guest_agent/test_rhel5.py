"""
Sanity test of guest agent of rhel 5 32/64b
"""
from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

DISKx64_NAME = 'rhel5_x64_Disk1'
DISKx86_NAME = 'rhel5_x86_Disk1'


def setup_module():
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


class RHEL5GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 5
    """
    __test__ = False
    package = config.GA_NAME
    list_app_cmd = ['rpm', '-qa']
    application_list = ['kernel', 'rhevm-guest-agent']
    cmd_chkconf = [
        'chkconfig', '--list',
        '|', 'grep', 'ovirt',
        '|', 'egrep', '3:on',
    ]


class RHEL532bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 32b
    """
    __test__ = True
    disk_name = DISKx64_NAME

    @polarion("RHEVM3-7377")
    def test_aa_install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        self.install_guest_agent(config.GA_NAME)

    @polarion("RHEVM3-7406")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL5_32b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7425")
    def test_post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])

    @polarion("RHEVM3-7426")
    def test_service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7427")
    def test_agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app_cmd)

    @polarion("RHEVM3-7429")
    def test_function_continuity(self):
        """ RHEL5_32b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app_cmd)


class RHEL564bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 64b
    """
    __test__ = True
    disk_name = DISKx86_NAME

    @polarion("RHEVM3-7407")
    def test_aa_install_guest_agent(self):
        """ install_guest_agent """
        self.install_guest_agent(config.GA_NAME)

    @polarion("RHEVM3-7408")
    def test_zz_uninstall_guest_agent(self):
        """ uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7431")
    def test_post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])

    @polarion("RHEVM3-7432")
    def test_service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7433")
    def test_agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app_cmd)

    @polarion("RHEVM3-7435")
    def test_function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app_cmd)
