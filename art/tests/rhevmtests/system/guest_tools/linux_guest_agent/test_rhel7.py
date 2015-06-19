"""
Test installation and uninstallation of guest agent on RHEL 7
"""
import logging

from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.system.guest_tools.linux_guest_agent import config, common

LOGGER = logging.getLogger(__name__)
NAME = config.GA_NAME


class RHEL7_1x64Install(common.BaseInstallGA):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = 'rhel7.1_x64_Disk1'

    @polarion('RHEVM3-7378')
    def test_install_guest_agent(self):
        """ RHEL7_1_64b install_guest_agent """
        self.install_guest_agent()


class RHEL7_1x64Uninstall(common.BaseUninstallGA):
    ''' '''
    __test__ = True
    disk_name = 'rhel7.1_x64_Disk1'
    package = '%s-*' % NAME

    @polarion('RHEVM3-7400')
    def test_uninstall_guest_agent(self):
        """ RHEL7_1_64b uninstall_guest_agent """
        self.uninstall()

    def tearDown(self):
        ''' install GA back '''
        common.runPackagerCommand(self.machine, self.package_manager,
                                  'install', self.package)


class RHEL7_1x64PostInstall(common.BasePostInstall):
    ''' '''
    __test__ = True
    disk_name = 'rhel7.1_x64_Disk1'
    cmd_chkconf = [
        'systemctl', 'list-unit-files', '|',
        'grep', 'ovirt', '|',
        'grep', 'enabled',
    ]

    @polarion('RHEVM3-7380')
    def test_post_install(self):
        """ RHEL7_1_64b rhevm-guest-agent post-install """
        self.post_install()
        stat = ['stat', '-L', '/dev/virtio-ports/*rhevm*', '|', 'grep', 'Uid',
                '|', 'grep', '660']
        self.assertTrue(self.machine.runCmd(stat)[0])
        if not config.UPSTREAM:
            tuned_cmd = [
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual',
            ]
            self.assertTrue(self.machine.runCmd(tuned_cmd)[0])


class RHEL7_1x64ServiceTest(common.BaseServiceTest):
    ''' '''
    __test__ = True
    disk_name = 'rhel7.1_x64_Disk1'

    @polarion('RHEVM3-7382')
    def test_service_test(self):
        """ RHEL7_1_64b rhevm-guest-agent start-stop-restart-status """
        self.service_test()


class RHEL7_1x64AgentData(common.BaseAgentData):
    ''' '''
    __test__ = True
    disk_name = 'rhel7.1_x64_Disk1'
    list_app = ['rpm', '-qa']
    application_list = ['kernel', config.PACKAGE_NAME]

    def _check_guestIP(self):
        ip = [
            'ifconfig', '|',
            'grep', '-Eo', 'inet [0-9\.]+', '|',
            'cut', '-d', ' ', '-f2',
        ]
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'guestIPs')
        ip_agent = common.runOnHost(cmd, self.disk_name)
        ip_agent = common.get_data(ip_agent)
        ip_list = ip_agent.split(' ')

        for iface in self.iface_dict:
            ip.insert(1, iface['name'])
            rc, ip_real = self.machine.runCmd(ip)
            ip_real = ip_real[:-2]
            self.assertTrue(ip_real in ip_list)

    @polarion('RHEVM3-7384')
    def test_agent_data(self):
        """ RHEL7_1_64b rhevm-guest-agent data """
        self.agent_data()
