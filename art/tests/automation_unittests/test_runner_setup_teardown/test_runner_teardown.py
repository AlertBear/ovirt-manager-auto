'''
Created on Jul 24, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.test_runner_setup_teardown.verify_results \
    import VerifyTeardownResults

logger = logging.getLogger(__name__)


class TestCaseClassTeardown(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')
        raise Exception('Raise exception in class setup')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')
        VerifyTeardownResults.increase_teardown_counter()

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')


class TestCaseTestTeardown(TestCase):

    __test__ = True

    def setUp(self):
        logger.info('************** setup test **************')
        raise Exception('Raise exception in test setup')

    def tearDown(self):
        logger.info('************** teardown test **************')
        VerifyTeardownResults.increase_teardown_counter()

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')


class VerifyResults(VerifyTeardownResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(4)