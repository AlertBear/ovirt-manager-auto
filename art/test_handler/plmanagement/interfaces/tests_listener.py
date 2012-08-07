from art.test_handler.plmanagement import Interface


class SkipTest(Exception):
    pass


class ITestCaseHandler(Interface):

    def pre_test_case(self, test_case):
        """
        Called before test_case is executed.
        Parameters:
         * test_case - TestCase instance
        """

    def post_test_case(self, test_case):
        """
        Called after test_case is executed.
        Parameters:
         * test_case - TestCase instance
        """

    def test_case_skipped(self, test_case):
        """
        Called when test was skipped.
        Parameters:
         * test_case - TestCase instance
        """


class ITestGroupHandler(Interface):

    def pre_test_group(self, test_group):
        """
        Called before test_group is executed.
        Parameters:
         * test_group - TestGroup instance
        """

    def post_test_group(self, test_group):
        """
        Called after test_group is executed.
        Parameters:
         * test_group - TestGroup instance
        """

    def test_group_skipped(self, test_group):
        """
        Called when test was skipped.
        Parameters:
         * test_group - TestGroup instance
        """


class ITestSuiteHandler(Interface):

    def pre_test_suite(self, test_suite):
        """
        Called before test_suite is executed.
        Parameters:
         * test_suite - TestSuite instance
        """

    def post_test_suite(self, test_suite):
        """
        Called after test_suite is executed.
        Parameters:
         * test_suite - TestSuite instance
        """


class ITestSkipper(Interface):

    def should_be_test_case_skipped(self, test_case):
        """
        Raise SkipTest exception when test should be skipped
        Parameters:
         * test_suite - TestSuite instance
        """

    def should_be_test_group_skipped(self, test_group):
        """
        Raise SkipTest exception when group should be skipped
        Parameters:
         * test_suite - TestSuite instance
        """

