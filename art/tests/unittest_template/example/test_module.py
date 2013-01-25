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
    print "setup module"

def tearDownModule():
    print "teardown module"


class MyTestCase(TestCase):
    __test__ = True # nose.loader will collect it
    @classmethod
    def setUpClass(cls):
        print "setup class"

    @classmethod
    def tearDownClass(cls):
        print "tear down class"

    def setUp(self):
        print "setup test"

    def tearDown(self):
        print "tear down test"

    @istest
    @skipIf(True, "testing reason")
    def test_ahoj(self):
        """TEST ahoj"""
        print "testing 'ahoj' functionality"

    @istest
    def test_cau(self):
        """TEST cau"""
        print "testing 'cau' functionality"


