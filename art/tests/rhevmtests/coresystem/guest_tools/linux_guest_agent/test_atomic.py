'''
Atomic guest agent test
'''
import pytest

from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.tools import polarion
from art.unittest_lib import tier3
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import vms

import common
import config

DISK_NAME = 'ATOMIC-IMAGE-QE'


@pytest.fixture(scope="module", autouse=True)
def setup_vms(request):
    vm_name = DISK_NAME

    def fin():
        testflow.teardown("Remove VM %s", vm_name)
        assert vms.removeVm(True, vm_name, stopVM='true')
    request.addfinalizer(fin)
    common.prepare_vms([vm_name])

    testflow.step("Wait for guest agent to report FQDN")
    for sample in TimeoutingSampler(
        config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
        vms.get_vm, vm_name
    ):
        if sample.get_fqdn() and len(sample.get_fqdn()) > 0:
            break


@tier3
class TestAtomicGA(common.GABaseTestCase):
    """ Sanity testing of atomic guest agent """
    vm_name = disk_name = DISK_NAME

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def atomic_setup(cls, request):
        def fin():
            testflow.teardown("Stop VM %s safely", cls.vm_name)
            assert vms.stop_vms_safely([cls.vm_name])
        request.addfinalizer(fin)
        super(TestAtomicGA, cls).ga_base_setup()

    @polarion('RHEVM3-12076')
    def test_aa_install_guest_agent(self):
        """ RHEL_Atomic install guest_agent """
        pass  # GA is already installed in setup

    @polarion('RHEVM-24775')
    def test_post_install(self):
        """ RHEL_Atomic guest-agent post-install """
        self.post_install(root_path=config.ATOMIC_ROOT)

    @polarion('RHEVM-24776')
    def test_service_test(self):
        """ RHEL_Atomic guest-agent start-stop-restart-status """
        self.services(config.AGENT_SERVICE_NAME)

    @polarion('RHEVM3-12078')
    def test_agent_data(self):
        """ RHEL_Atomic guest-agent data """
        self.agent_data()

    @polarion("RHEVM-24774")
    def test_function_continuity(self):
        """ RHEL_Atomic, guest-agent function continuity """
        self.function_continuity()

    @polarion('RHEVM3-12077')
    def test_zz_uninstall_guest_agent(self):
        """ RHEL_Atomic uninstall guest_agent """
        testflow.step("Remove guest agent container")
        rc, _, err = self.machine.executor().run_cmd(
            ['atomic', '-y', 'containers', 'delete', config.GA_NAME]
        )
        assert not rc, "Failed to remove guest agent container: %s" % err
