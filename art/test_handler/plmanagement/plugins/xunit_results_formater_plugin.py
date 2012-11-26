from lxml.etree import Element, ElementTree, PI
from lxml.builder import E
import datetime
from dateutil import tz
import logging

import os
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

JUNIT_NOFRAMES_STYLESHEET = "junit-noframes.xsl"


# TODO: same problem as tcms_plugin
logger = logging.getLogger('xunit_results_formatter')

DEFAULT_OUT_MSG = 'Sorry, no support for backtrace yet.'


def total_seconds(td):
    ''' For Py2.7 compatibility. There is no function in Py2.6 computing this. '''
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6


class XUnit(Component):
    """
    Generates x-unit report; deafult: %(const)s
    """
    implements(IResultsFormatter, IConfigurable, IPackaging)
    name = 'X unit'
    enabled = True
    default_file_name = "xunit_output.xml"

    def __init__(self):
        super(XUnit, self).__init__()
        self.path = None
        self.tree = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.expanduser("~/results/%s" % cls.default_file_name)
        parser.add_argument('--rf-x-unit', action="store", dest='rf_x_unit', \
                help=cls.__doc__, const=out, default=None, nargs='?')

    def configure(self, params, config):
        if not self.is_enabled(params, config):
            return
        self.path = params.rf_x_unit
        self.suite_start = datetime.datetime.now(tz.tzutc())
        timestamp = self.suite_start.replace(microsecond=0).isoformat()

        self.testsuites = E.testsuites()
        XSLT = PI('xml-stylesheet',
                text='type="text/xsl" href="%s"'
                % JUNIT_NOFRAMES_STYLESHEET)
        self.testsuites.addprevious(XSLT)
        test_name = config['RUN']['tests_file'].split('/')[-1]
        self.testsuite = E.testsuite(name=test_name, timestamp=timestamp,
                            hostname=config['REST_CONNECTION']['host'])
        self.testsuites.append(self.testsuite)

        self.testsuite_props = E.properties()
        self.testsuite.append(self.testsuite_props)

        self.failures = self.errors = self.tests = self.skip = 0
        self.__update_testsuite_attrs()
        self.tree = ElementTree(self.testsuites)
        self.testsuites.addprevious(XSLT)

        from art.test_handler.settings import opts
        self.testsuite_props.append(E.property(name='log_path',
                                               value=opts['log']))
        self.testsuite_props.append(E.property(name='test_sheet_path',
                                    value=config['RUN']['tests_file']))

    def add_test_result(self, kwargs, test_case):
        if not kwargs._report:
            return
        time_delta = kwargs['end_time'] - kwargs['start_time']
        test_name = '{0}({1[parameters]})'.format(
                        test_case.test_action, kwargs)
        test_name = kwargs['test_name'] if 'test_name' in kwargs else ''
        mod_path = test_case.mod_path if 'mod_path' in test_case else ''
        test_classname = '%s.%s-%s' % (kwargs['module_name'],
                    kwargs['iter_num'], kwargs['test_name'].replace(".", ";"))
        real_classname = '%s.%s' % (mod_path, test_case.test_action)
        start_time = kwargs['start_time'].astimezone(tz.tzlocal())
        start_time = start_time.isoformat()

        testcase = Element('testcase')
        testcase.attrib['name']         = test_name
        testcase.attrib['classname']    = test_classname
        testcase.attrib['time']         = str(total_seconds(time_delta))

        written = ['start_time', 'end_time', 'test_name', 'status']
        out_msg = DEFAULT_OUT_MSG
        if 'captured_log' in kwargs:
            out_msg = kwargs['captured_log']
            written.append('captured_log')

        if kwargs['status'] == test_case.TEST_STATUS_FAILED:
            self.failures += 1
            failure = E.failure(out_msg)
            testcase.append(failure)
        elif kwargs['status'] == test_case.TEST_STATUS_SKIPPED:
            self.skip += 1
            skipped = E.skipped(out_msg)
            testcase.append(skipped)
        elif kwargs['status'] is test_case.TEST_STATUS_ERROR:
            self.errors += 1
            error = E.error(out_msg)
            testcase.append(error)
        self.tests += 1

        self.testsuite.append(testcase)
        self.__update_testsuite_attrs()

        if kwargs['status'] not in [test_case.TEST_STATUS_FAILED,
        test_case.TEST_STATUS_SKIPPED, test_case.TEST_STATUS_ERROR]:
            systemout = Element('system-out')
            systemout.text = out_msg
            testcase.append(systemout)

        properties = E.properties()
        for k in set(kwargs.keys()) - set(written):
            self.__add_aditional_attrs(properties, k, kwargs[k])
        properties.append(E.property(name='real_classname',
                              value=real_classname))
        properties.append(E.property(name='start_time',
                              value=start_time))
        testcase.append(properties)
        self.generate_report()

    def __add_aditional_attrs(self, root, key, val):
        if isinstance(val, dict):
            for subkey, subval in val.items():
                self.__add_aditional_attrs(root, subkey, subval)
        elif isinstance(val, (list, tuple, set)):
            for subelm in val:
                self.__add_aditional_attrs(root, key, subelm)
        else:
            if not isinstance(val, basestring):
                val = str(val)
            try:
                e = E.property(name=key, value=val)
            except ValueError:
                logger.debug(
                    "failed setting key: {0} to val={1}, type(val)={2}".format(
                    key, val, type(val)))
            root.append(e)

    def add_group_result(self, res, tg):
        for key, val in res.items():
            self.__add_aditional_attrs(self.testsuite, key, val)

    def add_suite_result(self, res, ts):
        for key, val in res.items():
            self.__add_aditional_attrs(self.testsuite, key, val)

    def __update_testsuite_attrs(self):
        tsa = self.testsuite.attrib
        tsa['failures'] = str(self.failures)
        tsa['errors'] = str(self.errors)
        tsa['skip'] = str(self.skip)
        tsa['tests'] = str(self.tests)
        time_delta = datetime.datetime.now(tz.tzutc()) - self.suite_start
        tsa['time'] = str(total_seconds(time_delta))

    def generate_report(self):
        if self.tree is not None:
            folder = os.path.dirname(self.path)
            if not os.path.exists(folder):
                os.makedirs(folder)
            self.tree.write(self.path, encoding="utf-8",
                            pretty_print=True, xml_declaration=True)

    @classmethod
    def is_enabled(cls, params, conf):
        return params.rf_x_unit is not None

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'xunit-reports'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Xunit results formatter for ART'
        params['long_description'] = 'Plugin for ART which allows to you '\
                'generete results in Xunit format.'
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.xunit_results_formater_plugin']


