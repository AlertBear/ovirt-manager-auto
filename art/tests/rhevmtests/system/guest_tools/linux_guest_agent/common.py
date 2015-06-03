import ast
import logging

from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.test_handler.settings import opts
from art.rhevm_api.tests_lib.low_level import vms, storagedomains, hosts, disks
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils import test_utils
from rhevmtests.system.guest_tools.linux_guest_agent import config
from utilities import machine

__test__ = False

VM_API = test_utils.get_api('vm', 'vms')
HOST_API = test_utils.get_api('host', 'hosts')
ENUMS = opts['elements_conf']['RHEVM Enums']
LOGGER = logging.getLogger(__name__)


def import_image(diskName, async=True):
    glance_image = storagedomains.GlanceImage(
        image_name=diskName,
        glance_repository_name=config.GLANCE_NAME,
    )
    glance_image.import_image(
        destination_storage_domain=config.STORAGE_NAME[0],
        cluster_name=None,
        new_disk_alias=diskName,
        async=async
    )
    return glance_image


def runOnHost(cmd, vm_name):
    LOGGER.info(cmd)
    vm_obj = VM_API.find(vm_name)
    running_host_ip = HOST_API.find(vm_obj.host.id, 'id').get_address()
    return runMachineCommand(True, ip=running_host_ip, user=config.HOSTS_USER,
                             password=config.HOSTS_PW, cmd=cmd)


def start_vdsm(vm_name):
    hosts.start_vdsm(
        HOST_API.find(
            VM_API.find(vm_name).get_id(),
            'id',
        ).get_name(),
        config.HOSTS_PW,
        config.DC_NAME[0],
    )


def stop_vdsm(vm_name):
    hosts.stop_vdsm(
        HOST_API.find(
            VM_API.find(vm_name).get_id(),
            'id',
        ).get_name(),
        config.HOSTS_PW,
    )


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


class GABaseTestCase(TestCase):
    """ Base class handles preparation of glance image """
    __test__ = False

    @classmethod
    def getMachine(cls, diskName):
        """
        Will return machine instance which handle acccess to vm with rhel

        :param diskName: name of the machine disk
        :type diskName: str
        :returns: vm machine object
        :rtype: instance of MyLinuxMachine
        """
        if config.TEST_IMAGES[diskName]['machine'] is None:
            assert disks.attachDisk(True, diskName, diskName)
            assert vms.startVm(True, diskName, wait_for_status=config.VM_UP)
            mac = vms.getVmMacAddress(
                True, vm=diskName, nic=config.NIC_NAME
            )[1].get('macAddress', None)
            LOGGER.info("Mac address is %s", mac)

            ip = test_utils.convertMacToIpAddress(
                True, mac, subnetClassB=config.SUBNET_CLASS
            )[1].get('ip', None)
            myMachine = MyLinuxMachine(ip)
            config.TEST_IMAGES[diskName]['machine'] = myMachine
            assert myMachine.isConnective(attempt=6)

            # FIXME: not flexible, get rid of this
            if 'rhel' in cls.__name__.lower() and not config.UPSTREAM:
                assert myMachine.runCmd(
                    ['wget', config.RHEL_GA_RPM, '-O', '/tmp/ovirt.rpm']
                )[0]
                runPackagerCommand(
                    myMachine,
                    cls.package_manager,
                    'install',
                    '/tmp/ovirt.rpm',
                )
            runPackagerCommand(
                myMachine, cls.package_manager, 'install', config.GA_NAME
            )
            LOGGER.info(
                'guest agent started %s',
                myMachine.startService(config.AGENT_SERVICE_NAME)
            )

        return config.TEST_IMAGES[diskName]['machine']

    @classmethod
    def setup_class(cls):
        image = config.TEST_IMAGES[cls.disk_name]
        assert image['image']._is_import_success(timeout=1800)
        cls.vm_id = image['id']
        cls.package_manager = image['manager']
        cls.machine = cls.getMachine(cls.disk_name)


@attr(tier=1)
class BasePostInstall(GABaseTestCase):
    """ rhevm-guest-agent post-install """
    cmd_chkconf = None

    def post_install(self):
        """ rhevm-guest-agent post-install """
        cmd_ls = ['ls', '-l', '/etc/ovirt-guest-agent.conf']
        cmd_passwd = ['grep', 'ovirtagent', '/etc/{passwd,group}']

        self.assertTrue(self.machine.runCmd(cmd_ls)[0])
        if self.cmd_chkconf is not None:
            self.assertTrue(self.machine.runCmd(self.cmd_chkconf)[0])
        self.assertTrue(self.machine.runCmd(cmd_passwd)[0])


@attr(tier=1)
class BaseUninstallGA(GABaseTestCase):
    """ rhevm-guest-agent uninstall """
    package_manager = 'yum'
    package = 'ovirt-guest-agent'
    remove_command = 'remove'
    os = None

    def uninstall(self):
        """ uninstall guest agent """
        self.assertTrue(runPackagerCommand(self.machine, self.package_manager,
                                           self.remove_command, self.package))
        LOGGER.info("Uninstallation of GA passed.")

    def tearDown(self):
        """ install it again """
        self.assertTrue(runPackagerCommand(self.machine, self.package_manager,
                                           'install', self.package))


@attr(tier=1)
class BaseServiceTest(GABaseTestCase):
    """ rhevm-guest-agent service test """
    os = None

    def service_test(self):
        """ rhevm-guest-agent start-stop-restart-status """
        if self.machine.isServiceRunning(config.AGENT_SERVICE_NAME):
            self.machine.stopService(config.AGENT_SERVICE_NAME)

        self.assertTrue(self.machine.startService(config.AGENT_SERVICE_NAME))
        self.assertTrue(
            self.machine.isServiceRunning(config.AGENT_SERVICE_NAME)
        )
        self.assertTrue(self.machine.stopService(config.AGENT_SERVICE_NAME))
        self.assertFalse(
            self.machine.isServiceRunning(config.AGENT_SERVICE_NAME)
        )
        self.assertTrue(self.machine.restartService(config.AGENT_SERVICE_NAME))
        self.assertTrue(
            self.machine.isServiceRunning(config.AGENT_SERVICE_NAME)
        )


@attr(tier=1)
class BaseAgentDataUpdate(GABaseTestCase):
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
class BaseFunctionContinuity(GABaseTestCase):
    """ rhevm-guest-agent agent function continuity """
    os = None

    def _isAgentRunning(self):
        raise NotImplementedError("User should implement it in child class!")

    def agent_data(self):
        raise NotImplementedError("User should implement it in child class!")

    def function_continuity(self):
        """ rhevm-guest-agent function continuity """
        ag = self.agent_data()

        self.assertTrue(vms.migrateVm(True, self.disk_name))
        self.assertTrue(self._isAgentRunning())
        ag.agent_data()

        self.assertTrue(vms.suspendVm(True, self.disk_name))
        self.assertTrue(vms.startVm(True, self.disk_name,
                                    wait_for_status=ENUMS['vm_state_up'],
                                    wait_for_ip=True))
        self.assertTrue(self._isAgentRunning())
        ag.agent_data()
        stop_vdsm(self.disk_name)
        self.assertTrue(self._isAgentRunning())
        start_vdsm(self.disk_name)


@attr(tier=1)
class BaseAgentData(GABaseTestCase):
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
        fqdn_agent = runOnHost(
            cmd % (self.stats, self.vm_id, 'FQDN'),
            self.disk_name,
        )
        fqdn_agent = get_data(fqdn_agent)
        res, fqdn_real = self.machine.runCmd(fqdn_cmd)

        self.assertEqual(fqdn_real[:-2], fqdn_agent,
                         "Agent returned wrong FQDN %s != %s" % (fqdn_real,
                                                                 fqdn_agent))

    def _check_net_ifaces(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = cmd % (self.stats, self.vm_id, 'netIfaces')
        iface_agent = runOnHost(cmd, self.disk_name)
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
        cmd = cmd % (self.stats, self.vm_id, 'disksUsage')
        df_agent = runOnHost(cmd, self.disk_name)
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
        cmd = cmd % (self.stats, self.vm_id, 'appsList')
        app_agent = runOnHost(cmd, self.disk_name)
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
        cmd = cmd % (self.stats, self.vm_id, 'guestIPs')
        ip_agent = runOnHost(cmd, self.disk_name)
        ip_agent = get_data(ip_agent)
        ip_list = ip_agent.split(' ')

        for iface in self.iface_dict:
            ip.insert(1, iface['name'])
            rc, ip_real = self.machine.runCmd(ip)
            ip_real = ip_real[:-2]
            self.assertTrue(ip_real in ip_list)

    def agent_data(self):
        """ rhevm-guest-agent data """
        self._check_fqdn()
        self._check_net_ifaces()
        self._check_diskusage()
        self._check_applist()
        self._check_guestIP()


@attr(tier=1)
class BaseInstallGA(GABaseTestCase):
    """ rhevm-guest-agent install """
    __test__ = False

    def install_guest_agent(self):
        """ install guest agent on rhel """
        # pass, once setup_module passes, then install passes too
