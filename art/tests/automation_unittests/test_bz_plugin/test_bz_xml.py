'''
Created on Aug 20, 2014

@author: ncredi
'''

import logging
import os
from nose.tools import istest

from utilities.issuesdb import IssuesDB

from art.test_handler.tools import bz as bzd  # pylint: disable=E0611
from art.test_handler.settings import initPlmanager

from art.unittest_lib import BaseTestCase as TestCase

from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)

BZ_PLUGIN = None


def setup_module():
    global BZ_PLUGIN
    plmanager = initPlmanager()
    BZ_PLUGIN = [
        pl for pl in plmanager.application_liteners if pl.name == "Bugzilla"
    ][0]
    BZ_PLUGIN.issuedb = IssuesDB(
        os.path.join(os.path.dirname(__file__), 'known_issuedb_bz.xml')
    )


def teardown_module():
    BZ_PLUGIN.issuedb = None


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

    @istest  # should skip
    @bzd({'1': {}})
    def t01(self):
        logger.info('************** NEW BUG in xml & decorator **************')

    @istest  # should skip
    def t02(self):
        logger.info('************** ON QA BUG **************')

    @istest  # should run
    def t03(self):
        logger.info('************** Verify backward compatible **************')

    @istest  # should skip
    @bzd({'1': {}})
    def t04(self):
        logger.info(
            '************ '
            '2 different bugs (skip & pass) skip is expected'
            '************'
        )


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(1, 0, 3, 0)
