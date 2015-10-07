"""
-----------------
test_mixed
-----------------

@author: Nelly Credi
"""

import logging

from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import (
    hosts,
    general,
    vms,
    users,
    mla,
    tags
)
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError
from art.test_handler.tools import bz  # pylint: disable=E0611

from rhevmtests.infra.regression_infra import config
from art.test_handler.settings import opts


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS


@attr(team='automationInfra', tier=1)
class TestCaseMixed(TestCase):
    """
    Scenario tests
    """

    __test__ = (ENUMS['storage_type_nfs'] in opts['storages'])
    tag_name = config.TAG_1_NAME

    @classmethod
    def teardown_class(cls):
        """
        Clear the environment
        Remove users and tags if still exists
        """
        logger.info('Remove user in case not removed in the test')
        try:
            users.removeUser(positive=False, user=config.USERNAME_NAME)
        except EntityNotFound:
                logger.info(
                    'Failed to remove user %s - this is expected if: '
                    '1. remove user test passed successfully '
                    '2. add user test failed', config.USERNAME_NAME
                )

        logger.info('Remove tags in case not removed in the tests')
        tags_to_remove = [
            cls.tag_name, config.TAG_2_NAME,
            config.TAG_3_NAME, config.TAG_4_NAME, config.TAG_5_NAME,
            config.TAG_SUB_NAME
        ]
        for tag_name in tags_to_remove:
            try:
                tags.removeTag(positive=False, tag=tag_name)
            except EntityNotFound:
                logger.info(
                    'Failed to remove tag %s - this is expected if: '
                    '1. remove tags test passed successfully '
                    '2. add tag tests failed', tag_name
                )

    def test01_check_product_name(self):
        """
        test verifies product name
        """
        logger.info('Check product name')
        status = general.checkProductName(config.PRODUCT_NAME)
        self.assertTrue(status, 'Check product name')

    @bz({'1188176': {'engine': ['cli'], 'version': ['3.5', '3.6']}})
    def test02_create_user(self):
        """
        test verifies user functionality
        the test adds a user
        """
        logger.info('Add user')
        status = users.addExternalUser(
            positive=True,
            user_name=config.USERNAME,
            principal=config.USERNAME,
            domain=config.USER_DOMAIN,
        )
        self.assertTrue(status, 'Add user')

    @bz({'1188176': {'engine': ['cli'], 'version': ['3.5', '3.6']}})
    def test03_add_data_center_permissions_to_user(self):
        """
        test verifies permissions functionality
        the test adds data center permissions to user
        """
        logger.info('Add dc permissions to user')
        status = mla.addPermissionsForDataCenter(
            positive=True, user=config.USERNAME_NAME,
            data_center=config.DATA_CENTER_1_NAME)
        self.assertTrue(status, 'Add dc permissions to user')

    @bz({'1188176': {'engine': ['cli'], 'version': ['3.5', '3.6']}})
    def test04_remove_all_permissions_for_user(self):
        """
        test verifies permissions functionality
        the test removes all permissions for a given user
        """
        logger.info('Remove permissions for user')
        status = mla.removeAllPermissionsFromUser(
            positive=True, user=config.USERNAME_NAME)
        self.assertTrue(status, 'Remove permissions for user')

    def test05_create_tag(self):
        """
        test verifies tags functionality
        the test creates a tag
        """
        tags_to_create = [config.TAG_1_NAME, config.TAG_2_NAME,
                          config.TAG_3_NAME, config.TAG_4_NAME,
                          config.TAG_5_NAME]
        for tag in tags_to_create:
            logger.info('Create tag ' + tag)
            status = tags.addTag(positive=True, name=tag,
                                 description='Test Tag Description')
            self.assertTrue(status, 'Create tag ' + tag)

    def test06_create_sub_tag(self):
        """
        test verifies tags functionality
        the test creates a sub tag
        """
        logger.info('Create sub tag')
        status = tags.addTag(positive=True, name=config.TAG_SUB_NAME,
                             description='Test Tag Description',
                             parent=config.TAG_2_NAME)
        self.assertTrue(status, 'Create sub tag')

    def test07_add_existing_tag(self):
        """
        test verifies tags functionality
        the test tries to add an existing tag & verifies failure
        """
        logger.info('Create existing tag')
        status = tags.addTag(positive=False, name=config.TAG_SUB_NAME,
                             description='Test Tag Description')
        self.assertTrue(status, 'Create existing tag')

    def test08_update_tag(self):
        """
        test verifies tags functionality
        the test updates tag name & description
        """
        logger.info('Update tag')
        new_name = config.TAG_1_NAME + 'Updated'
        status = tags.updateTag(positive=True, tag=config.TAG_1_NAME,
                                name=new_name,
                                description='Test Tag Description updated')
        self.assertTrue(status, 'Update tag')
        self.__class__.tag_name = new_name

    def test09_tag_itself_as_parent(self):
        """
        test verifies tags functionality
        the test tries to tag itself as his own parent
        """
        logger.info('Tag as parent')
        status = tags.updateTag(positive=False, tag=config.TAG_2_NAME,
                                parent=config.TAG_2_NAME)
        self.assertTrue(status, 'Tag as parent')

    def test10_update_tag_parent(self):
        """
        test verifies tags functionality
        the test updates a tags parent
        """
        logger.info('Update tag parent')
        status = tags.updateTag(positive=True, tag=config.TAG_3_NAME,
                                parent=config.TAG_SUB_NAME)
        self.assertTrue(status, 'Update tag parent')

    def test11_create_tag_loop(self):
        """
        test verifies tags functionality
        the test tries to update a tag's parent to be one of his descendants &
        verifies failure
        """
        logger.info('Update tag parent to descendants')
        status = tags.updateTag(positive=False, tag=config.TAG_2_NAME,
                                parent=config.TAG_3_NAME)
        self.assertTrue(status, 'Update tag parent to descendants')

    def test12_remove_tag_with_sub_tag(self):
        """
        test verifies tags functionality
        the test removes tag
        """
        logger.info('Remove tag')
        status = tags.removeTag(positive=True, tag=config.TAG_2_NAME)
        self.assertTrue(status, 'Remove tag')

    def test13_associate_tag_with_vm(self):
        """
        test verifies tags functionality
        the test associates a tag with vm
        """
        logger.info('Associate tag with vm')
        status = vms.addTagToVm(positive=True, tag=self.__class__.tag_name,
                                vm=config.VM_NAME)
        self.assertTrue(status, 'Associate tag with vm')

    def test14_associate_non_existing_tag_with_vm(self):
        """
        test verifies tags functionality
        the test associates a non existing tag with vm & verifies failure
        """
        logger.info('Associate non existing tag with vm')
        status = vms.addTagToVm(positive=False, tag='bad_config',
                                vm=config.VM_NAME)
        self.assertTrue(status, 'Associate non existing tag with vm')

    def test15_search_vm_by_tag(self):
        """
        test verifies tags functionality
        the test searches a vm by tag
        """
        logger.info('Search vm by tag')
        status = vms.searchForVm(positive=True, query_key='tag',
                                 query_val='TagRestTest*', expected_count=1)
        self.assertTrue(status, 'Search vm by tag')

    def test16_associate_tag_with_host(self):
        """
        test verifies tags functionality
        the test associates a tag with host
        """
        logger.info('Associate tag with host')
        status = hosts.addTagToHost(positive=True, tag=self.__class__.tag_name,
                                    host=config.HOST_NAME)
        self.assertTrue(status, 'Associate tag with host')

    def test17_search_host_by_tag(self):
        """
        test verifies tags functionality
        the test searches a host by tag
        """
        logger.info('Search host by tag')
        status = hosts.searchForHost(positive=True, query_key='tag',
                                     query_val='TagRestTest*',
                                     expected_count=1)
        self.assertTrue(status, 'Search host by tag')

    def test18_remove_tag_from_vm(self):
        """
        test verifies tags functionality
        the test removes tag from vm
        """
        logger.info('Remove tag from vm')
        status = vms.removeTagFromVm(positive=True, vm=config.VM_NAME,
                                     tag=self.__class__.tag_name)
        self.assertTrue(status, 'Remove tag from vm')

    def test19_remove_tag_from_host(self):
        """
        test verifies tags functionality
        the test removes tag from host
        """
        logger.info('Remove tag from host')
        status = hosts.removeTagFromHost(positive=True, host=config.HOST_NAME,
                                         tag=self.__class__.tag_name)
        self.assertTrue(status, 'Remove tag from host')

    def test20_update_tag_name_to_existing_tag(self):
        """
        test verifies tags functionality
        the test updates a tag's name to an existing one & verifies failure
        """
        logger.info('Update tag name to existing')
        status = tags.updateTag(positive=False, tag=config.TAG_4_NAME,
                                name=config.TAG_5_NAME)
        self.assertTrue(status, 'Update tag name to existing')

    def test21_check_tag_is_unique(self):
        """
        test verifies tags functionality
        the test checks via xpath whether the tag is unique
        """
        logger.info('Check tag unique')
        xpathMatch = XPathMatch(tags.util)
        expr = 'count(/tags/tag/name[text()="%s"])' % config.TAG_5_NAME
        try:
            status = xpathMatch(True, 'tags', expr, rslt_eval='1==result')
            self.assertTrue(status, 'Check tag unique')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')

    def test22_remove_all_tags(self):
        """
        test verifies tags functionality
        the test removes all tag
        """
        tags_to_remove = [self.__class__.tag_name, config.TAG_4_NAME,
                          config.TAG_5_NAME]
        for curr_tag in tags_to_remove:
            logger.info('Remove tag ' + curr_tag)
            status = tags.removeTag(positive=True, tag=curr_tag)
            self.assertTrue(status, 'Remove tag ' + curr_tag)

    @bz({'1188176': {'engine': ['cli'], 'version': ['3.5', '3.6']}})
    def test23_remove_user(self):
        """
        test verifies user functionality
        the test removes a user
        """
        logger.info('Remove user')
        status = users.removeUser(positive=True, user=config.USERNAME_NAME)
        self.assertTrue(status, 'Remove user')
