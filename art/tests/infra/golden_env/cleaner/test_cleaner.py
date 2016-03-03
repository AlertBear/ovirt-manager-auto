import logging

from art.unittest_lib import BaseTestCase
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.high_level.datacenters as hl_dc

import golden_env.config as config


LOGGER = logging.getLogger(__name__)


class CleanGoldenEnv(BaseTestCase):
    __test__ = True

    def test_clean_dc(self):
        dcs = ll_dc.get_datacenters_list()
        for dc in dcs:
            if dc.name != 'Default':
                hl_dc.clean_datacenter(
                    True,
                    dc.name,
                    vdc=config.VDC,
                    vdc_password=config.VDC_PASSWORD
                )
