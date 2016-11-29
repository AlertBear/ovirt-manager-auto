"""
Sanity test of guest agent of rhel 7 64b
"""
import shlex
import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow
from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

DISK_NAME = 'rhel7_x64_Disk1'


@pytest.fixture(scope="module", autouse=True)
def setup_module(request):
    def fin():
        testflow.teardown("Remove VM %s", DISK_NAME)
        assert vms.removeVm(True, DISK_NAME, stopVM='true')
    request.addfinalizer(fin)
    common.prepare_vms([DISK_NAME])


class RHEL7GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 7
    """
    __test__ = False
    package = config.GA_NAME
    list_app = ['rpm -qa']
    application_list = ['kernel', config.GA_NAME]
    cmd_chkconf = [
        'systemctl', 'list-unit-files', '|',
        'grep', 'ovirt', '|',
        'grep', 'enabled',
    ]

    @pytest.fixture(scope="class")
    def rhel7_setup(self, request):
        cls = request.cls

        def fin():
            testflow.teardown("Shutdown VM %s", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
            testflow.teardown("Undo snapshot preview")
            assert vms.undo_snapshot_preview(True, cls.vm_name)
            vms.wait_for_vm_snapshots(cls.vm_name, config.SNAPSHOT_OK)
        request.addfinalizer(fin)

        super(RHEL7GATest, cls).ga_base_setup()
        testflow.setup(
            "Preview snapshot %s of VM %s", cls.vm_name, cls.vm_name
        )
        assert vms.preview_snapshot(True, cls.vm_name, cls.vm_name)
        vms.wait_for_vm_snapshots(
            cls.vm_name,
            config.SNAPSHOT_IN_PREVIEW,
            cls.vm_name
        )
        testflow.setup("Start VM %s", cls.vm_name)
        assert vms.startVm(True, cls.vm_name, wait_for_status=config.VM_UP)
        common.wait_for_connective(cls.machine)

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

        testflow.step("Check that IP reported is correct")
        for iface in self.get_ifaces():
            ip.insert(1, iface['name'])
            rc, ip_real, err = self.machine.executor().run_cmd(ip)
            ip_real = ip_real.strip()
            assert ip_real in ip_list, (
                "Guest IP '%s' is not in IP list '%s'" % (ip_real, ip_list)
            )


@attr(tier=2)
class RHEL764bGATest(RHEL7GATest):
    """
    Cover basic testing of GA of rhel 7 64b
    """
    __test__ = True
    vm_name = disk_name = DISK_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel764_setup(cls, rhel7_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_URL % cls.os_codename
        )

    @polarion('RHEVM3-7378')
    def test_aa_install_guest_agent(self):
        """ RHEL7_1_64b install_guest_agent """
        self.install_guest_agent(config.GA_NAME)

    @polarion('RHEVM3-7400')
    def test_zz_uninstall_guest_agent(self):
        """ RHEL7_1_64b uninstall_guest_agent """
        self.uninstall('%s*' % config.GA_NAME)

    @polarion('RHEVM3-7380')
    def test_post_install(self):
        """ RHEL7_1_64b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])
        testflow.step("Check that there are open virtio ports")
        rc, out, err = self.machine.executor().run_cmd([
            'stat', '-L', '/dev/virtio-ports/*rhevm*',
            '|', 'grep', 'Uid',
            '|', 'grep', '660'
        ])
        assert not rc, "Failed to check virtio ports: %s" % err
        if not config.UPSTREAM:
            testflow.step("Check tuned profile")
            rc, out, err = self.machine.executor().run_cmd([
                'tuned-adm', 'list', '|',
                'grep', '^Current', '|',
                'grep', '-i', 'virtual',
            ])
            assert not rc, (
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

    @polarion("RHEVM3-7388")
    def test_function_continuity(self):
        """ RHEL7_1x64, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app)


@attr(tier=2)
class UpgradeRHEL764bGATest(RHEL7GATest):
    """
    Cover basic testing upgrade of GA of rhel 7 64b
    """
    __test__ = True
    vm_name = disk_name = DISK_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel764_setup(cls, rhel7_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_OLDER_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_OLDER_NAME,
            baseurl=config.GA_REPO_OLDER_URL % cls.os_codename
        )

    @polarion('RHEVM3-7404')
    def test_upgrade_guest_agent(self):
        """ RHEL7_1_64b upgrade_guest_agent """
        if not config.UPSTREAM:
            self.upgrade_guest_agent(config.OLD_GA_NAME)
        else:
            self.upgrade_guest_agent(config.GA_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app)
