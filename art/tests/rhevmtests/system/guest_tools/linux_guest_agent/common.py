import ast
import logging
from rhevmtests.system.guest_tools.linux_guest_agent import config
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.test_handler.settings import opts
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import get_api
from utilities import machine

__test__ = False

VM_API = get_api('vm', 'vms')
HOST_API = get_api('host', 'hosts')
ENUMS = opts['elements_conf']['RHEVM Enums']
LOGGER = logging.getLogger(__name__)


def runOnHost(cmd, vm_name):
    LOGGER.info(cmd)
    vm_obj = VM_API.find(vm_name)
    running_host_ip = HOST_API.find(vm_obj.host.id, 'id').get_address()
    return runMachineCommand(True, ip=running_host_ip, user=config.HOSTS_USER,
                             password=config.HOSTS_PW, cmd=cmd)


def start_vdsm(vm_name):
    runOnHost('service supervdsmd start', vm_name)
    runOnHost('service vdsmd start', vm_name)


def stop_vdsm(vm_name):
    runOnHost('service supervdsmd stop', vm_name)
    runOnHost('service vdsmd stop', vm_name)


def get_data(cmd):
    return cmd[1]['out'][:-2]


def runPackagerCommand(machine, package_manager, command, *args):
    ''' '''
    packager_cmd = [package_manager, command, '-y']
    packager_cmd.extend(args)
    res, out = machine.runCmd(packager_cmd, timeout=config.INSTALL_TIMEOUT)
    if not res:
        LOGGER.error("Fail to run cmd %s: %s", packager_cmd, out)
    else:
        LOGGER.debug('Packager ouput: %s', out)
    return res


class MyLinuxMachine(machine.LinuxMachine):

    def __init__(self, ip, service_handler=machine.eServiceHandlers.SERVICE):
        super(MyLinuxMachine, self).__init__(
            ip,
            config.GUEST_ROOT_USER,
            config.GUEST_ROOT_PASSWORD,
            local=False,
            serviceHandler=service_handler
        )


@attr(tier=1)
class BasePostInstall(TestCase):
    """ rhevm-guest-agent post-install """

    os = None
    cmd_chkconf = None

    def post_install(self):
        """ rhevm-guest-agent post-install """
        self.machine = config.TEMPLATES[self.os]['machine']
        cmd_ls = ['ls', '-l', '/etc/ovirt-guest-agent.conf']
        cmd_passwd = ['grep', 'ovirtagent', '/etc/{passwd,group}']

        self.assertTrue(self.machine.runCmd(cmd_ls)[0])
        if self.cmd_chkconf is not None:
            self.assertTrue(self.machine.runCmd(self.cmd_chkconf)[0])
        self.assertTrue(self.machine.runCmd(cmd_passwd)[0])


@attr(tier=1)
class BaseUninstallGA(TestCase):
    """ rhevm-guest-agent uninstall """
    package_manager = 'yum'
    package = 'ovirt-guest-agent'
    remove_command = 'remove'
    os = None

    def uninstall(self):
        """ uninstall guest agent """
        self.machine = config.TEMPLATES[self.os]['machine']
        self.assertTrue(runPackagerCommand(self.machine, self.package_manager,
                                           self.remove_command, self.package))
        LOGGER.info("Uninstallation of GA passed.")

    def tearDown(self):
        """ install it again """
        self.assertTrue(runPackagerCommand(self.machine, self.package_manager,
                                           'install', self.package))


@attr(tier=1)
class BaseServiceTest(TestCase):
    """ rhevm-guest-agent service test """
    os = None

    def service_test(self):
        """ rhevm-guest-agent start-stop-restart-status """
        machine = config.TEMPLATES[self.os]['machine']

        if machine.isServiceRunning(config.AGENT_SERVICE_NAME):
            machine.stopService(config.AGENT_SERVICE_NAME)

        self.assertTrue(machine.startService(config.AGENT_SERVICE_NAME))
        self.assertTrue(machine.isServiceRunning(config.AGENT_SERVICE_NAME))
        self.assertTrue(machine.stopService(config.AGENT_SERVICE_NAME))
        self.assertFalse(machine.isServiceRunning(config.AGENT_SERVICE_NAME))
        self.assertTrue(machine.restartService(config.AGENT_SERVICE_NAME))
        self.assertTrue(machine.isServiceRunning(config.AGENT_SERVICE_NAME))


@attr(tier=1)
class BaseAgentDataUpdate(TestCase):
    """ rhevm-guest-agent agent function agent data update """

    def agent_data(self):
        raise NotImplementedError("User should implement it in child class!")

    def agent_data_update(self):
        """ rhevm-guest-agent data update """
        self.agent_data()
        self._update_data()
        self.agent_data()

    def _update_data(self):
        pass


@attr(tier=1)
class BaseFunctionContinuity(TestCase):
    """ rhevm-guest-agent agent function continuity """
    os = None

    def _isAgentRunning(self):
        raise NotImplementedError("User should implement it in child class!")

    def agent_data(self):
        raise NotImplementedError("User should implement it in child class!")

    def function_continuity(self):
        """ rhevm-guest-agent function continuity """
        ag = self.agent_data()

        vm_name = config.TEMPLATES[self.os]['vm_name']
        self.assertTrue(vms.migrateVm(True, vm_name))
        self.assertTrue(self._isAgentRunning())
        ag.agent_data()

        self.assertTrue(vms.suspendVm(True, vm_name))
        self.assertTrue(vms.startVm(True, vm_name,
                                    wait_for_status=ENUMS['vm_state_up'],
                                    wait_for_ip=True))
        self.assertTrue(self._isAgentRunning())
        ag.agent_data()
        stop_vdsm(vm_name)
        self.assertTrue(self._isAgentRunning())
        start_vdsm(vm_name)


@attr(tier=1)
class BaseAgentData(TestCase):
    """ rhevm-guest-agent agent data """
    success_msg = "%s of guest agent was successfull on %s"
    stats = 'vdsClient -s 0 getVmStats'
    iface_dict = []
    os = None
    application_list = None
    list_app = None

    def _check_fqdn(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== )[A-Za-z0-9-.]*'"
        fqdn_cmd = ['hostname', '--fqdn']
        fqdn_agent = runOnHost(cmd % (self.stats,
                                      config.TEMPLATES[self.os]['vm_id'],
                                      'FQDN'),
                               config.TEMPLATES[self.os]['vm_name'])
        fqdn_agent = get_data(fqdn_agent)
        res, fqdn_real = self.machine.runCmd(fqdn_cmd)

        self.assertEqual(fqdn_real[:-2], fqdn_agent,
                         "Agent returned wrong FQDN %s != %s" % (fqdn_real,
                                                                 fqdn_agent))

    def _check_net_ifaces(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, config.TEMPLATES[self.os]['vm_id'],
                     'netIfaces')
        iface_agent = runOnHost(cmd, config.TEMPLATES[self.os]['vm_name'])
        LOGGER.info(iface_agent)
        iface_agent = get_data(iface_agent)
        self.assertTrue(iface_agent is not None)
        rc, iface_real = self.machine.runCmd(['ip', 'addr', 'show'])
        iface_real = iface_real[:-2]
        self.iface_dict = ast.literal_eval(iface_agent)
        for it in self.iface_dict:
            self.assertTrue(it['name'] in iface_real)
            self.assertTrue(it['hw'] in iface_real)
            for i in it['inet6'] + it['inet']:
                self.assertTrue(i in iface_real)

    def _check_diskusage(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, config.TEMPLATES[self.os]['vm_id'],
                     'disksUsage')
        df_agent = runOnHost(cmd, config.TEMPLATES[self.os]['vm_name'])
        df_agent = get_data(df_agent)
        df_dict = ast.literal_eval(df_agent)

        for fs in df_dict:
            rc, df_real = self.machine.runCmd(['df', '-B', '1', fs['path']])
            df_real = df_real[:-2]
            self.assertTrue(fs['total'] in df_real)
            # if fs['path'] != '/':
            #    self.assertTrue(fs['used'] in df_real)

    def _check_applist(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, config.TEMPLATES[self.os]['vm_id'],
                     'appsList')
        app_agent = runOnHost(cmd, config.TEMPLATES[self.os]['vm_name'])
        app_agent = get_data(app_agent)
        app_list = ast.literal_eval(app_agent)

        for app in self.application_list:
            self._check_app(app, app_list)

    def _check_app(self, app, app_list):
        self.list_app.extend(['|', 'grep', '-o', app])
        rc, app_real = self.machine.runCmd(self.list_app)
        app_real = app_real[:-2]
        app_real_list = app_real.split('\r\n')

        for app in app_real_list:
            if app.endswith(('i686', 'x86_64', 'noarch')):
                app = app[:app.rfind('.')]
            self.assertTrue(len(filter(lambda x: app in x, app_list)) > 0)

    def _check_guestIP(self):
        ip = ['ifconfig', '|', 'grep', 'inet addr:', '|', 'cut', '-d:',
              '-f2', '|', 'cut', '-d', ' ', '-f', '1']
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, config.TEMPLATES[self.os]['vm_id'],
                     'guestIPs')
        ip_agent = runOnHost(cmd, config.TEMPLATES[self.os]['vm_name'])
        ip_agent = get_data(ip_agent)
        ip_list = ip_agent.split(' ')

        for iface in self.iface_dict:
            ip.insert(1, iface['name'])
            rc, ip_real = self.machine.runCmd(ip)
            ip_real = ip_real[:-2]
            self.assertTrue(ip_real in ip_list)

    def agent_data(self):
        """ rhevm-guest-agent data """
        self.machine = config.TEMPLATES[self.os]['machine']

        self._check_fqdn()
        self._check_net_ifaces()
        self._check_diskusage()
        self._check_applist()
        self._check_guestIP()


@attr(tier=1)
class BaseInstallGA(TestCase):
    """ rhevm-guest-agent install """
    __test__ = False

    def install_guest_agent(self):
        """ install guest agent on rhel """
        # pass, once setup_module passes, then install passes too
