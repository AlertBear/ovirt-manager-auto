import logging
from art.unittest_lib import BaseTestCase as TestCase


logger = logging.getLogger(__name__)
bz = {'4': {'engines': None, 'version': None}}


class TestBzPluginSkipWholeModule(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True

    def test_01(self):
        logger.info("Should be executed!")
