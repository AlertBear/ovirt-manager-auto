import pytest

from art.test_handler.tools import polarion, bz
from art.unittest_lib import CoreSystemTest, tier1

import config


class TestDocsLinks(CoreSystemTest):
    """
    Check for documentation links existence and functionality.
    """
    @staticmethod
    @polarion("RHEVM3-8689")
    @bz({"1523685": {}})
    @pytest.mark.skipif(
        config.upstream_flag, reason="Tests supported only on downstream"
    )
    @tier1
    @pytest.mark.parametrize(
        'link_id', config.DOC_LINK_IDS
    )
    def test_docs_links(welcome_page, link_id):
        link = welcome_page.get_link_by_id(link_id)

        assert link, (
            'Docs link ID {0} not found on the welcome page.'.format(link_id)
        )
        assert link.is_reachable, (
            'Docs link {0} (ID {1}) is not reachable, href: {2}'.format(
                link.text, link_id, link.href
            )
        )
