'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest
from unittest2 import skipIf

from art.test_handler.exceptions import SkipTest
from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


class TestCase1(TestCase):

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
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')

    @istest
    @skipIf(True, 'always skip')
    def t02(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')


class TestCase2(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    @istest
    def t01(self):
        logger.info('************** test will be skipped **************')
        raise SkipTest('test should be skipped')

    @istest
    def t02(self):
        logger.info('************** test **************')

    @istest
    @skipIf(True, 'always skip')
    def t03(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')
