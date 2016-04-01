"""
Test indirect membership. Recursive and non-recursive. (AD and IPA)
"""

import logging
import pytest

from art.rhevm_api.tests_lib.low_level import users, mla
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow

from rhevmtests.system.aaa.ldap import config, common

__test__ = True

logger = logging.getLogger(__name__)


@attr(tier=2)
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

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)
            common.loginAsAdmin()
            assert users.deleteGroup(True, cls.GROUP)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)
        assert users.addGroup(
            True,
            cls.GROUP,
            cls.conf['authz_name'],
            cls.NAMESPACE,
        )
        assert mla.addClusterPermissionsToGroup(
            True,
            cls.GROUP,
            config.CLUSTER_NAME[0]
        )

    def indirect_group_membership(self):
        user = self.USER
        users.loginAsUser(user, self.conf['authn_name'], self.PASSWORD, True)
        assert common.connectionTest(), "%s can't login" % user
        logger.info("User %s can login and is indirect member of group %s.",
                    user, self.GROUP)


class IndirectMembershipRecursive(IndirectMembership):
    """
    Test recursive indirect membership.
    """
    __test__ = True
    conf = config.SIMPLE_AD
    GROUP = config.AD_GROUP41
    USER = config.AD_GROUP41_USER
    PASSWORD = config.ADW2k12_USER_PASSWORD
    NAMESPACE = config.AD_GROUP41_NS

    @polarion('RHEVM3-12862')
    @common.check(config.EXTENSIONS)
    def test_ad_indirect_group_membership(self):
        """ test AD indirect group membership """
        self.indirect_group_membership()


class IndirectMembershipNonRecursive(IndirectMembership):
    """
    Test non recursive indirect membership.
    """
    __test__ = True
    conf = config.SIMPLE_IPA
    GROUP = config.IPA_GROUP32
    USER = config.IPA_GROUP_USER
    PASSWORD = config.IPA_PASSWORD

    @polarion('RHEVM3-12863')
    @common.check(config.EXTENSIONS)
    def test_ipa_indirect_group_membership(self):
        """ test IPA indirect group membership """
        self.indirect_group_membership()


@attr(tier=2)
class GroupRecursion(TestCase):
    """
    Test group recursion handle.
    https://bugzilla.redhat.com/show_bug.cgi?id=1168631
    """
    __test__ = True
    conf = config.SIMPLE_IPA
    USER = config.IPA_GROUP_USER
    PASSWORD = config.IPA_PASSWORD

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Tearing down class %s", cls.__name__)
            testflow.teardown("Login as admin user")
            common.loginAsAdmin()
            testflow.teardown("Deleting group %s", config.IPA_GROUP_LOOP2)
            assert users.deleteGroup(True, config.IPA_GROUP_LOOP2)

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)
        testflow.setup("Adding group %s", config.IPA_GROUP_LOOP2)
        assert users.addGroup(
            True,
            config.IPA_GROUP_LOOP2,
            cls.conf['authz_name']
        )
        testflow.setup(
            "Adding cluster permissions to group %s", config.IPA_GROUP_LOOP2
        )
        assert mla.addClusterPermissionsToGroup(
            True,
            config.IPA_GROUP_LOOP2,
            config.CLUSTER_NAME[0]
        )

    @polarion('RHEVM3-12861')
    def test_group_recursion(self):
        """  test if engine can handle group recursion """
        testflow.step("Login as user %s", self.USER)
        users.loginAsUser(
            self.USER,
            self.conf['authn_name'],
            self.PASSWORD,
            True
        )
        testflow.step("Testing connection with user %s", self.USER)
        assert common.connectionTest(), "%s can't login" % self.USER


@attr(tier=2)
class ForeignGroup(IndirectMembership):
    """
    Test user authentication with group membership in different AD domains
    """
    __test__ = True
    conf = config.SIMPLE_AD
    GROUP = config.AD_FOREIGN_GROUP
    USER = config.AD_FOREIGN_GROUP_USER
    PASSWORD = config.ADW2k12_USER_PASSWORD
    NAMESPACE = config.AD_FOREIGN_GROUP_NS

    @common.check(config.EXTENSIONS)
    def test_ad_foreign_group_membership(self):
        """
        Test AD foreign group membership
        """
        self.indirect_group_membership()
