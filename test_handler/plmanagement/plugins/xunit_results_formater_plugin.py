from lxml.etree import Element, ElementTree, PI
from lxml.builder import E
import datetime
from dateutil import tz


import os
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter

JUNIT_NOFRAMES_STYLESHEET = "junit-noframes.xsl"


def total_seconds(td):
    ''' For Py2.7 compatibility. There is no function in Py2.6 computing this. '''
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6


class XUnit(Component):
    """
    Generates x-unit report; deafult: %(const)s
    """
    implements(IResultsFormatter, IConfigurable)
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
        self.testsuite = E.testsuite(name=str(config['RUN']['engine']),
                                     timestamp=timestamp)
        self.testsuites.append(self.testsuite)

        self.testsuite_props = E.properties()
        self.testsuite.append(self.testsuite_props)

        self.failures = self.errors = self.tests = 0
        self.__update_testsuite_attrs()
        self.tree = ElementTree(self.testsuites)
        self.testsuites.addprevious(XSLT)

        from test_handler.settings import opts
        self.testsuite_props.append(E.property(name='log_path',
                                               value=opts['log']))
        self.testsuite_props.append(E.property(name='test_sheet_path',
                                               value=str(config['RUN']['tests_file'])))

    def add_test_result(self, kwargs, test_case):
        time_delta = kwargs['end_time'] - kwargs['start_time']
        test_name = '{0}({1[test_parameters]})'.format(
                        test_case.test_action, kwargs)
        test_classname = '%s.%s.%s' % (kwargs['test_type'],
                                    kwargs['module_name'],
                                    kwargs['test_name'].replace(".", ";"))
        real_classname = '%s.%s' % (test_case.modPath, test_case.funcName)
        start_time = kwargs['start_time'].astimezone(tz.tzlocal())
        start_time = start_time.isoformat()

        testcase = Element('testcase')
        testcase.attrib['name']         = test_name
        testcase.attrib['classname']    = test_classname
        testcase.attrib['time']         = str(total_seconds(time_delta))

        if kwargs['status'] == 'Fail':
            self.failures += 1
            failure = E.failure('Sorry, no support for backtrace yet.')
            testcase.append(failure)
        elif kwargs['status'] is None:
            self.errors += 1
            error = E.error('Sorry, no support for backtrace yet.')
            testcase.append(error)
        self.tests += 1

        self.testsuite.append(testcase)
        self.__update_testsuite_attrs()


        traits = E.traits()
        testcase.append(traits)
        remainder = set(['start_time', 'end_time', 'test_name', 'status'])
        for k in kwargs.viewkeys() - remainder:
            traits.append(E.trait(name=str(k), value=str(kwargs[k])))
        traits.append(E.trait(name='real_classname',
                              value=real_classname))
        traits.append(E.trait(name='start_time',
                              value=start_time))

    def __update_testsuite_attrs(self):
        tsa = self.testsuite.attrib
        tsa['failures'] = str(self.failures)
        tsa['errors'] = str(self.errors)
        tsa['tests'] = str(self.tests)
        time_delta = datetime.datetime.now(tz.tzutc()) - self.suite_start
        tsa['time'] = str(total_seconds(time_delta))

    def generate_report(self):
        if self.tree is not None:
            self.tree.write(self.path, encoding="utf-8",
                            pretty_print=True, xml_declaration=True)

    @classmethod
    def is_enabled(cls, params, conf):
        return params.rf_x_unit is not None


