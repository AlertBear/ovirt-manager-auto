"""
----------------------
Unittest Runner Plugin
----------------------
Plugin that runs the unittets. It encapsulates nose test runner [nose_url]_ .
Actually it uses its TestLoader to load modules, and executes test cases.
In additional it provides integration with TCMS plugin, and Bugzilla plugin.
Also supports the unittest2 backport from py3.

CLI Options
-----------
  --test-tag name=value
  --test-tag-expr "python expression"  [nose_tag_expression]_
  --with-nose-apiselector  mutiplies test-cases per each rhevm api

Configuration Options:
----------------------
    | **[RUN]**
    | **tests_file** the test specification;
        unittest://path/to/module:name_of_module
    | **[UNITTEST]**
    | **nose_config** path to file with nose configuration
    | **nose_custom_paths** path to nose customization (nose custom plugins)
    | **nose_apiselector** - enable/disable api selector plugin
    | **tags** - list of tags
    | **tag_expressions** - list of tag's expressions [nose_tag_expression]_
    | **exclude** - list of expressions which module should be excluded
        [nose_exclude]_

How to start
------------
there [unittets_example]_ is commented basic example how the test module
should look like.


.. [nose_url] https://nose.readthedocs.org/en/latest/
.. [unittets_example] ART/art/tests/unittest_template/example
.. [nose_tag_expression] http://nose.readthedocs.org/en/latest/plugins/\
attrib.html#expression-evaluation
.. [nose_exclude] http://nose.readthedocs.org/en/latest/usage.html#cmdoption-e

"""

import os
import re
import sys
import parser as pyparser
import argparse
from functools import wraps

from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import ITestParser,\
    IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter \
    import IResultExtension
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.tests_listener import \
    ITestGroupHandler
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.test_runner import TestCase, TestSuite, TestGroup,\
    TestResult, TEST_CASES_SEPARATOR
from art.test_handler.exceptions import SkipTest
from art.test_handler import find_test_file, locate_file
import art

logger = get_logger("unittest_loader")

DEPS_INSTALLED = None

try:
    from nose.suite import ContextSuite
    from nose.case import Test
    from nose.config import Config as NoseConfig
    from nose.loader import TestLoader
    from nose.failure import Failure
    from nose.plugins.manager import DefaultPluginManager as NosePluginManager
    from nose.plugins.attrib import AttributeSelector
except ImportError as ex:
    # this is required
    ContextSuite = Test = NoseConfig = NosePluginManager = None
    TestLoader = AttributeSelector = Failure = None
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
UNITTEST_SEC = 'UNITTEST'
DEFAULT_STATE = False
DEFAULT_NOSE_CUSTOM_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(art.__file__),
                    '..', 'nose_customization')),
    '/opt/art/nose_customization']

BZ_ID = 'bz'  # TODO: should be removed
TCMS_PLAN_ID = 'tcms_plan_id'  # TODO: should be removed
TCMS_TEST_CASE = 'tcms_test_case'  # TODO: should be removed
CLI_VALIDATION = 'cli_validation'  # TODO: should be removed
NOSE_CUSTOMIZATION_PATHS = 'nose_custom_paths'
NOSE_CONFIG_PATH = 'nose_config'
NOSE_API_SELECTOR = 'nose_apiselector'
NOSE_TAGS = 'tags'
NOSE_TAG_EXPRESSIONS = 'tag_expressions'
NOSE_EXCLUDE = 'exclude'

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


def python_expr_list(value):
    """
    validates list of py-expressions: "a == b", "a in (1, 2)", ...
    """
    if not isinstance(value, basestring):
        return value

    values = list()
    value = value.strip()
    if value == ',':
        return values

    try:
        value = eval(value)  # convert to tuple
        if not isinstance(value, tuple):
            raise SyntaxError()
    except (SyntaxError, NameError):
        raise TypeError("'%s' is not list of expressions" % value)

    for expr in value:
        try:
            pyparser.expr(expr)
        except SyntaxError as ex:
            raise TypeError("'%s' is not python expression: %s" % (expr, ex))
        values.append(expr)

    return values


class PythonExprAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            pyparser.expr(values)
        except SyntaxError as ex:
            raise argparse.ArgumentError(self, "%s in '%s'" % (ex, values))
        exprs = getattr(namespace, self.dest, [])
        if exprs is None:
            exprs = list()
        exprs.append(values)
        setattr(namespace, self.dest, exprs)


class UTestCase(TestCase):
    skip_exceptions = (USkipTest, USkipTest2, SkipTest)

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
                logger.info(self.format_attr('serial'))
                self.t.plugins.startTest(self.t.test)
                self.f()
                self.status = self.TEST_STATUS_PASSED
            except AssertionError:
                self.incr_exc()
                self.status = self.TEST_STATUS_FAILED
            except self.skip_exceptions as ex:
                self.status = self.TEST_STATUS_SKIPPED
                raise SkipTest(str(ex))
            except Exception:
                self.status = self.TEST_STATUS_ERROR
                self.incr_exc()
            finally:
                self.t.plugins.stopTest(self.t.test)
        finally:
            logger.info("tearDown: %s", self.test_name)
            try:
                self.t.test.tearDown()
            except Exception:
                self.incr_exc()
                self.status = self.TEST_STATUS_FAILED
            if self.status in (self.TEST_STATUS_FAILED,
                               self.TEST_STATUS_ERROR):
                if self.t.test.vital4group:
                    self.vital4group = True

    def __str__(self):
        return "Test Action: %s; Test Name: %s" % (self.test_action,
                                                   self.test_name)

    @property
    def api(self):
        return getattr(self.t.test, 'api', None)


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
                self.incr_exc()
                raise SkipTest(str(ex))
            for c in self.context:
                if isinstance(c, Failure):
                    logger.error("There is critical failure in test module, "
                                 "please see nose.log for more info: %s", c)
                    continue
                elif isinstance(c, Test):
                    test_elm = UTestCase(c)
                elif None is c.context:
                    continue
                else:
                    if not c.countTestCases():
                        continue
                    test_elm = UTestGroup(c)
                test_elm.parent = self.context
                yield test_elm
        finally:
            logger.info("TEST GROUP tearDown: %s", self.test_name)
            try:
                self.context.was_setup = True
                self.context.tearDown()
            except Exception:
                self.incr_exc()
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
        if not self.context.countTestCases():
            raise StopIteration("No test cases found")
        try:
            logger.info(TEST_CASES_SEPARATOR)
            logger.info("TEST SUITE setUp: %s", self.test_name)
            try:
                self.context.setUp()
            except Exception as ex:
                logger.error("TEST SUITE setUp ERROR: %s: %s", ex,
                             self.test_name, exc_info=True)
                self.status = self.TEST_STATUS_ERROR
                self.incr_exc()
                raise SkipTest(str(ex))
            for c in self.context:
                if isinstance(c, Failure):
                    logger.error("There is critical failure in test module, "
                                 "please see nose.log for more info: %s", c)
                    continue
                elif isinstance(c, Test):
                    test_elm = UTestCase(c)
                elif None is c.context:
                    continue
                else:
                    if not c.countTestCases():
                        continue
                    test_elm = UTestGroup(c)
                test_elm.parent = self.context
                yield test_elm
        finally:
            logger.info("TEST SUITE tearDown: %s", self.test_name)
            try:
                self.context.was_setup = True
                self.context.tearDown()
            except Exception:
                self.incr_exc()
                self.status = self.TEST_STATUS_FAILED
            logger.info(TEST_CASES_SEPARATOR)

    def __str__(self):
        return self.test_name


class UnittestLoader(Component):
    """
    Plugin allows to test_runner be able to run unittest based tests
    """
    implements(ITestParser,
               IResultExtension,
               IConfigurable,
               IPackaging,
               IConfigValidation,
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

            # NOTE: maybe all this part could be replaced by
            # nose.core.collector function
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

            # Initialize TestLoader
            loader = TestLoader(workingDir=self.root_path,
                                config=self.nose_conf)
            pl_loader = self.nose_conf.plugins.prepareTestLoader(loader)
            if pl_loader is not None:
                loader = pl_loader

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

        #configuring nose
        self._configure_nose(params, conf)

    def _configure_nose(self, params, conf):
        # init config
        self.nose_conf = NoseConfig(env=os.environ,
                                    plugins=NosePluginManager())
        # init log (maybe to pass loggingConfig in future)
        #self.nose_conf.configureLogging()
        #logger.info("Nose log: %s", conf[UNITTEST_SEC]['nose_log'])

        custom_paths = conf[UNITTEST_SEC][NOSE_CUSTOMIZATION_PATHS]

        # load custom plugins - make it more generic
        plugins_dir = locate_file('plugins', custom_paths)
        self._load_nose_custom_plugins(plugins_dir)

        # first is name of program
        nose_config_path = conf[UNITTEST_SEC][NOSE_CONFIG_PATH]
        nose_config_path = locate_file(nose_config_path, custom_paths)
        nose_args = ['nosetests', '-c', nose_config_path]
        if params.nose_apiselector_enabled or \
                conf[UNITTEST_SEC].as_bool(NOSE_API_SELECTOR):
            nose_args.append('--with-apiselector')

        # Add tags
        if params.test_tags is not None:
            test_tags = params.test_tags
        else:
            test_tags = conf[UNITTEST_SEC].as_list(NOSE_TAGS)
        for tag in test_tags:
            nose_args.extend(['-a', tag])

        # Add tag's expressions
        if params.test_tag_expressions is not None:
            test_tag_exprs = params.test_tag_expressions
        else:
            test_tag_exprs = conf[UNITTEST_SEC].as_list(NOSE_TAG_EXPRESSIONS)
        for expr in test_tag_exprs:
            nose_args.extend(['-A', expr])

        # Exclude test patterns
        for expr in conf[UNITTEST_SEC].as_list(NOSE_EXCLUDE):
            nose_args.extend(['-e', expr])

        self.nose_conf.configure(nose_args)

    def _load_nose_custom_plugins(self, path):
        custom_plugins = []
        mod = os.path.basename(os.path.abspath(path))
        sys.path.insert(0, path)
        try:
            for root, dirs, files in os.walk(path, followlinks=True):
                for f in (f for f in files if f.endswith('plugin.py')):
                    mod = __import__(f.rstrip('.py'))
                    plugs_list = filter(lambda x: x.endswith('Plugin')
                                        and x != 'NosePlugin', dir(mod))
                    custom_plugins.extend([getattr(mod, plug)
                                           for plug in plugs_list])
            self.nose_conf.plugins.addPlugins([plug() for plug in
                                               custom_plugins])
            logger.info("Loading Nose custom plugins %s DONE.",
                        [plug.__name__ for plug in custom_plugins])
        finally:
            sys.path.remove(path)

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--test-tag', action='append',
                           dest='test_tags', help="tier=xx or/and team=yy",
                           default=None)
        group.add_argument('--test-tag-expr', action=PythonExprAction,
                           dest='test_tag_expressions',
                           help="python expression "
                           "like: 'team == \"storage\" and tier == 0'",
                           default=None)
        group.add_argument('--with-nose-apiselector', action='store_true',
                           dest='nose_apiselector_enabled',
                           help="enable nose apiselector plugin")

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
        params['requires'] = ['python-nose >= 0.11.0', 'python-unittest2']
        params['data_files'] = ['nose_customization/'
                                'plugins/api_selector_plugin.py',
                                'nose_customization/configs/default.conf']
        params['py_modules'] = [
            'art.test_handler.plmanagement.plugins.'
            'unittest_test_runner_plugin']

    @classmethod
    def config_spec(self, spec, val_funcs):
        val_funcs['expr_list'] = python_expr_list
        section_spec = spec.setdefault(UNITTEST_SEC, {})
        section_spec[NOSE_CUSTOMIZATION_PATHS] = \
            ('list(default=list(%s))' % ','.join(DEFAULT_NOSE_CUSTOM_PATHS))
        section_spec[NOSE_CONFIG_PATH] = ('string('
                                          'default="configs/default.conf")')
        section_spec[NOSE_API_SELECTOR] = \
            'boolean(default=%s)' % DEFAULT_STATE
        section_spec[NOSE_TAGS] = 'force_list(default=list())'
        section_spec[NOSE_TAG_EXPRESSIONS] = 'expr_list(default=list())'
        section_spec[NOSE_EXCLUDE] = 'force_list(default=list())'
