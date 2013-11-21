'''
Testing authentication of users from active directory.
Nothing is created using default DC and default cluster.
Authentication of users expiredPw/expiredAcc/disabled is tested.
Testing authentication user from groups and users from 2 AD.
'''

__test__ = True

import time
import logging
import config
from unittest import TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import tcms


LOGGER = logging.getLogger(__name__)

OUT = '> /dev/null 2>&1 &'
MB = 1024 * 1024
AUTH = 'auth'
AUTH_CONF = 'auth-conf'
SET_AUTH = """rhevm-config -s SASL_QOP=%s && service ovirt-engine restart"""
TCP_DUMP = 'nohup tcpdump -l -s 65535 -A -vv port 389 -w /tmp/tmp.cap %s' % OUT
CHECK_DUMP = 'tcpdump -A -r /tmp/tmp.cap 2>/dev/null | grep %s'
CLEAN = 'rm -f /tmp/tmp.cap && kill -9 `pgrep tcpdump`'
USERVMMANAGER = 'UserVmManager'


def addUserWithClusterPermissions(user_name):
    name, domain = user_name.split('@')
    assert users.addUser(True, user_name=name, domain=domain)
    assert mla.addClusterPermissionsToUser(True, name,
                                           config.MAIN_CLUSTER_NAME,
                                           role=USERVMMANAGER, domain=domain)

def setUpModule():
    for user in [config.AD1_USER, config.USER_EXPIRED_PSW, config.AD2_USER,
                 config.USER_EXPIRED_USER, config.USER_DISABLED,
                 config.USER_WITH_GROUP, config.AD1_NORMAL_USER]:
        addUserWithClusterPermissions(user)

def tearDownModule():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.USER_PASSWORD, False)
    for username in [config.AD1_USER, config.USER_EXPIRED_PSW, config.AD2_USER,
                     config.USER_EXPIRED_USER, config.USER_DISABLED,
                     config.USER_WITH_GROUP, config.AD1_NORMAL_USER]:
        user, domain = username.split('@')
        assert users.removeUser(True, user, domain)


def connectionTest():
    try:
        return general.getProductName()[0]
    except AttributeError:
        return False


class ActiveDirectory(TestCase):
    __test__ = True

    def setUp(self):
        users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                          config.USER_PASSWORD, False)

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47586)
    def disabledAccount(self):
        """ Disabled account """
        users.loginAsUser(config.AD1_DISABLED, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertFalse(connectionTest(), "User with disabled acc can login.")
        LOGGER.info("User with disabled acc can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47587)
    def expiredPassword(self):
        """ Expired password """
        users.loginAsUser(config.AD1_EXPIRED_PSW, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertFalse(connectionTest(), "User with expired psw can login.")
        LOGGER.info("User with expired password can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 47585)
    def expiredUser(self):
        """ Expired user """
        users.loginAsUser(config.AD1_EXPIRED_USER, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertFalse(connectionTest(), "Expired user can login.")
        LOGGER.info("Expired user can't login.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 91742)
    def fetchingGroupsWithUser(self):
        """ Fetching user groups when logging with UPN """
        users.loginAsUser(config.AD1_USER_WITH_GROUP, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        groups = users.fetchUserGroups(True, user_name=config.USER_WITH_GROUP)
        LOGGER.info("User's groups: %s" % [g.get_name() for g in groups])
        assert len(groups) > 0

    def _checkEnc(self, auth, result):
        user, domain = config.AD1_NORMAL_USER.split('@')

        self.assertTrue(
            runMachineCommand(True, ip=config.OVIRT_ADDRESS, cmd=auth,
                              user=config.OVIRT_ROOT,
                              password=config.OVIRT_ROOT_PASSWORD)[0],
            "Run cmd %s failed." % auth)
        time.sleep(config.RESTART_TIMEOUT)
        self.assertTrue(
            runMachineCommand(True, ip=config.OVIRT_ADDRESS,
                              cmd=TCP_DUMP,
                              user=config.OVIRT_ROOT,
                              password=config.OVIRT_ROOT_PASSWORD)[0],
            "Run cmd %s failed." % TCP_DUMP)

        users.loginAsUser(user, domain, config.USER_PASSWORD, 'true')
        self.assertTrue(connectionTest())
        time.sleep(20)

        status = runMachineCommand(True, ip=config.OVIRT_ADDRESS,
                                   cmd=CHECK_DUMP % config.AD1_NORMAL,
                                   user=config.OVIRT_ROOT,
                                   password=config.OVIRT_ROOT_PASSWORD)
        self.assertTrue(status[0] == result, "Run cmd %s failed." % CHECK_DUMP)

        self.assertTrue(
            runMachineCommand(True, ip=config.OVIRT_ADDRESS, cmd=CLEAN,
                              user=config.OVIRT_ROOT,
                              password=config.OVIRT_ROOT_PASSWORD)[0],
            "Run cmd %s failed." % CLEAN)
        LOGGER.info("Authorization passed.")

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 91745)
    def ldapEncryption(self):
        """ LDAP encryption """
        self._checkEnc(SET_AUTH % AUTH, True)
        self._checkEnc(SET_AUTH % AUTH_CONF, False)

    @istest
    @tcms(config.AD_TCMS_PLAN_ID, 41716)
    def multipleDomains(self):
        """ Multiple domains: Two ADs, using FQDN names """
        users.loginAsUser(config.AD1_USER_NAME, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertTrue(connectionTest())
        users.loginAsUser(config.AD2_USER_NAME, config.AD2_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertTrue(connectionTest())
        LOGGER.info("User with same name from different domains can login.")
