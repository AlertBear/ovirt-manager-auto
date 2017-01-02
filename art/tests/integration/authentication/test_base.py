# This module can be used to inherit basic sanity cases for every new domain
# Check test_rhds.py how to use it.

from authentication import config
import logging
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.low_level import mla, users, general
from art.core_api.apis_exceptions import APIException
from art.test_handler.tools import bz
from config import non_ge

__test__ = False

logger = logging.getLogger(__name__)
USERROLE = 'UserRole'


def connectionTest():
    try:
        return general.getProductName()[0]
    except (APIException, AttributeError):
        # We expect either login will fail (wrong user) or
        # general.getProductName() will return None (correct user + filter set)
        return False
    return True


def loginAsAdmin():
    users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                      config.USER_PASSWORD, False)


def loginAsUser(user_name, domain, filter_=True):
    users.loginAsUser(user_name, domain, config.USER_PASSWORD, filter_)


def addUser(user_name, domain):
    users.addUser(True, user_name=user_name, domain=domain)


@non_ge
@attr(tier=1)
class BaseNormalUserAndGroupUser(TestCase):
    """ Login as normal user and user from group. """
    __test__ = False
    domain = None

    def setUp(self):
        addUser(config.REGULAR_NAME(self.domain), self.domain)
        users.addGroup(True, group_name=config.GROUP(self.domain),
                       domain=self.domain)
        mla.addClusterPermissionsToGroup(True, config.GROUP(self.domain),
                                         config.MAIN_CLUSTER_NAME,
                                         role=USERROLE)
        mla.addClusterPermissionsToUser(True, config.REGULAR_NAME(self.domain),
                                        config.MAIN_CLUSTER_NAME,
                                        role=USERROLE, domain=self.domain)

    def normalUserAndGroupUser(self):
        """ Authenticate as normal user and user from group """
        msg_f = "%s user can't log in."
        msg_t = "%s user can log in."

        loginAsUser(config.REGULAR_NAME(self.domain), self.domain)
        assert connectionTest(), msg_f % 'Regular'
        logger.info(msg_t % 'Regular')

        loginAsUser(config.USER_FROM_GROUP(self.domain), self.domain)
        assert connectionTest(), msg_f % 'Group'
        logger.info(msg_t % 'Group')

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, user=config.REGULAR_NAME(self.domain),
                         domain=self.domain)
        users.removeUser(positive=True,
                         user=config.USER_FROM_GROUP(self.domain),
                         domain=self.domain)
        users.deleteGroup(positive=True, group_name=config.GROUP(self.domain))


@non_ge
@attr(tier=1)
class BaseExpiredAccount(TestCase):
    """ Login as user with expired account """
    __test__ = False
    domain = None

    def setUp(self):
        addUser(config.EXPIRED_ACC_NAME(self.domain), self.domain)
        mla.addClusterPermissionsToUser(
            True, config.EXPIRED_ACC_NAME(self.domain),
            config.MAIN_CLUSTER_NAME,
            role=USERROLE, domain=self.domain)

    def expiredAccount(self):
        """ Login as user with expired password """
        msg = "User with expired acc can login."
        loginAsUser(config.EXPIRED_ACC_NAME(self.domain), self.domain)
        assert not connectionTest(), msg
        logger.info("User with expired account can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True,
                         user=config.EXPIRED_ACC_NAME(self.domain),
                         domain=self.domain)


@non_ge
@attr(tier=1)
class BaseExpiredPassword(TestCase):
    """ Login as user with expired password """
    __test__ = False
    domain = None

    def setUp(self):
        addUser(config.EXPIRED_PSW_NAME(self.domain), self.domain)
        mla.addClusterPermissionsToUser(
            True, config.EXPIRED_PSW_NAME(self.domain),
            config.MAIN_CLUSTER_NAME,
            role=USERROLE, domain=self.domain)

    def expiredPassword(self):
        """ Login as user with disabled account """
        msg = "User with expired psw can login."
        loginAsUser(config.EXPIRED_PSW_NAME(self.domain), self.domain, True)
        assert not connectionTest(), msg
        logger.info("User with expired password can't login.")

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True,
                         user=config.EXPIRED_PSW_NAME(self.domain),
                         domain=self.domain)


@non_ge
@attr(tier=2)
class BaseGroupsPersistency(TestCase):
    """ Persistency of group rights """
    __test__ = False
    domain = None

    def setUp(self):
        users.addGroup(True, group_name=config.GROUP(self.domain),
                       domain=self.domain)
        mla.addClusterPermissionsToGroup(True, config.GROUP(self.domain),
                                         config.MAIN_CLUSTER_NAME)

    @bz({'1125161': {}})
    def basePersistencyOfGroupRights(self):
        """ After user removal, check that his group persist """
        loginAsUser(config.USER_FROM_GROUP(self.domain), self.domain, False)
        assert connectionTest(), 'User from group cant log in'
        logger.info('User from group logged in')
        loginAsAdmin()
        users.removeUser(positive=True,
                         user=config.USER_FROM_GROUP(self.domain),
                         domain=self.domain)
        assert users.groupExists(
            True, config.GROUP(self.domain)
        ), "Group was removed with user"
        logger.info("Group persisted after user from group was removed.")

    def tearDown(self):
        loginAsAdmin()
        users.deleteGroup(True, group_name=config.GROUP(self.domain))


@non_ge
@attr(tier=2)
class BaseUserWithManyGroups(TestCase):
    """ Login as user with many groups """
    __test__ = False
    domain = None

    def setUp(self):
        addUser(config.WITH_MANY_GROUPS_NAME(self.domain), self.domain)
        mla.addClusterPermissionsToUser(
            True, config.WITH_MANY_GROUPS_NAME(self.domain),
            config.MAIN_CLUSTER_NAME, role=USERROLE, domain=self.domain)

    def userWithManyGroups(self):
        """ Check that user with many groups can login """
        loginAsUser(config.WITH_MANY_GROUPS_NAME(self.domain), self.domain)
        assert connectionTest(), (
            "User with many groups can't connect to system"
        )

    def tearDown(self):
        loginAsAdmin()
        users.removeUser(positive=True, domain=self.domain,
                         user=config.WITH_MANY_GROUPS_NAME(self.domain))


@non_ge
@attr(tier=2)
class BaseSearchForUsersAndGroups(TestCase):
    """ Search within domain for users and groups """
    __test__ = False
    domain = None
    name = None
    last_name = None

    apis = TestCase.apis - set(['java', 'sdk'])

    def setUp(self):
        domainID = users.domUtil.find(self.domain).get_id()
        self.query = '/api/domains/' + domainID + '/%s?search={query}'

    @bz({'1177367': {'engine': ['cli'], 'version': ['3.5']}})
    def searchForUsersAndGroups(self):
        """ Search within domain for users and groups """
        assert users.groupUtil.query(
            '', href=self.query % 'groups'
        ) is not None

        assert len(users.util.query('', href=self.query % 'users')) > 0
        user = users.util.query("{0}={1}".format('name', self.name),
                                href=self.query % 'users')[0]
        assert user.get_name().lower() == self.name
        logger.info("Searching for users by name works OK.")
        user = users.util.query("{0}={1}".format('lastname', self.last_name),
                                href=self.query % 'users')[0]
        assert user.get_name().lower() == self.last_name
        logger.info("Searching for users by lastname works OK.")
