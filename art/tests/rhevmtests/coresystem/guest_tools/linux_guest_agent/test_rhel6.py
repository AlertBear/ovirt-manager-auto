"""
Sanity test of guest agent of rhel 6 32/64b
"""
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import tier2
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import vms

import config
import common

DISKx64_NAME = 'rhel6_x64_Disk1'
DISKx86_NAME = 'rhel6_x86_Disk1'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    def fin():
        for vm in [DISKx64_NAME, DISKx86_NAME]:
            testflow.teardown("Remove VM %s", vm)
            assert vms.removeVm(True, vm, stopVM='true')
    request.addfinalizer(fin)
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


class RHEL6GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 6
    """
    list_app = ['rpm -qa']
    application_list = ['kernel', 'ovirt-guest-agent-common']
    cmd_chkconf = [
        'chkconfig', '--list', '|', 'grep', 'ovirt', '|', 'egrep', '3:on'
    ]

    @classmethod
    @pytest.fixture(scope="class")
    def rhel6_setup(cls, request):
        def fin():
            testflow.teardown("Shutdown VM %s", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
        request.addfinalizer(fin)

        cls.ga_base_setup()
        testflow.setup(
            "Preview snapshot %s of VM %s", cls.vm_name, cls.vm_name
        )
        assert vms.preview_snapshot(
            True, cls.vm_name, cls.vm_name, ensure_vm_down=True
        )
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
        assert vms.runVmOnce(
            True, cls.vm_name, wait_for_state=config.VM_UP, use_cloud_init=True
        )
        common.wait_for_connective(cls.machine)


@tier2
class TestRHEL664bGATest(RHEL6GATest):
    """ test installation of guest agent on rhel 6 64b """
    vm_name = disk_name = DISKx64_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel664_setup(cls, rhel6_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_URL % cls.os_codename
        )

    @polarion("RHEVM3-7422")
    def test_aa_install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        self.install_guest_agent(config.OLD_PACKAGE_NAME)

    @polarion("RHEVM3-7437")
    def test_post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        self.post_install()
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

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
    def test_basic_migration_hook(self):
        """ Test for basic GA migration hook """
        self.ga_hooks.hooks_test(True, "migration")

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
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
    def test_hibernation_hook_legacy_policy(self):
        """
        Check if GA hooks are executed when legacy migration policy is set
        """
        self.ga_hooks.hooks_test(
            True, "hibernation", config.MIGRATION_POLICY_LEGACY
        )

    @polarion("RHEVM3-7423")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        self.uninstall('%s*' % config.GA_NAME)


@tier2
class TestRHEL632bGATest(RHEL6GATest):
    """ test installation of guest agent on rhel 6 32b """
    vm_name = disk_name = DISKx86_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel632_setup(cls, rhel6_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_URL % cls.os_codename
        )

    @polarion("RHEVM3-7420")
    def test_aa_install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        self.install_guest_agent(config.OLD_PACKAGE_NAME)

    @polarion("RHEVM3-7410")
    def test_post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
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

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
    def test_basic_migration_hook(self):
        """ Test for basic GA migration hook """
        self.ga_hooks.hooks_test(True, "migration")

    @polarion("RHEVM-15589")
    @pytest.mark.usefixtures('clean_after_hooks')
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
    def test_hibernation_hook_legacy_policy(self):
        """
        Check if GA hooks are executed when legacy migration policy is set
        """
        self.ga_hooks.hooks_test(
            True, "hibernation", config.MIGRATION_POLICY_LEGACY
        )

    @polarion("RHEVM3-7419")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        self.uninstall('%s*' % config.GA_NAME)


@tier2
class TestUpgradeRHEL664bGATest(RHEL6GATest):
    """ test of upgrade guest agent on rhel 6 64b """
    vm_name = disk_name = DISKx64_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel664_setup(cls, rhel6_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_OLDER_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_OLDER_NAME,
            baseurl=config.GA_REPO_OLDER_URL % cls.os_codename
        )

    @polarion('RHEVM3-7436')
    def test_upgrade_guest_agent(self):
        """ RHEL6_64b upgrade_guest_agent """
        self.upgrade_guest_agent(config.OLD_PACKAGE_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app)


@tier2
class TestUpgradeRHEL632bGATest(RHEL6GATest):
    """ test of upgrade guest agent on rhel 6 32b """
    vm_name = disk_name = DISKx86_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel632_setup(cls, rhel6_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_OLDER_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_OLDER_NAME,
            baseurl=config.GA_REPO_OLDER_URL % cls.os_codename
        )

    @polarion('RHEVM3-7421')
    def test_upgrade_guest_agent(self):
        """ RHEL6_32b upgrade_guest_agent """
        self.upgrade_guest_agent(config.OLD_PACKAGE_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app)
