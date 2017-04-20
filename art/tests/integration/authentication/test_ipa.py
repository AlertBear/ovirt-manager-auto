"""
Testing authentication of users from IPA.
Nothing is created using default DC and default cluster.
Authentication of expired users, users from group and correct users.
Login formats, user with many groups and if updating of user is propagated.
"""


from authentication import config
import logging

from art.unittest_lib import IntegrationTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import mla, users
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import get_api
from art.core_api.apis_utils import getDS
from art.test_handler.tools import polarion, bz
from test_base import connectionTest
from config import non_ge

__test__ = True

logger = logging.getLogger(__name__)
KINIT = 'kinit nonascii <<< %s'
UPDATE_USER = 'ipa user-mod %s --last=%s --first=%s'
USER_ROLE = 'UserRole'
User = getDS('User')
Domain = getDS('Domain')
util = get_api('user', 'users')
group_api = get_api('group', 'groups')


def addUser(user_name):
    userName = '%s@%s' % (user_name, config.IPA_DOMAIN)
    user = User(domain=Domain(name=config.IPA_DOMAIN), user_name=userName)
    user, status = util.create(user, True)


def loginAsUser(user_name, filter_):
    users.loginAsUser(user_name, config.IPA_DOMAIN,
                      config.USER_PASSWORD, filter_)


def loginAsAdmin():
    users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                      config.USER_PASSWORD, False)


@non_ge
@attr(tier=1)
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

    @polarion("RHEVM3-8953")
    def authenticateUsersNegative(self):
        """ Authenticate users - negative """
        msg_f = "%s user can log in."
        msg_t = "%s user can't log in."

        loginAsUser(config.IPA_EXPIRED_PSW_NAME, True)
        assert not connectionTest(), msg_f % 'Expired'
        logger.info(msg_t % 'Expired')

        loginAsUser(config.IPA_DISABLED_NAME, True)
        assert not connectionTest(), msg_f % 'Disabled'
        logger.info(msg_t % 'Disabled')

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.IPA_EXPIRED_PSW_NAME,
                         domain=config.IPA_DOMAIN)
        users.removeUser(positive=True, user=config.IPA_DISABLED_NAME,
                         domain=config.IPA_DOMAIN)


@non_ge
@attr(tier=1)
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
        users.addGroup(True, group_name=config.IPA_GROUP,
                       domain=config.IPA_DOMAIN)
        mla.addClusterPermissionsToGroup(
            True, config.IPA_GROUP, config.MAIN_CLUSTER_NAME, role=USER_ROLE)

    @polarion("RHEVM3-8952")
    def authenticateUsers(self):
        """ Authenticate users """
        # Login as regular user
        loginAsUser(config.IPA_REGULAR_NAME, True)
        assert connectionTest(), "Regular user can't log in."
        logger.info("Regular user can log in.")

        # Login as user from group
        loginAsUser(config.IPA_WITH_GROUP_NAME, True)
        assert connectionTest(), "User from group can't log in."
        logger.info("User from group can log in.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(positive=True, group_name=config.IPA_GROUP)
        users.removeUser(
            True, user=config.IPA_REGULAR_NAME, domain=config.IPA_DOMAIN
        )
        users.removeUser(
            True, user=config.IPA_WITH_GROUP_NAME, domain=config.IPA_DOMAIN
        )


@non_ge
@attr(tier=2)
class IPACase93881(TestCase):
    """ Try to login with different login formats """
    __test__ = True

    apis = set(['rest'])

    def setUp(self):
        # Add regular users, and add him permissions
        addUser(config.IPA_REGULAR_NAME)
        mla.addClusterPermissionsToUser(
            True, config.IPA_REGULAR_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)

    @polarion("RHEVM3-8954")
    @bz({'1123545': {}})
    def loginFormats(self):
        """ Login formats """
        msg_f = "Login format %s doesn't not work."
        msg_t = "Login format %s works OK."

        for format in [config.REGULAR_FORMAT1, config.REGULAR_FORMAT2]:
            users.loginAsUser(format, None, config.USER_PASSWORD, True)
            assert connectionTest(), msg_f % format
            logger.info(msg_t % format)

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.IPA_REGULAR_NAME,
                         domain=config.IPA_DOMAIN)


@non_ge
@attr(tier=2)
class IPACase109871(TestCase):
    """ Test if user which has lot of groups assigned can be added & login """
    __test__ = True

    def setUp(self):
        addUser(config.IPA_WITH_MANY_GROUPS_NAME)
        mla.addClusterPermissionsToUser(
            True, config.IPA_WITH_MANY_GROUPS_NAME, config.MAIN_CLUSTER_NAME,
            role=USER_ROLE, domain=config.IPA_DOMAIN)

    @polarion("RHEVM3-8959")
    def userWithManyGroups(self):
        """ User with many groups """
        loginAsUser(config.IPA_WITH_MANY_GROUPS_NAME, True)
        assert connectionTest(), (
            "User with many groups can't connect to system"
        )

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(True, user=config.IPA_WITH_MANY_GROUPS_NAME,
                         domain=config.IPA_DOMAIN)


@non_ge
@attr(tier=2)
class IPACase109146(TestCase):
    """ If user which is part of group is removed, the group still persists """
    __test__ = True

    def setUp(self):
        users.addGroup(True, group_name=config.IPA_GROUP,
                       domain=config.IPA_DOMAIN)
        mla.addClusterPermissionsToGroup(
            True, config.IPA_GROUP, config.MAIN_CLUSTER_NAME)

    @polarion("RHEVM3-8958")
    @bz({'1125161': {}})
    def persistencyOfGroupRights(self):
        """ Persistency of group rights """
        loginAsUser(config.IPA_WITH_GROUP_NAME, False)
        assert connectionTest(), "User from group can't login."
        logger.info("User from group can login.")
        loginAsAdmin()
        assert users.removeUser(
            True, user=config.IPA_WITH_GROUP_NAME, domain=config.IPA_DOMAIN
        )
        assert users.groupExists(
            True, config.IPA_GROUP
        ), "Group was removed with user"
        logger.info("Group persisted after user from group was removed.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(True, group_name=config.IPA_GROUP)


@non_ge
@attr(tier=2)
class IPACase93882(TestCase):
    """ Try to search via REST with firstname, lastname """
    __test__ = True

    # FIXME: https://projects.engineering.redhat.com/browse/RHEVM-1615
    apis = TestCase.apis - set(['java', 'sdk'])

    @polarion("RHEVM3-8955")
    @bz({'1125161': {}})
    def search(self):
        """ Search """
        domain_id = users.domUtil.find(config.IPA_DOMAIN.lower()).get_id()
        query = '/api/domains/' + domain_id + '/users?search={query}'

        domain_obj = users.domUtil.find(config.IPA_DOMAIN.lower())
        groups_in_domain = group_api.getElemFromLink(domain_obj,
                                                     link_name='groups',
                                                     attr='group',
                                                     get_href=False)
        assert len(groups_in_domain) > 0

        users_in_domain = util.getElemFromLink(domain_obj, link_name='users',
                                               attr='user', get_href=False)
        assert len(users_in_domain) > 0
        name = "{0}={1}".format('name', 'uzivatel')
        user = util.query(name, href=query)[0]
        assert user.get_name().lower() == 'uzivatel'
        lastname = "{0}={1}".format('lastname', 'bezskupiny')
        user = util.query(lastname, href=query)[0]
        assert user.get_last_name().lower() == 'bezskupiny'
        logger.info("Searching for users and groups works correctly.")


@non_ge
@attr(tier=2)
class IPACase93883(TestCase):
    """ If the information is updated on IPA side it's propageted to rhevm """
    __test__ = True

    apis = set(['rest'])

    def _find_user_in_directory(self, name):
        domain_obj = users.domUtil.find(config.IPA_DOMAIN.lower())
        return filter(lambda x: x.get_name() == name,
                      users.util.getElemFromLink(domain_obj,
                                                 link_name='users',
                                                 attr='user',
                                                 get_href=False))[0]

    def setUp(self):
        addUser(config.IPA_TESTING_USER_NAME)
        self.user = self._find_user_in_directory(config.IPA_TESTING_USER_NAME)
        assert runMachineCommand(
            True, ip=config.IPA_DOMAIN.lower(),
            cmd=KINIT % config.USER_PASSWORD, user=config.HOSTS_USER,
            password=config.IPA_PASSWORD
        )[0]

    @polarion("RHEVM3-8956")
    @bz({'1117240': {}})
    def update(self):
        """ Update """
        new_name = 'new_name'
        new_last_name = 'new_last_name'

        assert runMachineCommand(
            True, ip=config.IPA_DOMAIN.lower(), cmd=UPDATE_USER %
            (config.IPA_TESTING_USER_NAME, new_last_name, new_name),
            user=config.HOSTS_USER, password=config.IPA_PASSWORD
        )[0]
        user = self._find_user_in_directory(new_name)
        assert user.get_name() == new_name
        assert user.get_last_name() == new_last_name

    def tearDown(self):
        runMachineCommand(True, ip=config.IPA_DOMAIN.lower(),
                          cmd=UPDATE_USER % (config.IPA_TESTING_USER_NAME,
                                             self.user.get_last_name(),
                                             self.user.get_name()),
                          user=config.HOSTS_USER,
                          password=config.IPA_PASSWORD)
        users.removeUser(True, user=config.IPA_TESTING_USER_NAME,
                         domain=config.IPA_DOMAIN)
