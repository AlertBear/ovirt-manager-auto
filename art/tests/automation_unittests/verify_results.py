'''
Created on Jul 31, 2014

@author: ncredi
'''

import logging
from abc import abstractmethod

from art.test_handler.settings import initPlmanager
from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


class VerifyUnittestResults(TestCase):

    __test__ = False

    @classmethod
    def teardown_class(cls):
        """
        Initialize test summary parameters to verify results
        """
        sum_plugin = cls.get_summary_plugin()
        logger.info('Init test result summary parameters')
        sum_plugin.passed = sum_plugin.failed = 0
        sum_plugin.skipped = sum_plugin.error = 0

    def assert_expected_results(self, passed, failed, skipped, error):
        sum_plugin = self.get_summary_plugin()
        logger.info("Run summary: Pass - %s, Fail - %s, Skip - %s, "
                    "Error - %s", sum_plugin.passed, sum_plugin.failed,
                    sum_plugin.skipped, sum_plugin.error)
        logger.info("Expected summary: Pass - %s, Fail - %s, Skip - %s, "
                    "Error - %s", passed, failed, skipped, error)
        self.assertEquals((passed, failed, skipped, error),
                          (sum_plugin.passed, sum_plugin.failed,
                           sum_plugin.skipped, sum_plugin.error))

    @classmethod
    def get_summary_plugin(cls):
        plmanager = initPlmanager()
        return [pl for pl in plmanager.application_liteners
                if pl.name == "Results Summary"][0]

    @abstractmethod
    def verify(self):
        pass
