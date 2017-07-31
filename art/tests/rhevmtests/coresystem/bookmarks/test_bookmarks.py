"""
Tests for creating/updating/deleting/searching of bookmarks
"""
import logging
import pytest

from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import bookmarks as ll_bookmarks
from art.unittest_lib import tier1
from art.unittest_lib import CoreSystemTest as TestCase, testflow

logger = logging.getLogger(__name__)


class BookmarkBase(TestCase):
    """ Base class for bookmarks"""
    @pytest.fixture(scope="function", autouse=True)
    def setup_function(self, request):
        def finalize():
            testflow.teardown("Remove bookmark %s", self.bookmark_name)
            assert ll_bookmarks.remove_bookmark(bookmark=self.bookmark_name)
        request.addfinalizer(finalize)

    def _add_bookmark(self, value):
        """
        Add bookmark with value

        Args:
            value (str): value for a bookmark

        Returns:
            bool: True if operation successful, otherwise - False
        """
        testflow.step(
            "Create a bookmark with name %s and value %s",
            self.bookmark_name, value
        )
        return ll_bookmarks.create_bookmark(
            name=self.bookmark_name, value=value
        )

    def basic_vms_bookmark(self):
        value = "Vms: test*"
        assert self._add_bookmark(value=value)

    def underscore_vms_bookmark(self):
        value = "Vms: test_vm*"
        assert self._add_bookmark(value=value)

    def dash_vms_bookmark(self):
        value = "Vms: test-vm*"
        assert self._add_bookmark(value=value)

    def update_vms_bookmark(self):
        value = "Vms: test*"
        new_value = "Vms: testtest*"
        assert self._add_bookmark(value=value)
        testflow.step(
            "Update bookmark %s with value %s to value %s",
            self.bookmark_name, value, new_value
        )
        assert ll_bookmarks.update_bookmark(
            self.bookmark_name, value=new_value
        )


@tier1
class TestBookmarksValue(BookmarkBase):
    """ Bookmarks test class """
    bookmark_name = "testBookmark"

    @polarion("RHEVM-22185")
    def test_basic_vms_bookmark(self):
        """
        Test adding a bookmark with basic vms search
        """
        self.basic_vms_bookmark()

    @polarion("RHEVM-22186")
    def test_underscore_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with underscore
        """
        self.underscore_vms_bookmark()

    @polarion("RHEVM-22187")
    def test_dash_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with dash
        """
        self.dash_vms_bookmark()

    @polarion("RHEVM-22188")
    def test_update_vms_bookmark(self):
        """
        Test updating a bookmark with search for vms
        """
        self.update_vms_bookmark()


@tier1
class TestBookmarksUnderscoreName(BookmarkBase):
    """ Bookmark tests with underscore in name """
    bookmark_name = "test_bookmark"

    @polarion("RHEVM-22189")
    def test_basic_vms_bookmark(self):
        """
        Test adding a bookmark with basic vms search
        """
        self.basic_vms_bookmark()

    @polarion("RHEVM-22190")
    def test_underscore_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with underscore
        """
        self.underscore_vms_bookmark()

    @polarion("RHEVM-22191")
    def test_dash_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with dash
        """
        self.dash_vms_bookmark()

    @polarion("RHEVM-22192")
    def test_update_vms_bookmark(self):
        """
        Test updating a bookmark with search for vms
        """
        self.update_vms_bookmark()


@tier1
class TestBookmarksDashName(BookmarkBase):
    """ Bookmark tests with dash in name """
    bookmark_name = "test-bookmark"

    @polarion("RHEVM-22193")
    def test_basic_vms_bookmark(self):
        """
        Test adding a bookmark with basic vms search
        """
        self.basic_vms_bookmark()

    @polarion("RHEVM-22194")
    def test_underscore_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with underscore
        """
        self.underscore_vms_bookmark()

    @polarion("RHEVM-22195")
    def test_dash_vms_bookmark(self):
        """
        Test adding a bookmark with search for vms with dash
        """
        self.dash_vms_bookmark()

    @polarion("RHEVM-22196")
    def test_update_vms_bookmark(self):
        """
        Test updating a bookmark with search for vms
        """
        self.update_vms_bookmark()


@tier1
class TestBookmarksAdvanced(BookmarkBase):
    """ Advanced bookmark tests """
    bookmark_name = "testBookmark"
    value = "Vms: test*"

    @polarion("RHEVM-22197")
    def test_create_bookmark_with_same_name(self):
        assert self._add_bookmark(value=self.value)
        assert not self._add_bookmark(value=self.value), (
            "Bookmark with the same name can be created"
        )

    @polarion("RHEVM-22198")
    def test_list_bookmarks(self):
        assert self._add_bookmark(self.value)
        all_bookmarks = ll_bookmarks.get_bookmark_names_list()
        testflow.step(
            "Check if bookmark %s is in list of all bookmarks %s",
            self.bookmark_name, ", ".join(all_bookmarks)
        )
        assert self.bookmark_name in all_bookmarks, (
            "Bookmark %s is not in all bookmarks list", self.bookmark_name
        )
