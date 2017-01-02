'''
Testing authentication of users from OpenLDAP.
Nothing is created using default DC and default cluster.
Authentication of expired users, users from group and correct users.
User with many groups and if updating of user is propagated.
'''


from authentication import config
import logging

from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import mla, users
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import polarion, bz
from test_base import connectionTest
from config import non_ge

__test__ = True

logger = logging.getLogger(__name__)
TEST_FOLDER = '/root/do_not_remove'
CN = 'cn=Manager,dc=brq-openldap,dc=rhev,dc=lab,dc=eng,dc=brq,dc=redhat,dc=com'
CMD = "ldapmodify -v -D '%s' -h $(hostname) -w %s -f %s"


def addUser(user_name):
    users.addUser(True, user_name=user_name, domain=config.LDAP_DOMAIN)


def loginAsUser(user_name, filter_):
    users.loginAsUser(user_name, config.LDAP_DOMAIN,
                      config.USER_PASSWORD, filter_)


def loginAsAdmin():
    users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                      config.USER_PASSWORD, False)


@non_ge
@attr(tier=1)
class LDAPCase289010(TestCase):
    """
    Login as normal user and user from group.
    """
    __test__ = True

    def setUp(self):
        addUser(config.LDAP_REGULAR_NAME)
        users.addGroup(True, group_name=config.LDAP_GROUP,
                       domain=config.LDAP_DOMAIN)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP, config.MAIN_CLUSTER_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_REGULAR_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @polarion("RHEVM3-8077")
    def normalUserAndGroupUser(self):
        """ Authenticate as normal user and user from group """
        msg_f = "%s user can't log in."
        msg_t = "%s user can log in."

        loginAsUser(config.LDAP_REGULAR_NAME, True)
        assert connectionTest(), msg_f % 'Regular'
        logger.info(msg_t % 'Regular')

        loginAsUser(config.LDAP_USER_FROM_GROUP, True)
        assert connectionTest(), msg_f % 'Group'
        logger.info(msg_t % 'Group')

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_REGULAR_NAME,
                         domain=config.LDAP_DOMAIN)
        users.removeUser(positive=True, user=config.LDAP_USER_FROM_GROUP,
                         domain=config.LDAP_DOMAIN)
        users.deleteGroup(positive=True, group_name=config.LDAP_GROUP)


@non_ge
@attr(tier=1)
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

    @polarion("RHEVM3-8078")
    def expiredPassword(self):
        """ Login as user with disabled account """
        msg = "User with expired psw can login."
        loginAsUser(config.LDAP_EXPIRED_PSW_NAME, True)
        assert not connectionTest(), msg
        logger.info("User with expired password can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_EXPIRED_PSW_NAME,
                         domain=config.LDAP_DOMAIN)


@non_ge
@attr(tier=1)
class LDAPCase289068(TestCase):
    """ Test if user with expired password can't login """
    __test__ = True

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.LDAP_EXPIRED_ACC_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_EXPIRED_ACC_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @polarion("RHEVM3-8079")
    def expiredAccount(self):
        """ Login as user with expired password """
        msg = "User with expired acc can login."
        loginAsUser(config.LDAP_EXPIRED_ACC_NAME, True)
        assert not connectionTest(), msg
        logger.info("User with expired account can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_EXPIRED_ACC_NAME,
                         domain=config.LDAP_DOMAIN)


@non_ge
@attr(tier=2)
class LDAPCase289069(TestCase):
    """ Try to search via REST with firstname, lastname """
    __test__ = True

    # FIXME: https://projects.engineering.redhat.com/browse/RHEVM-1615
    apis = TestCase.apis - set(['java', 'sdk'])

    def setUp(self):
        domainID = users.domUtil.find(config.LDAP_DOMAIN).get_id()
        self.query = '/api/domains/' + domainID + '/%s?search={query}'

    @polarion("RHEVM3-8080")
    @bz({'1177367': {'engine': ['cli'], 'version': ['3.5']}})
    def searchForUsersAndGroups(self):
        """ Search within domain for users and groups """
        assert users.groupUtil.query(
            '', href=self.query % 'groups'
        ) is not None

        assert len(users.util.query('', href=self.query % 'users')) > 0
        user = users.util.query("{0}={1}".format('name', 'user2'),
                                href=self.query % 'users')[0]
        assert user.get_name().lower() == 'user2'
        user = users.util.query("{0}={1}".format('lastname', 'user2'),
                                href=self.query % 'users')[0]
        assert user.get_name().lower() == 'user2'
        logger.info("Searching for users and groups works correctly.")


@non_ge
@attr(tier=2)
class LDAPCase289071(TestCase):
    """ If the information is updated on LDAP side it's propageted to rhevm """
    __test__ = True
    UPDATE_USER1 = "%s/modify_user1.ldif" % TEST_FOLDER
    UPDATE_USER2 = "%s/modify_user2.ldif" % TEST_FOLDER
    new_name = 'new_name'
    new_last_name = 'new_last_name'
    new_email = 'new_email@mynewemail.com'

    def _find_user_in_directory(self, name):
        domain_obj = users.domUtil.find(config.LDAP_DOMAIN)
        return filter(lambda x: x.get_name() == name,
                      users.util.getElemFromLink(domain_obj,
                                                 link_name='users',
                                                 attr='user',
                                                 get_href=False))[0]

    def setUp(self):
        self.user = self._find_user_in_directory(config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)

    @polarion("RHEVM3-8081")
    @bz({'1125161': {}})
    def updateInformation(self):
        """ Update information """
        assert runMachineCommand(
            True, ip=config.LDAP_DOMAIN, cmd=CMD %
            (CN, config.LDAP_PASSWORD, self.UPDATE_USER1),
            user=config.HOSTS_USER, password=config.LDAP_PASSWORD
        )[0]
        user = self._find_user_in_directory(self.new_name)
        assert user.get_name() == self.new_name
        logger.info("User name was updated correctly.")
        assert user.get_last_name() == self.new_last_name
        logger.info("User last name was updated correctly.")
        assert user.get_email() == self.new_email
        logger.info("User email was updated correctly.")

    def tearDown(self):
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % (CN, config.LDAP_PASSWORD,
                                     self.UPDATE_USER2),
                          user=config.HOSTS_USER,
                          password=config.LDAP_PASSWORD)
        users.removeUser(True, user=config.LDAP_TESTING_USER_NAME,
                         domain=config.LDAP_DOMAIN)


@non_ge
@attr(tier=2)
class LDAPCase289072(TestCase):
    """ If user which is part of group is removed, the group still persists """
    __test__ = True

    def setUp(self):
        users.addGroup(True, group_name=config.LDAP_GROUP,
                       domain=config.LDAP_DOMAIN)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP, config.MAIN_CLUSTER_NAME)
        addUser(config.LDAP_USER_FROM_GROUP)

    @polarion("RHEVM3-8082")
    @bz({'1125161': {}})
    def persistencyOfGroupRights(self):
        """ Persistency of group rights """
        loginAsUser(config.LDAP_USER_FROM_GROUP, True)
        assert connectionTest(), "User from group can't log in"
        logger.info('User from group logged in')
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_USER_FROM_GROUP,
                         domain=config.LDAP_DOMAIN)
        assert users.groupExists(
            True, config.LDAP_GROUP
        ), "Group was removed with user"
        logger.info("Group persisted after user from group was removed.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(True, group_name=config.LDAP_GROUP)


@non_ge
@attr(tier=2)
class LDAPCase289076(TestCase):
    """ Test if user which has lot of groups assigned can be added & login """
    __test__ = True

    def setUp(self):
        addUser(config.LDAP_WITH_MANY_GROUPS_NAME)
        mla.addClusterPermissionsToUser(
            True, config.LDAP_WITH_MANY_GROUPS_NAME, config.MAIN_CLUSTER_NAME,
            role='UserRole', domain=config.LDAP_DOMAIN)

    @polarion("RHEVM3-8083")
    def userWithManyGroups(self):
        """ User with many groups """
        loginAsUser(config.LDAP_WITH_MANY_GROUPS_NAME, True)
        assert connectionTest(), (
            "User with many groups can't connect to system"
        )

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.LDAP_WITH_MANY_GROUPS_NAME,
                         domain=config.LDAP_DOMAIN)


@non_ge
@attr(tier=2)
class LDAPCase289078(TestCase):
    """ Test if user can't login after group removal from user """
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
        users.addGroup(True, group_name=config.LDAP_GROUP2,
                       domain=config.LDAP_DOMAIN)
        mla.addClusterPermissionsToGroup(
            True, config.LDAP_GROUP2, config.MAIN_CLUSTER_NAME)

    @polarion("RHEVM3-8084")
    def removeUserFromOpenLDAP(self):
        """ remove user from OpenLDAP """
        msg = "After group del, user can login."
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        assert connectionTest(), "User from group can't log in."
        logger.info("User from group can log in.")
        # Remove group from user
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % (CN, config.LDAP_PASSWORD, self.DEL_GROUP),
                          user=config.HOSTS_USER,
                          password=config.LDAP_PASSWORD)
        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        assert not connectionTest(), msg
        logger.info("User can't login after group removal.")
        # Add group to user
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=CMD % (CN, config.LDAP_PASSWORD, self.ADD_GROUP),
                          user=config.HOSTS_USER,
                          password=config.LDAP_PASSWORD)
        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        assert connectionTest(), "User from group can't log in."
        logger.info("User from group can log in.")

        # Remove group from OpenLDAP
        runMachineCommand(True, ip=config.LDAP_DOMAIN,
                          cmd=self.REMOVE,
                          user=config.HOSTS_USER,
                          password=config.LDAP_PASSWORD)

        loginAsAdmin()
        users.removeUser(True, config.LDAP_TESTING_USER_NAME)
        addUser(config.LDAP_TESTING_USER_NAME)
        loginAsUser(config.LDAP_TESTING_USER_NAME, True)
        assert not connectionTest(), msg
        logger.info("User can't login after group removal.")

    def tearDown(self):
        loginAsAdmin()
        runMachineCommand(
            True, ip=config.LDAP_DOMAIN,
            cmd=self.ADD, user=config.HOSTS_USER,
            password=config.LDAP_PASSWORD,
        )
        runMachineCommand(
            True, ip=config.LDAP_DOMAIN,
            cmd=CMD % (
                CN, config.LDAP_PASSWORD,
                self.ADD_GROUP
            ),
            user=config.HOSTS_USER,
            password=config.LDAP_PASSWORD,
        )
        users.deleteGroup(positive=True, group_name=config.LDAP_GROUP2)
