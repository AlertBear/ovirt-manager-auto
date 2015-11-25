"""
Sanity test of guest agent of rhel 7 64b
"""
import shlex

from art.test_handler.tools import polarion  # pylint: disable=E0611

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

DISK_NAME = 'rhel7.1_x64_Disk1'


def setup_module():
    common.prepare_vms([DISK_NAME])


class RHEL7GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 7
    """
    __test__ = False
    package = config.GA_NAME
    list_app = ['rpm', '-qa']
    application_list = ['kernel', config.PACKAGE_NAME]
    cmd_chkconf = [
        'systemctl', 'list-unit-files', '|',
        'grep', 'ovirt', '|',
        'grep', 'enabled',
    ]


class RHEL764bGATest(RHEL7GATest):
    """
    Cover basic testing of GA of rhel 5 32b
    """
    __test__ = True
    disk_name = DISK_NAME

    @polarion('RHEVM3-7378')
    def test_aa_install_guest_agent(self):
        """ RHEL7_1_64b install_guest_agent """
        self.install_guest_agent(config.PACKAGE_NAME)

    @polarion('RHEVM3-7400')
    def test_zz_uninstall_guest_agent(self):
        """ RHEL7_1_64b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion('RHEVM3-7380')
    def test_post_install(self):
        """ RHEL7_1_64b rhevm-guest-agent post-install """
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

    @polarion('RHEVM3-7382')
    def test_service_test(self):
        """ RHEL7_1_64b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion('RHEVM3-7384')
    def test_agent_data(self):
        """ RHEL7_1_64b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app)

    def _check_guestIP(self):
        ip = [
            'ifconfig', '|',
            'grep', '-Eo', 'inet [0-9\.]+', '|',
            'cut', '-d', ' ', '-f2',
        ]
        cmd = shlex.split(
            "%s %s | egrep %s | grep -Po '(?<== ).*'" % (
                self.stats, self.vm_id, 'guestIPs'
            )
        )
        ip_list = self._run_cmd_on_hosts_vm(cmd, self.disk_name).split(' ')

        for iface in self.get_ifaces():
            ip.insert(1, iface['name'])
            rc, ip_real, err = self.machine.executor().run_cmd(ip)
            ip_real = ip_real.strip()
            self.assertTrue(
                ip_real in ip_list,
                "Guest IP '%s' is not in IP list '%s'" % (ip_real, ip_list)
            )

    @polarion("RHEVM3-7388")
    def test_function_continuity(self):
        """ RHEL7_1x64, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app)
