'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


def setup_module():
    logger.info('************ SETUP MODULE SHOULD NOT EXECUTE ************')
    raise Exception('setup module should be skipped')


def teardown_module():
    logger.info('************ TEARDOWN MODULE SHOULD NOT EXECUTE ************')
    raise Exception('teardown module should be skipped')


class TestCase5(TestCase):

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
