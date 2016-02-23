"""
This module is responsible to produce logs which our automation engineers
are used to see (:

NOTE: this module will be removed once we ensure proper logging our tests
independently on test runner.
"""
import logging
import pytest


__all__ = [
    "pytest_artconf_ready",
]


DELIMITER = "=" * 80
logger = logging.getLogger('art.logging')
flow_logger = logging.getLogger('art.flow')


def align_description(doc):
    if doc:
        doc = doc.strip()
        if doc:
            return [l.strip() for l in doc.splitlines()]
    return []


class RecordingFilter(logging.Filter):
    """
    It does not allow user to log messages outside of this module.
    """
    def __init__(self):
        logging.Filter.__init__(self, 'art.flow')
        self._messages = []
        self._on = False

    def filter(self, rec):
        if self._on:
            self._messages.insert(0, rec)
        return not self._on

    def toggle(self, status):
        self._on = status

    def __iter__(self):
        return self

    def next(self):
        if not self._messages:
            raise StopIteration()
        return self._messages.pop()

    def flush(self):
        self._messages = list()


class ARTLogging(object):
    """
    Collection of pytest item related hooks.
    According these we can generate logs similar to ART logs.
    """

    def __init__(self):
        super(ARTLogging, self).__init__()
        self.log_filter = RecordingFilter()
        self.itnum = 0
        self.current_item = None
        self.last_test_class = None
        flow_logger.addFilter(self.log_filter)

    @staticmethod
    def get_test_name(item):
        # Get name of test
        name = item.name
        # Add class name in case test is method
        if item.cls:
            name = "%s.%s" % (item.cls.__name__, name)
        # Add module name
        name = "%s.%s" % (item.module.__name__, name)
        return name

    @staticmethod
    def get_desctription(item):
        """
        Get description of test, doc string
        """
        return align_description(item.function.__doc__)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """
        :param item: test item to perform setup for
        :type item: instance of pytest.Item
        """
        self.current_item = item
        logger.info(DELIMITER)
        # Print the test class description only once and at beginning.
        if item.cls:
            # Is it new class ?
            if self.last_test_class != item.cls.__name__:
                self.last_test_class = item.cls.__name__
                for line in align_description(item.cls.__doc__):
                    logger.info(
                        "Test class description: %s", line,
                    )
        logger.info("SETUP %s", item)
        self.log_filter.toggle(True)
        yield
        logger.info(DELIMITER)

    def pytest_runtest_call(self, item):
        """
        :param item: test item to perform call for
        :type item: instance of pytest.Item
        """
        self.log_filter.toggle(False)
        self._log_header(item)
        self.log_filter.toggle(True)

    def _log_header(self, item):
        if item is None:
            return  # It shouldn't happen but just for case it will.
        self.itnum += 1
        description = self.get_desctription(item)
        logger.info("Test Name: %s", self.get_test_name(item))
        for line in description:
            logger.info("Test Description: %s", line)
        logger.info("Iteration number: %s", self.itnum)

        team = "no-team"
        attr = item.get_marker('attr')
        if attr:
            for info in attr:
                if 'team' in info.kwargs:
                    team = info.kwargs['team']
                    break
        flow_logger.info(
            "%03d: %s/%s", self.itnum, team, self.get_test_name(item)
        )
        for line in description:
            flow_logger.info("    %s", line)
        for attr in ('api', 'storage'):
            value = getattr(item.parent.obj, attr, None)
            if value:
                flow_logger.info("  %s: %s", attr.upper(), value.upper())
        for mname in ('polarion-id', 'bugzilla', 'jira'):
            m = item.get_marker(mname)
            if m:
                for value in m.args:
                    flow_logger.info("  %s: %s", mname.upper(), value)

    def pytest_report_teststatus(self, report):
        level = {
            'passed': logging.INFO,
            'failed': logging.ERROR,
            'error': logging.ERROR,
            'skipped': logging.WARN,
        }.get(report.outcome, logging.INFO)
        self.log_filter.toggle(False)
        if report.when == "setup" and report.outcome in ("failed", "error"):
            self._log_header(self.current_item)
            flow_logger.error(" NOTE: Test failed on setup phase!")
            self._log_footer(level, report)
        if report.when == "call":
            self._log_footer(level, report)
        if report.outcome == "skipped":
            if report.when == "setup":
                self._log_header(self.current_item)
            self._log_footer(level, report)
        self.log_filter.toggle(True)

    def _log_footer(self, level, report):
        logger.log(level, "Status: %s", report.outcome)
        flow_logger.log(level, "Result: %s", report.outcome.upper())
        if report.outcome in ("failed", "error"):
            for rec in self.log_filter:
                flow_logger.log(level, " ERR: %s", rec.getMessage())
        else:
            self.log_filter.flush()
        flow_logger.info(DELIMITER)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        """
        :param item: test item to perform teardown for
        :type item: instance of pytest.Item
        """
        logger.info(DELIMITER)
        logger.info("TEARDOWN %s", item)
        yield

    def pytest_package_setup(self, entry):
        logger.info("PACKAGE SETUP: %s", entry)

    def pytest_package_teardown(self, entry):
        logger.info("PACKAGE TEARDOWN: %s", entry)

    def pytest_unconfigure(self, config):
        flow_logger.removeFilter(self.log_filter)


def pytest_artconf_ready(config):
    """
    Load the logging plugin into pytest
    """
    config.pluginmanager.register(ARTLogging())
