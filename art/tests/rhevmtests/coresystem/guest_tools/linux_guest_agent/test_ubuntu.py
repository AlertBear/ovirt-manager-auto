'''
Ubuntu guest agent test
'''
import logging
import pytest

from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow
from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.coresystem.guest_tools.linux_guest_agent import common
from rhevmtests.coresystem.guest_tools.linux_guest_agent import config

logger = logging.getLogger(__name__)
NAME = 'ovirt-guest-agent'
DISK_NAME = 'ubuntu-16.04_Disk1'
KEY_ID = 'D5C7F7C373A1A299'
APT_KEY = '73A1A299'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    vm_name = DISK_NAME

    def fin():
        testflow.teardown("Remove VM %s", vm_name)
        assert vms.removeVm(True, vm_name, stopVM='true')
    request.addfinalizer(fin)

    common.prepare_vms([DISK_NAME])
    testflow.setup("Start VM %s", vm_name)
    assert vms.startVm(True, vm_name, wait_for_status=config.VM_UP)
    machine = config.TEST_IMAGES[vm_name]['machine']

    executor = machine.executor()
    testflow.setup("Add %s repo to VM %s", config.UBUNTU_REPOSITORY, vm_name)
    rc, _, err = executor.run_cmd([
        'echo', 'deb', config.UBUNTU_REPOSITORY, './',
        '>>', '/etc/apt/sources.list',
    ])
    assert not rc, "Failed to add repo to vm '%s': %s" % (machine, err)
    logger.info(
        "Vm's '%s' repo '%s' enabled", machine, config.UBUNTU_REPOSITORY
    )
    testflow.setup("Add gpg key to %s repo", config.UBUNTU_REPOSITORY)
    rc, _, err = executor.run_cmd([
        'gpg', '-v', '-a', '--keyserver',
        '%sRelease.key' % config.UBUNTU_REPOSITORY,
        '--recv-keys', KEY_ID
    ])
    assert not rc, "Failed to import key to vm '%s': %s" % (machine, err)
    rc, _, err = executor.run_cmd([
        'gpg', '--export', '--armor', APT_KEY, '|', 'apt-key', 'add', '-'
    ])
    assert not rc, "Failed to import apt key to vm '%s': %s" % (machine, err)
    logger.info('Gpg keys exported.')

    testflow.setup("Update system")
    assert machine.package_manager.update(), 'Failed to update system'


@pytest.mark.skip(
    "There is no GA for Ubuntu that would work with 4.2 "
    "(https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=863806)"
)
@attr(tier=3)
class TestUbuntu1604TestCase(common.GABaseTestCase):
    """ Sanity testing of ubuntu guest agent """
    vm_name = disk_name = DISK_NAME
    list_app = ['dpkg --list']
    application_list = [
        'ovirt-guest-agent', 'linux-image', 'xserver-xorg-video-qxl'
    ]

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def ubuntu_setup(cls, request):
        def fin():
            testflow.teardown("Stop VM %s safely", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
        request.addfinalizer(fin)
        super(TestUbuntu1604TestCase, cls).ga_base_setup()

    @polarion("RHEVM3-9331")
    def test_aa_install_guest_agent(self):
        """ Ubuntu rhevm-guest-agent install """
        self.install_guest_agent(NAME)

    @polarion("RHEVM3-9333")
    def test_post_install(self):
        """ Ubuntu rhevm-guest-agent post-install """
        self.post_install()

    @polarion("RHEVM3-9335")
    def test_service_test(self):
        """ Ubuntu rhevm-guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion("RHEVM3-9325")
    def test_agent_data(self):
        """ Ubuntu rhevm-guest-agent data """
        self.agent_data(self.application_list, self.list_app)

    @polarion("RHEVM3-9330")
    def test_function_continuity(self):
        """ Ubuntu rhevm-guest-agent function continuity """
        self.function_continuity(self.application_list, self.list_app)

    @polarion("RHEVM3-9337")
    def test_zz_uninstall_guest_agent(self):
        """ Ubuntu rhevm-guest-agent uninstall """
        self.uninstall(NAME)
