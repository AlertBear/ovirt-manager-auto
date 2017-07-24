import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow
from art.rhevm_api.tests_lib.low_level import mla, users

from rhevmtests.coresystem.aaa.ldap import config, common


logger = logging.getLogger(__name__)


@tier2
class AuthBaseCase(TestCase):
    """ test login with user """
    password = '123456'
    domain = None
    user = None
    namespace = None

    @pytest.fixture(autouse=True, scope="class")
    def setup_base_class(self, request):
        def finalize():
            testflow.teardown("Tearing down class %s", self.__class__.__name__)

            testflow.teardown("Login as admin")
            common.loginAsAdmin()

            testflow.teardown("Removing user %s", self.user)
            try:
                users.removeUser(True, self.user)
            except EntityNotFound as err:
                logger.warning(err)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", self.__class__.__name__)

        testflow.setup("Adding user %s", self.user)
        authz = '%s-authz' % self.domain
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
        testflow.step("Login as user %s", user)
        users.loginAsUser(user, self.domain, self.password, True)

        testflow.step("Testing connection")
        connected = common.connectionTest()
        logger.info(
            "User '%s' %s login",
            user,
            'can' if connected else "can't"
        )
        return connected


class BaseUserFromGroup(AuthBaseCase):
    """ Login as user from group. """
    group = 'automation_users_group'
    user = 'automation_user_with_group'

    @pytest.fixture(autouse=True, scope="class")
    def setup_class(self, request):
        def finalize():
            testflow.teardown("Tearing down class %s", self.__class__.__name__)

            testflow.teardown("Login as admin")
            common.loginAsAdmin()

            testflow.teardown("Deleting group %s", self.group)
            assert users.deleteGroup(True, group_name=self.group)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", self.__class__.__name__)

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


class BaseExpiredAccount(AuthBaseCase):
    """ Login as user with expired account """
    user = 'automation_expired_account'

    def expired_account(self):
        """ Login as user with expired password """
        assert not self.login()


class BaseExpiredPassword(AuthBaseCase):
    """ Login as user with expired password """
    user = 'automation_expired_password'

    def expired_password(self):
        """ Login as user with disabled account """
        assert not self.login()


class BaseDisabledAccount(AuthBaseCase):
    """ Login as disabled user """
    user = 'automation_disabled_account'

    def disabled_account(self):
        """ Login as user with disabled account """
        assert not self.login()


@tier2
class BaseSpecialCharsSearch(TestCase):
    """ Test search of special characters """
    def search(self, special_characters=('#', '%', '$',)):
        """ search special characters """
        testflow.step(
            "Trying to search by these '%s' special chars",
            ','.join(special_characters)
        )
        for special_char in special_characters:
            user_name = 'special%s' % special_char
            testflow.step("Search for user '%s'", user_name)
            # https://bugzilla.redhat.com/show_bug.cgi?id=1275237
            # When resolved modify this test based, on implmentation details
            assert users.search_user(
                self.domain, 'name', user_name
            ) is not None, "Failed to search by special character '%s'" % (
                special_char
            )
