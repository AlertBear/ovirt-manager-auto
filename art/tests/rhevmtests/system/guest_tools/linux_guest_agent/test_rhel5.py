"""
Sanity test of guest agent of rhel 5 32/64b
"""
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

from art.rhevm_api.tests_lib.low_level import vms

DISKx64_NAME = 'rhel5_x64_Disk1'
DISKx86_NAME = 'rhel5_x86_Disk1'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    def fin():
        for vm in [DISKx64_NAME, DISKx86_NAME]:
            testflow.teardown("Remove VM %s", vm)
            assert vms.removeVm(True, vm, stopVM='true')
    request.addfinalizer(fin)
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


class RHEL5GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 5
    """
    __test__ = False
    package = config.GA_NAME
    list_app_cmd = ['rpm -qa']
    application_list = ['kernel', 'rhevm-guest-agent']
    cmd_chkconf = [
        'chkconfig', '--list',
        '|', 'grep', 'ovirt',
        '|', 'egrep', '3:on',
    ]

    @pytest.fixture(scope="class")
    def rhel5_setup(self, request):
        cls = request.cls

        def fin():
            testflow.teardown("Shutdown VM %s", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
            testflow.teardown("Undo snapshot preview")
            assert vms.undo_snapshot_preview(True, cls.vm_name)
            vms.wait_for_vm_snapshots(cls.vm_name, config.SNAPSHOT_OK)
        request.addfinalizer(fin)

        super(RHEL5GATest, cls).ga_base_setup()
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


@attr(tier=3)
@pytest.mark.skipif(
    config.UPSTREAM is None,
    reason="Cannot run on oVirt since 4.0"
)
class RHEL532bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 32b
    """
    __test__ = True
    vm_name = disk_name = DISKx86_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel532_setup(cls, rhel5_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_OLDER_URL % cls.os_codename
        )

    @polarion("RHEVM3-7377")
    def test_aa_install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        self.install_guest_agent(config.OLD_GA_NAME)

    @polarion("RHEVM3-7406")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL5_32b uninstall_guest_agent """
        self.uninstall('%s*' % config.OLD_GA_NAME)

    @polarion("RHEVM3-7425")
    def test_post_install(self):
        """ RHEL5_32b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])

    @polarion("RHEVM3-7426")
    def test_service_test(self):
        """ RHEL5_32b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7427")
    def test_agent_data(self):
        """ RHEL5_32b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app_cmd)

    @polarion("RHEVM3-7429")
    def test_function_continuity(self):
        """ RHEL5_32b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app_cmd)

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


@attr(tier=3)
@pytest.mark.skipif(
    config.UPSTREAM is None,
    reason="Cannot run on oVirt since 4.0"
)
class RHEL564bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 64b
    """
    __test__ = True
    vm_name = disk_name = DISKx64_NAME
    os_codename = disk_name[2:5]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel564_setup(cls, rhel5_setup):
        testflow.setup(
            "Add repo %s to VM %s", config.GA_REPO_NAME, cls.machine
        )
        vms.add_repo_to_vm(
            vm_host=cls.machine,
            repo_name=config.GA_REPO_NAME,
            baseurl=config.GA_REPO_OLDER_URL % cls.os_codename
        )

    @polarion("RHEVM3-7407")
    def test_aa_install_guest_agent(self):
        """ install_guest_agent """
        self.install_guest_agent(config.OLD_GA_NAME)

    @polarion("RHEVM3-7408")
    def test_zz_uninstall_guest_agent(self):
        """ uninstall_guest_agent """
        self.uninstall('%s*' % config.OLD_GA_NAME)

    @polarion("RHEVM3-7431")
    def test_post_install(self):
        """ RHEL5_64b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])

    @polarion("RHEVM3-7432")
    def test_service_test(self):
        """ RHEL5_64b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7433")
    def test_agent_data(self):
        """ RHEL5_64b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app_cmd)

    @polarion("RHEVM3-7435")
    def test_function_continuity(self):
        """ RHEL5_64b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app_cmd)

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
