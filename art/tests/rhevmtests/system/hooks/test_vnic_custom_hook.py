'''
Testing vnic profile hooks: after_update_device_fail,  after_update_device
before_update_device, after_nic_hotunplug, before_nic_hotunplug,
after_nic_hotplug, before_nic_hotplug
'''

__test__ = True

from art.rhevm_api.tests_lib.low_level import hooks, vms, networks
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import tcms
from utilities.enum import Enum
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import CoreSystemTest as TestCase
from time import sleep
from os import path

from rhevmtests.system.hooks import config
import logging

LOGGER = logging.getLogger(__name__)
SPEED = '1000'
CUSTOM_PROPERTIES = 'speed=%s;port_mirroring=True;bandwidth=10000' % SPEED
CUSTOM_PROPERTIES2 = 'port_mirroring=True;bandwidth=10000'
REMOVE_HOOKS = 'rm -f /var/tmp/*.hook'
HOOK_PATH = '/usr/libexec/vdsm/hooks'
TMP = '/var/tmp'
PROFILE_A = 'profile_a'
PROFILE_B = 'profile_B'
PROFILE_BAD_A = 'profile_bad_a'
PROFILE_BAD_B = 'profile_bad_b'
SCRIPT_TYPE = Enum(PYTHON='py', SHELL='sh')
PLAN = config.TCMS_PLAN_VNIC
SLEEP_TIME = 15
UPDATE_NIC = 'update_nic'
HOTUNPLUG_NIC = 'hotunplug_nic'


def setup_module():
    assert vms.createVm(True, config.VM_NAME[0], '',
                        cluster=config.CLUSTER_NAME[0],
                        display_type=config.DISPLAY_TYPE,
                        template=config.TEMPLATE_NAME)
    assert vms.startVm(True, vm=config.VM_NAME[0],
                       wait_for_status=config.VM_UP,
                       wait_for_ip=True)
    assert networks.addVnicProfile(True, name=PROFILE_A,
                                   cluster=config.CLUSTER_NAME[0],
                                   network=config.MGMT_BRIDGE,
                                   custom_properties=CUSTOM_PROPERTIES)
    assert networks.addVnicProfile(True, name=PROFILE_B,
                                   cluster=config.CLUSTER_NAME[0],
                                   network=config.MGMT_BRIDGE,
                                   custom_properties=CUSTOM_PROPERTIES2)
    assert networks.addVnicProfile(False, name=PROFILE_BAD_A,
                                   cluster=config.CLUSTER_NAME[0],
                                   network=config.MGMT_BRIDGE,
                                   custom_properties='test=250')
    assert networks.addVnicProfile(False, name=PROFILE_BAD_B,
                                   cluster=config.CLUSTER_NAME[0],
                                   network=config.MGMT_BRIDGE,
                                   custom_properties='speed=abc')
    assert vms.addNic(True, vm=config.VM_NAME[0], name=UPDATE_NIC,
                      network=config.MGMT_BRIDGE, vnic_profile=PROFILE_A,
                      linked=True)
    assert vms.addNic(True, vm=config.VM_NAME[0], name=HOTUNPLUG_NIC,
                      network=config.MGMT_BRIDGE, vnic_profile=PROFILE_A)


def teardown_module():
    assert runMachineCommand(True, ip=config.HOSTS[0],
                             user=config.HOSTS_USER,
                             password=config.HOSTS_PW,
                             cmd=REMOVE_HOOKS)[0]
    assert vms.removeVm(True, config.VM_NAME[0], stopVM='true')


class TestCaseVnic(TestCase):
    __test__ = False
    CUSTOM_HOOK = 'speed'
    HOOK_NAMES = None

    def _create_python_script_to_verify_custom_hook(self, name):
        my_hook = '%s.hook' % name
        scriptName = '%s.%s' % (name, 'py')
        hooks.createPythonScriptToVerifyCustomHook(
            ip=config.HOSTS[0], password=config.HOSTS_PW,
            scriptName=scriptName, customHook=self.CUSTOM_HOOK,
            target=path.join(HOOK_PATH, name),
            outputFile=path.join(TMP, my_hook))

    def _create_one_line_shell_script(self, name):
        my_hook = '%s.hook' % name
        scriptName = '%s.%s' % (name, 'sh')
        hooks.createOneLineShellScript(ip=config.HOSTS[0],
                                       password=config.HOSTS_PW,
                                       scriptName=scriptName, command='touch',
                                       arguments=path.join(TMP, my_hook),
                                       target=path.join(HOOK_PATH, name))

    def setUp(self):
        """ create python script """
        for n, t in self.HOOK_NAMES.iteritems():
            if t == SCRIPT_TYPE.PYTHON:
                self._create_python_script_to_verify_custom_hook(n)
            elif t == SCRIPT_TYPE.SHELL:
                self._create_one_line_shell_script(n)
            else:
                LOGGER.error("Unsupported script type.")

    def check_for_files(self):
        """ Check for file created by hook """
        result = False
        for name, t in self.HOOK_NAMES.iteritems():
            my_hook = '%s.hook' % name
            LOGGER.info("Checking existence of %s%s", TMP, my_hook)
            ret = hooks.checkForFileExistenceAndContent(
                True, ip=config.HOSTS[0], password=config.HOSTS_PW,
                filename=path.join(TMP, my_hook),
                content=(SPEED if t == SCRIPT_TYPE.PYTHON else None))
            result = result or (not ret)

        self.assertFalse(result)

    def tearDown(self):
        """ remove created script """
        for name, t in self.HOOK_NAMES.iteritems():
            hook_name = '%s/%s.%s' % (name, name, t)
            test_utils.removeFileOnHost(positive=True, ip=config.HOSTS[0],
                                        password=config.HOSTS_PW,
                                        filename=path.join(HOOK_PATH,
                                                           hook_name))


@attr(tier=1)
class TestCaseAfterBeforeNicHotplug(TestCaseVnic):
    """ after_before_nic_hotplug hook """
    __test__ = True

    NIC_NAME = 'hot_plugged_nic'
    HOOK_NAMES = {
        'after_nic_hotplug': SCRIPT_TYPE.SHELL,
        'before_nic_hotplug': SCRIPT_TYPE.PYTHON,
    }

    def setUp(self):
        """ hot plug nic """
        super(TestCaseAfterBeforeNicHotplug, self).setUp()
        assert vms.addNic(True, vm=config.VM_NAME[0], name=self.NIC_NAME,
                          network=config.MGMT_BRIDGE, vnic_profile=PROFILE_A)

    def tearDown(self):
        """ remove created nic """
        assert vms.stopVm(True, config.VM_NAME[0])
        assert vms.removeNic(True, config.VM_NAME[0], self.NIC_NAME)
        assert vms.startVm(True, vm=config.VM_NAME[0],
                           wait_for_status=config.VM_UP,
                           wait_for_ip=True)
        super(TestCaseAfterBeforeNicHotplug, self).tearDown()

    @istest
    @tcms(PLAN, 295122)
    def after_before_nic_hotplug(self):
        """ test_after_before_nic_hotplug """
        self.check_for_files()
        sleep(SLEEP_TIME)  # Sleep to let nic receive network stats


@attr(tier=1)
class TestCaseAfterBeforeNicHotunplug(TestCaseVnic):
    """ before_after_nic_hotunplug hook """
    __test__ = True

    HOOK_NAMES = {
        'before_nic_hotunplug': SCRIPT_TYPE.SHELL,
        'after_nic_hotunplug': SCRIPT_TYPE.PYTHON,
    }

    def setUp(self):
        """ hot unplug nic """
        super(TestCaseAfterBeforeNicHotunplug, self).setUp()
        assert vms.hotUnplugNic(True, vm=config.VM_NAME[0], nic=HOTUNPLUG_NIC)

    def tearDown(self):
        """ plug nic back """
        super(TestCaseAfterBeforeNicHotunplug, self).tearDown()
        assert vms.hotPlugNic(True, config.VM_NAME[0], HOTUNPLUG_NIC)

    @istest
    @tcms(PLAN, 295128)
    def after_before_nic_hotunplug(self):
        """ test_after_before_nic_hotunplug """
        self.check_for_files()


@attr(tier=1)
class TestCaseAfterBeforeUpdateDevice(TestCaseVnic):
    """ before_after_update_device hook """
    __test__ = True

    HOOK_NAMES = {
        'before_update_device': SCRIPT_TYPE.PYTHON,
        'after_update_device': SCRIPT_TYPE.PYTHON,
    }

    def setUp(self):
        """ update nic """
        super(TestCaseAfterBeforeUpdateDevice, self).setUp()
        assert vms.updateNic(True, vm=config.VM_NAME[0], nic=UPDATE_NIC,
                             linked=False, network=config.MGMT_BRIDGE,
                             vnic_profile=PROFILE_A)

    @istest
    @tcms(PLAN, 295144)
    def after_before_update_device(self):
        """ test_after_before_update_device """
        self.check_for_files()


@attr(tier=1)
class TestCaseAfterUpdateDeviceFail(TestCaseVnic):
    """ after_update_device_fail hook """
    __test__ = True

    FAIL_NIC = 'net1'
    NONEXISTENT = 'xxxyxxx'
    UPDATE_FAIL = ('vdsClient -s 0 vmUpdateDevice %s deviceType=interface '
                   'alias=%s network=%s')
    HOOK_NAMES = {'after_update_device_fail': SCRIPT_TYPE.SHELL}

    def setUp(self):
        """ update fail nic """
        super(TestCaseAfterUpdateDeviceFail, self).setUp()
        vm_id = vms.VM_API.find(config.VM_NAME[0]).get_id()
        cmd = self.UPDATE_FAIL % (vm_id, self.FAIL_NIC, self.NONEXISTENT)
        self.assertFalse(
            runMachineCommand(True, ip=config.HOSTS[0],
                              user=config.HOSTS_USER,
                              password=config.HOSTS_PW,
                              cmd=cmd)[0])

    @istest
    @tcms(PLAN, 295174)
    def after_update_device_fail(self):
        """ test_after_update_device_fail """
        self.check_for_files()
