'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


def setup_module():
    logger.info('************** setup module **************')


def teardown_module():
    logger.info('************** teardown module **************')


class TestCase6(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    @istest
    def t01(self):
        logger.info('************** should be skipped **************')
        raise Exception('test should be skipped')
