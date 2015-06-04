from automation_unittests.verify_results import VerifyUnittestResults


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    apis = set(['rest'])

    def test_verify(self):
        self.assert_expected_results(4, 0, 4, 0)
