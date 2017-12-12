"""
-----------------
test_users_and_roles
-----------------
"""
import logging
import pytest

from art.core_api.apis_exceptions import EngineTypeError
from art.rhevm_api.tests_lib.low_level import (
    users as ll_users,
    tags as ll_tags,
    general as ll_general,
    mla as ll_mla,
)
from rhevmtests.coresystem.helpers import XPathMatch
from art.unittest_lib import (
    CoreSystemTest as TestCase,
    testflow,
    tier1,
    tier2,
)

from rhevmtests.config import ENGINE_ENTRY_POINT as engine_entry_point

from rhevmtests.coresystem.regression.flow import config

logger = logging.getLogger(__name__)


class TestCaseUserAndRoles(TestCase):
    """
    User And Roles tests
    """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            testflow.teardown("Removing user.")
            ll_users.removeUser(
                positive=True,
                user=config.USER_NAME
            )
        request.addfinalizer(finalize)

        testflow.setup("Adding user for perform tests.")
        ll_users.addExternalUser(
            positive=True,
            user_name=config.USER_NAME,
            domain=config.USER_DOMAIN,
        )

    @tier1
    def test_remove_inherited_permissions_for_user(self):
        """
        Verify impossibility of removing inherited permissions
        """
        testflow.step("Removing inherited permissions.")
        assert not ll_mla.remove_all_permissions_from_user(
            config.USER_NAME
        ), "Something gone wrong"

    @tier2
    def test_delete_everyone_group(self):
        """
        verify group functionality
        try to delete "Everyone" group & verify failure
        """
        testflow.step("Deleting 'Everyone' group.")
        assert ll_users.deleteGroup(positive=False, group_name="Everyone")

    @tier2
    def test_create_user_with_wrong_domain(self):
        """
        verify users functionality
        create a user with no roles & verify failure
        """
        testflow.step("Creating user with wrong domain.")
        assert ll_users.addExternalUser(
            positive=False,
            domain="bad_config",
            user_name=config.USER_NAME,
        )

    @tier2
    def test_create_user_not_in_domain(self):
        """
        verify users functionality
        create a user which does not exists in domain & verify failure
        """
        testflow.step("Creating user which does not exists in domain.")
        assert ll_users.addExternalUser(
            positive=False,
            domain=config.USER_DOMAIN,
            user_name=config.USER_NON_EXISTING,
        )

    @tier1
    def test_add_tag_to_user(self):
        """
        verify users functionality
        add a tag to user and remove it
        """
        TAG_NAME = "Tag_A"

        testflow.step("Adding tag.")
        assert ll_tags.addTag(positive=True, name=TAG_NAME)

        testflow.step("Adding tag to user.")
        assert ll_users.addTagToUser(
            positive=True,
            user=config.USER_NAME,
            tag=TAG_NAME
        )

        testflow.step("Removing tag from user.")
        assert ll_tags.removeTag(positive=True, tag=TAG_NAME)

    @tier1
    def test_check_system_summary(self):
        """
        verify users functionality
        check system summary
        """
        testflow.step("Checking system summary.")
        assert ll_general.checkSummary(
            positive=True,
            domain=config.USER_DOMAIN
        )

    @tier1
    def test_check_system_version_tag(self):
        """
        verify system version tag
        """
        testflow.step("Checking system version tag.")
        assert ll_general.check_system_version_tag(positive=True)

    @tier1
    def test_check_definition_of_blank_template(self):
        """
        verify definition of blank template
        """
        xpathMatch = XPathMatch(ll_general.util)
        expr = (
            "count(/api/special_objects/blank_template["
            "@href=\"/%s/templates/00000000-0000-0000-0000-000000000000\"])" %
            engine_entry_point
        )

        try:
            testflow.step("Checking definition of blank template.")
            assert xpathMatch(True, "api", expr)
        except EngineTypeError:
            logger.info("xPath is only supported for rest")

    @tier1
    def test_check_definition_of_tag_root_object(self):
        """
        verify definition of tag root object
        """
        xpathMatch = XPathMatch(ll_general.util)
        expr = (
            "count(/api/special_objects/root_tag["
            "@href=\"/%s/tags/00000000-0000-0000-0000-000000000000\"])" %
            engine_entry_point
        )

        try:
            testflow.step("Checking definition of tag root object.")
            assert xpathMatch(True, "api", expr)
        except EngineTypeError:
            logger.info("xPath is only supported for rest.")

    @tier1
    def test_check_userp_properties_in_active_directory(self):
        """
        verify users functionality
        verify user properties in active directory
        """
        testflow.step("Checking user properties in aaa-jdbc provider.")
        assert ll_users.verifyADUserProperties(
            positive=True,
            domain=config.USER_DOMAIN,
            user=config.USER_NAME,
            expected_username="{0}@{1}".format(
                config.USER_NAME,
                config.USER_DOMAIN
            ),
            expected_department="Quality Assurance"
        )
