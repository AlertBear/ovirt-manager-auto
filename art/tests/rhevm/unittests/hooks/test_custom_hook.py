'''
Testing vmdsm hooks and vm hooks: before_vm_start, after_vm_pause,
before_vdsm_start, after_vdsm_stop
'''

__test__ = True

from art.rhevm_api.tests_lib.low_level import hooks, vms, hosts
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import tcms
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase

import config
import logging

LOGGER = logging.getLogger(__name__)
HOOK_VALUE = '1234'
CUSTOM_HOOK = 'auto_custom_hook=%s' % HOOK_VALUE
REMOVE_HOOKS = 'rm -f /var/tmp/*.hook'
HOOK_PATH = '/usr/libexec/vdsm/hooks/%s'
TMP = '/var/tmp/%s.hook'


def setup_module():
    assert vms.createVm(True, config.VM_NAME, '', cluster=config.CLUSTER_NAME,
                        display_type=config.DISPLAY_TYPE,
                        template=config.TEMPLATE_NAME,
                        custom_properties=CUSTOM_HOOK)


def teardown_module():
    assert runMachineCommand(True, ip=config.HOST, user=config.VM_LINUX_USER,
                             password=config.VM_LINUX_PASSWORD,
                             cmd=REMOVE_HOOKS)[0]
    assert vms.removeVm(True, config.VM_NAME, stopVM='true')


def check_vdsmd():
    if not test_utils.isVdsmdRunning(config.HOST, config.HOST_USER,
                                     config.HOST_PASSWORD):
        hosts.start_vdsm(config.HOST, config.HOST_PASSWORD,
                         config.DATA_CENTER_NAME)


def check_vm():
    if not vms.checkVmState(True, config.VM_NAME, config.VM_UP):
        vms.stopVm(True, config.VM_NAME)
        vms.startVm(True, config.VM_NAME, wait_for_status=config.VM_UP,
                    wait_for_ip=True)


class TestCaseVm(TestCase):
    """ vm hooks """
    __test__ = False
    CUSTOM_HOOK = 'auto_custom_hook'
    PY = 'py'

    def setUp(self):
        """ create shell script """
        check_vm()
        hooks.createPythonScriptToVerifyCustomHook(
            ip=config.HOST, password=config.HOST_PASSWORD,
            scriptName='%s.%s' % (self.NAME, self.PY),
            customHook=self.CUSTOM_HOOK,
            target=HOOK_PATH % self.NAME,
            outputFile=TMP % self.NAME)

    def check_for_file(self):
        """ Check for file created by vdsm_stop hook """
        LOGGER.info("Checking for existence of file %s%s", TMP, self.NAME)
        return hooks.checkForFileExistenceAndContent(
            True, ip=config.HOST, password=config.HOST_PASSWORD,
            filename=TMP % self.NAME, content=HOOK_VALUE)

    def tearDown(self):
        """ remove created script """
        hook_name = '%s/%s.%s' % (self.NAME, self.NAME, self.PY)
        test_utils.removeFileOnHost(positive=True, ip=config.HOST,
                                    password=config.HOST_PASSWORD,
                                    filename=HOOK_PATH % hook_name)
        check_vm()


class TestCaseVdsm(TestCase):
    """ vdsm hooks """
    __test__ = False
    SHELL = 'sh'

    def setUp(self):
        """ create shell script """
        check_vdsmd()
        script_name = '%s.%s' % (self.NAME, self.SHELL)
        hooks.createOneLineShellScript(ip=config.HOST,
                                       password=config.HOST_PASSWORD,
                                       scriptName=script_name,
                                       command='touch',
                                       arguments=TMP % self.NAME,
                                       target=HOOK_PATH % self.NAME)

    def check_for_file(self):
        """ Check for file created by vdsm_stop hook """
        LOGGER.info("Checking for existence of file %s%s", TMP, self.NAME)
        return hooks.checkForFileExistenceAndContent(
            True, ip=config.HOST, password=config.HOST_PASSWORD,
            filename=TMP % self.NAME)

    def tearDown(self):
        """ remove created script """
        hook_name = '%s/%s.%s' % (self.NAME, self.NAME, self.SHELL)
        test_utils.removeFileOnHost(positive=True, ip=config.HOST,
                                    password=config.HOST_PASSWORD,
                                    filename=HOOK_PATH % hook_name)
        check_vdsmd()


class TestCaseAfterVdsmStop(TestCaseVdsm):
    """ after_vdsm_stop hook """
    __test__ = True
    NAME = 'after_vdsm_stop'

    @istest
    @tcms(config.TCMS_PLAN_CUSTOM, 289788)
    def after_vdsm_stop(self):
        """ test_after_vdsm_stop """
        hosts.stop_vdsm(config.HOST, config.HOST_PASSWORD)
        self.assertTrue(self.check_for_file())


class TestCaseBeforeVdsmStart(TestCaseVdsm):
    """ before_vdsm_start hook """
    __test__ = True
    NAME = 'before_vdsm_start'

    @istest
    @tcms(config.TCMS_PLAN_CUSTOM, 289789)
    def before_vdsm_start(self):
        """ test_before_vdsm_start """
        hosts.stop_vdsm(config.HOST, config.HOST_PASSWORD)
        self.assertFalse(self.check_for_file())
        hosts.start_vdsm(config.HOST, config.HOST_PASSWORD,
                         config.DATA_CENTER_NAME)
        self.assertTrue(self.check_for_file())


class TestCaseBeforeVmStart(TestCaseVm):
    """ befora_vm_start hook """
    __test__ = True
    NAME = 'before_vm_start'

    @istest
    @tcms(config.TCMS_PLAN_CUSTOM, 289791)
    def before_vm_start(self):
        """ Check for file created by befora_vm_start hook """
        self.assertTrue(vms.stopVm(True, vm=config.VM_NAME))
        self.assertFalse(self.check_for_file())
        self.assertTrue(vms.startVm(True, vm=config.VM_NAME,
                                    wait_for_status=config.VM_UP,
                                    wait_for_ip=True))
        self.assertTrue(self.check_for_file())


class TestCaseAfterVmPause(TestCaseVm):
    """ after_vm_pause hook """
    __test__ = True
    NAME = 'after_vm_pause'

    @istest
    @tcms(config.TCMS_PLAN_CUSTOM, 289793)
    def after_vm_pause(self):
        """ Check for file created by after_vm_pause hook """
        self.assertTrue(vms.suspendVm(True, vm=config.VM_NAME, wait=True))
        self.assertTrue(self.check_for_file())
