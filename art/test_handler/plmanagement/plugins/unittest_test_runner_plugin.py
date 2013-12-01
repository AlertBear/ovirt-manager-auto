"""
----------------------
Unittest Runner Plugin
----------------------
Plugin that runs the unittets. It encapsulates nose test runner [nose_url]_ .
Actually it uses its TestLoader to load modules, and executes test cases.
In additional it provides integration with TCMS plugin, and Bugzilla plugin.
Also supports the unittest2 backport from py3.


Configuration Options:
----------------------
    | **[RUN]**
    | **tests_file** the test specification;
        unittest://path/to/module:name_of_module

How to start
------------
there [unittets_example]_ is commented basic example how the test module
should look like.


.. [nose_url] https://nose.readthedocs.org/en/latest/
.. [unittets_example] ART/art/tests/unittest_template/example

"""

import re
import sys
from functools import wraps

from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import ITestParser,\
    IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter \
    import IResultExtension
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.tests_listener \
    import ITestGroupHandler
from art.test_handler.test_runner import TestCase, TestSuite, TestGroup,\
    TestResult, TEST_CASES_SEPARATOR
from art.test_handler.exceptions import SkipTest, formatExcInfo
from art.test_handler import find_test_file

logger = get_logger("unittest_loader")

DEPS_INSTALLED = None

try:
    from nose.suite import ContextSuite
    from nose.case import Test
except ImportError as ex:
    ContextSuite = Test = None  # this is required
    DEPS_INSTALLED = ex

try:
    from unittest import SkipTest as USkipTest
except ImportError as ex:  # py2.6 doesn't contain this class
    USkipTest = None
try:
    from unittest2 import SkipTest as USkipTest2
except ImportError as ex:
    # it can work without it
    logger.warning("unittest2 module is not installed")
    USkipTest2 = None

RUN_SEC = 'RUN'
TESTS_FILE = 'tests_file'
CONFIG_PARAMS = 'PARAMETERS'
REST_CONNECTION = 'REST_CONNECTION'

BZ_ID = 'bz'  # TODO: should be removed
TCMS_PLAN_ID = 'tcms_plan_id'  # TODO: should be removed
TCMS_TEST_CASE = 'tcms_test_case'  # TODO: should be removed
CLI_VALIDATION = 'cli_validation'  # TODO: should be removed

ITER_NUM = 0


def iterNumber():
    # FIXME: this will not work in parallel, use serial from test_runner.py
    # instead.
    global ITER_NUM
    ITER_NUM += 1
    return ITER_NUM


def isvital4group(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        self.vital4group = True
        return f(self, *args, **kwargs)
    return wrapper


class UTestCase(TestCase):
    skip_exceptios = (USkipTest, USkipTest2, SkipTest)

    def __init__(self, t):
        super(UTestCase, self).__init__()
        self.mod_name, self.test_action = t.address()[1:]
        self.t = t
        self.f = getattr(t.test, t.test._testMethodName)
        self.test_name = self.test_action
        self.bz = getattr(self.f, BZ_ID, None)
        self.tcms_plan_id = getattr(self.f, TCMS_PLAN_ID, None)
        self.tcms_test_case = getattr(self.f, TCMS_TEST_CASE, None)
        self.cli_validation = getattr(self.f, CLI_VALIDATION, None)
        setattr(self.t.test, 'vital4group', False)
        self.serial = iterNumber()
        try:
            self.description = self.f.__doc__.strip()
        except AttributeError:
            logger.error("Test case %s has missing documentation string!",
                         self.test_name)
        # TODO: set another atts

    def __call__(self):
        try:
            logger.info("setUp: %s", self.test_name)
            try:
                self.t.test.setUp()
                logger.info(self.format_attr('test_name'))
                logger.info('Test description: %s', self.description)
                logger.debug(self.format_attr('serial'))
                self.f()
                self.status = self.TEST_STATUS_PASSED
            except AssertionError:
                self.exc = formatExcInfo()
                self.status = self.TEST_STATUS_FAILED
            except self.skip_exceptios as ex:
                self.status = self.TEST_STATUS_SKIPPED
                raise SkipTest(str(ex))
            except Exception:
                self.status = self.TEST_STATUS_ERROR
                self.exc = formatExcInfo()
        finally:
            logger.info("tearDown: %s", self.test_name)
            try:
                self.t.test.tearDown()
            except Exception:
                self.exc = formatExcInfo()
                self.status = self.TEST_STATUS_FAILED
            if self.status in (self.TEST_STATUS_FAILED,
                               self.TEST_STATUS_ERROR):
                if self.t.test.vital4group:
                    self.vital4group = True

    def __str__(self):
        return "Test Action: %s; Test Name: %s" % (self.test_action,
                                                   self.test_name)


class UTestGroup(TestGroup):
    def __init__(self, c):
        super(UTestGroup, self).__init__()
        self.context = c
        self.tcms_plan_id = getattr(c.context, TCMS_PLAN_ID, None)
        self.test_name = self.context.context.__name__
        try:
            self.description = self.context.context.__doc__.strip()
        except AttributeError:
            logger.error("Test class %s has missing documentation string!",
                         self.test_name)

    def __iter__(self):
        try:
            logger.info(TEST_CASES_SEPARATOR)
            logger.info("TEST GROUP setUp: %s", self.test_name)
            logger.info('Group description: %s', self.description)
            try:
                self.context.setUp()
            except Exception as ex:
                logger.error("TEST GROUP setUp ERROR: %s: %s", ex,
                             self.test_name, exc_info=True)
                self.status = self.TEST_STATUS_ERROR
                self.exc = formatExcInfo()
                self.error += 1
                raise StopIteration(str(ex))
            for c in self.context:
                if isinstance(c, Test):
                    test_elm = UTestCase(c)
                elif None is c.context:
                    continue
                else:
                    test_elm = UTestGroup(c)
                test_elm.parent = self.context
                yield test_elm
        finally:
            logger.info("TEST GROUP tearDown: %s", self.test_name)
            try:
                self.context.tearDown()
            except Exception:
                self.exc = formatExcInfo()
                self.status = self.TEST_STATUS_FAILED
            logger.info(TEST_CASES_SEPARATOR)

    def __str__(self):
        return self.test_name


class UTestSuite(TestSuite):
    def __init__(self, context):
        super(UTestSuite, self).__init__()
        self.context = context
        self.tcms_plan_id = getattr(context.context, TCMS_PLAN_ID, None)
        self.test_name = self.context.context.__name__

    def __iter__(self):
        try:
            logger.info(TEST_CASES_SEPARATOR)
            logger.info("TEST SUITE setUp: %s", self.test_name)
            try:
                self.context.setUp()
            except Exception as ex:
                logger.error("TEST SUITE setUp ERROR: %s: %s", ex,
                             self.test_name, exc_info=True)
                self.status = self.TEST_STATUS_ERROR
                self.exc = formatExcInfo()
                self.error += 1
                raise StopIteration(str(ex))
            for c in self.context:
                if isinstance(c, Test):
                    test_elm = UTestCase(c)
                elif None is c.context:
                    continue
                else:
                    test_elm = UTestGroup(c)
                test_elm.parent = self.context
                yield test_elm
        finally:
            logger.info("TEST SUITE tearDown: %s", self.test_name)
            try:
                self.context.tearDown()
            except Exception:
                self.exc = formatExcInfo()
                self.status = self.TEST_STATUS_FAILED
            logger.info(TEST_CASES_SEPARATOR)

    def __str__(self):
        return self.test_name


class UnittestLoader(Component):
    """
    Plugin allows to test_runner be able to run unittest based tests
    """
    implements(ITestParser, IResultExtension, IConfigurable, IPackaging,
               ITestGroupHandler)
    name = 'Unittest runner'

    def __init__(self):
        super(UnittestLoader, self).__init__()
        self.suites = None

    def __check_deps(self):
        if DEPS_INSTALLED is not None:
            raise DEPS_INSTALLED

    def is_able_to_run(self, ti):
        m = re.match('unittest://((?P<root_path>[^:]+):)?(?P<mod_path>.+)', ti)
        if not m:
            return False
        self.__check_deps()
        self.mod_path = m.group('mod_path')
        self.root_path = m.group('root_path')
        if self.root_path:
            self.root_path = find_test_file(self.root_path)
        return True

    def next_test_object(self):
        self.__check_deps()
        if not hasattr(self, 'done'):
            self.done = True
        if self.suites is None:
            self.suites = []
            modules = []
            description = {}
            if self.root_path:
                sys.path.insert(0, self.root_path)

            from nose.loader import TestLoader
            for mod_path in self.mod_path.split(':'):

                m = re.match("(?P<module>.+?)((\.(?P<name>[A-Z].+))|$)",
                             mod_path)
                if not m:
                    return None
                module = m.group('module')
                name = m.group('name')

                mod = __import__(module.rsplit('.')[0])
                setattr(mod, 'ART_CONFIG', self.conf)

                mod = __import__(module, fromlist=[module.split('.')[-1]])
                description[mod.__name__] = mod.__doc__
                modules.append([name, mod])

            loader = TestLoader(workingDir=self.root_path)
            for m in modules:
                if m[0] is not None:
                    tests = loader.loadTestsFromName(module=m[1], name=m[0])
                    suite = UTestSuite(tests)
                else:
                    tests = loader.loadTestsFromModule(m[1])
                    suite = UTestSuite(tests)
                    for t in [t for t in tests.factory.context]:
                        if t.context.__name__ == 'Failure':
                            logger.error("Failed to load test: %s",
                                         t._get_tests().next().__str__())
                suite.description = description[m[1].__name__]
                self.suites.append(suite)
        try:
            return self.suites.pop()
        except IndexError:
            return None

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        self.__check_deps()

        # FIXME: why this is done in both matrix_runner and here ?
        # it should be somewhere else.
        self.conf = conf
        self.conf[CONFIG_PARAMS].merge(self.conf[REST_CONNECTION])

        TestResult.ATTRIBUTES['module_name'] = ('mod_name', None, None)
        TestResult.ATTRIBUTES['test_action'] = ('test_action', None, None)
        TestResult.ATTRIBUTES['iter_num'] = ('serial', None, None)

    @classmethod
    def add_options(cls, parser):
        pass

    def pre_test_result_reported(self, res, tc):
        res.add_result_attribute('module_name', 'mod_name', 'Module Name', '')
        res.add_result_attribute('iter_num', 'serial', 'Iteration Number', '')
        res.add_result_attribute('parameters', '', 'Test Parameters', '')

        if tc.status in (tc.TEST_STATUS_PASSED, tc.TEST_STATUS_SKIPPED):
            st_msg = logger.info
        elif tc.status == tc.TEST_STATUS_UNDEFINED:
            st_msg = logger.warn
        else:
            st_msg = logger.error
        st_msg(tc.format_attr('status'))

    def pre_group_result_reported(self, res, tg):
        pass

    def pre_suite_result_reported(self, res, ts):
        pass

    def pre_test_group(self, test_group):
        pass

    def post_test_group(self, test_group):
        """
        Calls test group teardown if test case set that it has failure. Another
        teardown will be called on test group after all test cases were run.
        Before following test case is run, test group setup will be called.
        """
        parent = test_group.parent
        if parent is not None:
            if not hasattr(parent, 'tests_to_run'):
                parent.tests_to_run = len([test for test in parent])
            context = test_group.context
            parent.tests_to_run -= 1
            if hasattr(context.context, 'automatic_rebuild') and \
                    context.context.automatic_rebuild and \
                    test_group.failed > 0 and \
                    parent.tests_to_run > 0:
                parent.teardownContext(parent.context)
                del parent.factory.was_torndown[parent.context]
                del parent.factory.was_setup[parent.context]
                parent.setupContext(parent.context)

    def test_group_skipped(self, test_group):
        pass

    @classmethod
    def is_enabled(cls, a, b):
        return True

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Unittest runner plugin for ART'
        params['long_description'] = cls.__doc__
        params['requires'] = ['python-nose', 'python-unittest2']
#        params['pip_deps'] = ['unittest2']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'unittest_test_runner_plugin']
