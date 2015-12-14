import ast
import logging
import shlex

from art.core_api.apis_utils import TimeoutingSampler
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.low_level import vms, storagedomains, hosts, disks
from art.rhevm_api.utils import test_utils

from rhevmtests.system.guest_tools.linux_guest_agent import config

from art.rhevm_api.resources.host import Host
from art.rhevm_api.resources.user import RootUser

VM_API = test_utils.get_api('vm', 'vms')
HOST_API = test_utils.get_api('host', 'hosts')
logger = logging.getLogger(__name__)


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


def wait_for_connective(machine, timeout=200, sleep=10):
    for sample in TimeoutingSampler(
        timeout=timeout,
        sleep=sleep,
        func=machine.is_connective,
    ):
        if sample:
            break


def prepare_vms(vm_disks, add_repo=True):
    for image in vm_disks:
        config.TEST_IMAGES[image]['image'] = import_image(image)
        assert vms.createVm(
            positive=True,
            vmName=image,
            vmDescription=image,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE,
            nic=config.NIC_NAME,
            nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.ENUMS['display_type_vnc'],
        )
        config.TEST_IMAGES[image]['id'] = VM_API.find(image).id

    for image in vm_disks:
        if config.TEST_IMAGES[image]['image']._is_import_success(5400):
            assert disks.attachDisk(True, image, image)
            assert vms.startVm(True, image, wait_for_status=config.VM_UP)
            mac = vms.getVmMacAddress(
                True, vm=image, nic=config.NIC_NAME
            )[1].get('macAddress', None)
            logger.info("Mac address is %s", mac)

            ip = test_utils.convertMacToIpAddress(
                True, mac, subnetClassB=config.SUBNET_CLASS
            )[1].get('ip', None)

            machine = Host(ip)
            machine.users.append(
                RootUser(config.GUEST_ROOT_PASSWORD)
            )
            config.TEST_IMAGES[image]['machine'] = machine
            wait_for_connective(machine)
            if not config.UPSTREAM and add_repo:
                vms.add_repo_to_vm(
                    vm_host=machine,
                    repo_name=config.GA_REPO_NAME,
                    baseurl=config.GA_REPO_URL % (
                        config.PRODUCT_BUILD, image[2:5]
                    ),
                )


@attr(tier=2)
class GABaseTestCase(TestCase):
    """ Base class handles preparation of glance image """
    __test__ = False
    stats = 'vdsClient -s 0 getVmStats'

    @classmethod
    def setup_class(cls):
        image = config.TEST_IMAGES[cls.disk_name]
        cls.vm_id = image['id']
        cls.machine = image['machine']
        cls.package_manager = image['manager'](cls.machine)
        wait_for_connective(cls.machine)

    def install_guest_agent(self, package):
        self.assertTrue(
            self.package_manager.install(package),
            "Failed to install '%s' on machine '%s'" % (package, self.machine)
        )
        self.machine.service(config.AGENT_SERVICE_NAME).start()

    def post_install(self, commands=None):
        """
        Check for existence of guest agent config and user/group
        Then run additional commands to be checked

        :param command: command to be checked
        :type command: list
        """
        executor = self.machine.executor()
        rc, _, err = executor.run_cmd(
            ['ls', '-l', '/etc/ovirt-guest-agent.conf']
        )
        self.assertTrue(
            not rc,
            "Failed to check guest agent config: %s" % err
        )
        rc, _, err = executor.run_cmd(
            ['grep', 'ovirtagent', '/etc/{passwd,group}']
        )
        self.assertTrue(
            not rc,
            'User/Group ovirtagent was no found: %s' % err
        )
        rc, out, err = executor.run_cmd([
            'stat',
            '--format=%U:%G',
            '-L',
            '/dev/virtio-ports/com.redhat.rhevm.vdsm',
        ])
        self.assertTrue(
            not rc,
            "Failed to run check of ownership of virtio-ports: %s" % err
        )
        self.assertTrue(
            out.strip() == 'ovirtagent:ovirtagent',
            "Virtio port have invalid ownership '%s': %s" % (out, err)
        )
        if commands:
            for command in commands:
                rc, _, err = executor.run_cmd(command)
                self.assertTrue(
                    not rc,
                    "Failed to run command '%s': %s" % (command, err)
                )

    def uninstall(self, package):
        """ uninstall guest agent """
        self.assertTrue(
            self.package_manager.remove(package),
            "Failed to remove '%s' on machine '%s'" % (package, self.machine)
        )

    def services(self, service_name):
        """ rhevm-guest-agent start-stop-restart-status """
        ga_service = self.machine.service(service_name)
        ga_service.stop()
        self.assertTrue(ga_service.start())
        self.assertTrue(ga_service.stop())
        self.assertTrue(ga_service.restart())

    def _check_fqdn(self):
        fqdn_agent = self._run_cmd_on_hosts_vm(
            shlex.split(
                "%s %s | egrep %s | grep -Po '(?<== )[A-Za-z0-9-.]*'" % (
                    self.stats, self.vm_id, 'FQDN'
                )
            ),
            self.disk_name,
        )
        rc, fqdn_real, err = self.machine.executor().run_cmd([
            'hostname', '--fqdn'
        ])

        self.assertEqual(
            fqdn_real.strip(), fqdn_agent,
            "Agent returned wrong FQDN '%s' != '%s'" % (fqdn_real, fqdn_agent)
        )

    def get_ifaces(self):
        cmd = shlex.split(
            "%s %s | egrep %s | grep -Po '(?<== ).*'" % (
                self.stats,
                self.vm_id,
                'netIfaces',
            )
        )
        iface_agent = self._run_cmd_on_hosts_vm(cmd, self.disk_name)
        logger.info(iface_agent)
        self.assertTrue(iface_agent is not None)
        return ast.literal_eval(iface_agent)

    def _check_net_ifaces(self):
        rc, iface_real, err = self.machine.executor().run_cmd([
            'ip', 'addr', 'show'
        ])
        iface_real = iface_real.strip()
        for it in self.get_ifaces():
            self.assertTrue(it['name'] in iface_real)
            self.assertTrue(it['hw'] in iface_real)
            for i in it['inet6'] + it['inet']:
                self.assertTrue(i in iface_real)

    def _check_diskusage(self):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = shlex.split(cmd % (self.stats, self.vm_id, 'disksUsage'))
        df_agent = self._run_cmd_on_hosts_vm(cmd, self.disk_name)
        df_dict = ast.literal_eval(df_agent)

        for fs in df_dict:
            rc, df_real, err = self.machine.executor().run_cmd([
                'df', '-B', '1', fs['path']]
            )
            df_real = df_real.strip()
            self.assertTrue(fs['total'] in df_real)

    def _check_applist(self, application_list, list_app_cmd):
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = shlex.split(cmd % (self.stats, self.vm_id, 'appsList'))
        app_agent = self._run_cmd_on_hosts_vm(cmd, self.disk_name)
        app_list = ast.literal_eval(app_agent)

        for app in application_list:
            self._check_app(list_app_cmd, app, app_list)

    def _check_app(self, list_app_cmd, app, app_list):
        rc, app_real, err = self.machine.executor().run_cmd(
            [list_app_cmd] + ['|', 'grep', '-o', app]
        )
        app_real = app_real.strip()
        app_real_list = app_real.split('\r\n')

        for app in app_real_list:
            if app.endswith(('i686', 'x86_64', 'noarch')):
                app = app[:app.rfind('.')]
            self.assertTrue(len(filter(lambda x: app in x, app_list)) > 0)

    def _check_guestIP(self):
        ip = ['ifconfig', '|', 'grep', 'inet addr:', '|', 'cut', '-d:',
              '-f2', '|', 'cut', '-d', ' ', '-f', '1']
        cmd = "%s %s | egrep %s | grep -Po '(?<== ).*'"
        cmd = shlex.split(cmd % (self.stats, self.vm_id, 'guestIPs'))
        ip_agent = self._run_cmd_on_hosts_vm(cmd, self.disk_name)
        ip_list = ip_agent.split(' ')

        for iface in self.get_ifaces():
            ip.insert(1, iface['name'])
            rc, ip_real, err = self.machine.executor().run_cmd(ip)
            ip_real = ip_real.strip()
            self.assertTrue(ip_real in ip_list)

    def agent_data(self, application_list, list_app_cmd):
        """ rhevm-guest-agent data """
        self._check_fqdn()
        self._check_net_ifaces()
        self._check_diskusage()
        self._check_applist(application_list, list_app_cmd)
        self._check_guestIP()

    def is_agent_running(self):
        return self.machine.service(config.AGENT_SERVICE_NAME).status()

    def function_continuity(self, application_list, list_app_cmd):
        """ rhevm-guest-agent function continuity """
        self.assertTrue(self.is_agent_running())
        self.assertTrue(vms.migrateVm(True, self.disk_name))
        self.assertTrue(self.is_agent_running())
        self.agent_data(application_list, list_app_cmd)

    def _run_cmd_on_hosts_vm(self, cmd, vm_name):
        host = Host(hosts.get_host_vm_run_on(vm_name))
        host.users.append(
            RootUser(config.VDC_ROOT_PASSWORD)
        )
        rc, out, err = host.executor().run_cmd(cmd)
        if rc:
            logger.error("Failed to run cmd '%s': %s", cmd, err)
            return None

        return out.strip()
