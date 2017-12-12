"""
-----------------
test_tags
-----------------
"""

import logging
import pytest

from art.core_api.apis_exceptions import EngineTypeError, EntityNotFound
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    vms as ll_vms,
    tags as ll_tags,
)
from rhevmtests.coresystem.helpers import XPathMatch
from art.unittest_lib import (
    testflow,
    CoreSystemTest as TestCase,
    tier1,
    tier2,
)

from rhevmtests.config import (
    HOSTS as hosts,
    VM_NAME as vms_names,
)

TAG_DESCRIPTION = 'Test Tag Description'

logger = logging.getLogger(__name__)


class TestCaseTags(TestCase):
    """
    Tag tests
    """
    TAG_PREFIX = 'tag_'

    tag_set = set()

    def generate_tag_name(self):
        """
        Description:
            Generates tag name in and adds it to set of
            tags in ascending order.
        Returns:
            str: tag_name
        """
        tag_name = self.TAG_PREFIX + str(len(self.tag_set))
        self.tag_set.add(tag_name)
        return tag_name

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """
            Remove all tags
            """
            testflow.teardown("Removing tags")
            for tag in cls.tag_set:
                try:
                    ll_tags.removeTag(positive=True, tag=tag)
                except EntityNotFound:
                    logger.info('tag %s not found', tag)
        request.addfinalizer(finalize)

    @tier1
    def test_create_sub_tag(self):
        """
        verify tags functionality
        the test creates a sub tag
        """
        parent_tag = self.generate_tag_name()
        sub_tag = self.generate_tag_name()

        testflow.step("Adding perent tag.")
        assert ll_tags.addTag(
            positive=True,
            name=parent_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Adding sub tag.")
        assert ll_tags.addTag(
            positive=True,
            name=sub_tag,
            description=TAG_DESCRIPTION,
            parent=parent_tag
        )

    @tier2
    def test_add_existing_tag(self):
        """
        verify tags functionality
        try to add an existing tag & verify failure
        """
        tag_name = self.generate_tag_name()

        testflow.step("Creating a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        testflow.step("Creating the same tag again.")
        assert ll_tags.addTag(
            positive=False,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

    @tier1
    def test_update_tag(self):
        """
        verify tags functionality
        update tag name & description
        """
        tag_name = self.generate_tag_name()
        new_name = tag_name + "Updated"

        testflow.step("Adding a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        testflow.step("Updating tag.")
        assert ll_tags.updateTag(
            positive=True,
            tag=tag_name,
            name=new_name,
            description="Test Tag Description updated."
        )
        testflow.step("Removing tag.")
        self.tag_set.remove(tag_name)

        testflow.step("Adding tag with new name to tag set.")
        self.tag_set.add(new_name)

    @tier2
    def test_tag_itself_as_parent(self):
        """
        verify tags functionality
        try to set tag as its own parent
        """
        tag_name = self.generate_tag_name()

        testflow.step("Adding a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        testflow.step("Setting tag as its own parent.")
        assert ll_tags.updateTag(
            positive=False,
            tag=tag_name,
            parent=tag_name
        )

    @tier1
    def test_update_tag_parent_and_remove_parent(self):
        """
        verify tags functionality
        update tag parent
        remove parent - should remove parent and descendant
        """
        parent_tag = self.generate_tag_name()
        sub_tag = self.generate_tag_name()

        testflow.step("Adding a parent tag.")
        assert ll_tags.addTag(
            positive=True,
            name=parent_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Adding sub tag.")
        assert ll_tags.addTag(
            positive=True,
            name=sub_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Setting parent tag to sub tag.")
        assert ll_tags.updateTag(
            positive=True,
            tag=sub_tag,
            parent=parent_tag
        )

        testflow.step("Removing parent tag.")
        assert ll_tags.removeTag(positive=True, tag=parent_tag)

    @tier2
    def test_create_tag_loop(self):
        """
        verify tags functionality
        try to update a tag's parent to be one of his descendants &
        verify failuren
        """
        parent_tag = self.generate_tag_name()
        sub_tag = self.generate_tag_name()

        testflow.step("Adding a parent tag.")
        assert ll_tags.addTag(
            positive=True,
            name=parent_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Adding sub tag.")
        assert ll_tags.addTag(
            positive=True,
            name=sub_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Setting parent of sub tag.")
        assert ll_tags.updateTag(
            positive=True,
            tag=sub_tag,
            parent=parent_tag
        )

        testflow.step("Updating tag parent to descendants.")
        assert ll_tags.updateTag(
            positive=False,
            tag=parent_tag,
            parent=sub_tag
        )

    @tier1
    def test_associate_tag_with_vm_and_search_by_tag(self):
        """
        verify tags functionality
        associate a tag with vm
        search vm by tag
        remove tag from vm
        """
        tag_name = self.generate_tag_name()

        testflow.step("Adding a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        testflow.step("Associating tag with vm.")
        assert ll_vms.addTagToVm(
            positive=True,
            tag=tag_name,
            vm=vms_names[0]
        )

        testflow.step("Searching vm by tag.")
        assert ll_vms.searchForVm(
            positive=True,
            query_key='tag',
            query_val=tag_name,
            expected_count=1
        )

        testflow.step("Removing tag from vm.")
        assert ll_vms.removeTagFromVm(
            positive=True,
            vm=vms_names[0],
            tag=tag_name
        )

    @tier2
    def test_associate_non_existing_tag_with_vm(self):
        """
        verify tags functionality
        associate non existing tag with vm & verify failure
        """
        testflow.step("Associating non existing tag with vm.")
        assert ll_vms.addTagToVm(
            positive=False,
            tag='bad_config',
            vm=vms_names[0]
        )

    @tier1
    def test_associate_tag_with_host_and_search_host_by_tag(self):
        """
        verify tags functionality
        associate a tag with host
        search host by tag
        remove tag from host
        """
        tag_name = self.generate_tag_name()

        testflow.step("Adding a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        testflow.step("Associating tag with host.")
        assert ll_hosts.add_tag_to_host(
            positive=True,
            tag=tag_name,
            host=hosts[0]
        )

        testflow.step("Searching host by tag.")
        assert ll_hosts.search_for_host(
            positive=True,
            query_key='tag',
            query_val=tag_name,
            expected_count=1
        )

        testflow.step("Removing tag from host.")
        assert ll_hosts.remove_tag_from_host(
            positive=True,
            host=hosts[0],
            tag=tag_name
        )

    @tier2
    def test_update_tag_name_to_existing_tag(self):
        """
        verify tags functionality
        update tag name to an existing one & verify failure
        """
        first_tag = self.generate_tag_name()
        second_tag = self.generate_tag_name()

        testflow.step("Adding first tag.")
        assert ll_tags.addTag(
            positive=True,
            name=first_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Adding second tag.")
        assert ll_tags.addTag(
            positive=True,
            name=second_tag,
            description=TAG_DESCRIPTION
        )

        testflow.step("Updating tag name to existing.")
        assert ll_tags.updateTag(
            positive=False,
            tag=second_tag,
            name=first_tag
        )

    @tier1
    def test_check_tag_is_unique(self):
        """
        verify tags functionality
        check via xpath whether the tag is unique
        """
        tag_name = self.generate_tag_name()
        xpathMatch = XPathMatch(ll_tags.util)
        expr = 'count(/tags/tag/name[text()="{0}"])'.format(tag_name)

        testflow.step("Adding a tag.")
        assert ll_tags.addTag(
            positive=True,
            name=tag_name,
            description=TAG_DESCRIPTION
        )

        try:
            testflow.step("Checking if tag is unique.")
            assert xpathMatch(True, 'tags', expr, rslt_eval='1==result')
        except EngineTypeError:
            logger.info('xPath is only supported for rest')
