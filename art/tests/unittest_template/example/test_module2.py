"""
Here you can implement your test cases. you also can add another modules into
this folder.
"""


from unittest import TestCase, TestSuite, skipIf
from nose.tools import istest
from nose.suite import ContextSuite

try:
    from . import ART_CONFIG
    print "found configuration of ART"
except ImportError:
    ART_CONFIG = None

def setUpModule():
    print "setup module2"

def tearDownModule():
    print "teardown module2"


class MyTestCase2(TestCase):
    __test__ = True # nose.loader will collect it
    @classmethod
    def setUpClass(cls):
        print "setup class2"

    @classmethod
    def tearDownClass(cls):
        print "tear down class2"

    def setUp(self):
        print "setup test2"

    def tearDown(self):
        print "tear down test2"

    @istest
    @skipIf(True, "testing reason")
    def test_ahoj(self):
        """TEST ahoj"""
        print "testing 'ahoj' functionality2"

    @istest
    def test_cau(self):
        """TEST cau"""
        print "testing 'cau' functionality2"


