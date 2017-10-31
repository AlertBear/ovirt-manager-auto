"""
Sanity test of guest agent of rhel 7 64b
"""
import pytest

from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.coresystem.guest_tools.linux_guest_agent import config
from rhevmtests.coresystem.guest_tools.linux_guest_agent import common

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
    package = config.GA_NAME
    list_app = ['rpm -qa']
    application_list = ['kernel', config.GA_NAME]
    cmd_chkconf = [
        'systemctl', 'list-unit-files', '|',
        'grep', 'ovirt', '|',
        'grep', 'enabled',
    ]

    @classmethod
    @pytest.fixture(scope="class")
    def rhel7_setup(cls, request):
        def fin():
            testflow.teardown("Shutdown VM %s", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
        request.addfinalizer(fin)

        cls.ga_base_setup()
        testflow.setup(
            "Preview snapshot %s of VM %s", cls.vm_name, cls.vm_name
        )
        assert vms.preview_snapshot(True, cls.vm_name, cls.vm_name)
        vms.wait_for_vm_snapshots(
            cls.vm_name,
            config.SNAPSHOT_IN_PREVIEW,
            cls.vm_name
        )
        testflow.setup("Commit snapshot %s of VM %s", cls.vm_name, cls.vm_name)
        assert vms.commit_snapshot(True, cls.vm_name)
        vms.wait_for_vm_snapshots(
            cls.vm_name,
            config.SNAPSHOT_OK,
            cls.vm_name
        )
        testflow.setup("Start VM %s", cls.vm_name)
        assert vms.startVm(
            True, cls.vm_name, wait_for_status=config.VM_UP,
            use_cloud_init=True
        )
        common.wait_for_connective(cls.machine)


@tier2
class TestRHEL764bGATest(RHEL7GATest):
    """
    Cover basic testing of GA of rhel 7 64b
    """
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

    @polarion('RHEVM3-7380')
    @bz({"1508399": {}})
    def test_post_install(self):
        """ RHEL7_1_64b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])
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

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
    def test_basic_migration_hook(self):
        """ Test for basic GA migration hook """
        self.ga_hooks.hooks_test(True, "migration")

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
    @bz({"1507884": {}})
    def test_basic_hibernation_hook(self):
        """ Test for basic GA migration hook """
        self.ga_hooks.hooks_test(True, "hibernation")

    @polarion("RHEVM-16225")
    @pytest.mark.usefixtures('clean_after_hooks')
    def test_migration_hook_legacy_policy(self):
        """
        Check if GA hooks are executed when legacy migration policy is set
        """
        self.ga_hooks.hooks_test(
            False, "migration", config.MIGRATION_POLICY_LEGACY
        )

    @polarion("RHEVM-16316")
    @pytest.mark.usefixtures('clean_after_hooks')
    @bz({"1507884": {}})
    def test_hibernation_hook_legacy_policy(self):
        """
        Check if GA hooks are executed when legacy migration policy is set
        """
        self.ga_hooks.hooks_test(
            True, "hibernation", config.MIGRATION_POLICY_LEGACY
        )

    @polarion("RHEVM-21804")
    def test_sso_logon_to_vm(self):
        """
        Test if you can log on to VM with SSO
        """
        assert vms.set_sso_ticket(vm_name=self.vm_name)
        assert vms.logon_vm(vm_name=self.vm_name)
        assert self.check_admin_session()

    @polarion('RHEVM3-7400')
    def test_zz_uninstall_guest_agent(self):
        """ RHEL7_1_64b uninstall_guest_agent """
        self.uninstall('%s*' % config.GA_NAME)


@tier2
class TestUpgradeRHEL764bGATest(RHEL7GATest):
    """
    Cover basic testing upgrade of GA of rhel 7 64b
    """
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
