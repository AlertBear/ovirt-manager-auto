'''
Testing vmdsm hooks and vm hooks: before_vm_start, after_vm_pause,
before_vdsm_start, after_vdsm_stop
'''

__test__ = True

from art.rhevm_api.tests_lib.low_level import hooks, vms, hosts
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from os import path
from art.unittest_lib import CoreSystemTest as TestCase

from rhevmtests.system.hooks import config
import logging

logger = logging.getLogger(__name__)
HOOK_VALUE = '1234'
CUSTOM_HOOK = 'auto_custom_hook=%s' % HOOK_VALUE
REMOVE_HOOKS = 'rm -f /var/tmp/*.hook'
HOOK_DIR = '/usr/libexec/vdsm/hooks'
TMP = '/var/tmp'


def setup_module():
    assert vms.createVm(True, config.HOOKS_VM_NAME, '',
                        cluster=config.CLUSTER_NAME[0],
                        display_type=config.DISPLAY_TYPE,
                        template=config.TEMPLATE_NAME[0],
                        custom_properties=CUSTOM_HOOK)


def teardown_module():
    assert runMachineCommand(True, ip=config.HOSTS_IP[0],
                             user=config.HOSTS_USER,
                             password=config.HOSTS_PW,
                             cmd=REMOVE_HOOKS)[0]
    assert vms.removeVm(True, config.HOOKS_VM_NAME, stopVM='true')


def check_vdsmd():
    if not test_utils.isVdsmdRunning(config.HOSTS_IP[0], config.HOSTS_USER,
                                     config.HOSTS_PW):
        hosts.start_vdsm(config.HOSTS[0], config.HOSTS_PW,
                         config.DC_NAME[0])


def check_vm():
    if not vms.checkVmState(True, config.HOOKS_VM_NAME, config.VM_UP):
        vms.restartVm(
            config.HOOKS_VM_NAME,
            wait_for_ip=True,
            placement_host=config.HOSTS[0] if config.GOLDEN_ENV else None,
        )


class TestCaseVm(TestCase):
    """ vm hooks """
    __test__ = False
    CUSTOM_HOOK = 'auto_custom_hook'
    PY = 'py'

    def setUp(self):
        """ create shell script """
        check_vm()
        hooks.createPythonScriptToVerifyCustomHook(
            ip=config.HOSTS_IP[0],
            password=config.HOSTS_PW,
            scriptName=self._hook_name(ext=self.PY),
            customHook=self.CUSTOM_HOOK,
            target=path.join(HOOK_DIR, self.NAME),
            outputFile=path.join(TMP, self._hook_name()),
        )

    def check_for_file(self, positive):
        """ Check for file created by vdsm_stop hook """
        logger.info("Checking for existence of file %s/%s", TMP, self.NAME)
        return hooks.checkForFileExistenceAndContent(
            positive, ip=config.HOSTS_IP[0], password=config.HOSTS_PW,
            filename=path.join(TMP, self._hook_name()), content=HOOK_VALUE)

    def _hook_name(self, ext='hook'):
        return '%s.%s' % (self.NAME, ext)

    def tearDown(self):
        """ remove created script """
        hook_name = path.join(self.NAME, self._hook_name(ext=self.PY))
        test_utils.removeFileOnHost(positive=True, ip=config.HOSTS_IP[0],
                                    password=config.HOSTS_PW,
                                    filename=path.join(HOOK_DIR, hook_name))
        check_vm()


class TestCaseVdsm(TestCase):
    """ vdsm hooks """
    __test__ = False
    SHELL = 'sh'

    def setUp(self):
        """ create shell script """
        check_vdsmd()
        script_name = self._hook_name(ext=self.SHELL)
        hooks.createOneLineShellScript(ip=config.HOSTS_IP[0],
                                       password=config.HOSTS_PW,
                                       scriptName=script_name,
                                       command='touch',
                                       arguments=path.join(TMP,
                                                           self._hook_name()),
                                       target=path.join(HOOK_DIR, self.NAME))

    def check_for_file(self, positive):
        """ Check for file created by vdsm_stop hook """
        logger.info("Checking for existence of file %s/%s", TMP, self.NAME)
        return hooks.checkForFileExistenceAndContent(
            True, ip=config.HOSTS_IP[0], password=config.HOSTS_PW,
            filename=path.join(TMP, self._hook_name()))

    def _hook_name(self, ext='hook'):
        return '%s.%s' % (self.NAME, ext)

    def tearDown(self):
        """ remove created script """
        hook_name = path.join(self.NAME, self._hook_name(ext=self.SHELL))
        test_utils.removeFileOnHost(positive=True, ip=config.HOSTS_IP[0],
                                    password=config.HOSTS_PW,
                                    filename=path.join(HOOK_DIR, hook_name))
        test_utils.removeFileOnHost(positive=True, ip=config.HOSTS_IP[0],
                                    password=config.HOSTS_PW,
                                    filename=path.join(TMP, self._hook_name()))
        check_vdsmd()


@attr(tier=2)
class TestCaseAfterVdsmStop(TestCaseVdsm):
    """ after_vdsm_stop hook """
    __test__ = True
    NAME = 'after_vdsm_stop'

    @polarion("RHEVM3-8482")
    def test_after_vdsm_stop(self):
        """ test_after_vdsm_stop """
        hosts.stop_vdsm(config.HOSTS[0], config.HOSTS_PW)
        assert self.check_for_file(positive=True)


@attr(tier=2)
class TestCaseBeforeVdsmStart(TestCaseVdsm):
    """ before_vdsm_start hook """
    __test__ = True
    NAME = 'before_vdsm_start'

    @polarion("RHEVM3-8483")
    def test_before_vdsm_start(self):
        """ test_before_vdsm_start """
        hosts.stop_vdsm(config.HOSTS[0], config.HOSTS_PW)
        assert not self.check_for_file(positive=False)
        hosts.start_vdsm(config.HOSTS[0], config.HOSTS_PW,
                         config.DC_NAME[0])
        assert self.check_for_file(positive=True)


@attr(tier=2)
class TestCaseBeforeVmStart(TestCaseVm):
    """ before_vm_start hook """
    __test__ = True
    NAME = 'before_vm_start'

    @polarion("RHEVM3-8484")
    def test_before_vm_start(self):
        """ Check for file created by before_vm_start hook """
        assert vms.stopVm(True, vm=config.HOOKS_VM_NAME)
        assert not self.check_for_file(positive=False)
        assert vms.startVm(
            True,
            vm=config.HOOKS_VM_NAME,
            wait_for_status=config.VM_UP,
            wait_for_ip=True,
            placement_host=config.HOSTS[0] if config.GOLDEN_ENV else None,
        )
        assert self.check_for_file(positive=True)


@attr(tier=2)
class TestCaseAfterVmPause(TestCaseVm):
    """ after_vm_pause hook """
    __test__ = True
    NAME = 'after_vm_pause'

    @polarion("RHEVM3-8485")
    def test_after_vm_pause(self):
        """ Check for file created by after_vm_pause hook """
        assert vms.suspendVm(True, vm=config.HOOKS_VM_NAME, wait=True)
        assert self.check_for_file(positive=True)
