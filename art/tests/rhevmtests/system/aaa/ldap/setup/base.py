import logging
import pytest

from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import mla, users

from rhevmtests.system.aaa.ldap import config, common


logger = logging.getLogger(__name__)


@attr(tier=2)
class AuthBaseCase(TestCase):
    """ test login with user """
    __test__ = False
    password = '123456'
    domain = None
    user = None
    namespace = None

    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self, request):
        def finalize():
            testflow.teardown("Tearing down class %s", self.__name__)

            common.loginAsAdmin()
            testflow.teardown("Removing user %s", self.user)
            users.removeUser(True, self.user)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", self.__name__)
        authz = '%s-authz' % self.domain
        testflow.setup("Adding user %s", self.user)
        assert users.addExternalUser(
            True,
            '%s@%s' % (self.user, authz),
            authz,
            namespace=self.namespace,
        )
        testflow.setup("Adding cluster permissions to user %s", self.user)
        assert mla.addClusterPermissionsToUser(
            True,
            self.user,
            config.CLUSTER_NAME[0],
            role='UserRole',
        )

    def login(self, user=None):
        """ test login with user """
        user = user if user else self.user
        users.loginAsUser(user, self.domain, self.password, True)
        connected = common.connectionTest()
        logger.info(
            "User '%s' %s login",
            user,
            'can' if connected else "can't"
        )
        return connected


class BaseUserFromGroup(AuthBaseCase):
    """ Login as user from group. """
    __test__ = False
    group = 'automation_users_group'
    user = 'automation_user_with_group'

    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self, request):
        testflow.setup("Setting up class %s", self.__name__)

        testflow.setup("Adding group %s", self.group)
        assert users.addGroup(
            True,
            self.group,
            domain='%s-authz' % self.domain
        )

        testflow.setup("Adding cluster permissions to group %s", self.group)
        assert mla.addClusterPermissionsToGroup(
            True,
            self.group,
            config.CLUSTER_NAME[0],
            role='UserRole',
        )

    def user_from_group(self):
        """ Authenticate as user from group """
        assert self.login()

    def tearDown(self):
        common.loginAsAdmin()
        users.deleteGroup(True, group_name=self.group)


class BaseExpiredAccount(AuthBaseCase):
    """ Login as user with expired account """
    __test__ = False
    user = 'automation_expired_account'

    def expired_account(self):
        """ Login as user with expired password """
        assert not self.login()


class BaseExpiredPassword(AuthBaseCase):
    """ Login as user with expired password """
    __test__ = False
    user = 'automation_expired_password'

    def expired_password(self):
        """ Login as user with disabled account """
        assert not self.login()


class BaseDisabledAccount(AuthBaseCase):
    """ Login as disabled user """
    __test__ = False
    user = 'automation_disabled_account'

    def disabled_account(self):
        """ Login as user with disabled account """
        assert not self.login()


@attr(tier=2)
class BaseSpecialCharsSearch(TestCase):
    """ Test search of special characters """
    __test__ = False

    def search(self, special_characters=('#', '%', '$',)):
        """ search special characters """
        logger.info(
            "Trying to search by these '%s' special chars",
            ','.join(special_characters)
        )
        for special_char in special_characters:
            user_name = 'special%s' % special_char
            logger.info("Search for user '%s'", user_name)
            # https://bugzilla.redhat.com/show_bug.cgi?id=1275237
            # When resolved modify this test based, on implmentation details
            assert users.search_user(
                self.domain, 'name', user_name
            ) is not None, "Failed to search by special character '%s'" % (
                special_char
            )
