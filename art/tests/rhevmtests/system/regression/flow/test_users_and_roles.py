"""
-----------------
test_users_and_roles
-----------------

@author: Nelly Credi
"""

import logging

from art.test_handler.tools import bz

from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from rhevmtests.system.regression.flow import config

from art.rhevm_api.tests_lib.low_level import (
    users as ll_users,
    tags as ll_tags,
    general as ll_general,
    mla as ll_mla,
)
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EngineTypeError

logger = logging.getLogger(__name__)


class TestCaseUserAndRoles(TestCase):
    """
    User And Roles tests
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create user for tests
        """
        logger.info('Add user')
        ll_users.addExternalUser(
            positive=True,
            user_name=config.USERNAME_NAME,
            domain=config.USER_DOMAIN,
        )

    @classmethod
    def teardown_class(cls):
        """
        Clear the environment
        Remove users and tags if still exists
        """
        logger.info('Remove user')
        ll_users.removeUser(positive=True, user=config.USERNAME_NAME)

    @bz({'1302034': {}})
    @attr(tier=1)
    def test_remove_all_permissions_for_user(self):
        """
        verify permissions functionality
        remove all permissions for a given user
        """
        logger.info('Remove permissions for user')
        status = ll_mla.removeAllPermissionsFromUser(
            positive=True, user=config.USERNAME_NAME
        )
        self.assertTrue(status, 'Remove permissions for user')

    @attr(tier=2)
    def test_delete_everyone_group(self):
        """
        verify group functionality
        try to delete 'Everyone' group & verify failure
        """
        logger.info('Delete \'Everyone\' group')
        status = ll_users.deleteGroup(positive=False, group_name='Everyone')
        self.assertTrue(status, "Delete 'Everyone' group failed as expected")

    @attr(tier=2)
    def test_create_user_with_wrong_domain(self):
        """
        verify users functionality
        create a user with no roles & verify failure
        """
        logger.info('Create user - wrong domain')
        status = ll_users.addExternalUser(
            positive=False,
            domain='bad_config',
            user_name=config.USERNAME_NAME,
        )
        self.assertTrue(status, 'Create user - wrong domain')

    @attr(tier=2)
    def test_create_user_not_in_domain(self):
        """
        verify users functionality
        create a user which does not exists in domain & verify failure
        """
        logger.info('Create user which does not exists in domain')
        status = ll_users.addExternalUser(
            positive=False,
            domain=config.USER_DOMAIN,
            user_name=config.USER_NON_EXISTING,
        )
        self.assertTrue(status, 'Create user which does not exists in domain')

    @attr(tier=1)
    def test_add_tag_to_user(self):
        """
        verify users functionality
        add a tag to user and remove it
        """
        logger.info('Create tag')
        tag_name = 'Tag_A'
        tag_status = ll_tags.addTag(positive=True, name=tag_name)
        self.assertTrue(tag_status, 'Create tag')
        logger.info('Add tag to user')
        status = ll_users.addTagToUser(
            positive=True, user=config.USERNAME_NAME, tag=tag_name
        )
        remove_status = ll_tags.removeTag(positive=True, tag=tag_name)
        self.assertTrue(status, 'Add tag to user')
        self.assertTrue(remove_status, 'Delete tag')

    @attr(tier=1)
    def test_check_system_summary(self):
        """
        verify users functionality
        check system summary
        """
        logger.info('Check system summary')
        status = ll_general.checkSummary(
            positive=True, domain=config.USER_DOMAIN
        )
        self.assertTrue(status, 'Check system summary')

    @attr(tier=1)
    def test_check_system_version_tag(self):
        """
        verify system version tag
        """
        logger.info('Check system version tag')
        status = ll_general.checkSystemVersionTag(positive=True)
        self.assertTrue(status, 'Check system version tag')

    @attr(tier=1)
    def test_check_definition_of_blank_template(self):
        """
        verify definition of blank template
        """
        logger.info('Check definition of blank template')
        xpathMatch = XPathMatch(ll_general.util)
        expr = (
            'count(/api/special_objects/link[@rel="templates/blank" and '
            '@href="/%s/templates/00000000-0000-0000-0000-000000000000"])' %
            config.ENGINE_ENTRY_POINT
        )
        try:
            status = xpathMatch(True, 'api', expr)
            self.assertTrue(status, 'Check definition of blank template')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @attr(tier=1)
    def test_check_definition_of_tag_root_object(self):
        """
        verify definition of tag root object
        """
        logger.info('Check definition of tag root object')
        xpathMatch = XPathMatch(ll_general.util)
        expr = (
            'count(/api/special_objects/link[@rel="tags/root" and '
            '@href="/%s/tags/00000000-0000-0000-0000-000000000000"])' %
            config.ENGINE_ENTRY_POINT
        )
        try:
            status = xpathMatch(True, 'api', expr)
            self.assertTrue(status, 'Check definition of tag root object')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    @attr(tier=1)
    def test_check_user_properties_in_active_directory(self):
        """
        verify users functionality
        verify user properties in active directory
        """
        logger.info('Check user properties in aaa-jdbc provider')
        status = ll_users.verifyADUserProperties(
            positive=True, domain=config.USER_DOMAIN,
            user=config.USERNAME_NAME,
            expected_username='%s@%s' % (
                config.USERNAME_NAME,
                config.USER_DOMAIN
            ),
            expected_department='Quality Assurance'
        )
        self.assertTrue(status, 'Check user properties in aaa-jdbc provider')
