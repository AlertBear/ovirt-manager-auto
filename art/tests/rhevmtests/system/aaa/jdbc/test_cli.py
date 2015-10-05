"""
Test possible configuration option of properties file.

This is automation of- RHEVM3/wiki/System/Local user authentication management
"""
__test__ = True

from art.core_api.apis_exceptions import APIException
from art.rhevm_api.tests_lib.low_level import general, mla, users
from art.rhevm_api.utils import jdbccli
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import attr, CoreSystemTest as TestCase

from rhevmtests.system.aaa.jdbc import config

ss = config.ENGINE_HOST.executor().session()
USER_CLI = jdbccli.JDBCCLI(session=ss, entity='user')
GROUP_CLI = jdbccli.JDBCCLI(session=ss, entity='group')
MANAGE_CLI = jdbccli.JDBCCLI(session=ss, entity='group-manage')
TEST_USER1 = 'user1'
TEST_USER2 = 'user2'
TEST_USER_DISABLED = 'user_disabled'
TEST_USER_DELETE = 'user_to_be_deleted'
TEST_GROUP1 = 'group1'
TEST_GROUP2 = 'group2'
TEST_GROUP_DELETE = 'group_deleted'


def setup_module():
    assert USER_CLI.run('add', TEST_USER1)
    assert USER_CLI.run('add', TEST_USER2)
    assert USER_CLI.run('add', TEST_USER_DELETE)
    assert USER_CLI.run('add', TEST_USER_DISABLED, flag='+disabled')
    assert GROUP_CLI.run('add', TEST_GROUP1)
    assert GROUP_CLI.run('add', TEST_GROUP2)
    assert GROUP_CLI.run('add', TEST_GROUP_DELETE)


def teardown_module():
    USER_CLI.run('delete', TEST_USER1)
    USER_CLI.run('delete', TEST_USER2)
    USER_CLI.run('delete', TEST_USER_DISABLED)
    USER_CLI.run('delete', TEST_USER_DELETE)
    GROUP_CLI.run('delete', TEST_GROUP1)
    GROUP_CLI.run('delete', TEST_GROUP2)
    GROUP_CLI.run('delete', TEST_GROUP_DELETE)


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

    @classmethod
    def teardown_class(cls):
        loginAsAdmin()
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

    @polarion('RHEVM3-11328')
    def test_000_add_user(self):
        """add user via via aaa-jdbc cli"""
        # This case is always passed because it's tested in setup_module,
        # If setup module fails, this case will never run
        pass

    @attr(tier=1)
    @polarion('RHEVM3-12857')
    def test_011_add_same_user(self):
        """ add user via aaa-jdbc cli """
        assert not USER_CLI.run('add', TEST_USER1)

    @polarion('RHEVM3-11306')
    def test_030_login_as_user(self):
        """ login as user from aaa-jdbc """
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert connectionTest(), "User '%s' can't login" % TEST_USER1

    @polarion('RHEVM3-11304')
    def test_031_login_as_exp_pwd_user(self):
        """ login as user with expired password from aaa-jdbc """
        users.loginAsUser(
            TEST_USER2,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert not connectionTest(), "User '%s' can login" % TEST_USER2

    @polarion('RHEVM3-11305')
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
    @polarion('RHEVM3-11329')
    def test_040_update_user(self):
        """ update user via aaa-jdbc cli """
        assert USER_CLI.run(
            'edit',
            TEST_USER1,
            attribute='firstName=user1',
        )

    @attr(tier=1)
    @polarion('RHEVM3-11301')
    @bz({'1258271': {'engine': None, 'version': ['3.6']}})
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
    @polarion('RHEVM3-11331')
    def test_060_unlock_user(self):
        """ unlock user via aaa-jdbc cli """
        assert USER_CLI.run('unlock', TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert connectionTest(), "User %s can't login" % TEST_USER1

    @polarion('RHEVM3-11338')
    def test_080_user_delete(self):
        """ user delete from aaa-jdbc """
        assert USER_CLI.run('delete', TEST_USER_DELETE)


@attr(tier=0)
class JDBCCLIGroupUser(TestCase):
    """Test managing of users via aaa-jdbc CLI"""
    __test__ = True
    user_password = '1234567'

    @classmethod
    def setup_class(cls):
        loginAsAdmin()
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

    @classmethod
    def teardown_class(cls):
        loginAsAdmin()
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)
        users.deleteGroup(True, TEST_GROUP1)

    @polarion('RHEVM3-11324')
    def test_000_add_group(self):
        """test group add via aaa-jdbc-cli"""
        # This case is always passed because it's tested in setup_module,
        # If setup module fails, this case will never run
        pass

    @polarion('RHEVM3-11332')
    def test_010_change_user_password(self):
        """ change user password via aaa-jdbc cli """
        assert USER_CLI.run(
            'password-reset',
            TEST_USER1,
            password='pass:%s' % self.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        ), "Failed to change user's '%s' password" % TEST_USER1

    @polarion('RHEVM3-11333')
    def test_020_add_user_to_group(self):
        """ change add user to group via aaa-jdbc cli """
        assert MANAGE_CLI.run(
            'useradd',
            TEST_GROUP1,
            user=TEST_USER1
        ), "Failed to add user to group '%s'" % TEST_GROUP1
        assert not MANAGE_CLI.run(
            'useradd',
            TEST_GROUP1,
            user='nonsense'
        ), "Possible to add nonexisting user to group"
        assert not MANAGE_CLI.run(
            'useradd',
            'nonsense',
            user=TEST_USER2
        ), "Possible to add user to nonexisting group"

    def test_030_assign_group_permissions(self):
        """ assign group permissions via aaa-jdbc cli """
        assert users.addGroup(
            True,
            group_name=TEST_GROUP1,
            domain=config.INTERNAL_AUTHZ,
        ), "Can't add group '%s'" % TEST_GROUP1
        assert mla.addClusterPermissionsToGroup(
            True,
            group=TEST_GROUP1,
            cluster='Default',
            role='UserRole',
        ), "Failed to add permissions to group '%s'" % TEST_GROUP1

    def test_040_login_as_user(self):
        """ login as user from group from aaa-jdbc """
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )
        assert connectionTest(), "User %s can't login" % TEST_USER1

    @polarion('RHEVM3-11334')
    def test_050_delete_user_from_group(self):
        """ delete user from group via aaa-jdbc cli """
        assert MANAGE_CLI.run(
            'userdel',
            TEST_GROUP1,
            user=TEST_USER1
        ), "Failed to remove user from group '%s'" % TEST_GROUP1
        assert not MANAGE_CLI.run(
            'userdel',
            TEST_GROUP1,
            user='nonsense'
        ), "Possible to remove nonexisting user from group"
        assert not MANAGE_CLI.run(
            'userdel',
            'nonsense',
            user=TEST_USER1
        ), "Possible to remove user from nonexisting group"

    @polarion('RHEVM3-11335')
    def test_060_add_group_to_group(self):
        """ add group to group via aaa-jdbc cli """
        assert MANAGE_CLI.run(
            'groupadd',
            TEST_GROUP1,
            group=TEST_GROUP2,
        ), "Failed to add group to group '%s'" % TEST_GROUP1

    @polarion('RHEVM3-11336')
    def test_070_delete_group_from_group(self):
        """ delete group from group via aaa-jdbc cli """
        assert MANAGE_CLI.run(
            'groupdel',
            TEST_GROUP1,
            group=TEST_GROUP2,
        ), "Failed to delete group from group '%s'" % TEST_GROUP1

    @polarion('RHEVM3-11327')
    def test_080_group_delete(self):
        """ group delete from aaa-jdbc """
        assert GROUP_CLI.run(
            'delete',
            TEST_GROUP_DELETE
        ), "Failed to delete group '%s'" % TEST_GROUP_DELETE


@attr(tier=0)
class JDBCCLIQuery(TestCase):
    """Test quering of users/groups via aaa-jdbc CLI"""
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.query_cli = jdbccli.JDBCCLI(
            session=config.ENGINE_HOST.executor().session(),
            entity='query'
        )

    @polarion('RHEVM3-11323')
    def test_010_query_users(self):
        """ query users via aaa-jdbc cli """
        assert self.query_cli.run(what='user'), "Failed to search for users"

    @polarion('RHEVM3-11322')
    def test_020_query_groups(self):
        """ query groups via aaa-jdbc cli """
        assert self.query_cli.run(what='group'), "Failed to search for groups"

    @attr(tier=1)
    @polarion('RHEVM3-12858')
    def test_030_query_nothing(self):
        """ query nothing via aaa-jdbc cli """
        assert not self.query_cli.run(), "Invalid arguments of query passed"
