"""
Test possible configuration option of properties file.
"""
__test__ = True

from art.core_api.apis_exceptions import APIException
from art.rhevm_api.tests_lib.low_level import general, mla, users
from art.rhevm_api.utils import jdbccli
from art.unittest_lib import attr, CoreSystemTest as TestCase

from rhevmtests.system.aaa.jdbc import config

ss = config.ENGINE_HOST.executor().session()
USER_CLI = jdbccli.JDBCCLI(session=ss, entity='user')
GROUP_CLI = jdbccli.JDBCCLI(session=ss, entity='group')
TEST_USER1 = 'user1'
TEST_USER2 = 'user2'
TEST_USER_DISABLED = 'user_disabled'
TEST_USER_DELETE = 'user_to_be_deleted'
TEST_GROUP1 = 'group1'
TEST_GROUP2 = 'group2'


def setup_module():
    assert USER_CLI.run('add', TEST_USER1)
    assert USER_CLI.run('add', TEST_USER2)
    assert USER_CLI.run('add', TEST_USER_DELETE)
    assert USER_CLI.run('add', TEST_USER_DISABLED, flag='+disabled')
    assert GROUP_CLI.run('add', TEST_GROUP1)
    assert GROUP_CLI.run('add', TEST_GROUP2)


def teardown_module():
    USER_CLI.run('delete', TEST_USER1)
    USER_CLI.run('delete', TEST_USER2)
    USER_CLI.run('delete', TEST_USER_DISABLED)
    USER_CLI.run('delete', TEST_USER_DELETE)
    GROUP_CLI.run('delete', TEST_GROUP1)
    GROUP_CLI.run('delete', TEST_GROUP2)


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER,
        config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD,
        filter=False,
    )


def connectionTest():
    try:
        return general.getProductName()[0]
    except (APIException, AttributeError):
        # We expect either login will fail (wrong user) or
        # general.getProductName() will return None (correct user + filter set)
        return False
    return True


@attr(tier=0)
class JDBCCLIUser(TestCase):
    """Test managing of users via aaa-jdbc CLI"""
    __test__ = True
    user_password = '123456'

    @classmethod
    def setup_class(cls):
        loginAsAdmin()
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)
        assert USER_CLI.run(
            'password-reset',
            TEST_USER1,
            password='pass:%s' % cls.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        )
        assert USER_CLI.run(
            'password-reset',
            TEST_USER_DISABLED,
            password='pass:%s' % cls.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        )

    @classmethod
    def teardown_class(cls):
        loginAsAdmin()
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

    @attr(tier=1)
    def test_011_add_same_user(self):
        """ add user via aaa-jdbc cli """
        assert not USER_CLI.run('add', TEST_USER1)

    def test_020_assign_user_permissions(self):
        """ assign user permissions via aaa-jdbc cli """
        assert users.addExternalUser(
            True,
            user_name=TEST_USER1,
            domain=config.INTERNAL_AUTHZ,
        ), "Can't add user '%s'" % TEST_USER1
        assert mla.addClusterPermissionsToUser(
            True,
            user=TEST_USER1,
            cluster='Default',
            role='UserRole',
            domain=config.INTERNAL_AUTHZ,
        )

    def test_030_login_as_user(self):
        """ login as user from aaa-jdbc """
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert connectionTest(), "User '%s' can't login" % TEST_USER1

    def test_031_login_as_exp_pwd_user(self):
        """ login as user with expired password from aaa-jdbc """
        users.loginAsUser(
            TEST_USER2,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert not connectionTest(), "User '%s' can login" % TEST_USER2

    def test_032_login_as_disabled_user(self):
        """ login as disabled user from aaa-jdbc """
        users.loginAsUser(
            TEST_USER_DISABLED,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert not connectionTest(), "User '%s' can login" % TEST_USER_DISABLED

    @attr(tier=1)
    def test_040_update_user(self):
        """ update user via aaa-jdbc cli """
        assert USER_CLI.run(
            'edit',
            TEST_USER1,
            attribute='firstName=user1',
        )

    @attr(tier=1)
    def test_050_lock_user(self):
        """ lock user from aaa-jdbc"""
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            'IncorrectPassword',
            True,
        )
        for i in range(0, 5):  # user will be locked after 5 wrong attempts
            assert not connectionTest()
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert not connectionTest()  # It's locked now..

    @attr(tier=1)
    def test_060_unlock_user(self):
        """ unlock user via aaa-jdbc cli """
        assert USER_CLI.run('unlock', TEST_USER1)

    @attr(tier=1)
    def test_070_login_after_unlock(self):
        """ login as user from aaa-jdbc """
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert connectionTest(), "User %s can't login" % TEST_USER1

    def test_080_user_delete(self):
        """ user delete from aaa-jdbc """
        assert USER_CLI.run('delete', TEST_USER_DELETE)
