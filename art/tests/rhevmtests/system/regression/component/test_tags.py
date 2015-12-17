"""
-----------------
test_tags
-----------------

@author: Nelly Credi
"""

import logging

from art.unittest_lib import (
    attr,
    CoreSystemTest as TestCase,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    vms as ll_vms,
    tags as ll_tags,
)
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api.apis_exceptions import EngineTypeError, EntityNotFound

from rhevmtests import config

TAG_DESCRIPTION = 'Test Tag Description'

logger = logging.getLogger(__name__)


class TestCaseTags(TestCase):
    """
    Tag tests
    """
    __test__ = True

    tag_set = set()
    tag_prefix = 'tag_'

    def generate_tag_name(self):
        """
        The tag_name is generated in ascending order
        :return: tag_name
        :rtype: str
        """
        tag_name = self.tag_prefix + str(len(self.tag_set))
        self.tag_set.add(tag_name)
        return tag_name

    @classmethod
    def teardown_class(cls):
        """
        Remove all tags
        """
        for tag in cls.tag_set:
            try:
                ll_tags.removeTag(positive=True, tag=tag)
            except EntityNotFound:
                logger.info('tag %s not found', tag)

    @attr(tier=1)
    def test_create_sub_tag(self):
        """
        verify tags functionality
        the test creates a sub tag
        """
        logger.info('Create sub tag')
        parent_tag = self.generate_tag_name()
        status = ll_tags.addTag(
            positive=True, name=parent_tag, description=TAG_DESCRIPTION
        )
        self.assertTrue(status, 'Create tag')
        sub_tag = self.generate_tag_name()
        status = ll_tags.addTag(
            positive=True, name=sub_tag, description=TAG_DESCRIPTION,
            parent=parent_tag
        )
        self.assertTrue(status, 'Create sub tag')

    @attr(tier=2)
    def test_add_existing_tag(self):
        """
        verify tags functionality
        try to add an existing tag & verify failure
        """
        logger.info('Create existing tag')
        tag_name = self.generate_tag_name()
        status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(status, 'Create tag')
        status = ll_tags.addTag(
            positive=False, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(status, 'Create existing tag')

    @attr(tier=1)
    def test_update_tag(self):
        """
        verify tags functionality
        update tag name & description
        """
        logger.info('Update tag')
        tag_name = self.generate_tag_name()
        status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(status, 'Create tag')
        new_name = tag_name + 'Updated'
        status = ll_tags.updateTag(
            positive=True, tag=tag_name, name=new_name,
            description='Test Tag Description updated'
        )
        self.assertTrue(status, 'Update tag')
        self.tag_set.remove(tag_name)
        self.tag_set.add(new_name)

    @attr(tier=2)
    def test_tag_itself_as_parent(self):
        """
        verify tags functionality
        try to set tag as his own parent
        """
        logger.info('Tag as parent')
        tag_name = self.generate_tag_name()
        status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(status, 'Create tag')
        status = ll_tags.updateTag(
            positive=False, tag=tag_name, parent=tag_name
        )
        self.assertTrue(status, 'Tag as parent')

    @attr(tier=1)
    def test_update_tag_parent_and_remove_parent(self):
        """
        verify tags functionality
        update tag parent
        remove parent - should remove parent and descendant
        """
        logger.info('Update tag parent')
        parent_tag = self.generate_tag_name()
        sub_tag = self.generate_tag_name()
        parent_status = ll_tags.addTag(
            positive=True, name=parent_tag, description=TAG_DESCRIPTION
        )
        sub_status = ll_tags.addTag(
            positive=True, name=sub_tag, description=TAG_DESCRIPTION
        )
        self.assertTrue(parent_status & sub_status, 'Create tags')
        status = ll_tags.updateTag(
            positive=True, tag=sub_tag, parent=parent_tag
        )
        self.assertTrue(status, 'Update tag parent')
        logger.info('Remove tag parent')
        status = ll_tags.removeTag(positive=True, tag=parent_tag)
        self.assertTrue(status, 'Remove tag parent')

    @attr(tier=2)
    def test_create_tag_loop(self):
        """
        verify tags functionality
        try to update a tag's parent to be one of his descendants &
        verify failure
        """
        logger.info('Update tag parent to descendants')
        parent_tag = self.generate_tag_name()
        sub_tag = self.generate_tag_name()
        parent_status = ll_tags.addTag(
            positive=True, name=parent_tag, description=TAG_DESCRIPTION
        )
        sub_status = ll_tags.addTag(
            positive=True, name=sub_tag, description=TAG_DESCRIPTION
        )
        self.assertTrue(parent_status & sub_status, 'Create tags')
        status = ll_tags.updateTag(
            positive=True, tag=sub_tag, parent=parent_tag
        )
        self.assertTrue(status, 'Update tag parent')
        loop_status = ll_tags.updateTag(
            positive=False, tag=parent_tag, parent=sub_tag
        )
        self.assertTrue(loop_status, 'Update tag parent to descendant')

    @attr(tier=1)
    def test_associate_tag_with_vm_and_search_by_tag(self):
        """
        verify tags functionality
        associate a tag with vm
        search vm by tag
        remove tag from vm
        """
        logger.info('Associate tag with vm')
        tag_name = self.generate_tag_name()
        tag_status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(tag_status, 'Create tag')
        associate_status = ll_vms.addTagToVm(
            positive=True, tag=tag_name, vm=config.VM_NAME[0]
        )
        self.assertTrue(associate_status, 'Associate tag with vm')
        logger.info('Search vm by tag')
        search_status = ll_vms.searchForVm(
            positive=True, query_key='tag',
            query_val=tag_name, expected_count=1
        )
        logger.info('Remove tag from vm')
        remove_status = ll_vms.removeTagFromVm(
            positive=True, vm=config.VM_NAME[0], tag=tag_name
        )
        self.assertTrue(search_status, 'Search vm by tag')
        self.assertTrue(remove_status, 'Remove tag from vm')

    @attr(tier=2)
    def test_associate_non_existing_tag_with_vm(self):
        """
        verify tags functionality
        associate non existing tag with vm & verify failure
        """
        logger.info('Associate non existing tag with vm')
        status = ll_vms.addTagToVm(
            positive=False, tag='bad_config', vm=config.VM_NAME[0]
        )
        self.assertTrue(status, 'Associate non existing tag with vm')

    @attr(tier=1)
    def test_associate_tag_with_host_and_search_host_by_tag(self):
        """
        verify tags functionality
        associate a tag with host
        search host by tag
        remove tag from host
        """
        logger.info('Associate tag with host')
        tag_name = self.generate_tag_name()
        tag_status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(tag_status, 'Create tag')
        associate_status = ll_hosts.addTagToHost(
            positive=True, tag=tag_name, host=config.HOSTS[0]
        )
        self.assertTrue(associate_status, 'Associate tag with host')
        logger.info('Search host by tag')
        search_status = ll_hosts.searchForHost(
            positive=True, query_key='tag',
            query_val=tag_name, expected_count=1
        )
        logger.info('Remove tag from host')
        remove_status = ll_hosts.removeTagFromHost(
            positive=True, host=config.HOSTS[0], tag=tag_name
        )
        self.assertTrue(search_status, 'Search host by tag')
        self.assertTrue(remove_status, 'Remove tag from host')

    @attr(tier=2)
    def test_update_tag_name_to_existing_tag(self):
        """
        verify tags functionality
        update tag name to an existing one & verify failure
        """
        logger.info('Update tag name to existing')
        first_tag = self.generate_tag_name()
        second_tag = self.generate_tag_name()
        first_status = ll_tags.addTag(
            positive=True, name=first_tag, description=TAG_DESCRIPTION
        )
        second_status = ll_tags.addTag(
            positive=True, name=second_tag, description=TAG_DESCRIPTION
        )
        self.assertTrue(first_status & second_status, 'Create tags')
        status = ll_tags.updateTag(
            positive=False, tag=second_tag, name=first_tag
        )
        self.assertTrue(status, 'Update tag name to existing')

    @attr(tier=1)
    def test_check_tag_is_unique(self):
        """
        verify tags functionality
        check via xpath whether the tag is unique
        """
        logger.info('Check tag unique')
        tag_name = self.generate_tag_name()
        tag_status = ll_tags.addTag(
            positive=True, name=tag_name, description=TAG_DESCRIPTION
        )
        self.assertTrue(tag_status, 'Create tag')
        xpathMatch = XPathMatch(ll_tags.util)
        expr = 'count(/tags/tag/name[text()="%s"])' % tag_name
        try:
            status = xpathMatch(True, 'tags', expr, rslt_eval='1==result')
            self.assertTrue(status, 'Check tag unique')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')
