"""
Test indirect membership. Recursive and non-recursive. (AD and IPA)
"""
__test__ = True

import logging

from rhevmtests.system.generic_ldap import config, common
from art.rhevm_api.tests_lib.low_level import users, mla
from art.unittest_lib import attr, CoreSystemTest as TestCase
from nose.tools import istest

LOGGER = logging.getLogger(__name__)
EXTENSIONS = {}
NAME = 'simple'


def setup_module():
    common.prepareExtensions(NAME, config.ENGINE_EXTENSIONS_DIR, EXTENSIONS)


def teardown_module():
    common.cleanExtDirectory(config.ENGINE_EXTENSIONS_DIR)


class IndirectMembership(TestCase):
    """
    Test indirect membership.
    """
    __test__ = False
    # Override those variables in inherited class
    conf = None
    GROUP = None
    USER = None
    PASSWORD = None
    NAMESPACE = None

    def setUp(self):
        assert users.addGroup(True, self.GROUP, self.conf['authz_name'],
                              self.NAMESPACE)
        assert mla.addClusterPermissionsToGroup(True, self.GROUP,
                                                config.DEFAULT_CLUSTER_NAME)

    @classmethod
    def teardown_class(cls):
        common.loginAsAdmin()
        assert users.deleteGroup(True, cls.GROUP)
        assert users.removeUser(True, cls.USER, cls.conf['authz_name'])

    def indirect_group_membership(self):
        user = self.USER
        users.loginAsUser(user, self.conf['authn_name'], self.PASSWORD, True)
        self.assertTrue(common.connectionTest(), "%s can't login" % user)
        LOGGER.info("User %s can login and is indirect member of group %s.",
                    user, self.GROUP)


@attr(tier=1)
class IndirectMembershipRecursive(IndirectMembership):
    """
    Test recursive indirect membership.
    """
    __test__ = True
    conf = config.SIMPLE_AD
    GROUP = config.AD_GROUP32
    USER = config.AD_GROUP_USER
    PASSWORD = config.ADW2k12_USER_PASSWORD
    NAMESPACE = config.AD_GROUP32_NS

    @istest
    @common.check(EXTENSIONS)
    def ad_indirect_group_membership(self):
        """ test AD indirect group membership """
        self.indirect_group_membership()


@attr(tier=1)
class IndirectMembershipNonRecursive(IndirectMembership):
    """
    Test non recursive indirect membership.
    """
    __test__ = True
    conf = config.SIMPLE_IPA
    GROUP = config.IPA_GROUP32
    USER = config.IPA_GROUP_USER
    PASSWORD = config.IPA_PASSWORD

    @istest
    @common.check(EXTENSIONS)
    def ipa_indirect_group_membership(self):
        """ test IPA indirect group membership """
        self.indirect_group_membership()


class GroupRecursion(TestCase):
    """
    Test group recursion handle.
    https://bugzilla.redhat.com/show_bug.cgi?id=1168631
    """
    __test__ = True
    conf = config.SIMPLE_IPA
    GROUPS = [config.IPA_GROUP_LOOP1, config.IPA_GROUP_LOOP2]
    USER = config.IPA_GROUP_USER
    PASSWORD = config.IPA_PASSWORD

    def setUp(self):
        for group in self.GROUPS:
            assert users.addGroup(
                True,
                group,
                self.conf['authz_name']
            )
            assert mla.addClusterPermissionsToGroup(
                True,
                group,
                config.DEFAULT_CLUSTER_NAME
            )

    @classmethod
    def teardown_class(cls):
        common.loginAsAdmin()
        for group in cls.GROUPS:
            assert users.deleteGroup(True, group)
        assert users.removeUser(True, cls.USER, cls.conf['authz_name'])

    def test_group_recursion(self):
        """  test if engine can handle group recursion """
        users.loginAsUser(
            self.USER,
            self.conf['authn_name'],
            self.PASSWORD,
            True
        )
        self.assertTrue(common.connectionTest(), "%s can't login" % self.USER)