'''
Testing authentication of users from IPA.
Nothing is created using default DC and default cluster.
Authentication of expired users, users from group and correct users.
Login formats, user with many groups and if updating of user is propagated.
'''


__test__ = True

import config
import logging

from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_utils import getDS
from art.test_handler.tools import tcms

LOGGER = logging.getLogger(__name__)
KINIT = 'kinit nonascii <<< %s'
UPDATE_USER = 'ipa user-mod %s --last=%s --first=%s'
USER_ROLE = 'UserRole'
User = getDS('User')
Domain = getDS('Domain')
util = get_api('user', 'users')


def connectionTest():
    try:
        return general.getProductName()[0]
    except AttributeError:
        return False


def addUser(user_name):
    userName = '%s@%s' % (user_name, config.IPA_DOMAIN.upper())
    user = User(domain=Domain(name=config.IPA_DOMAIN), user_name=userName)
    user, status = util.create(user, True)


def loginAsUser(user_name, filter):
    users.loginAsUser(user_name, config.IPA_DOMAIN,
                      config.USER_PASSWORD, filter)


def loginAsAdmin():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.USER_PASSWORD, False)


class IPACase93880(TestCase):
    """
    Login as:
     1) User-account which has expired password
     2) User-account whicih is disabled
    """
    __test__ = True

    def setUp(self):
        addUser(config.IPA_EXPIRED_PSW_NAME)
        addUser(config.IPA_DISABLED_NAME)

        mla.addClusterPermissionsToUser(
            True, config.IPA_EXPIRED_PSW_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)
        mla.addClusterPermissionsToUser(
            True, config.IPA_DISABLED_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 93880)
    def authenticateUsersNegative(self):
        """ Authenticate users - negative """
        msg_f = "%s user can log in."
        msg_t = "%s user can't log in."

        loginAsUser(config.IPA_EXPIRED_PSW_NAME, True)
        self.assertFalse(connectionTest(), msg_f % 'Expired')
        LOGGER.info(msg_t % 'Expired')

        loginAsUser(config.IPA_DISABLED_NAME, True)
        self.assertFalse(connectionTest(), msg_f % 'Disabled')
        LOGGER.info(msg_t % 'Disabled')

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.IPA_EXPIRED_PSW_NAME,
                         domain=config.IPA_DOMAIN)
        users.removeUser(positive=True, user=config.IPA_DISABLED_NAME,
                         domain=config.IPA_DOMAIN)


class IPACase93879(TestCase):
    """
    Login as:
     1) with regular user
     2) with a user that is registered to the system via a group
    """
    __test__ = True

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.IPA_REGULAR_NAME)
        mla.addClusterPermissionsToUser(
            True, config.IPA_REGULAR_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)
        # Add user's group, and add it permissions
        users.addGroup(True, group_name=config.IPA_GROUP)
        mla.addClusterPermissionsToGroup(
            True, config.IPA_GROUP, config.MAIN_CLUSTER_NAME, role=USER_ROLE)

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 93880)
    def authenticateUsers(self):
        """ Authenticate users """
        # Login as regular user
        loginAsUser(config.IPA_REGULAR_NAME, True)
        self.assertTrue(connectionTest(), "Regular user can't log in.")
        LOGGER.info("Regular user can log in.")

        # Login as user from group
        loginAsUser(config.IPA_WITH_GROUP_NAME, True)
        self.assertTrue(connectionTest(), "User from group can't log in.")
        LOGGER.info("User from group can log in.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.IPA_REGULAR_NAME,
                         domain=config.IPA_DOMAIN)
        users.deleteGroup(positive=True, group_name=config.IPA_GROUP)


class IPACase93881(TestCase):
    """ Try to login with different login formats """
    __test__ = True

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.IPA_REGULAR_NAME)
        mla.addClusterPermissionsToUser(
            True, config.IPA_REGULAR_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 93881)
    def loginFormats(self):
        """ Login formats """
        msg_f = "Login format %s doesn't not work."
        msg_t = "Login format %s works OK."

        for format in [config.REGULAR_FORMAT1, config.REGULAR_FORMAT2]:
            users.loginAsUser(format, None, config.USER_PASSWORD, True)
            self.assertTrue(connectionTest(), msg_f % format)
            LOGGER.info(msg_t % format)

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.IPA_REGULAR_NAME,
                         domain=config.IPA_DOMAIN)


class IPACase109871(TestCase):
    """ Test if user which has lot of groups assigned can be added & login """
    __test__ = True

    def setUp(self):
        addUser(config.IPA_WITH_MANY_GROUPS_NAME)
        mla.addClusterPermissionsToUser(
            True, config.IPA_WITH_MANY_GROUPS_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 109871)
    def userWithManyGroups(self):
        """ User with many groups """
        loginAsUser(config.IPA_WITH_MANY_GROUPS_NAME, 'true')
        self.assertTrue(
            connectionTest(), "User with many groups can't connect to system")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(True, user=config.IPA_WITH_MANY_GROUPS_NAME,
                         domain=config.IPA_DOMAIN)


class IPACase109146(TestCase):
    """ If user which is part of group is removed, the group still persists """
    __test__ = True

    def setUp(self):
        users.addGroup(True, group_name=config.IPA_GROUP)
        mla.addClusterPermissionsToGroup(
            True, config.IPA_GROUP, config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 109146)
    def persistencyOfGroupRights(self):
        """ Persistency of group rights """
        loginAsUser(config.IPA_WITH_GROUP_NAME, 'false')
        self.assertTrue(connectionTest(), "User from group can't login.")
        LOGGER.info("User from group can login.")
        loginAsAdmin()
        self.assertTrue(users.removeUser(True, user=config.IPA_WITH_GROUP_NAME,
                        domain=config.IPA_DOMAIN))
        self.assertTrue(
            users.groupExists(True, config.IPA_GROUP),
            "Group was removed with user")
        LOGGER.info("Group persisted after user from group was removed.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(True, group_name=config.IPA_GROUP)


class IPACase93882(TestCase):
    """ Try to search via REST with firstname, lastname """
    __test__ = True

    def setUp(self):
        domainID = users.domUtil.find(config.IPA_DOMAIN.lower()).get_id()
        self.query = '/api/domains/' + domainID + '/%s?search={query}'

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 93882)
    def search(self):
        """ Search """
        self.assertTrue(
            users.groupUtil.query('', href=self.query % 'groups') is not None)

        len_of_users = len(users.util.query('', href=self.query % 'users')) > 0
        self.assertTrue(len_of_users)
        user = users.util.query("{0}={1}".format('name', 'uzivatel'),
                                href=self.query % 'users')[0]
        self.assertTrue(user.get_name().lower() == 'uzivatel')
        user = users.util.query("{0}={1}".format('lastname', 'bezskupiny'),
                                href=self.query % 'users')[0]
        self.assertTrue(user.get_last_name().lower() == 'bezskupiny')
        LOGGER.info("Searching for users and groups works correctly.")


class IPACase93883(TestCase):
    """ If the information is updated on IPA side it's propageted to rhevm """
    __test__ = True

    def setUp(self):
        domainID = users.domUtil.find(config.IPA_DOMAIN.lower()).get_id()
        self.query = '/api/domains/' + domainID + '/users?search={query}'
        addUser(config.IPA_TESTING_USER_NAME)
        name_search = "{0}={1}".format('name', config.IPA_TESTING_USER_NAME)
        self.user = users.util.query(name_search, href=self.query)[0]
        self.assertTrue(
            runMachineCommand(True, ip=config.IPA_DOMAIN.lower(),
                              cmd=KINIT % config.USER_PASSWORD,
                              user=config.OVIRT_ROOT,
                              password=config.IPA_PASSWORD)[0])

    @istest
    @tcms(config.IPA_TCMS_PLAN_ID, 93883)
    def update(self):
        """ Update """
        new_name = 'new_name'
        new_last_name = 'new_last_name'

        self.assertTrue(
            runMachineCommand(True, ip=config.IPA_DOMAIN.lower(),
                              cmd=UPDATE_USER % (config.IPA_TESTING_USER_NAME,
                                                 new_last_name, new_name),
                              user=config.OVIRT_ROOT,
                              password=config.IPA_PASSWORD)[0])
        user = users.util.query("{0}={1}".format('name', new_name),
                                href=self.query)[0]
        self.assertTrue(user.get_name() == new_name)
        self.assertTrue(user.get_last_name() == new_last_name)

    def tearDown(self):
        runMachineCommand(True, ip=config.IPA_DOMAIN.lower(),
                          cmd=UPDATE_USER % (config.IPA_TESTING_USER_NAME,
                                             self.user.get_last_name(),
                                             self.user.get_name()),
                          user=config.OVIRT_ROOT,
                          password=config.IPA_PASSWORD)
        users.removeUser(True, user=config.IPA_TESTING_USER_NAME,
                         domain=config.IPA_DOMAIN)
