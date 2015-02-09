from automation_unittests.verify_results import VerifyUnittestResults


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    def test_verify(self):
        self.assert_expected_results(1, 0, 1, 0)
