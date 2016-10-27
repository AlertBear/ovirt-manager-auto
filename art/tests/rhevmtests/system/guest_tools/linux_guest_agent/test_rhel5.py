"""
Sanity test of guest agent of rhel 5 32/64b
"""
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import attr

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

from art.rhevm_api.tests_lib.low_level import vms

DISKx64_NAME = 'rhel5_x64_Disk1'
DISKx86_NAME = 'rhel5_x86_Disk1'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    def fin():
        for vm in [DISKx64_NAME, DISKx86_NAME]:
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
            assert vms.stop_vms_safely([cls.disk_name])
            assert vms.undo_snapshot_preview(True, cls.disk_name)
            vms.wait_for_vm_snapshots(cls.disk_name, config.SNAPSHOT_OK)
        request.addfinalizer(fin)

        super(RHEL5GATest, cls).ga_base_setup()
        assert vms.preview_snapshot(True, cls.disk_name, cls.disk_name)
        vms.wait_for_vm_snapshots(
            cls.disk_name,
            config.SNAPSHOT_IN_PREVIEW,
            cls.disk_name
        )
        assert vms.startVm(True, cls.disk_name, wait_for_status=config.VM_UP)
        common.wait_for_connective(cls.machine)


@attr(tier=3)
class RHEL532bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 32b
    """
    __test__ = True
    disk_name = DISKx86_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel532_setup(cls, rhel5_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_NAME,
                baseurl=config.GA_REPO_URL % (
                    config.PRODUCT_BUILD[:7], cls.disk_name[2:5]
                ),
            )

    @polarion("RHEVM3-7377")
    def test_aa_install_guest_agent(self):
        """ RHEL5_32b install_guest_agent """
        self.install_guest_agent(config.GA_NAME)

    @polarion("RHEVM3-7406")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL5_32b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

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


@attr(tier=3)
class RHEL564bGATest(RHEL5GATest):
    """
    Cover basic testing of GA of rhel 5 64b
    """
    __test__ = True
    disk_name = DISKx64_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel564_setup(cls, rhel5_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_NAME,
                baseurl=config.GA_REPO_URL % (
                    config.PRODUCT_BUILD, cls.disk_name[2:5]
                ),
            )

    @polarion("RHEVM3-7407")
    def test_aa_install_guest_agent(self):
        """ install_guest_agent """
        self.install_guest_agent(config.GA_NAME)

    @polarion("RHEVM3-7408")
    def test_zz_uninstall_guest_agent(self):
        """ uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7431")
    def test_post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])

    @polarion("RHEVM3-7432")
    def test_service_test(self):
        """ RHEL6_64b rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-7433")
    def test_agent_data(self):
        """ RHEL6_64b rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app_cmd)

    @polarion("RHEVM3-7435")
    def test_function_continuity(self):
        """ RHEL6_64b, rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app_cmd)


@attr(tier=3)
class UpgradeRHEL564bGATest(RHEL5GATest):
    """
    Cover basic testing of upgrade GA of rhel 5 64b
    """
    __test__ = True
    disk_name = DISKx64_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel564_setup(cls, rhel5_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_OLDER_NAME,
                baseurl=config.GA_REPO_OLDER_URL % cls.disk_name[2:5],
            )

    @polarion('RHEVM3-7430')
    def test_upgrade_guest_agent(self):
        """ upgrade_guest_agent """
        self.upgrade_guest_agent(config.GA_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app_cmd)


@attr(tier=3)
class UpgradeRHEL532bGATest(RHEL5GATest):
    """
    Cover basic testing of upgrade GA of rhel 5 32b
    """
    __test__ = True
    disk_name = DISKx86_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel532_setup(cls, rhel5_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_OLDER_NAME,
                baseurl=config.GA_REPO_OLDER_URL % cls.disk_name[2:5],
            )

    @polarion('RHEVM3-7424')
    def test_upgrade_guest_agent(self):
        """ upgrade_guest_agent """
        self.upgrade_guest_agent(config.GA_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app_cmd)
