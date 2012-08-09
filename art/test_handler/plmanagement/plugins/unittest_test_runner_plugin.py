
import re
import sys

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultExtension
from art.test_handler.test_runner import TestCase, TestSuite, TestGroup, TestResult
from art.test_handler.exceptions import SkipTest
try:
    from unittest import SkipTest as USkipTest
    from nose.suite import ContextSuite
    from nose.case import Test
except ImportError:
    USkipTest = SkipTest    # FIXME: I hate this!
    ContextSuite = None
    Test = None

RUN_SEC = 'RUN'
TESTS_FILE = 'tests_file'

class UTestCase(TestCase):
    def __init__(self, t):
        super(UTestCase, self).__init__()
        self.mod_name, self.test_action = t.address()[1:]
        self.t = t
        self.f = getattr(t.test, t.test._testMethodName)
        self.test_name = self.f.__doc__
        self.bz = getattr(self.f.im_func, 'bz_ids', None)
        # TODO: set another atts

    def __call__(self):
        try:
            self.t.test.setUp()
            try:
                self.f()
                self.status = self.TEST_STATUS_PASSED
            except AssertionError as ex:
                self.status = self.TEST_STATUS_FAILED
            except USkipTest as ex:
                self.status = self.TEST_STATUS_SKIPPED
                raise SkipTest(str(ex))
            # TODO: solve another cases
            # TODO: add error info
        finally:
            self.t.test.tearDown()


class UTestGroup(TestGroup):
    def __init__(self, c):
        super(UTestGroup, self).__init__()
        self.context = c
        self.tcms_test_plan_id = getattr(c.context, 'tcms_test_plan_id', None)

    def __iter__(self):
        try:
            self.context.setUp()
            for c in self.context:
                if not isinstance(c, Test):
                    yield UTestGroup(c)
                else:
                    yield UTestCase(c)
        finally:
            self.context.tearDown()


class UTestSuite(TestSuite):
    def __init__(self, context):
        super(UTestSuite, self).__init__()
        self.context = context
        self.tcms_test_plan_id = getattr(context.context, 'tcms_test_plan_id', None)

    def __iter__(self):
        try:
            self.context.setUp()
            for c in self.context:
                if not isinstance(c, Test):
                    yield UTestGroup(c)
                else:
                    yield UTestCase(c)
        finally:
            self.context.tearDown()


class UnittestLoader(Component):
    """
    Plugin allows to test_runner be able to run unittest based tests
    """
    implements(ITestParser, IResultExtension, IConfigurable)
    name = 'Unittest runner'
    enabled = True

    def is_able_to_run(self, ti):
        m = re.match('unittest://((?P<root_path>[^:]+):)?(?P<mod_path>.+)', ti)
        if not m:
            UnittestLoader.enabled = False
            return False
        self.mod_path = m.group('mod_path')
        self.root_path = m.group('root_path')
        return True

    def next_test_object(self):
        if not hasattr(self, 'suites'):
            if self.root_path is not None:
                sys.path.insert(0, self.root_path)
            from nose.loader import TestLoader
            mod = __import__(self.mod_path)
            loader = TestLoader()
            self.suites = [UTestSuite(x) for x in loader.loadTestsFromModule(mod)]
        try:
            return self.suites.pop()
        except IndexError:
            return None

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        self.conf = conf
        TestResult.ATTRIBUTES['module_name'] = \
                ('mod_name', None, None)
        TestResult.ATTRIBUTES['test_action'] = \
                ('test_action', None, None)

    @classmethod
    def add_options(cls, parser):
        pass

    def pre_test_result_reported(self, res, tc):
        print "safddf"
        res.module_name = tc.mod_name

    @classmethod
    def is_enabled(cls, a, b):
        #return cls.enabled
        return True

