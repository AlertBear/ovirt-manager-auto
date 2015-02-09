'''
Created on Aug 20, 2014

@author: ncredi
'''

import logging

from nose.tools import istest
from art.test_handler.tools import bz as bzd  # pylint: disable=E0611

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


class TestCaseBzPlugin(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    def setUp(self):
        logger.info('************** setup test **************')

    def tearDown(self):
        logger.info('************** teardown test **************')

    @istest  # should run
    @bzd({'1': {'engine': ['java'], 'version': ['3.5']}})
    def t01(self):
        logger.info('************** NEW BUG not current engine **************')

    @istest  # should skip
    @bzd({'2': {'engine': ['rest'], 'version': ['3.5']}})
    def t02(self):
        logger.info('************** ON QA BUG current engine **************')

    @istest  # should run
    @bzd({'3': {'engine': ['java', 'sdk'], 'version': ['3.4', '3.5']}})
    def t03(self):
        logger.info('*********** ON_QA BUG not current version ***********')

    @istest  # should run
    @bzd({'4': {'engine': ['rest'], 'version': ['3.5']}})
    def t04(self):
        logger.info('************* VERIFIED BUG current engine *************')

    @istest  # should skip
    @bzd({'5': {'engine': None, 'version': ['3.5']}})
    def t05(self):
        logger.info('************* CLOSED BUG in newer version *************')

    @istest  # should run
    @bzd({'5': {'engine': None, 'version': ['3.6.1']}})
    def t06(self):
        logger.info('************** CLOSED BUG **************')

    @istest  # should skip
    @bzd({'6': {'engine': ['rest'], 'version': ['3.5.1']}})
    def t07(self):
        logger.info('************* DUPLICATE BUG points to NEW *************')

    @istest  # should run
    @bzd('7')
    def t08(self):
        logger.info('************** Verify backward compatible **************')

    @istest  # should run
    @bzd({'7': {'engine': None, 'version': None},
          '8': {'engine': None, 'version': None}})
    def t09(self):
        logger.info('**************** Verify multiple bugs ****************')


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(6, 0, 3, 0)
