import logging
from unittest import TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_d
from art.test_handler.tools import tcms
import config

logger = logging.getLogger(__name__)


class TestCase284310(TestCase):
    """
    Starting version 3.3 attaching domains should activate them automatically.
    https://tcms.engineering.redhat.com/case/284310/?from_plan=5292
    """
    __test__ = True
    tcms_plan_id = '5292'
    tcms_test_case = '284310'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def add_another_storage_domain(self):
        """ Check that both storage domains were automatically activated after attaching them.
        """
        self.assertTrue(ll_st_d.attachStorageDomain(
            True, config.DATA_CENTER_NAME, config.ST_NAME))
        self.assertTrue(ll_st_d.attachStorageDomain(
            True, config.DATA_CENTER_NAME, config.ST_NAME_2))

        self.assertTrue(ll_st_d.is_storage_domain_active(
            config.DATA_CENTER_NAME, config.ST_NAME))
        self.assertTrue(ll_st_d.is_storage_domain_active(
            config.DATA_CENTER_NAME, config.ST_NAME_2))
