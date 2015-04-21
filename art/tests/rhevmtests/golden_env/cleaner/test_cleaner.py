import logging

from art.unittest_lib import BaseTestCase

import art.rhevm_api.tests_lib.high_level.datacenters as hl_dc

from rhevmtests.golden_env import config


LOGGER = logging.getLogger(__name__)


class CleanGoldenEnv(BaseTestCase):
    __test__ = True

    def test_clean_dc(self):

        for dc in config.DC_NAME:
            hl_dc.clean_datacenter(
                True,
                dc,
                vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )