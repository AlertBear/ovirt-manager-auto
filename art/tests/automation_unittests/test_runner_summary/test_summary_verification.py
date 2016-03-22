'''
Created on Jul 24, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase, SkipTest

from automation_unittests.verify_results import VerifyUnittestResults

logger = logging.getLogger(__name__)


class TestSummary1(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')
        raise Exception('Raise exception in class setup')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    @istest
    def t01(self):
        logger.info('************** test should not run  **************')
        raise Exception('test should be skipped')


class TestSummary2(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')

    @istest
    def t01(self):
        logger.info('************** test **************')

    @istest
    def t02(self):
        logger.info('************** test will fail **************')
        self.assertTrue(False)

    @istest
    def t03(self):
        logger.info('************** test will skip **************')
        raise SkipTest('test should be skipped')


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(1, 1, 2, 0)
