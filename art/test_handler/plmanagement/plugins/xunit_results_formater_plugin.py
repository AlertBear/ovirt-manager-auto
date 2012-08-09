from lxml.etree import Element, ElementTree, PI
from lxml.builder import E
import datetime
from dateutil import tz


import os
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

JUNIT_NOFRAMES_STYLESHEET = "junit-noframes.xsl"


# TODO: same problem as tcms_plugin


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
        self.testsuite = E.testsuite(name=str(config['RUN']['engine']),
                                     timestamp=timestamp)
        self.testsuites.append(self.testsuite)

        self.testsuite_props = E.properties()
        self.testsuite.append(self.testsuite_props)

        self.failures = self.errors = self.tests = 0
        self.__update_testsuite_attrs()
        self.tree = ElementTree(self.testsuites)
        self.testsuites.addprevious(XSLT)

        from art.test_handler.settings import opts
        self.testsuite_props.append(E.property(name='log_path',
                                               value=opts['log']))
        self.testsuite_props.append(E.property(name='test_sheet_path',
                                               value=str(config['RUN']['tests_file'])))

    def add_test_result(self, kwargs, test_case):
        if not kwargs._report:
            return
        time_delta = kwargs['end_time'] - kwargs['start_time']
        test_name = '{0}({1[parameters]})'.format( # these_hardcoded names must be changed
                        test_case.test_action, kwargs)
        test_classname = '%s.%s' % (kwargs['module_name'],
                                    kwargs['test_name'].replace(".", ";"))
        real_classname = '%s.%s' % (test_case.mod_path, test_case.test_action)
        start_time = kwargs['start_time'].astimezone(tz.tzlocal())
        start_time = start_time.isoformat()

        testcase = Element('testcase')
        testcase.attrib['name']         = test_name
        testcase.attrib['classname']    = test_classname
        testcase.attrib['time']         = str(total_seconds(time_delta))

        if kwargs['status'] == test_case.TEST_STATUS_FAILED:
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
        for k in set(kwargs.keys()) - remainder:
            traits.append(E.trait(name=str(k), value=str(kwargs[k])))
        traits.append(E.trait(name='real_classname',
                              value=real_classname))
        traits.append(E.trait(name='start_time',
                              value=start_time))
        self.generate_report()

    def __update_testsuite_attrs(self):
        tsa = self.testsuite.attrib
        tsa['failures'] = str(self.failures)
        tsa['errors'] = str(self.errors)
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


