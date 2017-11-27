import pytest

from art.test_handler.tools import polarion, bz
from art.unittest_lib import CoreSystemTest, tier1

from docs_links import check_links
import config


class TestDocsLinks(CoreSystemTest):
    """
    Check for documentation links existence and functionality.
    """
    @staticmethod
    @polarion("RHEVM3-8689")
    @bz({"1458444": {}})
    @pytest.mark.skipif(
        config.upstream_flag, reason="Tests supported only on downstream"
    )
    @tier1
    def test_docs_links():
        result, failed_link = check_links()
        assert result, failed_link
