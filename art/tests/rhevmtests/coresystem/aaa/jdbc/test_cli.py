"""
Test possible configuration option of properties file.

This is automation of- RHEVM3/wiki/System/Local user authentication management
"""
import pytest

from art.core_api.apis_exceptions import APIException
from art.rhevm_api.tests_lib.low_level import general, mla, users
from rhevmtests.coresystem.helpers import EngineCLI
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
    tier2,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.jdbc import config

TOOL = 'ovirt-aaa-jdbc-tool'
USER_CLI = None
GROUP_CLI = None
MANAGE_CLI = None
TEST_USER1 = 'userX1'
TEST_USER2 = 'userX2'
TEST_USER_DISABLED = 'user_disabled'
TEST_USER_DELETE = 'user_to_be_deleted'
TEST_GROUP1 = 'groupX1'
TEST_GROUP2 = 'groupX2'
TEST_GROUP_DELETE = 'group_deleted'

ADD_USR_MSG = "Adding user %s"
RMV_USR_MSG = "Removing user %s"
ADD_GRP_MSG = "Adding group %s"
RMV_GRP_MSG = "Removing group %s"
LOG_USR_MSG = "Login as user %s"
TST_CON_MSG = "Testing connection with user %s"


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Tearing down module %s", __name__)

        _cli_stepper_action(USER_CLI, 'delete', RMV_USR_MSG, TEST_USER1)
        _cli_stepper_action(USER_CLI, 'delete', RMV_USR_MSG, TEST_USER2)
        _cli_stepper_action(
            USER_CLI,
            'delete',
            RMV_USR_MSG,
            TEST_USER_DISABLED,
        )
        _cli_stepper_action(USER_CLI, 'delete', RMV_USR_MSG, TEST_USER_DELETE)
        _cli_stepper_action(GROUP_CLI, 'delete', RMV_GRP_MSG, TEST_GROUP1)
        _cli_stepper_action(GROUP_CLI, 'delete', RMV_GRP_MSG, TEST_GROUP2)
        _cli_stepper_action(
            GROUP_CLI,
            'delete',
            RMV_GRP_MSG,
            TEST_GROUP_DELETE,
        )

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)

    global USER_CLI, GROUP_CLI, MANAGE_CLI
    ss = config.ENGINE_HOST.executor().session()
    USER_CLI = EngineCLI(tool=TOOL, session=ss).setup_module('user')
    GROUP_CLI = EngineCLI(tool=TOOL, session=ss).setup_module('group')
    MANAGE_CLI = EngineCLI(tool=TOOL, session=ss).setup_module('group-manage')

    testflow.setup(ADD_USR_MSG, TEST_USER1)
    assert USER_CLI.run(
        'add',
        TEST_USER1,
        '--attribute=firstName=userX1',
        '--attribute=department=QA',
        '--attribute=description=our sysadmin',
        '--attribute=displayName=Uzivatel',
        '--attribute=email=userX1@internal',
        '--attribute=lastName=Blabla',
        '--attribute=title=user',
    )[0]

    testflow.setup(ADD_USR_MSG, TEST_USER2)
    assert USER_CLI.run('add', TEST_USER2)[0]

    testflow.setup(ADD_USR_MSG, TEST_USER_DELETE)
    assert USER_CLI.run('add', TEST_USER_DELETE)[0]

    testflow.setup(ADD_USR_MSG, TEST_USER_DISABLED)
    assert USER_CLI.run('add', TEST_USER_DISABLED, flag='+disabled')[0]

    testflow.setup(ADD_GRP_MSG, TEST_GROUP1)
    assert GROUP_CLI.run(
        'add',
        TEST_GROUP1,
        '--attribute=displayName=Group1',
        '--attribute=description=Admin Group',
    )[0]

    testflow.setup(ADD_GRP_MSG, TEST_GROUP2)
    assert GROUP_CLI.run('add', TEST_GROUP2)[0]

    testflow.setup(ADD_GRP_MSG, TEST_GROUP_DELETE)
    assert GROUP_CLI.run('add', TEST_GROUP_DELETE)[0]

    def _cli_stepper_action(cli, action, message, obj):
        testflow.teardown(message, obj)
        cli.run(action, obj)


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


class TestJDBCCLIUser(TestCase):
    """Test managing of users via aaa-jdbc CLI"""
    user_password = '123456'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)

            testflow.teardown("Login as admin user")
            loginAsAdmin()

            testflow.teardown(RMV_USR_MSG, TEST_USER1)
            users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        testflow.setup("Login as admin user")
        loginAsAdmin()

        testflow.setup(RMV_USR_MSG, TEST_USER1)
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

        testflow.setup("Resetting password for user %s", TEST_USER1)
        assert USER_CLI.run(
            'password-reset',
            TEST_USER1,
            password='pass:%s' % cls.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        )[0]

        testflow.setup("Resetting password for user %s", TEST_USER_DISABLED)
        assert USER_CLI.run(
            'password-reset',
            TEST_USER_DISABLED,
            password='pass:%s' % cls.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        )[0]

        testflow.setup(ADD_USR_MSG, TEST_USER1)
        assert users.addExternalUser(
            True,
            user_name=TEST_USER1,
            domain=config.INTERNAL_AUTHZ,
        ), "Can't add user '%s'" % TEST_USER1

        testflow.setup("Adding cluster permission to user %s", TEST_USER1)
        assert mla.addClusterPermissionsToUser(
            True,
            user=TEST_USER1,
            cluster=config.CLUSTER_NAME[0],
            role='UserRole',
            domain=config.INTERNAL_AUTHZ,
        )

    @tier1
    @polarion('RHEVM3-11328')
    def test_000_add_user(self):
        """add user via via aaa-jdbc cli"""
        # This case is always passed because it's tested in setup_module,
        # If setup module fails, this case will never run
        pass

    @tier2
    @polarion('RHEVM3-12857')
    def test_011_add_same_user(self):
        """ add user via aaa-jdbc cli """
        testflow.step(ADD_USR_MSG, TEST_USER1)
        assert not USER_CLI.run('add', TEST_USER1)[0]

    @tier1
    @polarion('RHEVM3-11306')
    def test_030_login_as_user(self):
        """ login as user from aaa-jdbc """

        testflow.step(LOG_USR_MSG, TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step(TST_CON_MSG, TEST_USER1)
        assert connectionTest(), "User '%s' can't login" % TEST_USER1

    @tier1
    @polarion('RHEVM3-11304')
    def test_031_login_as_exp_pwd_user(self):
        """ login as user with expired password from aaa-jdbc """

        testflow.step(LOG_USR_MSG, TEST_USER2)
        users.loginAsUser(
            TEST_USER2,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step(TST_CON_MSG, TEST_USER2)
        assert not connectionTest(), "User '%s' can login" % TEST_USER2

    @tier1
    @polarion('RHEVM3-11305')
    def test_032_login_as_disabled_user(self):
        """ login as disabled user from aaa-jdbc """

        testflow.step(LOG_USR_MSG, TEST_USER_DISABLED)
        users.loginAsUser(
            TEST_USER_DISABLED,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step(TST_CON_MSG, TEST_USER_DISABLED)
        assert not connectionTest(), "User '%s' can login" % TEST_USER_DISABLED

    @tier2
    @polarion('RHEVM3-11329')
    def test_040_update_user(self):
        """ update user via aaa-jdbc cli """

        testflow.step("Updating user %s", TEST_USER2)
        assert USER_CLI.run(
            'edit',
            TEST_USER2,
            attribute='firstName=userX2',
        )[0]

    @tier2
    @polarion('RHEVM3-11301')
    def test_050_lock_user(self):
        """ lock user from aaa-jdbc"""

        testflow.step(LOG_USR_MSG, TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            'IncorrectPassword',
            True,
        )

        testflow.step("Attempting to lock user %s", TEST_USER1)
        for i in range(0, 5):  # user will be locked after 5 wrong attempts
            assert not connectionTest()

        testflow.step("Login as locked user %s", TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step("Testing connection with locked user %s", TEST_USER1)
        assert not connectionTest()  # It's locked now..

    @tier2
    @polarion('RHEVM3-11331')
    def test_060_unlock_user(self):
        """ unlock user via aaa-jdbc cli """

        testflow.step("Unlocking user %s", TEST_USER1)
        assert USER_CLI.run('unlock', TEST_USER1)

        testflow.step(LOG_USR_MSG, TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step(TST_CON_MSG, TEST_USER1)
        assert connectionTest(), "User %s can't login" % TEST_USER1

    @tier1
    @polarion('RHEVM3-11338')
    def test_080_user_delete(self):
        """ user delete from aaa-jdbc """

        testflow.step(RMV_USR_MSG, TEST_GROUP_DELETE)
        assert USER_CLI.run('delete', TEST_USER_DELETE)[0]


@tier1
class TestJDBCCLIGroupUser(TestCase):
    """Test managing of users via aaa-jdbc CLI"""
    user_password = '1234567'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", __name__)

            testflow.teardown("Login as admin user")
            loginAsAdmin()

            testflow.teardown(RMV_USR_MSG, TEST_USER1)
            users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

            testflow.teardown(RMV_GRP_MSG, TEST_GROUP1)
            users.deleteGroup(True, TEST_GROUP1)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        testflow.setup("Login as admin user")
        loginAsAdmin()

        testflow.setup(RMV_USR_MSG, TEST_USER1)
        users.removeUser(True, TEST_USER1, config.INTERNAL_AUTHZ)

    @polarion('RHEVM3-11324')
    def test_000_add_group(self):
        """test group add via aaa-jdbc-cli"""
        # This case is always passed because it's tested in setup_module,
        # If setup module fails, this case will never run
        pass

    @polarion('RHEVM3-11332')
    def test_010_change_user_password(self):
        """ change user password via aaa-jdbc cli """

        testflow.step("Resetting password for user %s", TEST_USER1)
        assert USER_CLI.run(
            'password-reset',
            TEST_USER1,
            password='pass:%s' % self.user_password,
            password_valid_to='2100-01-01 11:11:11Z',
        )[0], "Failed to change user's '%s' password" % TEST_USER1

    @polarion('RHEVM3-11333')
    def test_020_add_user_to_group(self):
        """ change add user to group via aaa-jdbc cli """
        testflow.step("Adding user %s to group %s", TEST_USER1, TEST_GROUP1)
        assert MANAGE_CLI.run(
            'useradd',
            TEST_GROUP1,
            user=TEST_USER1
        )[0], "Failed to add user to group '%s'" % TEST_GROUP1

        testflow.step("Adding nonexisting user to group %s", TEST_GROUP1)
        assert not MANAGE_CLI.run(
            'useradd',
            TEST_GROUP1,
            user='nonsense'
        )[0], "Possible to add nonexisting user to group"

        testflow.step("Adding user %s to nonexisting group", TEST_USER2)
        assert not MANAGE_CLI.run(
            'useradd',
            'nonsense',
            user=TEST_USER2
        )[0], "Possible to add user to nonexisting group"

    @polarion('RHEVM3-11307')
    def test_040_login_as_user_from_group(self):
        """ login as user from group from aaa-jdbc """

        testflow.step(ADD_GRP_MSG, TEST_GROUP1)
        assert users.addGroup(
            True,
            group_name=TEST_GROUP1,
            domain=config.INTERNAL_AUTHZ,
        ), "Can't add group '%s'" % TEST_GROUP1

        testflow.step("Adding cluster permissions to group %s", TEST_GROUP1)
        assert mla.addClusterPermissionsToGroup(
            True,
            group=TEST_GROUP1,
            cluster=config.CLUSTER_NAME[0],
            role='UserRole',
        ), "Failed to add permissions to group '%s'" % TEST_GROUP1

        testflow.step(LOG_USR_MSG, TEST_USER1)
        users.loginAsUser(
            TEST_USER1,
            config.INTERNAL_PROFILE,
            self.user_password,
            True,
        )

        testflow.step(TST_CON_MSG, TEST_USER1)
        assert connectionTest(), "User %s can't login" % TEST_USER1

    @polarion('RHEVM3-11334')
    def test_050_delete_user_from_group(self):
        """ delete user from group via aaa-jdbc cli """

        testflow.step(
            "Removing user %s from group %s", TEST_USER1, TEST_GROUP1
        )
        assert MANAGE_CLI.run(
            'userdel',
            TEST_GROUP1,
            user=TEST_USER1
        )[0], "Failed to remove user from group '%s'" % TEST_GROUP1

        testflow.step(RMV_GRP_MSG, TEST_GROUP1)
        assert not MANAGE_CLI.run(
            'userdel',
            TEST_GROUP1,
            user='nonsense'
        )[0], "Possible to remove nonexisting user from group"

        testflow.step("Removing user %s from nonexistent group", TEST_GROUP1)
        assert not MANAGE_CLI.run(
            'userdel',
            'nonsense',
            user=TEST_USER1
        )[0], "Possible to remove user from nonexisting group"

    @polarion('RHEVM3-11335')
    def test_060_add_group_to_group(self):
        """ add group to group via aaa-jdbc cli """

        testflow.step("Adding group %s to group %s", TEST_GROUP1, TEST_GROUP2)
        assert MANAGE_CLI.run(
            'groupadd',
            TEST_GROUP1,
            group=TEST_GROUP2,
        )[0], "Failed to add group to group '%s'" % TEST_GROUP1

    @polarion('RHEVM3-11336')
    def test_070_delete_group_from_group(self):
        """ delete group from group via aaa-jdbc cli """

        testflow.step(
            "Removing group %s from group %s",
            TEST_GROUP1, TEST_GROUP2
        )
        assert MANAGE_CLI.run(
            'groupdel',
            TEST_GROUP1,
            group=TEST_GROUP2,
        )[0], "Failed to delete group from group '%s'" % TEST_GROUP1

    @polarion('RHEVM3-11327')
    def test_080_group_delete(self):
        """ group delete from aaa-jdbc """

        testflow.step(RMV_GRP_MSG, TEST_GROUP_DELETE)
        assert GROUP_CLI.run(
            'delete',
            TEST_GROUP_DELETE
        )[0], "Failed to delete group '%s'" % TEST_GROUP_DELETE


class TestJDBCCLIQuery(TestCase):
    """Test quering of users/groups via aaa-jdbc CLI"""
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        testflow.setup("Setting up class %s", cls.__name__)
        cls.query_cli = EngineCLI(
            tool=TOOL,
            session=config.ENGINE_HOST.executor().session(),
        ).setup_module(
            module='query',
        )

    @tier1
    @polarion('RHEVM3-11323')
    def test_010_query_users(self):
        """ query users via aaa-jdbc cli """

        testflow.step("Querying for users")
        assert self.query_cli.run(what='user')[0], "Failed to search for users"

    @tier1
    @polarion('RHEVM3-11322')
    def test_020_query_groups(self):
        """ query groups via aaa-jdbc cli """

        testflow.step("Querying for groups")
        assert self.query_cli.run(
            what='group'
        )[0], "Failed to search for groups"

    @tier2
    @polarion('RHEVM3-12858')
    def test_030_query_nothing(self):
        """ query nothing via aaa-jdbc cli """

        testflow.step("Querying for nothing")
        assert not self.query_cli.run()[0], "Invalid arguments of query passed"

    @tier1
    @polarion('RHEVM3-13896')
    def test_040_query_pattern(self):
        """ query users/group by pattern """
        # Test query user

        testflow.step("Querying for users by pattern")
        out_user = USER_CLI.run('show', TEST_USER1)[1]
        for k, v in {
            'firstName': 'userX1',
            'department': 'QA',
            'description': 'our sysadmin',
            'displayName': 'Uzivatel',
            'email': 'userX1@internal',
            'lastName': 'Blabla',
            'title': 'user',
        }.iteritems():
            rc, out = self.query_cli.run(
                what='user',
                pattern='%s=%s' % (k, v)
            )
            assert rc, 'Unable to find user by its %s' % k
            assert out_user == out, "Correct user wasn't found by %s" % k

        # Test query group
        testflow.step("Querying for groups by pattern")
        out_group = GROUP_CLI.run('show', TEST_GROUP1)[1]
        for k, v in {
            'description': 'Admin Group',
            'displayName': 'Group1',
        }.iteritems():
            rc, out = self.query_cli.run(
                what='group',
                pattern='%s=%s' % (k, v)
            )
            assert rc, 'Unable to find group by its %s' % k
            assert out_group == out, "Correct group wasn't found by %s" % k


class TestJDBCCLISettings(TestCase):
    """Test customize of settings via aaa-jdbc CLI"""
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        testflow.setup("Setting up class %s", cls.__name__)
        cls.settings_cli = EngineCLI(
            tool=TOOL,
            session=config.ENGINE_HOST.executor().session(),
        ).setup_module(
            module='settings',
        )

    @tier1
    @polarion('RHEVM3-11337')
    def test_010_view_settings(self):
        """ view settings via CLI """

        testflow.step("Showing setting via CLI")
        assert self.settings_cli.run('show')[0], "Failed to view settings"

    @tier2
    @polarion('RHEVM3-13908')
    def test_020_change_settings(self):
        """ change settings via CLI """

        testflow.step("Modifying settings via CLI")
        assert self.settings_cli.run(
            'set',
            name='MESSAGE_OF_THE_DAY',
            value='Zdravicko',
        )[0], "Failed to change MESSAGE_OF_THE_DAY setting"

        testflow.step("Querying for modified setting")
        show_out = self.settings_cli.run(
            'show',
            name='MESSAGE_OF_THE_DAY',
        )
        assert show_out[0], 'Failed to run show command'
        assert 'Zdravicko' in show_out[1], 'Setting value was not changed'

        testflow.step("Modifying setting back to default")
        assert self.settings_cli.run(  # Change value back to default
            'set',
            name='MESSAGE_OF_THE_DAY',
            value='',
        )[0], "Failed to change MESSAGE_OF_THE_DAY setting to defaul value"
