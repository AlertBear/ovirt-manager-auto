
from test_handler.plmanagement import Interface

class IResultsFormatter(Interface):
    def generate_report(self, results):
        """ Called when reports are needed to generate """

