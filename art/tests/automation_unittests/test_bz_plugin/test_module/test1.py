from art.unittest_lib import BaseTestCase as TestCase


bz = {'2': {'engines': None, 'version': None}}


def setup_module():
    raise Exception("Should be skipped!")


class TestBzPluginSkipWholeModule(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        raise Exception("Should be skipped!")

    def setUp(self):
        raise Exception("Should be skipped!")

    def test_01(self):
        raise Exception("Should be skipped!")
