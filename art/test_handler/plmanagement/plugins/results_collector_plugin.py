
from art.test_handler.plmanagement.interfaces.application import IApplicationListener
from art.test_handler.plmanagement import Component, ExtensionPoint, implements, get_logger
from art.test_handler.plmanagement.interfaces.report_formatter import \
        IResultsFormatter, IResultsCollector

logger = get_logger('results_collector')

class ResultsCollector(Component):
    """
    Plugin collects results and distributes them into formatters
    """
    implements(IResultsCollector, IApplicationListener)
    formatters = ExtensionPoint(IResultsFormatter)

    def add_test_result(self, res, test_case):
        self.formatters.add_test_result(res, test_case)

    def on_application_start(self):
        pass

    def on_application_exit(self):
        self.formatters.generate_report()

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, config):
        return True

