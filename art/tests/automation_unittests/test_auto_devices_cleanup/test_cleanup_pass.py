__author__ = 'khakimi'


import logging

from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase

logger = logging.getLogger(__name__)


class TestCase1(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class TestCase1 **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class TestCase1 **************')

    @istest
    def t01(self):
        logger.info('************** test 01 TestCase1 **************')
        assert True

    @istest
    def t02(self):
        logger.info('************** test 02 TestCase1 **************')
        assert True


class TestCase2(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class TestCase2 **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class TestCase2 **************')

    @istest
    def t01(self):
        logger.info('************** test 01 TestCase2 **************')
        assert True

    @istest
    def t02(self):
        logger.info('************** test 02 TestCase2 **************')
        assert True

    @istest
    def t03(self):
        logger.info('************** test 03 TestCase2 **************')
        assert True
