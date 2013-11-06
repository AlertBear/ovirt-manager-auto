#!/usr/bin/env python

__test__ = True

import config
import logging

from unittest import TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import bz, tcms

LOGGER = logging.getLogger(__name__)

TEST_FOLDER = '/root/do_not_remove'
CN = 'cn=Manager,dc=brq-openldap,dc=rhev,dc=lab,dc=eng,dc=brq,dc=redhat,dc=com'

CMD = "ldapmodify -v -D '" + CN + "' -h $(hostname) -w 123456 -f %s"


def connectionTest():
    try:
        return general.getProductName()[0]
    except AttributeError:
        return False


def addUser(user_name):
    users.addUser(True, user_name=user_name, domain=config.LDAP_DOMAIN)


def loginAsUser(user_name, filter):
    users.loginAsUser(user_name, config.LDAP_DOMAIN,
                      config.USER_PASSWORD, filter)


def loginAsAdmin():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.USER_PASSWORD, False)


class LDAPCase289010(TestCase):
    """
    Login as normal user and user from group.
    """
    __test__ = True

    def setUp(self):
        addUser(config.LDAP_REGULAR_NAME)
        users.addGroup(True, group_name=config.LDAP_GROUP)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP, config.MAIN_CLUSTER_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_REGULAR_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289010)
    def normalUserAndGroupUser(self):
        """ Authenticate as normal user and user from group """
        msg_f = "%s user can't log in."
        msg_t = "%s user can log in."

        loginAsUser(config.LDAP_REGULAR_NAME, True)
        self.assertTrue(connectionTest(), msg_f % 'Regular')
        LOGGER.info(msg_t % 'Regular')

        loginAsUser(config.LDAP_USER_FROM_GROUP, True)
        self.assertTrue(connectionTest(), msg_f % 'Group')
        LOGGER.info(msg_t % 'Group')

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_REGULAR_NAME,
                         domain=config.LDAP_DOMAIN)
        users.removeUser(positive=True, user=config.LDAP_USER_FROM_GROUP,
                         domain=config.LDAP_DOMAIN)
        users.deleteGroup(positive=True, group_name=config.LDAP_GROUP)


class LDAPCase289066(TestCase):
    """
    Login as user with disabled account.
    """
    __test__ = True

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.LDAP_EXPIRED_PSW_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_EXPIRED_PSW_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289066)
    def expiredPassword(self):
        """ Login as user with disabled account """
        msg = "User with expired psw can login."
        loginAsUser(config.LDAP_EXPIRED_PSW_NAME, True)
        self.assertTrue(not connectionTest(), msg)
        LOGGER.info("User with expired password can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_EXPIRED_PSW_NAME,
                         domain=config.LDAP_DOMAIN)


class LDAPCase289068(TestCase):
    __test__ = True

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.LDAP_EXPIRED_ACC_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_EXPIRED_ACC_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289068)
    def expiredAccount(self):
        """ Login as user with expired password """
        msg = "User with expired acc can login."
        loginAsUser(config.LDAP_EXPIRED_ACC_NAME, True)
        self.assertTrue(not connectionTest(), msg)
        LOGGER.info("User with expired account can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_EXPIRED_ACC_NAME,
                         domain=config.LDAP_DOMAIN)


class LDAPCase289069(TestCase):
    __test__ = True

    def setUp(self):
        domainID = users.domUtil.find(config.LDAP_DOMAIN).get_id()
        self.query = '/api/domains/' + domainID + '/%s?search={query}'

    @istest
    @bz(1027284)
    @tcms(config.LDAP_TCMS_PLAN_ID, 289069)
    def searchForUsersAndGroups(self):
        """ Search within domain for users and groups """
        self.assertTrue(
            users.groupUtil.query('', href=self.query % 'groups') is not None)

        self.assertTrue(
            len(users.util.query('', href=self.query % 'users')) > 0)
        user = users.util.query("{0}={1}".format('name', 'user2'),
                                href=self.query % 'users')[0]
        self.assertTrue(user.get_name().lower() == 'user2')
        user = users.util.query("{0}={1}".format('lastname', 'user2'),
                                href=self.query % 'users')[0]
        self.assertTrue(user.get_name().lower() == 'user2')
        LOGGER.info("Searching for users and groups works correctly.")


class LDAPCase289071(TestCase):
    __test__ = True
    UPDATE_USER1 = "%s/modify_user1.ldif" % TEST_FOLDER
    UPDATE_USER2 = "%s/modify_user2.ldif" % TEST_FOLDER
    new_name = 'new_name'
    new_last_name = 'new_last_name'
    new_email = 'new_email@mynewemail.com'

    def setUp(self):
        domainID = users.domUtil.find(config.LDAP_DOMAIN).get_id()
        self.query = '/api/domains/' + domainID + '/users?search={query}'
        addUser(config.LDAP_TESTING_USER_NAME)
        self.user = users.util.query(
            "{0}={1}".format('name',
                             config.LDAP_TESTING_USER_NAME),
            href=self.query)[0]

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289071)
    def updateInformation(self):
        """ Update information """
        self.assertTrue(
            runMachineCommand(True, ip=config.LDAP_DOMAIN,
                              cmd=CMD % self.UPDATE_USER1,
                              user=config.OVIRT_ROOT,
                              password=config.LDAP_PASSWORD)[0])
        user = users.util.query("{0}={1}".format('name', self.new_name),
                                href=self.query)[0]
        self.assertTrue(user.get_name() == self.new_name)
        LOGGER.info("User name was updated correctly.")
        self.assertTrue(user.get_last_name() == self.new_last_name)
        LOGGER.info("User last name was updated correctly.")
        self.assertTrue(user.get_email() == self.new_email)
        LOGGER.info("User email was updated correctly.")

    def tearDown(self):
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % self.UPDATE_USER2,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)
        users.removeUser(True, user=config.LDAP_TESTING_USER_NAME,
                         domain=config.LDAP_DOMAIN)


class LDAPCase289072(TestCase):
    __test__ = True

    def setUp(self):
        users.addGroup(True, group_name=config.LDAP_GROUP)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP, config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289072)
    def persistencyOfGroupRights(self):
        """ Persistency of group rights """
        loginAsUser(config.LDAP_USER_FROM_GROUP, True)
        self.assertTrue(connectionTest(), 'User from group cant log in')
        LOGGER.info('User from group logged in')
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_USER_FROM_GROUP,
                         domain=config.LDAP_DOMAIN)
        self.assertTrue(
            users.groupExists(True, config.LDAP_GROUP),
            "Group was removed with user")
        LOGGER.info("Group persisted after user from group was removed.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(True, group_name=config.LDAP_GROUP)


class LDAPCase289076(TestCase):
    __test__ = True

    def setUp(self):
        addUser(config.LDAP_WITH_MANY_GROUPS_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_WITH_MANY_GROUPS_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289076)
    def userWithManyGroups(self):
        """ User with many groups """
        loginAsUser(config.LDAP_WITH_MANY_GROUPS_NAME, 'true')
        self.assertTrue(
            connectionTest(), "User with many groups can't connect to system")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_WITH_MANY_GROUPS_NAME,
                         domain=config.LDAP_DOMAIN)


class LDAPCase289078(TestCase):
    __test__ = True
    DEL_LDIF = 'del_group.ldif'
    ADD_LDIF = 'add_group.ldif'

    DEL_GROUP = "%s/del_group_to_user.ldif" % TEST_FOLDER
    ADD_GROUP = "%s/add_group_to_user.ldif" % TEST_FOLDER
    REMOVE = "ldapdelete -h $(hostname) -D '%s' -w %s -f %s/%s" \
        % (CN, config.LDAP_PASSWORD, TEST_FOLDER, DEL_LDIF)
    ADD = "ldapadd -h $(hostname) -D '%s' -w %s -f %s/%s" \
        % (CN, config.LDAP_PASSWORD, TEST_FOLDER, ADD_LDIF)

    def setUp(self):
        users.addGroup(True, group_name=config.LDAP_GROUP2)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP2, config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(config.LDAP_TCMS_PLAN_ID, 289078)
    def removeUserFromOpenLDAP(self):
        """ remove user from OpenLDAP """
        msg = "After group del, user can login."
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        self.assertTrue(connectionTest(), "User from group can't log in.")
        LOGGER.info("User from group can log in.")
        # Remove group from user
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % self.DEL_GROUP,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)
        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        self.assertTrue(not connectionTest(), msg)
        LOGGER.info("User can't login after group removal.")
        # Add group to user
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % self.ADD_GROUP,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)
        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        self.assertTrue(connectionTest(), "User from group can't log in.")
        LOGGER.info("User from group can log in.")

        # Remove group from OpenLDAP
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=self.REMOVE,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)

        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        self.assertTrue(not connectionTest(), msg)
        LOGGER.info("User can't login after group removal.")

    def tearDown(self):
        loginAsAdmin()
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=self.ADD,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % self.ADD_GROUP,
                          user=config.OVIRT_ROOT,
                          password=config.LDAP_PASSWORD)
        users.deleteGroup(positive=True, group_name=config.LDAP_GROUP2)
