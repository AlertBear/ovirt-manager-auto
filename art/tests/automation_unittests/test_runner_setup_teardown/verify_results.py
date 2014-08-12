'''
Created on Aug 12, 2014

@author: ncredi
'''

import logging

from automation_unittests.verify_results import VerifyUnittestResults

logger = logging.getLogger(__name__)


class VerifyTeardownResults(VerifyUnittestResults):

    __test__ = False
    teardown_counter = 0

    @classmethod
    def increase_teardown_counter(cls):
        cls.teardown_counter += 1

    def assert_expected_results(self, expected):
        logger.info("Teardown execution: %s", self.__class__.teardown_counter)
        logger.info("Expected teardown: %s", expected)
        self.assertEquals(expected, self.__class__.teardown_counter)
