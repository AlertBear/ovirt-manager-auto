
import os
import csv
import time
from contextlib import contextmanager
from test_handler.plmanagement import Component, implements, get_logger
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from test_handler.plmanagement.interfaces.time_measurement import ITimeMeasurement


logger = get_logger('csv-formatter')
CSV = 'CSV_FORMATER'
precision = 'precision'
order = 'order'

I_ID = 'id'
I_MODULE_NAME = 'module_name'
I_TEST_NAME = 'test_name'
I_START_TIME = 'start_time'
I_REQ_ELAPSED_TIME = 'req_elapsed_time'
I_TEST_STATUS = 'test_status'
I_DEBUG_INFO = 'debug_info'


DEFAULT_PRECISSION = '5'
DEFAULT_ORDER = ', '.join((
    I_ID, I_MODULE_NAME, I_START_TIME, \
            I_REQ_ELAPSED_TIME, I_TEST_STATUS, \
            I_DEBUG_INFO
    ))


class CSVFormatter(Component):
    """
    Generates CSV report; default: %(const)s
    """
    implements(IResultsFormatter, IConfigurable, ITimeMeasurement, ITestCaseHandler)
    name = 'CSV'
    default_file_name = "results.csv"

    def __init__(self):
        super(CSVFormatter, self).__init__()
        self.fh = None
        self.csv = None
        self.format_str = '%.3f'
        self.measurements = []
        self.order = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.abspath("results/%s" % cls.default_file_name)
        parser.add_argument('--rf-csv', action="store", dest='rf_csv', \
                help=cls.__doc__, const=out, default=out, nargs='?')

    def configure(self, params, config):
        if not self.is_enabled(params, config):
            return

        self.format_str = '%%.%sf' % \
                config.get(CSV, {}).get(precision, DEFAULT_PRECISSION)
        folder = os.path.dirname(params.rf_csv)
        if not os.path.exists(folder):
            os.makedirs(folder)
        self.fh = open(params.rf_csv, 'w')
        self.csv = csv.writer(self.fh)
        try:
            self.order = config[CSV].as_list(order)
        except KeyError:
            self.order = DEFAULT_ORDER.replace(',', ' ').split()

    def generate_report(self):
        if self.fh is not None:
            self.fh.close()

    def add_test_result(self, kwargs, test_case):
        items = []
        for i in self.order:
            if i == I_ID:
                items.append(getattr(kwargs, 'id', None))
            elif i == I_MODULE_NAME:
                items.append(getattr(kwargs, 'module_name', None))
            elif i == I_TEST_NAME:
                items.append(getattr(kwargs, 'test_name', None))
            elif i == I_START_TIME:
                items.append(getattr(kwargs, 'start_time', None))
            elif i == I_REQ_ELAPSED_TIME:
                measure = float('nan')
                if self.measurements:
                    if len(self.measurements) != 1:
                        logger.warn("Got more measure_time records, "\
                                "then expected: %", self.measurements)
                    measure = self.format_str % self.measurements.pop()
                items.append(measure)
            elif i == I_TEST_STATUS:
                items.append(getattr(kwargs, 'status', None))
            elif i == I_DEBUG_INFO:
                #items.append(getattr(test_case, 'log', None))
                pass
        self.csv.writerow(items)

    def pre_test_case(self, t):
        self.measurements = []

    def post_test_case(self, t):
        pass

    def test_case_skipped(self, t):
        pass

    def on_start_measure(self):
        pass

    def on_stop_measure(self, t):
        if self.measurements is not None:
            self.measurements.append(t)

    @classmethod
    def is_enabled(cls, params, conf):
        return params.rf_csv is not None


