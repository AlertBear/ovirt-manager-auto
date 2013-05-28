#!/usr/bin/env python

__test__ = True

import logging
import config
from unittest import TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import bz, tcms


LOGGER = logging.getLogger(__name__)

MB = 1024 * 1024
AUTH = 'auth'
AUTH_CONF = 'auth-conf'
SET_AUTH = """rhevm-config -s SASL_QOP=%s && service ovirt-engine restart && while [ "`curl -o /dev/null --silent --head --write-out '%%{http_code}\n' localhost`" != 200 ]; do sleep 1; done"""
TCP_DUMP = 'nohup tcpdump -l -s 65535 -A -vv port 389 -w /tmp/tmp.cap > /dev/null 2>&1 &'
CHECK_DUMP = 'tcpdump -A -r /tmp/tmp.cap 2>/dev/null | grep %s'
CLEAN = 'rm -f /tmp/tmp.cap && kill -9 `pgrep tcpdump`'


def setUpModule():
    assert users.addUser(True, user_name=config.AD2_USER_NAME,
                         domain=config.AD2_DOMAIN)
    for u in [config.AD1_USER_NAME, config.AD1_EXPIRED_PSW,
              config.AD1_EXPIRED_USER, config.AD1_DISABLED,
              config.AD1_USER_WITH_GROUP, config.AD1_NORMAL]:
        assert users.addUser(True, user_name=u, domain=config.AD1_DOMAIN)
        assert mla.addClusterPermissionsToUser(
            True, u, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.AD1_DOMAIN)

    assert mla.addClusterPermissionsToUser(
        True, config.AD2_USER_NAME, config.MAIN_CLUSTER_NAME,
        role='UserRole', domain=config.AD2_DOMAIN)


def tearDownModule():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.USER_PASSWORD, False)
    for u in [config.AD1_EXPIRED_PSW, config.AD1_EXPIRED_USER,
              config.AD1_DISABLED, config.AD1_USER_WITH_GROUP]:
        assert users.removeUser(True, u)
    assert users.removeUser(True, config.AD1_NORMAL, config.AD1_DOMAIN)
    assert users.removeUser(True, config.AD1_USER_NAME, config.AD1_DOMAIN)
    assert users.removeUser(True, config.AD2_USER_NAME, config.AD2_DOMAIN)


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
        msg = "Supposed result is %s, got %s"
        self.assertTrue(
            runMachineCommand(True, ip=config.OVIRT_ADDRESS, cmd=auth,
                              user=config.OVIRT_ROOT,
                              password=config.OVIRT_ROOT_PASSWORD)[0],
            "Run cmd %s failed." % auth)
        self.assertTrue(
            runMachineCommand(True, ip=config.OVIRT_ADDRESS,
                              cmd=TCP_DUMP,
                              user=config.OVIRT_ROOT,
                              password=config.OVIRT_ROOT_PASSWORD)[0],
            "Run cmd %s failed." % TCP_DUMP)

        users.loginAsUser(config.AD1_NORMAL, config.AD1_DOMAIN,
                          config.USER_PASSWORD, 'true')
        self.assertTrue(connectionTest())
        import time;time.sleep(10)

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
