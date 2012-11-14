
from art.test_handler.plmanagement.interfaces.application import IApplicationListener
from art.test_handler.plmanagement import Component, ExtensionPoint, implements, get_logger
from art.test_handler.plmanagement.interfaces.report_formatter import \
        IResultsFormatter, IResultsCollector, IResultExtension
from art.test_handler.test_runner import TestCase, TestGroup, TestSuite, \
        SuiteResult, GroupResult, TestResult

logger = get_logger('results_collector')

class ResultsCollector(Component):
    """
    Plugin collects results and distributes them into formatters
    """
    implements(IResultsCollector, IApplicationListener)
    formatters = ExtensionPoint(IResultsFormatter)
    extenders = ExtensionPoint(IResultExtension)

    def add_test_result(self, test):
        if isinstance(test, TestSuite):
            res = SuiteResult()
            self.extenders.pre_suite_result_reported(res, test)
            self.formatters.add_suite_result(res, test)
        elif isinstance(test, TestGroup):
            res = GroupResult()
            self.extenders.pre_group_result_reported(res, test)
            self.formatters.add_group_result(res, test)
        elif isinstance(test, TestCase):
            res = TestResult()
            self.extenders.pre_test_result_reported(res, test)
            res = res.result_from_test_case(test)
            self.formatters.add_test_result(res, test)
        else:
            assert False, "%s is not in (%s, %s, %s)" % \
                    (test, TestCase, TestGroup, TestSuite)

    def on_application_start(self):
        pass

    def on_application_exit(self):
        self.formatters.generate_report()

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, config):
        return True

