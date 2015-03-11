'''
Testing authentication of users from active directory.
Nothing is created using default DC and default cluster.
Authentication of users expiredPw/expiredAcc/disabled is tested.
Testing authentication user from groups and users from 2 AD.
'''

__test__ = True

import time
import logging
from rhevmtests.system.authentication import config
from art.unittest_lib import CoreSystemTest as TestCase
from nose.tools import istest
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import tcms  # pylint: disable=E0611
from test_base import connectionTest
from utilities.machine import LINUX, Machine
from art.core_api.apis_utils import TimeoutingSampler

LOGGER = logging.getLogger(__name__)
OUT = '> /dev/null 2>&1 &'
MB = 1024 * 1024
AUTH = 'auth'
AUTH_CONF = 'auth-conf'
SET_AUTH = """%s-config -s SASL_QOP=%s"""
TCP_DUMP = 'nohup tcpdump -l -s 65535 -A -vv port 389 -w /tmp/tmp.cap %s' % OUT
CHECK_DUMP = 'tcpdump -A -r /tmp/tmp.cap 2>/dev/null | grep %s'
CLEAN = 'rm -f /tmp/tmp.cap && kill -9 `pgrep tcpdump`'
USERVMMANAGER = 'UserVmManager'
OVIRT = 'ovirt'
ENGINE = 'engine'
RHEVM = 'rhevm'


def teardown_module():
    config.ENGINE_HOST.executor().run_cmd([SET_AUTH % (ENGINE, AUTH)])
    config.ENGINE.restart()
    for status in TimeoutingSampler(
        timeout=70,
        sleep=5,
        func=lambda: config.ENGINE.health_page_status,
    ):
        if status:
            break


def addUserWithClusterPermissions(user_name):
    name, domain = user_name.split('@')
    assert users.addUser(True, user_name=name, domain=domain)
    assert mla.addClusterPermissionsToUser(
        True, name, config.MAIN_CLUSTER_NAME, role=USERVMMANAGER, domain=domain
    )


@attr(tier=1)
class ActiveDirectory(TestCase):
    __test__ = False

    PASSWORD = None
    domain = None
    product = ENGINE

    def __init__(self, *args, **kwargs):
        super(ActiveDirectory, self).__init__(*args, **kwargs)
        if OVIRT not in general.getProductName()[1]['product_name'].lower():
            self.product = ENGINE

    def _loginAsUser(self, user_name, filter=True):
        name, domain = user_name.split('@')
        users.loginAsUser(name, domain, self.PASSWORD, filter)

    @classmethod
    def setup_class(cls):
        for user in [
            config.AD2_USER,
            config.TEST_USER(cls.domain),
            config.EXPIRED_PSW_NAME(cls.domain),
            config.DISABLED_ACC(cls.domain),
            config.EXPIRED_ACC_NAME(cls.domain),
            config.NORMAL_USER(cls.domain),
            config.TEST_USER_DIFFERENT_AD(cls.domain)[0],
        ]:
            addUserWithClusterPermissions(user)
        assert users.addGroup(True, config.GROUP(cls.domain))
        assert mla.addClusterPermissionsToGroup(
            True, config.GROUP(cls.domain),
            config.MAIN_CLUSTER_NAME)

    @classmethod
    def teardown_class(cls):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.USER_PASSWORD, False)
        for username in [
            config.TEST_USER(cls.domain),
            config.EXPIRED_PSW_NAME(cls.domain),
            config.DISABLED_ACC(cls.domain),
            config.EXPIRED_ACC_NAME(cls.domain),
            config.NORMAL_USER(cls.domain),
            config.USER_FROM_GROUP(cls.domain),
            config.TEST_USER_DIFFERENT_AD(cls.domain)[0],
        ]:
            user, domain = username.split('@')
            assert users.removeUser(True, user, domain)
        assert users.deleteGroup(True, config.GROUP(cls.domain))

    def setUp(self):
        users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                          config.USER_PASSWORD, False)

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47586)
    @attr(tier=0)
    def disabledAccount(self):
        """ Disabled account """
        self._loginAsUser(config.DISABLED_ACC(self.domain))
        self.assertFalse(connectionTest(), "User with disabled acc can login.")
        LOGGER.info("User with disabled acc can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47587)
    @attr(tier=0)
    def expiredPassword(self):
        """ Expired password """
        self._loginAsUser(config.EXPIRED_PSW_NAME(self.domain))
        self.assertFalse(connectionTest(), "User with expired psw can login.")
        LOGGER.info("User with expired password can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47585)
    @attr(tier=0)
    def expiredUser(self):
        """ Expired user """
        self._loginAsUser(config.EXPIRED_ACC_NAME(self.domain))
        self.assertFalse(connectionTest(), "Expired user can login.")
        LOGGER.info("Expired user can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 91742)
    @attr(tier=0)
    def fetchingGroupsWithUser(self):
        """ Fetching user groups when logging with UPN """
        user_name = config.USER_FROM_GROUP(self.domain)
        self._loginAsUser(user_name, filter=False)
        groups = users.fetchUserGroups(True, user_name=user_name)
        LOGGER.info("User's groups: %s", [g.get_name() for g in groups])
        assert len(groups)

    def _checkEnc(self, auth, result):
        user, domain = config.NORMAL_USER(self.domain).split('@')

        self.assertTrue(
            runMachineCommand(True, ip=config.VDC_HOST, cmd=auth,
                              user=config.HOSTS_USER,
                              password=config.VDC_PASSWORD)[0],
            "Run cmd %s failed." % auth)
        machine = Machine(config.VDC_HOST, config.HOSTS_USER,
                          config.VDC_PASSWORD).util(LINUX)
        test_utils.restartOvirtEngine(machine, 5, 25, 70)
        self.assertTrue(
            runMachineCommand(True, ip=config.VDC_HOST,
                              cmd=TCP_DUMP,
                              user=config.HOSTS_USER,
                              password=config.VDC_PASSWORD)[0],
            "Run cmd %s failed." % TCP_DUMP)

        users.loginAsUser(user, domain, self.PASSWORD, True)
        self.assertTrue(connectionTest())
        time.sleep(20)

        status = runMachineCommand(True, ip=config.VDC_HOST,
                                   cmd=CHECK_DUMP % user,
                                   user=config.HOSTS_USER,
                                   password=config.VDC_PASSWORD)
        self.assertTrue(status[0] == result, "Run cmd %s failed." % CHECK_DUMP)

        self.assertTrue(
            runMachineCommand(True, ip=config.VDC_HOST, cmd=CLEAN,
                              user=config.HOSTS_USER,
                              password=config.VDC_PASSWORD)[0],
            "Run cmd %s failed." % CLEAN)
        LOGGER.info("Authorization passed.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 91745)
    def ldapEncryption(self):
        """ LDAP encryption """
        self._checkEnc(SET_AUTH % (self.product, AUTH), True)
        self._checkEnc(SET_AUTH % (self.product, AUTH_CONF), False)

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 41716)
    def multipleDomains(self):
        """ Multiple domains: Two ADs, using FQDN names """
        self._loginAsUser(config.TEST_USER(self.domain))
        self.assertTrue(connectionTest())
        user_name, password = config.TEST_USER_DIFFERENT_AD(self.domain)
        name, domain = user_name.split('@')
        users.loginAsUser(name, domain, password, True)
        self.assertTrue(connectionTest())
        LOGGER.info("User with same name from different domains can login.")


class AD(ActiveDirectory):
    """ AD 2003 """
    __test__ = True
    domain = config.AD2_DOMAIN
    PASSWORD = config.USER_PASSWORD


class AD_W2K12_R2(ActiveDirectory):
    """ AD 2012 """
    __test__ = True
    domain = config.W2K12R2_DOMAIN
    PASSWORD = config.W2K12R2_PASSWORD


class AD_W2K8_R2(ActiveDirectory):
    """ AD 2008 """
    __test__ = True
    domain = config.W2K8R2_DOMAIN
    PASSWORD = config.W2K8R2_PASSWORD
