
from art.test_handler.plmanagement import Interface

class IResultsFormatter(Interface):
    def generate_report(self):
        """ Called when reports are needed to generate """

    def add_test_result(self, result, test_case):
        """
        Called when new result is avaiable
        Parameters:
         * result - dict_like object which contains all avaiable results
                    related to test_case
         * test_case - TestCase object
        """

class IResultsCollector(Interface):
    def add_test_result(self, result, test_case):
        """ Called when new result is avaiable """
