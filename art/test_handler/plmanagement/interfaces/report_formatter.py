
from art.test_handler.plmanagement import Interface

class IResultsFormatter(Interface):
    def generate_report(self):
        """ Called when reports are needed to generate """

    def add_test_result(self, result, test_case):
        """ Called when new result is avaiable """

class IResultsCollector(Interface):
    def add_test_result(self, result, test_case):
        """ Called when new result is avaiable """
