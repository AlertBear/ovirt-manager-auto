"""
Test installation and uninstallation of guest agent on RHEL 5/6 32b/64b
"""
import logging
import config
import art.rhevm_api.utils.test_utils as utils
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from art.test_handler.settings import opts
from art.test_handler.tools import tcms
from art.rhevm_api.tests_lib.low_level import vms, templates
from art.rhevm_api.utils.resource_utils import runMachineCommand


ENUMS = opts['elements_conf']['RHEVM Enums']
LOGGER = logging.getLogger(__name__)
INSTALL_6 = 'yum install -y rhevm-guest-agent rhevm-guest-agent-gdm-plugin'
UNINSTALL_6 = 'yum remove -y rhevm-guest-agent rhevm-guest-agent-gdm-plugin'
INSTALL_5 = 'yum install -y rhevm-guest-agent -x rhevm-guest-agent-common'
UNINSTALL_5 = 'yum remove -y rhevm-guest-agent'


# Please don't change name of test case methods.
# Cases are ran alphabetically and this test rely on it.
class RHEL(TestCase):
    """ Testing installation and uninstallation of guest agent on RHEL 5/6 """
    __test__ = False
    SUCCESS_MSG = "%s of guest agent was successfull on %s"

    @classmethod
    def setup_class(cls):
        """ prepare vms and templates """
        cls.vm_name = 'vm_%s' % cls.TEMPLATE_NAME
        assert templates.importTemplate(
            True, template=cls.TEMPLATE_NAME,
            export_storagedomain=config.EXPORT_STORAGE_DOMAIN,
            import_storagedomain=config.STORAGE_DOMAIN,
            cluster=config.CLUSTER_NAME,
            name=cls.TEMPLATE_NAME)
        assert vms.createVm(True, cls.vm_name, cls.vm_name,
                            cluster=config.CLUSTER_NAME,
                            template=cls.TEMPLATE_NAME,
                            network=config.MGMT_BRIDGE)
        assert vms.startVm(True, cls.vm_name,
                           wait_for_status=ENUMS['vm_state_up'])

        cls.mac = vms.getVmMacAddress(True, vm=cls.vm_name, nic='nic1')
        assert cls.mac[0], "vm %s MAC was not found." % cls.vm_name
        cls.mac = cls.mac[1].get('macAddress', None)
        LOGGER.info("Mac adress is %s", cls.mac)

        cls.ip = utils.convertMacToIpAddress(True, cls.mac,
                                             subnetClassB=config.SUBNET_CLASS)
        assert cls.ip[0], "MacToIp was not corretly converted."
        cls.ip = cls.ip[1].get('ip', None)

    @classmethod
    def teardown_class(cls):
        """ remove vms and templates """
        assert vms.removeVm(True, vm=cls.vm_name, stopVM='true')
        assert templates.removeTemplate(True, cls.TEMPLATE_NAME)

    def _runOnMachine(self, cmd):
        status = runMachineCommand(True, ip=self.ip, cmd=cmd,
                                   user=config.USER_ROOT,
                                   password=config.USER_PASSWORD, timeout=240)
        LOGGER.debug(status)
        return status[0]

    def install_guest_agent(self):
        """ install guest agent on rhel """
        self.assertTrue(self._runOnMachine(self.INSTALL))
        LOGGER.info(self.SUCCESS_MSG % ('Installation', self.TEMPLATE_NAME))

    def uninstall_guest_agent(self):
        """ uninstall guest agent on rhel """
        self.assertTrue(self._runOnMachine(self.UNINSTALL))
        LOGGER.info(self.SUCCESS_MSG % ('Uninstallation', self.TEMPLATE_NAME))


class RHEL6_64b(RHEL):
    """ RHEL6 64b"""
    __test__ = True
    TEMPLATE_NAME = config.RHEL_6_64b
    INSTALL = INSTALL_6
    UNINSTALL = UNINSTALL_6

    @istest
    @tcms(config.TCMS_PLAN_ID, 325219)
    def install_guest_agent(self):
        super(RHEL6_64b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325292)
    def uninstall_guest_agent(self):
        super(RHEL6_64b, self).uninstall_guest_agent()


class RHEL6_32b(RHEL):
    """ RHEL6 32b"""
    __test__ = True
    TEMPLATE_NAME = config.RHEL_6_32b
    INSTALL = INSTALL_6
    UNINSTALL = UNINSTALL_6

    @istest
    @tcms(config.TCMS_PLAN_ID, 325218)
    def install_guest_agent(self):
        super(RHEL6_32b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325291)
    def uninstall_guest_agent(self):
        super(RHEL6_32b, self).uninstall_guest_agent()


class RHEL5_64b(RHEL):
    """ RHEL5 64b"""
    __test__ = True
    TEMPLATE_NAME = config.RHEL_5_64b
    INSTALL = INSTALL_5
    UNINSTALL = UNINSTALL_5

    @istest
    @tcms(config.TCMS_PLAN_ID, 325217)
    def install_guest_agent(self):
        super(RHEL5_64b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325290)
    def uninstall_guest_agent(self):
        super(RHEL5_64b, self).uninstall_guest_agent()


class RHEL5_32b(RHEL):
    """ RHEL5 32b"""
    __test__ = True
    TEMPLATE_NAME = config.RHEL_5_32b
    INSTALL = INSTALL_5
    UNINSTALL = UNINSTALL_5

    @istest
    @tcms(config.TCMS_PLAN_ID, 325215)
    def install_guest_agent(self):
        super(RHEL5_32b, self).install_guest_agent()

    @istest
    @tcms(config.TCMS_PLAN_ID, 325289)
    def uninstall_guest_agent(self):
        super(RHEL5_32b, self).uninstall_guest_agent()
