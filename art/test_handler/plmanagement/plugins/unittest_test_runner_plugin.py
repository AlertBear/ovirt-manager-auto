
import os
import re
import sys
import copy

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultExtension
from art.test_handler.test_runner import TestCase, TestSuite, TestGroup, TestResult
from art.test_handler.exceptions import SkipTest
import art
try:
    from unittest import SkipTest as USkipTest
except ImportError:
    USkipTest = None
from nose.suite import ContextSuite
from nose.case import Test
from unittest2 import SkipTest as USkipTest2

RUN_SEC = 'RUN'
TESTS_FILE = 'tests_file'
CONFIG_PARAMS = 'PARAMETERS'
REST_CONNECTION = 'REST_CONNECTION'

BZ_ID = 'bz'
TCMS_PLAN_ID = 'tcms_plan_id'
TCMS_TEST_CASE = 'tcms_test_case'

TEST_CASES_SEPARATOR = '\n' + '=' * 80

logger = get_logger("unittest_loader")


class UTestCase(TestCase):
    skip_exceptios = (USkipTest, USkipTest2)
    def __init__(self, t):
        super(UTestCase, self).__init__()
        self.mod_name, self.test_action = t.address()[1:]
        self.t = t
        self.f = getattr(t.test, t.test._testMethodName)
        self.test_name = self.f.__doc__
        self.bz = getattr(self.f.im_func, BZ_ID, None)
        self.tcms_plan_id = getattr(self.f.im_func, TCMS_PLAN_ID, None)
        self.tcms_test_case = getattr(self.f.im_func, TCMS_TEST_CASE, None)
        # TODO: set another atts

    def __call__(self):
        try:
            self.t.test.setUp()
            try:
                self.f()
                self.status = self.TEST_STATUS_PASSED
            except AssertionError as ex:
                logger.error("Test case failed: %s", ex)
                self.exc = ex
                self.status = self.TEST_STATUS_FAILED
            except self.skip_exceptios as ex:
                self.status = self.TEST_STATUS_SKIPPED
                raise SkipTest(str(ex))
            except Exception as ex:
                self.status = self.TEST_STATUS_ERROR
                self.exc = ex
        finally:
            self.t.test.tearDown()

    def __str__(self):
        return "Test Action: %s; Test Name: %s" % (self.test_action, self.test_name)


class UTestGroup(TestGroup):
    def __init__(self, c):
        super(UTestGroup, self).__init__()
        self.context = c
        self.tcms_plan_id = getattr(c.context, TCMS_PLAN_ID, None)

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

#    def __str__(self):
#        return "FIXME: I don't know what should be here."


class UTestSuite(TestSuite):
    def __init__(self, context):
        super(UTestSuite, self).__init__()
        self.context = context
        self.tcms_plan_id = getattr(context.context, TCMS_PLAN_ID, None)

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

#    def __str__(self):
#        return "FIXME: I don't know what should be here."


class UnittestLoader(Component):
    """
    Plugin allows to test_runner be able to run unittest based tests
    """
    implements(ITestParser, IResultExtension, IConfigurable)
    name = 'Unittest runner'

    def is_able_to_run(self, ti):
        m = re.match('unittest://((?P<root_path>[^:]+):)?(?P<mod_path>.+)', ti)
        if not m:
            return False
        self.mod_path = m.group('mod_path')
        self.root_path = m.group('root_path')
        if not os.path.exists(self.root_path):
            self.root_path = os.path.join(os.path.dirname(art.__file__), self.root_path)
            if not os.path.exists(self.root_path):
                raise IOError(self.root_path)
        return True

    def next_test_object(self):
        if not hasattr(self, 'suites'):
            if self.root_path is not None:
                sys.path.insert(0, self.root_path)
            from nose.loader import TestLoader
            mod = __import__(self.mod_path)
            setattr(mod, 'ART_CONFIG', self.conf)
            loader = TestLoader()
            self.suites = [UTestSuite(x) for x in loader.loadTestsFromModule(mod)]
        try:
            return self.suites.pop()
        except IndexError:
            return None

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        # FIXME: why this is done in both matrix_runner and here ? it should be somewhere else.
        self.conf = conf
        self.conf[CONFIG_PARAMS].merge(self.conf[REST_CONNECTION])
        dc_type_sec = conf[CONFIG_PARAMS].get('data_center_type','none').upper()
        if dc_type_sec != 'NONE' and dc_type_sec in conf:
            self.conf[CONFIG_PARAMS].merge(conf[dc_type_sec])

        TestResult.ATTRIBUTES['module_name'] = \
                ('mod_name', None, None)
        TestResult.ATTRIBUTES['test_action'] = \
                ('test_action', None, None)
        TestResult.ATTRIBUTES['iter_num'] = \
                ('serial', None, None)

    @classmethod
    def add_options(cls, parser):
        pass

    def pre_test_result_reported(self, res, tc):
        res.module_name = tc.mod_name
        res.iter_num = "%03d" % res.iter_num
        logger.info(TEST_CASES_SEPARATOR)

    def pre_group_result_reported(self, res, tg):
        pass

    def pre_suite_result_reported(self, res, ts):
        pass

    @classmethod
    def is_enabled(cls, a, b):
        return True

