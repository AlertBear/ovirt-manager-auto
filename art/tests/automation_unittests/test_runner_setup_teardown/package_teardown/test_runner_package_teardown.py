'''
Created on Jul 28, 2014

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

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')
        VerifyTeardownResults.increase_teardown_counter()

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')
