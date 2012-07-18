
import re
import logging

from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from test_handler.reports import FMT


LOGS = 'LOG_CAPTURE'

enabled = 'enabled'
fmt = 'fmt'


class LogCaptureHandler(logging.Handler):
    def __init__(self):
        super(LogCaptureHandler, self).__init__(logging.DEBUG)
        self.test_case = None

    def set_test_case(self, t):
        try:
            self.acquire()
            self.test_case = t
        finally:
            self.release()

    def emit(self, rec):
        if self.test_case is None:
            return
        log = getattr(self.test_case, 'log', str())
        log +=  self.format(rec) + '\n'
        self.test_case.log = log


class LogCapture(Component):
    """
    Plugin captures logs and assigns them to related to test_case
    """
    implements(IConfigurable, ITestCaseHandler)
    name = "Log Capture"

    def __init__(self):
        super(LogCapture, self).__init__()
        self.log_handler = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--log-capture', action='store_true', \
                dest='log_capture', help="enable plugin")


    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        fmt_ = conf.get(LOGS, {}).get(fmt, re.sub('[$][A-Z_]+', '', FMT))
        self.log_handler = LogCaptureHandler()
        self.log_handler.setFormatter(logging.Formatter(fmt_))
        root = logging.getLogger()
        root.addHandler(self.log_handler)

    def pre_test_case(self, t):
        self.log_handler.set_test_case(t)

    def post_test_case(self, t):
        self.log_handler.set_test_case(None)

    def test_case_skipped(self, t):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(LOGS, {}).get(enabled, 'false').lower() == 'true'
        return params.log_capture or conf_en
