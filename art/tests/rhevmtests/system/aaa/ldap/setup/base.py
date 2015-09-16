import logging

from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.low_level import mla, users

from rhevmtests.system.aaa.ldap import config, common


logger = logging.getLogger(__name__)


@attr(tier=0)
class AuthBaseCase(TestCase):
    """ test login with user """
    __test__ = False
    password = '123456'
    domain = None
    user = None

    def setUp(self):
        authz = '%s-authz' % self.domain
        assert users.addExternalUser(True, '%s@%s' % (self.user, authz), authz)
        assert mla.addClusterPermissionsToUser(
            True,
            self.user,
            config.DEFAULT_CLUSTER_NAME,
            role='UserRole',
        )

    def login(self):
        """ test login with user """
        users.loginAsUser(self.user, self.domain, self.password, True)
        connected = common.connectionTest()
        logger.info(
            "User '%s' %s login",
            self.user,
            'can' if connected else "can't"
        )
        return connected

    def tearDown(self):
        common.loginAsAdmin()
        users.removeUser(True, self.user)


class BaseUserFromGroup(AuthBaseCase):
    """ Login as user from group. """
    __test__ = False
    group = 'automation_users_group'
    user = 'automation_user_with_group'

    def setUp(self):
        assert users.addGroup(
            True,
            self.group,
            domain='%s-authz' % self.domain
        )
        assert mla.addClusterPermissionsToGroup(
            True,
            self.group,
            config.DEFAULT_CLUSTER_NAME,
            role='UserRole',
        )

    def user_from_group(self):
        """ Authenticate as user from group """
        self.assertTrue(self.login())

    def tearDown(self):
        common.loginAsAdmin()
        users.deleteGroup(True, group_name=self.group)
        users.removeUser(True, self.user)


class BaseExpiredAccount(AuthBaseCase):
    """ Login as user with expired account """
    __test__ = False
    user = 'automation_expired_account'

    def expired_account(self):
        """ Login as user with expired password """
        self.assertTrue(not self.login())


class BaseExpiredPassword(AuthBaseCase):
    """ Login as user with expired password """
    __test__ = False
    user = 'automation_expired_password'

    def expired_password(self):
        """ Login as user with disabled account """
        self.assertTrue(not self.login())


class BaseDisabledAccount(AuthBaseCase):
    """ Login as disabled user """
    __test__ = False
    user = 'automation_disabled_account'

    def disabled_account(self):
        """ Login as user with disabled account """
        self.assertTrue(not self.login())
