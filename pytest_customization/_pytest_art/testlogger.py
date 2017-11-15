"""
This module is responsible to produce logs which our automation engineers
are used to see (:

NOTE: this module will be removed once we ensure proper logging our tests
independently on test runner.
"""
import types
import logging
import pytest

import marks


__all__ = [
    "pytest_addoption",
    "pytest_artconf_ready",
    "pytest_sessionstart",
]


DELIMITER = "=" * 80
BUGZILLA_SHOW_BUG_URL = "https://bugzilla.redhat.com/show_bug.cgi?id=%s"
POLARION_WI_RHEVM_URL = (
    "https://polarion.engineering.redhat.com/polarion/#"
    "/project/RHEVM3/workitem?id=%s"
)
JIRA_SHOW_ISSUE_URL = "https://projects.engineering.redhat.com/browse/%s"
logger = logging.getLogger('art.logging')
flow_logger = logging.getLogger('art.flow')


def align_description(doc):
    if doc:
        doc = doc.strip()
        if doc:
            return [l.strip() for l in doc.splitlines()]
    return []


class TestFlowInterface(object):
    """
    This class provide static interfaces to user in order to contribute on
    CI console content per each test.
    """

    @staticmethod
    def _get_logger():
        return getattr(pytest.config, '_testlogger', None)

    @staticmethod
    def step(msg, *args, **kwargs):
        """
        This function add single step into console.

        :param msg: step description
        :type msg: str
        :param args: arguments used to format message
        :type args: tuple
        :param kwargs: keywords used to format message
        :type kwargs: dict
        """
        tl = TestFlowInterface._get_logger()
        if tl:
            tl.log_teststep(msg, *args, **kwargs)

    @staticmethod
    def skip(msg, *args, **kwargs):
        """
        This function add single skip step into console.

        :param msg: step description
        :type msg: str
        :param args: arguments used to format message
        :type args: tuple
        :param kwargs: keywords used to format message
        :type kwargs: dict
        """
        tl = TestFlowInterface._get_logger()
        if tl:
            tl.log_test_skip_step(msg, *args, **kwargs)

    @staticmethod
    def setup(msg, *args, **kwargs):
        """
        This function add single setup step into console.

        :param msg: step description
        :type msg: str
        :param args: arguments used to format message
        :type args: tuple
        :param kwargs: keywords used to format message
        :type kwargs: dict
        """
        tl = TestFlowInterface._get_logger()
        if tl:
            tl.log_testsetup(msg, *args, **kwargs)

    @staticmethod
    def teardown(msg, *args, **kwargs):
        """
        This function add single teardown step into console.

        :param msg: step description
        :type msg: str
        :param args: arguments used to format message
        :type args: tuple
        :param kwargs: keywords used to format message
        :type kwargs: dict
        """
        tl = TestFlowInterface._get_logger()
        if tl:
            tl.log_testteardown(msg, *args, **kwargs)


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
        self.step_id = 0
        flow_logger.addFilter(self.log_filter)
        self.log_delimiter = False

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
        self.step_id = 0
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
        logger.info("--TEST START-- %s", item)
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

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        """
        :param item: test item to perform teardown for
        :type item: instance of pytest.Item
        """
        logger.info(DELIMITER)
        logger.info("--TEST END-- %s", item)
        yield

    def _log_header(self, item):
        if item is None:
            return  # It shouldn't happen but just for case it will.

        if self.step_id == 0:
            flow_logger.info(DELIMITER)
            self.log_delimiter = True

        self.itnum += 1
        description = self.get_desctription(item)
        logger.info("Test Name: %s", self.get_test_name(item))
        for line in description:
            logger.info("Test Description: %s", line)
        logger.info("Iteration number: %s", self.itnum)

        team = marks.get_item_team(item)

        flow_logger.info(
            "%03d: %s/%s", self.itnum, team, self.get_test_name(item)
        )
        for line in description:
            flow_logger.info("    %s", line)
        if hasattr(item, "callspec"):
            parametrized_params = getattr(item.callspec, "params", {})
            if "storage" in parametrized_params:
                storage = parametrized_params["storage"]
                flow_logger.info("STORAGE: %s", storage.upper())

        m = item.get_marker("polarion-testcase-id")
        if m:
            message = "  POLARION: %s"
            for value in m.args:
                url = POLARION_WI_RHEVM_URL % value
                flow_logger.info(message, url)

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
        if report.outcome == "skipped":
            if report.when == "setup":
                self._log_header(self.current_item)
            if report.when != "call":
                self._log_footer(level, report)
        if report.when == "call":
            self._log_footer(level, report)
        self.log_filter.toggle(True)

    def _log_footer(self, level, report):
        if report.outcome == 'skipped':
            # Report possible issues why the test-case was skipped.
            for mname in ('bugzilla', 'jira'):
                m = self.current_item.get_marker(mname)
                if m:
                    message = "  {0}: %s".format(mname.upper())
                    for value in m.args:
                        if mname == "bugzilla":
                            if isinstance(value, dict):
                                for key in value.keys():
                                    url = BUGZILLA_SHOW_BUG_URL % key
                                    flow_logger.info(message, url)
                            else:
                                flow_logger.info(message, value)
                        elif mname == "jira":
                            url = JIRA_SHOW_ISSUE_URL % value
                            flow_logger.info(message, url)

        logger.log(level, "Status: %s", report.outcome)
        flow_logger.log(level, "Result: %s", report.outcome.upper())
        if report.outcome in ("failed", "error"):
            for rec in self.log_filter:
                flow_logger.log(level, " ERR: %s", rec.getMessage())
        else:
            self.log_filter.flush()

    def pytest_unconfigure(self, config):
        flow_logger.removeFilter(self.log_filter)

    def print_flow_logger(self, log_level, log_type, msg, *args, **kwargs):
        self.log_filter.toggle(False)
        if self.step_id == 0 and not self.log_delimiter:
            flow_logger.info(DELIMITER)
        else:
            self.log_delimiter = False

        self.step_id += 1
        msg = "      Test {0}  {1:2}: {2}".format(log_type, self.step_id, msg)
        try:
            # we may want to check length of message
            flow_logger.log(log_level, msg, *args, **kwargs)
        finally:
            self.log_filter.toggle(True)

    def log_teststep(self, msg, *args, **kwargs):
        """
        User interface to add the Test Step into console.
        """
        self.print_flow_logger(logging.INFO, "Step", msg, *args, **kwargs)

    def log_test_skip_step(self, msg, *args, **kwargs):
        """
        User interface to add Warning to Test skip into console.
        """
        self.print_flow_logger(logging.WARN, "Skip", msg, *args, **kwargs)

    def log_testsetup(self, msg, *args, **kwargs):
        """
        User interface to add the Test setup into console.
        """
        self.print_flow_logger(logging.INFO, "Setup", msg, *args, **kwargs)

    def log_testteardown(self, msg, *args, **kwargs):
        """
        User interface to add the Test teardown into console.
        """
        self.print_flow_logger(logging.INFO, "Teardown", msg, *args, **kwargs)


def pytest_artconf_ready(config):
    """
    Load the logging plugin into pytest
    """
    config._testlogger = ARTLogging()
    config.pluginmanager.register(config._testlogger)


def pytest_sessionstart(session):
    if not session.config.getoption("drop_summary"):
        return

    terminal_name = "terminalreporter"
    try:  # there was change in interface of plugin management
        terminal = session.config.pluginmanager.getplugin(terminal_name)
    except AttributeError:
        terminal = session.config.pluginmanager.get_plugin(terminal_name)

    def fake_summary(self):
        pass  # this function does nothing instead of printing summary

    # Error summary
    terminal.summary_errors = types.MethodType(
        fake_summary, terminal, terminal.__class__
    )

    # Failure summary
    terminal.summary_failures = types.MethodType(
        fake_summary, terminal, terminal.__class__
    )


def pytest_addoption(parser):
    parser.addoption(
        '--drop-summary',
        dest="drop_summary",
        action="store_true",
        default=False,
        help="You can dissable print of summary at the end of session.",
    )
