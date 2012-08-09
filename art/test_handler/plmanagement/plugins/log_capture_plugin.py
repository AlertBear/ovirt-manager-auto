
import re
import logging

from art.test_handler.plmanagement import Component, implements, ThreadScope
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.report_formatter import IResultExtension
from art.test_handler.reports import FMT


LOGS = 'LOG_CAPTURE'

enabled = 'enabled'
fmt = 'fmt'
logging_level = 'level'
record_name = 'record_name'

DEFAULT_LEVEL = 'debug'
ATTR_NAME = 'captured_log'


class LogCaptureHandler(logging.Handler):
    def __init__(self):
        #super(LogCaptureHandler, self).__init__(logging.DEBUG)
        logging.Handler.__init__(self, logging.DEBUG)
        self.th_scope = ThreadScope()

    def set_test_case(self, t):
        try:
            self.acquire()
            if t is not None:
                assert self.th_scope.tc is None, \
                        "There is test_case left: %s" % self.th_scope.tc
                setattr(t, ATTR_NAME, str())
                self.th_scope.tc = t
            else:
                del self.th_scope.tc
        finally:
            self.release()

    def emit(self, rec):
        if self.th_scope.tc is None:
            return
        log = getattr(self.th_scope.tc, ATTR_NAME, str())
        log +=  self.format(rec) + '\n'
        setattr(self.th_scope.tc, ATTR_NAME, log)


class LogCapture(Component):
    """
    Plugin captures logs and assigns them to related to test_case
    """
    implements(IConfigurable, ITestCaseHandler, IPackaging, IResultExtension)
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

        self.rec_name = conf.get(LOGS, {}).get(record_name, ATTR_NAME)

        fmt_ = conf.get(LOGS, {}).get(fmt, re.sub('[$][A-Z_]+', '', FMT))
        level = conf.get(LOGS, {}).get(logging_level, DEFAULT_LEVEL).upper()
        level = getattr(logging, level)
        self.log_handler = LogCaptureHandler()
        self.log_handler.setLevel(level)
        self.log_handler.setFormatter(logging.Formatter(fmt_))
        root = logging.getLogger()
        root.addHandler(self.log_handler)

    def pre_test_result_reported(self, res, t):
        self.log_handler.set_test_case(None)
        setattr(res, self.rec_name, getattr(t, ATTR_NAME, str()))

    def pre_test_case(self, t):
        self.log_handler.set_test_case(t)

    def post_test_case(self, t):
        pass

    def test_case_skipped(self, t):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(LOGS, {}).get(enabled, 'false').lower() == 'true'
        return params.log_capture or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Log capturing for ART'
        params['long_description'] = 'Log capturing plugin for ART. '\
                                'It collects logs related to running test_case.'
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.log_capture_plugin']

