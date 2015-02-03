import logging

from art.test_handler.settings import opts
from art.test_handler.tools import jira  # pylint: disable=E0611

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults
from automation_unittests.test_jira_plugin import get_plugin


logger = logging.getLogger(__name__)


class TestCaseJiraPlugin(TestCase):

    __test__ = False
    version = None
    b_version = None
    engine = None
    b_engine = None

    @classmethod
    def setup_class(cls):
        pl = get_plugin("Jira")
        cls.b_version = pl.version
        pl._set_version(cls.version)
        cls.b_engine = opts['engine']
        opts['engine'] = cls.engine

    @classmethod
    def teardown_class(cls):
        pl = get_plugin("Jira")
        pl.version = cls.b_version
        opts['engine'] = cls.b_engine


class Test34SpecificCase(TestCaseJiraPlugin):

    __test__ = True
    version = "3.4"
    engine = 'rest'

    @jira({'ISSUE-1': None})
    def test_01(self):
        raise Exception('Should not run')

    @jira({'ISSUE-2': None})
    def test_02(self):
        logging.info("Passing test case")

    @jira({'ISSUE-4': None})
    def test_03(self):
        raise Exception('Should not run, because it affects 3.4')

    @jira({'ISSUE-3': None})
    def test_04(self):
        raise Exception('Should not run, becuase it is fixed in 3.5')

    @jira({'ISSUE-5': None})
    def test_05(self):
        logging.info("Passing test case")

    @jira({'ISSUE-7': None})
    def test_06(self):
        logging.info("Passing test case")


class Test35SpecificCase(TestCaseJiraPlugin):

    __test__ = True
    version = "3.5"
    engine = 'sdk'

    @jira({'ISSUE-3': None})
    def test_01(self):
        logging.info("Passing test case")

    @jira({'ISSUE-4': None})
    def test_02(self):
        logging.info("Passing test case")

    @jira({'ISSUE-5': None})
    def test_03(self):
        raise Exception('Should not run, becuase it is SDK')

    @jira({'ISSUE-6': None})
    def test_04(self):
        logging.info("Passing test case")


class Test34SDKSpecificCase(TestCaseJiraPlugin):

    __test__ = True
    version = "3.4"
    engine = 'sdk'

    @jira({'ISSUE-6': None})
    def test_01(self):
        raise Exception('Should not run, becuase it is 3.4 & SDK')


class Test34CLISpecificCase(TestCaseJiraPlugin):

    __test__ = True
    version = "3.4"
    engine = 'cli'

    @jira({'ISSUE-7': None})
    def test_01(self):
        raise Exception('Should not run, becuase it is CLI')


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    def test_verify(self):
        self.assert_expected_results(6, 0, 6, 0)
