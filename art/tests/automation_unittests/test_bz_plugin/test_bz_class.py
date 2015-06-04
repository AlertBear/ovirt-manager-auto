'''
Created on Aug 20, 2014

@author: ncredi
'''

import logging

from nose.tools import istest

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


NFS = 'nfs'
GLUSTERFS = 'glusterfs'


class TestBzPluginRunWholeClass(TestCase):
    """
    This classs and all its testcases should be executed
    """
    __test__ = True

    def test_01(self):
        logger.info("Verify all TestCase class is executed 1")

    def test_02(self):
        logger.info("Verify all TestCase class is executed 2")


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


class TestBzPluginRunCases(TestCase):
    """
    This classs and all its testcases should be be excuted bz verified
    """

    __test__ = True
    storages = set(['nfs', 'glusterfs'])

    bz = {'11': {'engine': None, 'version': None, 'storage': NFS}}

    def test_01(self):
        logger.info("Verify all TestCase class is executed 1")

    def test_02(self):
        logger.info("Verify all TestCase class is executed 2")


class TestBzPluginSkipClassDueToNFSBug(TestCase):
    """
    This classs and all its testcases should be skipped when nfs
    """
    __test__ = True
    storages = set(['nfs', 'glusterfs'])

    bz = {'10': {'engine': None, 'version': None, 'storage': NFS}}

    @classmethod
    def setupClass(cls):
        if cls.storage == NFS:
            raise Exception("Should be skipped when storage_type: nfs!")

        logger.info("Should Run on GlusterFS")

    def setUp(self):
        if self.storage == NFS:
            raise Exception("Should be skipped when storage_type: nfs!")

        logger.info("Should Run on GlusterFS")

    def test_01(self):
        if self.storage == NFS:
            raise Exception("Should be skipped when storage_type: nfs!")
        logger.info("Should Run on GlusterFS")

    def test_02(self):
        if self.storage == NFS:
            raise Exception("Should be skipped when storage_type: nfs!")
        logger.info("Should Run on GlusterFS")


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    apis = set(['rest'])

    @istest
    def verify(self):
        self.assert_expected_results(8, 0, 8, 0)