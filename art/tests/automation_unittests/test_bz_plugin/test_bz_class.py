'''
Created on Aug 20, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


class TestBzPluginSkipWholeClass(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True
    bz = {'2': {'engine': None, 'version': None}}

    @classmethod
    def setupClass(cls):
        raise Exception("Should be skipped!")

    def setUp(self):
        raise Exception("Should be skipped!")

    def test_01(self):
        raise Exception("Should be skipped!")

    def test_02(self):
        raise Exception("Should be skipped!")


class TestBzPluginRunWholeClass(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True
    bz = {'4': {'engine': None, 'version': None}}

    def test_01(self):
        logger.info("Verify all TestCase class is executed 1")

    def test_02(self):
        logger.info("Verify all TestCase class is executed 2")


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(2, 0, 2, 0)
