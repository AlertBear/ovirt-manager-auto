import logging
import pytest
import re

from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.resources import Host, RootUser, VDS
from art.rhevm_api.tests_lib.low_level import (
    clusters, disks, hosts, storagedomains, vms
)
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import testflow

import config

logger = logging.getLogger(__name__)

GA_HOOKS_FOLDER = "/etc/ovirt-guest-agent/hooks.d"
HOOK_NAME = "10_test"
PREFIX = "hooks"


def import_image(diskName, async=True):
    glance_image = storagedomains.GlanceImage(
        image_name=diskName,
        glance_repository_name=config.GLANCE_DOMAIN
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
        func=machine.executor().is_connective,
    ):
        if sample:
            break


def prepare_vms(vm_disks):
    for image in vm_disks:
        testflow.setup("Import image %s", image)
        config.TEST_IMAGES[image]['image'] = import_image(image)
        testflow.setup("Create VM %s", image)
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
        config.TEST_IMAGES[image]['id'] = vms.get_vm(image).id

    for image in vm_disks:
        if config.TEST_IMAGES[image]['image']._is_import_success(3600):
            testflow.setup("Attach disk %s to VM %s", image, image)
            disks.attachDisk(True, image, image)
            if image.startswith(config.RHEL_BASE_IMAGE_NAME):
                testflow.setup("Add snapshot %s to VM %s", image, image)
                assert vms.addSnapshot(True, image, image)
                os_codename = image[2:5]
                repo_url = config.GA_REPO_URL % os_codename
                initialization = vms.init_initialization_obj(
                    {'custom_script': config.CLOUD_INIT_SCRIPT % repo_url}
                )
            elif image.startswith(config.ATOMIC_BASE_IMAGE_NAME):
                initialization = vms.init_initialization_obj(
                    {
                        'user_name': config.GUEST_ROOT_USER,
                        'root_password': config.GUEST_ROOT_PASSWORD,
                        'custom_script': config.ATOMIC_CLOUD_INIT_SCRIPT
                    }
                )
            testflow.setup("Run once VM %s", image)
            assert vms.runVmOnce(
                True, image, wait_for_state=config.VM_UP,
                use_cloud_init=True, initialization=initialization
            )
            ip = vms.wait_for_vm_ip(image)[1].get('ip')

            testflow.setup("Setup a machine with ip %s", ip)
            machine = Host(ip)
            machine.users.append(
                RootUser(config.GUEST_ROOT_PASSWORD)
            )
            config.TEST_IMAGES[image]['machine'] = machine
            wait_for_connective(machine)


class GABaseTestCase(TestCase):
    """ Base class handles preparation of glance image """
    @pytest.fixture(scope="function")
    def clean_after_hooks(self, request):
        def fin():
            testflow.teardown(
                "Remove all files from /tmp starting with %s", PREFIX
            )
            self.machine.fs.remove("/tmp/%s*" % PREFIX)
            testflow.teardown("Remove created hooks")
            self.machine.fs.remove(
                "{0}/*/{1}".format(GA_HOOKS_FOLDER, HOOK_NAME)
            )
            testflow.teardown(
                "Update cluster %s to migration policy %s",
                config.CLUSTER_NAME[0], config.MIGRATION_POLICY_LEGACY
            )
            clusters.updateCluster(
                True, config.CLUSTER_NAME[0],
                migration_policy_id=config.MIGRATION_POLICY_LEGACY
            )
        request.addfinalizer(fin)

    @classmethod
    def ga_base_setup(cls):
        image = config.TEST_IMAGES[cls.disk_name]
        cls.vm_id = image['id']
        cls.machine = image['machine']
        cls.ga_hooks = GAHooks(cls.machine, cls.vm_name)

    def upgrade_guest_agent(self, package):
        testflow.step("Installing package %s", package)
        self.install_guest_agent(package)
        testflow.step("Update repo to newer version")
        vms.add_repo_to_vm(
            vm_host=self.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_URL % self.os_codename
        )
        testflow.step("Updating package %s", package)
        assert self.machine.package_manager.update(
            [package]
        ), "Failed to update package '%s'" % package

    def install_guest_agent(self, package):
        testflow.step("Installing package %s", package)
        assert self.machine.package_manager.install(
            package
        ), "Failed to install '%s' on machine '%s'" % (package, self.machine)
        testflow.step("Starting %s service", config.AGENT_SERVICE_NAME)
        self.machine.service(config.AGENT_SERVICE_NAME).start()
        vms.wait_for_vm_ip(self.vm_name, timeout=config.GAINSTALLED_TIMEOUT)

    def post_install(self, commands=None, root_path=""):
        """
        Check for existence of guest agent config and user/group
        Then run additional commands to be checked

        Args:
            commands (list): command to be checked
            root_path (str): path to root directory for atomic tests
        """
        executor = self.machine.executor()
        testflow.step("Check that there is ovirt-guest-agent.conf directory")
        rc, _, err = executor.run_cmd(
            ['ls', '-l', root_path + '/etc/ovirt-guest-agent.conf']
        )
        assert not rc, "Failed to check guest agent config: %s" % err
        testflow.step("Check that ovirtagent user and group exists")
        rc, _, err = executor.run_cmd(
            ['grep', 'ovirtagent', root_path + '/etc/{passwd,group}']
        )
        assert not rc, 'User/Group ovirtagent was no found: %s' % err
        if commands:
            for command in commands:
                testflow.step("Running command: %s", command)
                rc, _, err = executor.run_cmd(command)
                assert not rc, (
                    "Failed to run command '%s': %s" % (command, err)
                )

    def uninstall(self, package):
        """ uninstall guest agent """
        testflow.step("Removing package %s", package)
        assert self.machine.package_manager.remove(
            package
        ), "Failed to remove '%s' on machine '%s'" % (package, self.machine)

    def services(self, service_name):
        """ rhevm-guest-agent start-stop-restart-status """
        ga_service = self.machine.service(service_name)
        ga_service.stop()
        testflow.step("Starting service %s", service_name)
        assert ga_service.start()
        testflow.step("Stopping service %s", service_name)
        assert ga_service.stop()
        testflow.step("Restarting service %s", service_name)
        assert ga_service.restart()

    def _check_fqdn(self):
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            vms.get_vm, self.vm_name
        ):
            if sample.get_fqdn() and len(sample.get_fqdn()) > 0:
                break
        fqdn_agent = self._get_vm_stats(
            self.vm_name
        ).get("guestFQDN")
        rc, fqdn_real, err = self.machine.executor().run_cmd([
            'hostname', '--fqdn'
        ])

        testflow.step("Check that FQDN is the same on host and inside the VM")
        if (not fqdn_agent.startswith("localhost") and
                not fqdn_real.startswith("localhost")):
            assert fqdn_real.strip() == fqdn_agent, (
                "Agent returned wrong FQDN '%s' != '%s'" %
                (fqdn_real, fqdn_agent)
            )

    def get_ifaces(self):
        iface_agent = self._get_vm_stats(
            self.vm_name
        ).get("netIfaces")
        assert iface_agent is not None
        return iface_agent

    def _check_net_ifaces(self):
        rc, iface_real, err = self.machine.executor().run_cmd([
            'ip', 'addr', 'show'
        ])
        iface_real = iface_real.strip()
        testflow.step(
            "Check that network interfaces on the host correspond "
            "to the ones inside the VM"
        )
        for it in self.get_ifaces():
            assert it['name'] in iface_real
            assert it['hw'] in iface_real
            for i in it['inet6'] + it['inet']:
                assert i in iface_real

    def _check_diskusage(self):
        df_dict = self._get_vm_stats(
            self.vm_name
        ).get("disksUsage")

        testflow.step("Check that disk usage is correct")
        for fs in df_dict:
            rc, df_real, err = self.machine.executor().run_cmd([
                'df', '-B', '1', fs['path']]
            )
            df_real = df_real.strip()
            assert fs['total'] in df_real

    def _check_applist(self, application_list, list_app_cmd):
        app_list = self._get_vm_stats(
            self.vm_name
        ).get("appsList")
        for app in app_list:
            testflow.step("Check if app %s is reporting version", app)
            try:
                re.search("[ -]\d+.*", app).group(0)[1:]
            except AttributeError:
                logger.error("App %s is not reporting version", app)

        if application_list:
            for app in application_list:
                self._check_app(list_app_cmd, app, app_list)

    def _check_app(self, list_app_cmd, app, app_list):
        rc, app_real, err = self.machine.executor().run_cmd(
            [list_app_cmd] + ['|', 'grep', "^" + app + "-[0-9]"]
        )
        app_real = app_real.strip()
        app_real_list = app_real.split('\n')

        testflow.step("Check that all apps are reported correctly")
        for app_real in app_real_list:
            testflow.step("Checking app: %s", app_real)
            if app_real.endswith(('i686', 'x86_64', 'noarch')):
                app_real = app_real[:app_real.rfind('.')]
            assert len(filter(lambda x: app_real in x, app_list)) > 0

    def _check_guestIP(self):
        ip_list = self._get_vm_stats(
            self.vm_name
        ).get("guestIPs").split(' ')
        ip_check_ran = False

        testflow.step("Check that IP reported is correct")
        for ip_real in self.machine.network.find_ips()[0]:
            logger.info("Get IP line returned: %s", ip_real)
            if ip_real:
                ip_check_ran = True
                assert ip_real in ip_list
        assert ip_check_ran, "Check for IP was unsuccessful"

    def agent_data(self, application_list=None, list_app_cmd=None):
        """ rhevm-guest-agent data """
        self._check_fqdn()
        self._check_net_ifaces()
        if not self.vm_name.startswith(config.ATOMIC_BASE_IMAGE_NAME):
            self._check_diskusage()
        self._check_applist(application_list, list_app_cmd)
        self._check_guestIP()

    def is_agent_running(self):
        return self.machine.service(config.AGENT_SERVICE_NAME).status()

    def function_continuity(self, application_list=None, list_app_cmd=None):
        """ rhevm-guest-agent function continuity """
        testflow.step("Check that agent is running")
        assert self.is_agent_running()
        testflow.step("Migrating the VM")
        assert vms.migrateVm(True, self.vm_name)
        testflow.step("Check that agent is running")
        assert self.is_agent_running()
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

    def _get_vm_stats(self, vm_name):
        """
        Run VDSM client cmd VM.getStats on host vm runs on

        Args:
            vm_name (str): vm name

        Returns:
            dict: info about a VM from VDSM
        """
        host = VDS(hosts.get_host_vm_run_on(vm_name), config.VDC_ROOT_PASSWORD)
        return host.vds_client("VM.getStats", {"vmID": self.vm_id})[0]

    def check_admin_session(self):
        """
        Check if there is running session for admin@internal

        Returns:
            bool: True, if the action succeeded, otherwise False
        """
        for session in vms.get_vm_sessions(vm_name=self.vm_name):
            if (
                session.get_console_user()
                and
                session.get_user().get_user_name().startswith("admin")
            ):
                return True
        return False


class GAHooks:
    """ Base class for guest agent hooks tests """
    def __init__(self, machine, vm_name):
        """
        Initialize GA hooks object

        Args:
            machine (Host): VM object
            vm_name (str): name of VM
        """
        self.machine = machine
        self.vm_name = vm_name

    def create_hooks(self, action):
        """
        Create GA hooks on VM

        Args:
            action (str): migration/hibernation
        """
        for folder in (
            "{0}_{1}".format(time, action)
            for time in ["before", "after"]
        ):
            test_filename = "/tmp/{0}_{1}".format(PREFIX, folder)
            file_content = "#!/bin/bash\n\ntouch {0}\n".format(
                test_filename
            )
            hook_path = "{0}/{1}/{2}".format(
                GA_HOOKS_FOLDER, folder, HOOK_NAME
            )
            testflow.step(
                "Create hook file %s with content: %s",
                hook_path, file_content
            )
            self.machine.fs.create_script(file_content, hook_path)

    def check_file_existence(self, filename):
        """
        Check if file exists in /tmp folder

        Args:
            filename (str): filename to check

        Returns:
            bool: True if file was found, False otherwise
        """
        try:
            for sample in TimeoutingSampler(
                config.GAHOOKS_TIMEOUT, 1, self.machine.fs.exists,
                "/tmp/%s" % filename
            ):
                if sample:
                    return True
        except APITimeout:
            return False

    def check_both_tmp_files(self, positive, action):
        """
        Check if both before and after files of action exists

        Args:
            positive (bool): files should or should not be present
            action (str): migration/hibernation
        """
        for filename in (
            "{0}_{1}_{2}".format(PREFIX, time, action)
            for time in ["before", "after"]
        ):
            testflow.step("Check if file %s exists in /tmp", filename)
            assert self.check_file_existence(filename) is positive, (
                "File {0} {1} exist".format(
                    filename, "should" if positive else "shouldn't"
                )
            )

    def hooks_test(
            self, positive, action,
            policy=config.MIGRATION_POLICY_SUSPEND_WORK_IF_NEEDED
    ):
        """
        Basic test if GA hooks for migration are executed

        Args:
            positive (bool): test result should be positive or negative
            action (str): migration/hibernation
            policy (str): ID of migration policy to use
        """
        testflow.step(
            "Update cluster %s to migration policy %s",
            config.CLUSTER_NAME[0], policy
        )
        clusters.updateCluster(
            True, config.CLUSTER_NAME[0], migration_policy_id=policy
        )
        testflow.step("Create hooks for action %s", action)
        self.create_hooks(action)
        if action == "migration":
            testflow.step("Migrate VM %s", self.vm_name)
            vms.migrateVm(True, self.vm_name)
        elif action == "hibernation":
            testflow.step("Suspend VM %s", self.vm_name)
            vms.suspendVm(True, self.vm_name)
            testflow.step("Start VM %s", self.vm_name)
            vms.startVm(True, self.vm_name, wait_for_status=config.VM_UP)
        else:
            logger.error("Invalid action")
        testflow.step(
            "Check if both files from hooks for action %s %s created",
            action, "were" if positive else "were not"
        )
        self.check_both_tmp_files(positive, action)
