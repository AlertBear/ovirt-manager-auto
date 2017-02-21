from art.test_handler.tools import polarion
from art.unittest_lib import CoreSystemTest, attr

from docs_links import check_links


class TestDocsLinks(CoreSystemTest):
    """
    Check for documentation links existence and functionality.
    """
    __test__ = True

    @staticmethod
    @polarion("RHEVM3-8685")
    @attr(tier=1)
    def test_docs_links():
        result, failed_link = check_links()
        assert result, failed_link
