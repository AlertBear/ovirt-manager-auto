'''
Created on Jul 24, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


class TestCaseClassTeardown(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')
        raise Exception

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')


class TestCaseTestTeardown(TestCase):

    __test__ = True

    def setUp(self):
        logger.info('************** setup test **************')
        raise Exception

    def tearDown(self):
        logger.info('************** teardown test **************')

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')
