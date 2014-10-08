"""
----------------------------
Tests results summary plugin
----------------------------

This plugin counts number of passed, skipped and failed test cases

"""

import logging
from art.test_handler.test_runner import _TestElm, TestCase
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import (
    IApplicationListener
)
from art.test_handler.plmanagement.interfaces.report_formatter import (
    IResultsCollector
)
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

logger = logging.getLogger('tests_summary')


class TestsResultsSummary(Component):
    """
    Summarize tests results
    """
    implements(IResultsCollector, IPackaging, IApplicationListener)
    name = 'Results Summary'
    enabled = True

    def __init__(self):
        super(TestsResultsSummary, self).__init__()
        self.skipped = 0
        self.failed = 0
        self.passed = 0
        self.error = 0

    def add_test_result(self, result):
        """
        Called when new result is available
        Parameters:
         * result - dict_like object which contains all available results
                    related to test_case
         * test_case - TestCase object
        """
        if not isinstance(result, TestCase):
            return
        if result['status'] == _TestElm.TEST_STATUS_PASSED:
            self.passed += 1
        elif result['status'] == _TestElm.TEST_STATUS_FAILED:
            self.failed += 1
        elif result['status'] == _TestElm.TEST_STATUS_SKIPPED:
            self.skipped += 1
        elif result['status'] == _TestElm.TEST_STATUS_ERROR:
            self.error += 1

    def on_application_start(self):
        pass

    def on_application_exit(self):
        logger.info("Run summary:  Pass - %s, Fail - %s, Skip - %s, "
                    "Error - %s", self.passed, self.failed,
                    self.skipped, self.error)

    def on_plugins_loaded(self):
        pass

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Nelly Credi'
        params['author_email'] = 'ncredi@redhat.com'
        params['description'] = 'test results summary for ART'
        params['long_description'] = ('Plugin for ART which summarizes '
                                      'execution results')
        params['py_modules'] = ['art.test_handler.plmanagement'
                                '.plugins.tests_results_summary_plugin']
