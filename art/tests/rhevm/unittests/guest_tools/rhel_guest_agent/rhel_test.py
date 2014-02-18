"""
Test installation and uninstallation of guest agent on RHEL 5/6 32b/64b
"""
import ast
import logging
import config
import art.rhevm_api.utils.test_utils as utils
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from art.rhevm_api.tests_lib.low_level import vms, templates
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import get_api


VM_API = get_api('vm', 'vms')
HOST_API = get_api('host', 'hosts')
ENUMS = opts['elements_conf']['RHEVM Enums']
LOGGER = logging.getLogger(__name__)
INSTALL_6 = 'yum install -y rhevm-guest-agent rhevm-guest-agent-gdm-plugin'
UNINSTALL_6 = 'yum remove -y rhevm-guest-agent rhevm-guest-agent-gdm-plugin'
INSTALL_5 = 'yum install -y rhevm-guest-agent -x rhevm-guest-agent-common'
UNINSTALL_5 = 'yum remove -y rhevm-guest-agent'


class RHEL(TestCase):
    """ Testing installation and uninstallation of guest agent on RHEL 5/6 """
    __test__ = False
    success_msg = "%s of guest agent was successfull on %s"
    stats = 'vdsClient -s 0 getVmStats'
    cmd_service = 'service ovirt-guest-agent %s | grep -i OK'
    cmd_status = 'service ovirt-guest-agent status | grep -i %s'
    iface_dict = []

    @classmethod
    def setup_class(cls):
        """ prepare vms and templates """
        cls.vm_name = 'vm_%s' % cls.template_name
        assert templates.importTemplate(
            True, template=cls.template_name,
            export_storagedomain=config.EXPORT_STORAGE_DOMAIN,
            import_storagedomain=config.STORAGE_DOMAIN,
            cluster=config.CLUSTER_NAME,
            name=cls.template_name)
        assert vms.createVm(True, cls.vm_name, cls.vm_name,
                            cluster=config.CLUSTER_NAME,
                            template=cls.template_name,
                            network=config.MGMT_BRIDGE)
        assert vms.startVm(True, cls.vm_name,
                           wait_for_status=ENUMS['vm_state_up'])

        vm_obj = VM_API.find(cls.vm_name)
        cls.running_host_ip = HOST_API.find(vm_obj.host.id, 'id').get_address()

        cls.mac = vms.getVmMacAddress(True, vm=cls.vm_name, nic='nic1')
        assert cls.mac[0], "vm %s MAC was not found." % cls.vm_name
        cls.mac = cls.mac[1].get('macAddress', None)
        LOGGER.info("Mac adress is %s", cls.mac)

        cls.ip = utils.convertMacToIpAddress(True, cls.mac,
                                             subnetClassB=config.SUBNET_CLASS)
        assert cls.ip[0], "MacToIp was not corretly converted."
        cls.ip = cls.ip[1].get('ip', None)
        cls.vm_id = VM_API.find(cls.vm_name).get_id()

        status = runMachineCommand(True, ip=cls.ip, cmd=cls.install,
                                   user=config.USER_ROOT,
                                   password=config.USER_PASSWORD,
                                   timeout=240)
        LOGGER.info(status)
        assert status[0]
        cls.is_installed = status[0]
        LOGGER.info(cls.success_msg, 'Installation', cls.template_name)

        status = runMachineCommand(True, ip=cls.ip,
                                   cmd='service ovirt-guest-agent start',
                                   user=config.USER_ROOT,
                                   password=config.USER_PASSWORD,
                                   timeout=240)
        LOGGER.info(status)

    @classmethod
    def teardown_class(cls):
        """ remove vms and templates """
        assert vms.removeVm(True, vm=cls.vm_name, stopVM='true')
        assert templates.removeTemplate(True, cls.template_name)

    def __runCommand(self, ip, user, passwd, cmd, timeout=240):
        LOGGER.info('running command: "%s"', cmd)
        status = runMachineCommand(True, ip=ip, cmd=cmd, user=user,
                                   password=passwd, timeout=timeout)
        LOGGER.info(status)
        return status

    def _runOnMachine(self, cmd):
        return self.__runCommand(self.ip, config.USER_ROOT,
                                 config.USER_PASSWORD, cmd)

    def _runOnHost(self, cmd):
        return self.__runCommand(self.running_host_ip, config.USER_ROOT,
                                 config.VDS_PASSWORD[0], cmd)

    def service_test(self):
        """ rhevm-guest-agent start-stop-restart-status """
        if self._runOnMachine(self.cmd_status % 'running')[0]:
            self._runOnMachine(self.cmd_service % 'stop')

        self.assertTrue(self._runOnMachine(self.cmd_service % 'start')[0])
        self.assertTrue(self._runOnMachine(self.cmd_status % 'running')[0])
        self.assertTrue(self._runOnMachine(self.cmd_service % 'stop')[0])
        self.assertTrue(self._runOnMachine(self.cmd_status % 'stopped')[0])
        self.assertTrue(self._runOnMachine(self.cmd_service % 'restart')[0])
        self.assertTrue(self._runOnMachine(self.cmd_status % 'running')[0])

    def post_install(self):
        """  rhevm-guest-agent post-install """
        cmd_ls = 'ls -l /etc/ovirt-guest-agent.conf'
        cmd_chkconf = 'chkconfig --list | grep ovirt | egrep 3:on'
        cmd_passwd = 'grep ovirtagent /etc/{passwd,group}'

        self.assertTrue(self._runOnMachine(cmd_ls)[0])
        self.assertTrue(self._runOnMachine(cmd_chkconf)[0])
        self.assertTrue(self._runOnMachine(cmd_passwd)[0])

    def function_continuity(self):
        """ rhevm-guest-agent function continuity """
        self.assertTrue(vms.migrateVm(True, self.vm_name))
        self.assertTrue(self._isAgentRunning())
        self.agent_data()
        self.assertTrue(vms.suspendVm(True, self.vm_name))
        self.assertTrue(vms.startVm(True, self.vm_name,
                                    wait_for_status=ENUMS['vm_state_up'],
                                    wait_for_ip=True))
        self.assertTrue(self._isAgentRunning())
        self.agent_data()
        self._stop_vdsm()
        self.assertTrue(self._isAgentRunning())
        self._start_vdsm()

    def agent_data_update(self):
        """ rhevm-guest-agent data update """
        self.agent_data()
        self._update_data()
        self.agent_data()

    def _update_data(self):
        pass

    def _start_vdsm(self):
        self._runOnHost('service supervdsmd start')
        self._runOnHost('service vdsmd start')

    def _stop_vdsm(self):
        self._runOnHost('service supervdsmd stop')
        self._runOnHost('service vdsmd stop')

    def _check_fqdn(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== )[A-Za-z0-9-.]*'"
        fqdn_cmd = 'hostname --fqdn'
        fqdn_agent = self._runOnHost(cmd % (self.stats, self.vm_id, 'FQDN'))
        fqdn_agent = self._get_data(fqdn_agent)
        fqdn_real = self._runOnMachine(fqdn_cmd)
        fqdn_real = self._get_data(fqdn_real)

        self.assertEqual(fqdn_real, fqdn_agent, "Agent returned wrong FQDN")

    def _check_net_ifaces(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'netIfaces')
        iface_agent = self._runOnHost(cmd)
        iface_agent = self._get_data(iface_agent)
        iface_real = self._runOnMachine('ip addr show')
        iface_real = self._get_data(iface_real)
        self.iface_dict = ast.literal_eval(iface_agent)
        for it in self.iface_dict:
            self.assertTrue(it['name'] in iface_real)
            self.assertTrue(it['hw'] in iface_real)
            for i in it['inet6'] + it['inet']:
                self.assertTrue(i in iface_real)

    def _check_diskusage(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'disksUsage')
        df_agent = self._runOnHost(cmd)
        df_agent = self._get_data(df_agent)
        df_dict = ast.literal_eval(df_agent)

        for fs in df_dict:
            df_real = self._runOnMachine('df -B 1 %s' % fs['path'])
            df_real = self._get_data(df_real)

            self.assertTrue(fs['total'] in df_real)
            if fs['path'] != '/':
                self.assertTrue(fs['used'] in df_real)

    def _check_applist(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'appsList')
        app_agent = self._runOnHost(cmd)
        app_agent = self._get_data(app_agent)
        app_list = ast.literal_eval(app_agent)

        for app in self.application_list:
            self._check_app(app, app_list)

    def _check_app(self, app, app_list):
        app_real = self._runOnMachine('rpm -qa %s' % app)
        app_real = self._get_data(app_real)
        app_real_list = app_real.split('\r\n')

        for app in app_real_list:
            if app.endswith(('i686', 'x86_64', 'noarch')):
                app = app[:app.rfind('.')]
            self.assertTrue(app in app_list)

    def _check_guestIP(self):
        ip = "ifconfig %s | grep 'inet addr:' | cut -d: -f2 | cut -d ' ' -f 1"
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'guestIPs')
        ip_agent = self._runOnHost(cmd)
        ip_agent = self._get_data(ip_agent)
        ip_list = ip_agent.split(' ')

        for iface in self.iface_dict:
            ip_real = self._runOnMachine(ip % iface['name'])
            ip_real = self._get_data(ip_real)
            self.assertTrue(ip_real in ip_list)

    def agent_data(self):
        """ rhevm-guest-agent data """
        self._check_fqdn()
        self._check_net_ifaces()
        self._check_diskusage()
        self._check_applist()
        self._check_guestIP()

    def install_guest_agent(self):
        """ install guest agent on rhel """
        self.assertTrue(self.is_installed)

     # This have to be last case (last in alphabet)
    def zz_uninstall_guest_agent(self):
        """ uninstall guest agent on rhel """
        self.assertTrue(self._runOnMachine(self.uninstall)[0])
        LOGGER.info(self.success_msg, 'Uninstallation', self.template_name)

    def _get_data(self, cmd):
        return cmd[1]['out'][:-2]

    def _isAgentRunning(self):
        return self._runOnMachine(self.cmd_status % 'running')[0]


class RHEL6(RHEL):
    """ RHEL6 """
    __test__ = False
    install = INSTALL_6
    uninstall = UNINSTALL_6
    application_list = ['kernel', 'rhevm-guest-agent-common']

    def post_install(self):
        """ RHEL6 rhevm-guest-agent post-install """
        stat = 'stat -L /dev/virtio-ports/*rhevm* | grep Uid | grep 660'
        tuned_cmd = 'tuned-adm list | grep ^Current | grep -i virtual'
        tuned = self._runOnMachine(tuned_cmd)
        stat_res = self._runOnMachine(stat)
        self.assertTrue(tuned[0])
        self.assertTrue(stat_res[0])


class RHEL5(RHEL):
    """ RHEL5 """
    __test__ = False
    install = INSTALL_5
    uninstall = UNINSTALL_5
    application_list = ['kernel', 'rhevm-guest-agent']


class RHEL6_64b(RHEL6):
    """ RHEL6 64b"""
    __test__ = True
    template_name = config.RHEL_6_64b

    @istest
    @tcms(config.TCMS_PLAN_ID, 325219)
    def install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        super(RHEL6_64b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325292)
    def uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        super(RHEL6_64b, self).zz_uninstall_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325446)
    def post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        super(RHEL6_64b, self).post_install()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325497)
    def service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6_64b, self).service_test()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325504)
    def agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        super(RHEL6_64b, self).agent_data()


class RHEL6_32b(RHEL6):
    """ RHEL6 32b"""
    __test__ = True
    template_name = config.RHEL_6_32b

    @istest
    @tcms(config.TCMS_PLAN_ID, 325218)
    def install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        super(RHEL6_32b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325291)
    def uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        super(RHEL6_32b, self).zz_uninstall_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 175514)
    def post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
        super(RHEL6_32b, self).post_install()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325496)
    def service_test(self):
        """ RHEL6_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL6_32b, self).service_test()

    @istest
    @tcms(config.TCMS_PLAN_ID, 69880)
    def agent_data(self):
        """ RHEL6_32b rhevm-guest-agent data """
        super(RHEL6_32b, self).agent_data()


class RHEL5_64b(RHEL5):
    """ RHEL5 64b"""
    __test__ = True
    template_name = config.RHEL_5_64b

    @istest
    @tcms(config.TCMS_PLAN_ID, 325217)
    def install_guest_agent(self):
        """ RHEL5_64b install_guest_agent """
        super(RHEL5_64b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325290)
    def uninstall_guest_agent(self):
        """ RHEL5_64b uninstall_guest_agent """
        super(RHEL5_64b, self).zz_uninstall_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325493)
    def post_install(self):
        """ RHEL5_64b rhevm-guest-agent post-install """
        super(RHEL5_64b, self).post_install()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325495)
    def service_test(self):
        """ RHEL5_64b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5_64b, self).service_test()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325502)
    def agent_data(self):
        """ RHEL5_64b rhevm-guest-agent data """
        super(RHEL5_64b, self).agent_data()


class RHEL5_32b(RHEL5):
    """ RHEL5 32b"""
    __test__ = True
    template_name = config.RHEL_5_32b

    @istest
    @tcms(config.TCMS_PLAN_ID, 325215)
    def install_guest_agent(self):
        """ RHEL5_32b rhevm-guest-agent install """
        super(RHEL5_32b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325289)
    def uninstall_guest_agent(self):
        """ RHEL5_32b rhevm-guest-agent uninstall """
        super(RHEL5_32b, self).zz_uninstall_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325492)
    def post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        super(RHEL5_32b, self).post_install()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325494)
    def service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        super(RHEL5_32b, self).service_test()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325500)
    def agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        super(RHEL5_32b, self).agent_data()
