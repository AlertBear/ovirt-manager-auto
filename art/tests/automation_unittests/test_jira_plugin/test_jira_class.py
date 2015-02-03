
import logging


from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


class TestJiraPluginSkipWholeClass(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True
    jira = {'ISSUE-1': None}

    def setUp(self):
        raise Exception("Setup should not run")

    @classmethod
    def setupClass(cls):
        raise Exception("Setup class should not run")

    def test_01(self):
        raise Exception("Test1 should not run")

    def test_02(self):
        raise Exception("Test2 should not run")


class TestJiraPluginRunWholeClass(TestCase):
    """
    This classs and all its testcases should be executed
    """
    __test__ = True
    jira = {'ISSUE-2': None}

    def test_01(self):
        logger.info("Verify all TestCase class is executed 1")

    def test_02(self):
        logger.info("Verify all TestCase class is executed 2")


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    def test_verify(self):
        self.assert_expected_results(2, 0, 2, 0)
