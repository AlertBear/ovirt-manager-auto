'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest
from unittest2 import skipIf

from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


def setup_module():
    logger.info('************** setup module **************')
    raise Exception('Raise exception in module setup')


def teardown_module():
    logger.info('************** teardown module **************')


class TestCase3(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('*********** SETUP CLASS SHOULD NOT EXECUTE ***********')
        raise Exception('setup class should be skipped')

    @classmethod
    def teardown_class(cls):
        logger.info('********** TEARDOWN CLASS SHOULD NOT EXECUTE **********')
        raise Exception('teardown class should be skipped')

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')


class TestCase4(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('*********** SETUP CLASS SHOULD NOT EXECUTE ***********')
        raise Exception('Raise exception in class setup')

    @classmethod
    def teardown_class(cls):
        logger.info('********** TEARDOWN CLASS SHOULD NOT EXECUTE **********')
        raise Exception('teardown class should be skipped')

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')

    @istest
    @skipIf(True, 'always skip')
    def t02(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')
