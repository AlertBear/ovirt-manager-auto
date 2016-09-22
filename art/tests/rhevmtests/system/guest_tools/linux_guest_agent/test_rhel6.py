"""
Sanity test of guest agent of rhel 6 32/64b
"""
import pytest
from art.test_handler.tools import polarion

from rhevmtests.system.guest_tools.linux_guest_agent import config
from rhevmtests.system.guest_tools.linux_guest_agent import common

from art.rhevm_api.tests_lib.low_level import vms

DISKx64_NAME = 'rhel6_x64_Disk1'
DISKx86_NAME = 'rhel6_x86_Disk1'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    def fin():
        for vm in [DISKx64_NAME, DISKx86_NAME]:
            assert vms.removeVm(True, vm, stopVM='true')
    request.addfinalizer(fin)
    common.prepare_vms([DISKx64_NAME, DISKx86_NAME])


class RHEL6GATest(common.GABaseTestCase):
    """
    Cover basic testing of GA of rhel 6
    """
    __test__ = False
    list_app = ['rpm', '-qa']
    application_list = ['kernel', 'rhevm-guest-agent-common']
    cmd_chkconf = ['chkconfig', '--list', '|', 'grep',
                   'ovirt', '|', 'egrep', '3:on']

    @pytest.fixture(scope="class")
    def rhel6_setup(self, request):
        cls = request.cls

        def fin():
            assert vms.stop_vms_safely([cls.disk_name])
            assert vms.undo_snapshot_preview(True, cls.disk_name)
            vms.wait_for_vm_snapshots(cls.disk_name, config.SNAPSHOT_OK)
        request.addfinalizer(fin)

        super(RHEL6GATest, cls).ga_base_setup()
        assert vms.preview_snapshot(True, cls.disk_name, cls.disk_name)
        vms.wait_for_vm_snapshots(
            cls.disk_name,
            config.SNAPSHOT_IN_PREVIEW,
            cls.disk_name
        )
        assert vms.startVm(True, cls.disk_name, wait_for_status=config.VM_UP)
        common.wait_for_connective(cls.machine)


class RHEL664bGATest(RHEL6GATest):
    ''' test installation of guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = DISKx64_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel664_setup(cls, rhel6_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_NAME,
                baseurl=config.GA_REPO_URL % (
                    config.PRODUCT_BUILD[:7], cls.disk_name[2:5]
                ),
            )

    @polarion("RHEVM3-7422")
    def test_aa_install_guest_agent(self):
        """ RHEL6_64b install_guest_agent """
        self.install_guest_agent(config.PACKAGE_NAME)

    @polarion("RHEVM3-7423")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_64b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7437")
    def test_post_install(self):
        """ RHEL6_64b rhevm-guest-agent post-install """
        self.post_install()
        rc, out, err = self.machine.executor().run_cmd([
            'stat', '-L', '/dev/virtio-ports/*rhevm*',
            '|', 'grep', 'Uid',
            '|', 'grep', '660'
        ])
        assert not rc, "Failed to check virtio ports: %s" % err
        if not config.UPSTREAM:
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


class RHEL632bGATest(RHEL6GATest):
    ''' test installation of guest agent on rhel 6 32b '''
    __test__ = True
    disk_name = DISKx86_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def rhel632_setup(cls, rhel6_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_NAME,
                baseurl=config.GA_REPO_URL % (
                    config.PRODUCT_BUILD, cls.disk_name[2:5]
                ),
            )

    @polarion("RHEVM3-7420")
    def test_aa_install_guest_agent(self):
        """ RHEL6_32b install_guest_agent """
        self.install_guest_agent(config.PACKAGE_NAME)

    @polarion("RHEVM3-7419")
    def test_zz_uninstall_guest_agent(self):
        """ RHEL6_32b uninstall_guest_agent """
        self.uninstall('%s-*' % config.GA_NAME)

    @polarion("RHEVM3-7410")
    def test_post_install(self):
        """ RHEL6_32b rhevm-guest-agent post-install """
        self.post_install([self.cmd_chkconf])
        rc, out, err = self.machine.executor().run_cmd([
            'stat', '-L', '/dev/virtio-ports/*rhevm*',
            '|', 'grep', 'Uid',
            '|', 'grep', '660'
        ])
        assert not rc, "Failed to check virtio ports: %s" % err
        if not config.UPSTREAM:
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


class UpgradeRHEL664bGATest(RHEL6GATest):
    ''' test of upgrade guest agent on rhel 6 64b '''
    __test__ = True
    disk_name = DISKx64_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel664_setup(cls, rhel6_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_OLDER_NAME,
                baseurl=config.GA_REPO_OLDER_URL % cls.disk_name[2:5],
            )

    @polarion('RHEVM3-7436')
    def test_upgrade_guest_agent(self):
        """ RHEL6_64b upgrade_guest_agent """
        self.upgrade_guest_agent(config.PACKAGE_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app)


class UpgradeRHEL632bGATest(RHEL6GATest):
    ''' test of upgrade guest agent on rhel 6 32b '''
    __test__ = True
    disk_name = DISKx86_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def upgrade_rhel632_setup(cls, rhel6_setup):
        if not config.UPSTREAM:
            vms.add_repo_to_vm(
                vm_host=cls.machine,
                repo_name=config.GA_REPO_OLDER_NAME,
                baseurl=config.GA_REPO_OLDER_URL % cls.disk_name[2:5],
            )

    @polarion('RHEVM3-7421')
    def test_upgrade_guest_agent(self):
        """ RHEL6_32b upgrade_guest_agent """
        self.upgrade_guest_agent(config.PACKAGE_NAME)
        self.services(config.AGENT_SERVICE_NAME)
        self.agent_data(self.application_list, self.list_app)
