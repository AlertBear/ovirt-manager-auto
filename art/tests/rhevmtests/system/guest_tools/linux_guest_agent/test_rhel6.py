"""
Sanity test of guest agent of rhel 6 32/64b
"""
from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common


DISKx64_NAME = 'rhel6_x64_Disk1'
DISKx86_NAME = 'rhel6_x86_Disk1'


def setup_module():
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


class RHEL6GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 6
    """
    __test__ = False
    list_app = ['rpm', '-qa']
    application_list = ['kernel', 'rhevm-guest-agent-common']
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']


class RHEL664bGATest(RHEL6GATest):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = DISKx64_NAME

    @polarion("RHEVM3-7422")
    def test_aa_install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        self.install_guest_agent(config.PACKAGE_NAME)

    @polarion("RHEVM3-7423")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7437")
    def test_post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        self.post_install()
        rc, out, err = self.machine.executor().run_cmd([
            'stat', '-L', '/dev/virtio-ports/*rhevm*',
            '|', 'grep', 'Uid',
            '|', 'grep', '660'
        ])
        self.assertTrue(
            not rc, "Failed to check virtio ports: %s" % err
        )
        if not config.UPSTREAM:
            rc, out, err = self.machine.executor().run_cmd([
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual',
            ])
            self.assertTrue(
                not rc,
                "Tuned profile isn't virtual. It's '%s'. Err: %s" % (out, err)
            )

    @polarion("RHEVM3-7438")
    def test_service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7439")
    def test_agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app)

    @polarion("RHEVM3-7441")
    def test_function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app)


class RHEL632bGATest(RHEL6GATest):
    ''' test installation of guest agent on rhel 6 32b '''
    __test__ = True
    disk_name = DISKx86_NAME

    @polarion("RHEVM3-7420")
    def test_aa_install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        self.install_guest_agent(config.PACKAGE_NAME)

    @polarion("RHEVM3-7419")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7410")
    def test_post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])
        rc, out, err = self.machine.executor().run_cmd([
            'stat', '-L', '/dev/virtio-ports/*rhevm*',
            '|', 'grep', 'Uid',
            '|', 'grep', '660'
        ])
        self.assertTrue(
            not rc, "Failed to check virtio ports: %s" % err
        )
        if not config.UPSTREAM:
            rc, out, err = self.machine.executor().run_cmd([
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual',
            ])
            self.assertTrue(
                not rc,
                "Tuned profile isn't virtual. It's '%s'. Err: %s" % (out, err)
            )

    @polarion("RHEVM3-7411")
    def test_service_test(self):
        """ RHEL6_32b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7412")
    def test_agent_data(self):
        """ RHEL6_32b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app)

    @polarion("RHEVM3-7414")
    def test_function_continuity(self):
        """ RHEL6_32b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app)
