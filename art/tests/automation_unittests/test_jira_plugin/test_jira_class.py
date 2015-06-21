
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


class TestJiraPluginSkipClassWhenNFS(TestCase):
    """
    This classs and all its testcases should be skipped
    """
    __test__ = True
    jira = {'ISSUE-8': None}

    storages = set(['glusterfs', 'nfs', 'iscsi'])

    def setUp(self):
        if self.storage == 'nfs':
            raise Exception("Setup should not run")
        logging.info("Passing test case if not NFS")

    @classmethod
    def setupClass(cls):
        if cls.storage == 'nfs':
            raise Exception("Setup should not run")
        logging.info("Passing test case if not NFS")

    def test_01(self):
        if self.storage == 'nfs':
            raise Exception("Setup should not run")
        logging.info("Passing test case if not NFS")

    def test_02(self):
        if self.storage == 'nfs':
            raise Exception("Setup should not run")
        logging.info("Passing test case if not NFS")


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    apis = set(['rest'])

    def test_verify(self):
        self.assert_expected_results(24, 0, 16, 0)
