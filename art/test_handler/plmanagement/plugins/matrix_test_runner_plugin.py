"""
--------------------------------
Matrix Test Runner Plugin
--------------------------------

Plugin that runs the tests scenario (Test Suite).

CLI Options:
------------
    --lines     Defines what lines from the test scenario should be executed.
                Relevant for test scenarios in .ods format. When set only
                specicied lines will be executed, all others will be skipped.
                Possible formats: comma separated list of lines numbers or
                ranges, single line number or range
    --groups    Defines what groups from test scenario should be executed.
                When set only specicied groups will be executed,
                all others will be skipped.
                Possible formats: comma separated list of group names,
                single group
    --compile   Pre-complication of test suite without executing it. In this case
            the test scenario will be checked for syntax errors.
    --discover-actions  Enables actions auto discovery which goes over known
            modules and discover all test actions.

    Examples::

        # to execute only specific lines
        python run.py --conf=/tmp/mytest.conf --lines=1,5-20,30,40-50
        python run.py --conf=/tmp/mytest.conf --lines=6
        python run.py --conf=/tmp/mytest.conf --lines=7-9

        # to execute only specific groups
        python run.py --conf=/tmp/mytest.conf --groups=Group1,Group2
        python run.py --conf=/tmp/mytest.conf --groups=Group1

        # to check the test scenario for syntax errors
        python run.py --conf=/tmp/mytest.conf --compile

        # to rediscover tests actions
        python run.py --conf=/tmp/mytest.conf --discover-actions



Configuration Options:
----------------------
    | **[MATRIX_TEST_RUNNER]**
    | **test_modules**   list of modules which include testing functions
    | **discover_action**   true/false; if to enable actions auto discovery or
        not. When disabled the actions are loaded from cached data
        (conf/actions.conf). If cached data doesn't exist yet (first test run)
        the auto discovery will be still enabled. The default value is: false
"""

import re
import logging
from copy import copy
from socket import error as SocketError
from contextlib import contextmanager
from argparse import Action

from art.test_handler.plmanagement import Component, implements, ExtensionPoint, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultExtension
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement.interfaces.tests_listener import ITestGroupHandler
from art.test_handler.plmanagement.interfaces.config_validator import IConfigValidation
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement import Interface
from art.test_handler.test_runner import TestCase, TestGroup, TestSuite, TestResult
from art.test_handler import exceptions as errors
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError
from art.core_api import ActionSetType, TestAction
from art.test_handler.settings import opts


logger = get_logger('matrix-test-composer')

NO_TB_EXCEPTIONS = (EntityNotFound,)
RUN_SEC = 'RUN'

START_GROUP = 'START_GROUP'
END_GROUP = 'END_GROUP'
_LOOP_INDEX = '#loop_index'

RHEVM_ENUMS = 'RHEVM Enums'
RHEVM_PERMITS = 'RHEVM Permits'
CONFIG_PARAMS = 'PARAMETERS'
REST_CONNECTION = 'REST_CONNECTION'
MATRIX_TEST_RUNNER_SEC = 'MATRIX_TEST_RUNNER'

TEST_MODULES = 'test_modules'
DISCOVER_ACTIONS = 'discover_action'

ACTIONS = 'ACTIONS'


GLOBAL_SCOPE = {
        're': re,
        }


def assign_attributes(te, elm):
    te.test_name = elm[te.TEST_NAME]
    #te.description = elm[TEST_DESCR]


def get_attr_as_bool(elm, name, default='yes'):
    attr = elm.get(name, default)
    if isinstance(attr, bool):
        return attr
    if attr.lower().strip() in ('yes', '1', 'true'):
        return True
    return False


class LinesAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        line_range = re.compile('^((?P<s>[0-9]+)-)?(?P<e>[0-9]+)$')
        values = values.replace(',', ' ').split()
        lines = []
        for val in values:
            m = line_range.match(val)
            if not m:
                parser.error('%s: "%s" is not valid range' % (option_string, val))
            try:
                e = int(m.group('e'))
                s = e
                if m.group('s') is not None:
                    s = int(m.group('s'))
                lines.extend(range(s, e + 1)) # include the range end.
            except TypeError:
                parser.error('%s: "%s" is not valid range' % (option_string, val))
        setattr(namespace, self.dest, lines)


class GroupsAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))


class DoNotRun(errors.SkipTest):
    pass


class ActionConflict(PluginError):
    pass


class IMatrixBasedParser(Interface):
    """
    Interface for TestFile readers
    """
    def is_able_to_run(self, test_identifier):
        """
        Return True when is able to read test
        """
    def provide_test_file(self):
        """
        Return instance of TestFile, which provides test_elements
        """


class TestFile(object):
    def __init__(self, path_to_test):
        super(TestFile, self).__init__()
        self.path = path_to_test

    def get_suites(self):
        raise NotImplementedError()

    def iter_suite(self, suite_name):
        raise NotImplementedError()


class TestComposer(object):
    logger = logging.getLogger()

    def __init__(self, test_file, config, groups=None):
        self.tf = test_file
        #self.a = {}
        if MatrixBasedTestComposer.discover_actions:
            ActionSetType.reset_cache()
        for module in config.get(MATRIX_TEST_RUNNER_SEC).as_list(TEST_MODULES):
            ActionSetType.load_module(module)
        self.a = ActionSetType.actions()
        self.e = opts['elements_conf'][RHEVM_ENUMS]
        self.e.merge(opts['elements_conf'][RHEVM_PERMITS])
        self.c = config[CONFIG_PARAMS]
        self.c.merge(config[REST_CONNECTION])
        self.f = {}
        self.groups = groups

    def resolve_place_holders(self, value, local_scope=None):
        # replace all variables from local_scope
        if local_scope is not None:
            for key, val in local_scope.items():
                value = value.replace(key, val)

        # replace enums params
        vals = re.findall(r'e{\w+}', value)
        for place_holder in vals:
            try:
                place_holder_val = self.e[place_holder.lstrip("e{").rstrip('}')]
            except KeyError:
                logger.error("Enum %s doesn't exist." % (place_holder))
                raise

            value = value.replace(place_holder, str(place_holder_val))

        # replace settings params (single values)
        vals = re.findall(r'{\w+}', value)
        for place_holder in vals:
            try:
                place_holder_val = self.c[place_holder.strip("{}")]
            except KeyError:
                place_holder_val = place_holder
                logger.warn("Parameter %s doesn't exist." % (place_holder))
                #raise # it must be

            value = value.replace(place_holder, str(place_holder_val))

        # replace settings params (list values)
        vals = re.findall(r'{\w+\[\d+\]}', value)
        for place_holder in vals:
            place_holder = place_holder.strip("{}")
            place_holder_name, place_holder_ind = place_holder.strip(']').split('[')
            try:
                place_holderArr = self.c.as_list(place_holder_name)
                place_holder_val = place_holderArr[int(place_holder_ind)]
            except KeyError:
                place_holder_val = "{%s}" % place_holder_name
                logger.warn("Parameter %s with index %s doesn't exist." % (place_holder_name, place_holder_ind))
                #raise
            except IndexError:
                place_holder_val = "{%s}" % place_holder_name
                logger.warn("Parameter %s with index %s doesn't exist." % (place_holder_name, place_holder_ind))
                #raise

            value = value.replace('{%s}' % place_holder, str(place_holder_val))

        # replace settings params, take list value as a single string element
        vals = re.findall(r'\[\w+\]', value)
        for place_holder in vals:
            try:
                place_holder_val = self.c.as_list(place_holder.strip("[]"))
            except KeyError:
                place_holder_val = place_holder
                logger.warn("Parameter %s doesn't exist." % (place_holder))
                #raise
            else:
                value = value.replace(place_holder, \
                    ",".join([str(x) for x in place_holder_val]))

        # replace fetch output values with stored in ouput dictionary by key name
        vals = re.findall(r'%\w+%', value)
        for place_holder in vals:
            key = place_holder.strip("%")
            if key in self.f:
                value = value.replace(place_holder, "fetch_output['" + key + "']")
            else:
                value = value.replace(place_holder, 'None')

        return value

    def group_starts(self, test_name):
        test_name = self.resolve_place_holders(test_name)
        m = re.match("^%s *: *(?P<name>.*)" % START_GROUP, test_name)
        if m:
            return m.group('name')

    def group_ends(self, test_name):
        test_name = self.resolve_place_holders(test_name)
        m = re.match("^%s *: *(?P<name>.*)" % END_GROUP, test_name)
        if m:
            return m.group('name')

    def parse_run_attr(self, run):
        m = re.match('^(?P<yes>(yes|true|1))|(?P<no>(no|false|0))$', run, re.I)
        if m:
            return {'run': 'True' if m.group('yes') is not None else 'False'}
#            return {'run': 'True' if run == 'yes' else 'False'}

        #run = self.resolve_place_holders(run)
        regxs = {
                'if': re.compile('(?P<not>not +)?if[(](?P<condition>.+)[)]', re.I),
                'ifaction': re.compile('(?P<not>not +)?ifaction[(](?P<condition>.+)[)]', re.I),
                'loop': re.compile('loop(_(?P<var>[a-z0-9_]+))?[(](?P<range>.+)[)]', re.I),
                'fork': re.compile('forkfor(_(?P<var>[a-z0-9_]+))?[(](?P<range>.+)[)]', re.I),
                }
        matches = {}
        for elm in run.split(';'):
            for name in regxs.keys():
                m = regxs[name].search(elm)
                if m:
                    matches[name] = m.groupdict()
                    del regxs[name]
                    break

        run_attr = {}
        if 'if' in matches:
            cmd = ''
            if matches['if']['not']:
                cmd += 'not '
            cond = self.resolve_place_holders(matches['if']['condition'])
            cmd += '(%s)' % cond
            run_attr['if'] = cmd
        if 'ifaction' in matches:
            ifact = {'not': ''}
            if matches['ifaction']['not']:
                ifact['not'] = 'not'
            action = matches['ifaction']['condition'].split(',')
            ifact['action'], ifact['params'] = action[0], ','.join(action[1:])
            ifact['params'] = self.resolve_place_holders(ifact['params'])
            run_attr['ifaction'] = ifact

        def resolve_loop(stm):
            loop = {}
            if stm['var'] is None:
                loop['var'] = _LOOP_INDEX
            else:
                loop['var'] = '#' + stm['var']

            m = re.match('^((int(?P<s>{[^}]+})|(?P<s_i>[0-9+]))? *- *)?'\
                    '(int(?P<e>{[^}]+})|(?P<e_i>[0-9]+))$', stm['range'], re.I)
            if m:
                attrs = m.groupdict()
                attrs['s'] = attrs['s'] or attrs['s_i'] or '0'
                attrs['e'] = attrs['e'] or attrs['e_i']
                loop['attrs'] = 'xrange(int({s}), int({e}))'.format(**attrs)
                return loop

            attrs = []
            for att in stm['range'].split(','):
                m = re.match('{(?P<holder>.+)}', att)
                if not m:
                    raise errors.WrongIterableParams(att)
                attrs.append(m.group('holder'))
            if not attrs:
                raise errors.WrongIterableParams(stm['range'])
            loop['attrs'] = attrs
            return loop

        if 'loop' in matches:
            run_attr['loop'] = resolve_loop(matches['loop'])
        if 'fork' in matches:
            run_attr['forkfor'] = resolve_loop(matches['fork'])

        if not run_attr:
            run_attr['run'] = run
#            raise errors.WrongIterableParams(run)

        return run_attr


    def resolve_func_path(self, func_name):
        '''
        Prepare the funcName and modPath for executing
        from {modPath} import {funcName}
        '''
        try:
            func = self.a[func_name]
        except KeyError:
            if func_name.count('.') != 0:
                mod_path, func_name = func_name.rsplit(".", 1)
                exec("from {0} import {1}".format(mod_path, func_name))
                func = eval(func_name)
                func = TestAction(func, func_name, mod_path)
            else:
                logger.error("Action is not implemented yet '{0}'".format(func_name))
                raise errors.CanNotResolveActionPath(func_name)

        return func

    @classmethod
    def generate_suites(cls, test_file, config, groups=None):
        suites = []
        for s_name, s_attr in test_file.get_suites():
            tc = TestComposer(test_file, config, groups)
            s = MatrixTestSuite(s_name, tc)
            for attr in s_attr:
                setattr(s, attr, s_attr[attr])
            suites.append(s)
        return suites


class MatrixTestCase(TestCase):
    def __init__(self, tc, elm):
        super(MatrixTestCase, self).__init__()
        self.parent = None
        self.tc = tc
        self.expected_exc = ()
        self.local_scope = {}
        self.conf = None
        if TestGroup.TEST_RUN not in elm:
            elm[TestGroup.TEST_RUN] = 'yes'
        elm[TestGroup.TEST_VITAL] = get_attr_as_bool(elm,
                TestGroup.TEST_VITAL, default='no')
        for key, val in elm.items():
            self[key] = val

    @classmethod
    def _run(cls, run, tc):
        cmd = '%s' % run.get('run', 'True')
        scope = copy(GLOBAL_SCOPE)
        scope['fetch_output'] = tc.f
        if 'ifaction' in run:
            func = tc.resolve_func_path(run['ifaction']['action'])
            #exec("from {0} import {1}".format(mod, func))
            params = run['ifaction']['params']
            not_ = run['ifaction']['not']
            cmd += " and (%s %s(%s))" % (not_, func.name, params)
            scope[func.name] = func
        if 'if' in run:
            cmd += " and %s" % run['if']

        # Expose fetch_output into local namespace
        try:
            logger.debug("compossed <run> expression: %s", cmd)
            res = eval(cmd, scope)
            #res = True
        except Exception as ex:
            logger.warn("<run> expression failed: '%s' -> %s", cmd, ex)
            res = False
        finally:
            if not res:
                run['run'] = 'False'
                raise DoNotRun("<run> expression evalued as False: %s" % cmd)

    @property
    def group_name(self):
        a = self
        while a.parent is not None:
            if a.parent.__class__.__name__ == MatrixTestGroup.__name__:
                return a.parent.test_name
            a = a.parent
        return None

    def __call__(self):
        if self.conf:
            with self.change_config(self.conf):
                self.__run_test_case()
        else:
            self.__run_test_case()

    def __run_test_case(self):
        self._run(self.run, self.tc)

        self.test_name = self.tc.resolve_place_holders(self.test_name, self.local_scope)
        logger.info(self.format_attr(self.TEST_NAME))
        logger.info(self.format_attr(self.TEST_SERIAL))
        logger.info(self.format_attr(self.TEST_ID))
        self.parameters = self.tc.resolve_place_holders(self.parameters, self.local_scope)

        if self.positive is not None:
            self.parameters = "%s, %s" % (self.positive, self.parameters)
        logger.info(self.format_attr(self.TEST_POSITIVE))

        func = self.tc.resolve_func_path(self.test_action)
        self.test_action = func.name
        logger.info(self.format_attr(self.TEST_ACTION))
        logger.info(self.format_attr(self.TEST_PARAMS))
        self.mod_name = self.group_name
        if not self.mod_name:
            self.mod_name = func.module.split('.')[-1]
        self.mod_name = self.mod_name.capitalize()

        # FIXME: this is related to xunit_results_plugin, wchich should
        # be rewritten in order to follow general design as xml_results_plugin
        # does. please remove this line when xunit_plugin will be rewritten.
        self.mod_path = self.mod_name # THIS ONE!

        self.__resolve_exceptions()

        cmd = "%s(%s)" % (self.test_action, self.parameters)
        res = None

        scope = copy(GLOBAL_SCOPE)
        scope['fetch_output'] = self.tc.f
        scope[self.test_action] = func
        try:
            logger.info("Running command: %s", cmd)
            res = eval(cmd, scope)
            #res = (True, {})
            self.status = self.TEST_STATUS_PASSED
        except self.expected_exc as ex:
            logger.info("Handled expected exception: %s", ex)
            self.status = self.TEST_STATUS_PASSED
        except NO_TB_EXCEPTIONS as ex:
            self.status = self.TEST_STATUS_FAILED
            self.exc = ex
        except SocketError, errors.SkipTest:
            raise
        except EngineTypeError as ex:
            raise errors.SkipTest(str(ex))
        except Exception as ex:
            self.status = self.TEST_STATUS_ERROR
            self.exc = ex
            logger.error("Test Case exception info", exc_info=True)
        else:
            if self.expected_exc:
                self.status = self.TEST_STATUS_FAILED
                msg = "Expected %s but it passed without exception" % \
                      self.expected_exc
                self.exc = Exception(msg)

        if res is None:
            return
        if not isinstance(res, tuple):
            res = (res, {})

        if not res[0]:
            self.status = self.TEST_STATUS_FAILED
            self.exc = Exception("Test returned False")

        if self.fetch_output:
            for fetch in self.fetch_output.split(','):
                self.__fetch_output(fetch, res[1])

    def __fetch_output(self, fetch_output, results):
        fetch_output = self.tc.resolve_place_holders(fetch_output, self.local_scope)
        fetch_output = fetch_output.strip().split('->')
        res = results.get(fetch_output[0], None)
        self.tc.f[fetch_output[1]] = res
        logger.info("Fetch output: %s->%s : %s", fetch_output[0], fetch_output[1], res)

    @classmethod
    @contextmanager
    def change_config(cls, configs):
        '''
        Context manager to change global config values per test case
        Parameters:
        * configs - comma separated string of param names-values pairs
        '''
        try:
            save_opts = {} # save current values
            if configs:
                #dictConf = eval('dict((x, str(y) for x, y in %s.items())' % configs)
                dictConf = eval('dict(%s)' % configs)
                for k in dictConf:
                    save_opts[k] = opts[k]
                # set new conf values
                opts.update(dictConf)
            yield
        except KeyError as ex:
            logger.error("Can't find configuration parameter %s " % ex )
            yield
        finally: # reset previous values
            opts.update(save_opts)

    @classmethod
    def _resolve_run_attr(cls, run, elm):
        if 'loop' in run:
            elm.run = {'run': 'True'}
            elm = MatrixLoopElm(run['loop'], elm)
            del run['loop']
        if 'forkfor' in run:
            elm.run = {'run': 'True'}
            elm = MatrixLoopElm(run['forkfor'], elm)
            elm.workers = 10 # FIXME: make this general
            del run['forkfor']
        elm.run = dict((x, y) for x, y in run.items() if x in ('run', 'if', 'ifaction'))
        if not elm.run:
            elm.run = {'run': 'True'}
        return elm

    def __resolve_exceptions(self):
        excepts = []
        for ex in self.expected_exc:
            if '.' in ex:
                mod, ex = ex.rsplit('.', 1)
                exec("from %s import %s" % (mod, ex))
                excepts.append(eval(ex))
            elif ex in errors.TestExceptionType.EXCEPTIONS:
                excepts.append(errors.TestExceptionType.EXCEPTIONS[ex])
            else:
                excepts.append(eval(ex))
        self.expected_exc = tuple(excepts)

    @classmethod
    def _create_elm(cls, elm, tc):
        case = MatrixTestCase(tc, elm)
        run = tc.parse_run_attr(elm[cls.TEST_RUN])
        return MatrixTestCase._resolve_run_attr(run, case)

    def __str__(self):
        res = self.group_name
        if res is not None:
            res += ": %s" % self.test_name
        else:
            res = self.test_name
        res += "; TestAction: %s" % self.test_action
        if self.positive is not None:
            res += "; Positive: %s" % self.positive
        res += "; Parameters: %s" % self.parameters
        if self.status != self.TEST_STATUS_PASSED:
            res += "; Reason: %s" % self.exc
        return res


class MatrixTestGroup(TestGroup):
    def __init__(self, tc, elm, elms):
        super(MatrixTestGroup, self).__init__()
        self.parent = None
        #self.elm = elm
        self.tc = tc
        self.elms = elms
        self.conf = None
        self.local_scope = {}
        if TestGroup.TEST_RUN not in elm:
            elm[TestGroup.TEST_RUN] = 'yes'
        elm[TestGroup.TEST_VITAL] = get_attr_as_bool(elm,
                TestGroup.TEST_VITAL, default='no')
        for key, val in elm.items():
            self[key] = val

    def __iter__(self):
        conf = self.conf
        if conf is None:
            conf = str()

        with MatrixTestCase.change_config(conf):
            MatrixTestCase._run(self.run, self.tc)

            it = iter(self.elms)
            while True:
                elm = it.next()
                group_name = self.tc.group_starts(elm[self.TEST_NAME])
                if group_name:
                    elm[self.TEST_NAME] = group_name
                    te = MatrixTestGroup._create_elm(elm, it, self.tc, \
                            self.local_scope)
                    if self.tc.groups and group_name not in self.tc.groups:
                        continue
                else:# FIXME: add check for unexpected ending group
                    te = MatrixTestCase._create_elm(elm, self.tc)
                    te.local_scope.update(self.local_scope)
                te.parent = self
                yield te

    @classmethod
    def _create_elm(cls, elm, it, tc, local_scope=None):
        name = elm[cls.TEST_NAME]
        try:
            elms = []
            while True:
                next_elm = it.next()
                if tc.group_ends(next_elm[cls.TEST_NAME]) == name:
                    break
                elms.append(next_elm)
        except StopIteration as ex:
            raise errors.TestComposeError("missing end_group: '%s'" % name)
        g = MatrixTestGroup(tc, elm, elms)
        if local_scope is not None:
            g.local_scope.update(local_scope)
        assign_attributes(g, elm) #FIXME: seems to be redundant
        run = tc.parse_run_attr(elm[cls.TEST_RUN])
        g = MatrixTestCase._resolve_run_attr(run, g)
        return g

    def __str__(self):
        res = "GROUP: %s" % self.test_name
        if self.description:
            res += "; Description: %s" % self.description
        return res


class MatrixLoopElm(MatrixTestGroup):
    def __init__(self, loop, test_elm):
        super(MatrixLoopElm, self).__init__(test_elm.tc, test_elm, [])
        self.loop = loop['attrs']
        self.elm = test_elm
        self.var = loop['var']
        #self.local_scope = copy(getattr(test_elm, 'local_scope', {}))
        #if self.local_scope is None:
        #    self.local_scope = {}
        if test_elm.local_scope is None:
            self.local_scope = {}
        else:
            self.local_scope = copy(test_elm.local_scope)
        test_elm.parent = self

    def __iter__(self):
        MatrixTestCase._run(self.run, self.tc)
        if isinstance(self.loop, (tuple, list)):
            loop_id = 0
            params = dict((x, self.tc.c.as_list(x)) for x in self.loop)
            for vals in [ dict(zip(params.keys(), x)) for x in zip(*params.values()) ]:
                elm = copy(self.elm)
                elm.local_scope = copy(self.local_scope)
                elm.loop_index = loop_id
                # expose vars to local_scope
                elm.local_scope[self.var] = str(loop_id)
                for key, val in vals.items():
                    elm.local_scope["{"+key+"}"] = val
                yield elm
                loop_id += 1
        else:
            xrange_attr = self.tc.resolve_place_holders(self.loop)
            for ind in eval(xrange_attr):
                elm = copy(self.elm)
                elm.local_scope = copy(self.local_scope)
                elm.loop_index = ind
                # expose loop_index to local_scope
                elm.local_scope[self.var] = str(ind)
                yield elm

    def __str__(self):
        return "LOOP: %s" % self.loop


class MatrixTestSuite(TestSuite):
    """
    Contains iterator for test elements.
    """
    def __init__(self, name, tc):
        super(MatrixTestSuite, self).__init__()
        self.tc = tc
        self.it = tc.tf.iter_suite(name)
        self.name = name

    def __iter__(self):
        while True:
            yield self.__compose_element(self.it)

    def __compose_element(self, it):
        elm = it.next()
        group_name = self.tc.group_starts(elm[self.TEST_NAME])
        if group_name:
            elm[self.TEST_NAME] = group_name
            te = MatrixTestGroup._create_elm(elm, it, self.tc)
            if self.tc.groups and group_name not in self.tc.groups:
                return self.__compose_element(it)
            return te
        else:
            return MatrixTestCase._create_elm(elm, self.tc)

    def __str__(self):
        return self.name


class MatrixBasedTestComposer(Component):
    """
    Plugin allows to test_runner be able to run matrix_based tests
    """
    implements(ITestParser, IConfigurable, IResultExtension, ITestCaseHandler, \
            IPackaging, IConfigValidation, ITestGroupHandler)
    parsers = ExtensionPoint(IMatrixBasedParser)
    name = 'Matrix Based Test Composer'
    discover_actions = False

    def __init__(self):
        self.parser = None
        self.groups = []

    def is_able_to_run(self, ti):
        suitable_parser = None

        from art.test_handler.settings import initPlmanager
        plmanager = initPlmanager()
        for parser in self.parsers:
            if suitable_parser is None and parser.is_able_to_run(ti):
                suitable_parser = parser
            else:
                plmanager.disable_component(parser)
        if suitable_parser is None:
            return False
        self.parser = suitable_parser
        return True

    def next_test_object(self):
        if not hasattr(self, 'suites'):
            test_file = self.parser.provide_test_file()
            #tc = TestComposer(test_file, self.conf)
            self.suites = [x for x in TestComposer.generate_suites(test_file, \
                    self.conf, groups=self.groups)]
        try:
            return self.suites.pop()
        except IndexError:
            return None

    def configure(self, params, conf):
        if self.parser is None:
            return
        auto_discover = params.discover_actions or \
                conf[MATRIX_TEST_RUNNER_SEC].as_bool(DISCOVER_ACTIONS)
        self.groups = params.groups
        MatrixBasedTestComposer.discover_actions = auto_discover
        self.conf = conf

        TestCase.add_elm_attribute('TEST_SERIAL', 'serial')
        TestCase.add_elm_attribute('TEST_ID', 'id')
        TestGroup.add_elm_attribute('TEST_RUN', 'run')
        TestCase.add_elm_attribute('TEST_RUN', 'run')
        TestGroup.add_elm_attribute('TEST_ACTION', 'test_action')
        TestCase.add_elm_attribute('TEST_ACTION', 'test_action')
        TestGroup.add_elm_attribute('TEST_PARAMS', 'parameters')
        TestCase.add_elm_attribute('TEST_PARAMS', 'parameters')
        TestGroup.add_elm_attribute('TEST_POSITIVE', 'positive')
        TestCase.add_elm_attribute('TEST_POSITIVE', 'positive')
        TestGroup.add_elm_attribute('TEST_FETCH_OUTPUT', 'fetch_output')

        TestResult.add_result_attribute('module_name', 'mod_name',
                                        'Module name')
        TestResult.add_result_attribute('iter_num', 'serial',
                                        'Iteration number')
        TestResult.add_result_attribute('parameters', 'parameters',
                                        'Test parameters')
        TestResult.add_result_attribute('positive', 'positive',
                                        'Test positive')
        TestResult.add_result_attribute('test_action', 'test_action',
                                        'Test action')
        TestResult.add_result_attribute('report', 'report', 'Report test')
        TestResult.add_result_attribute('exp_events', 'exp_events',
                                 'Number of expected events')

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--lines', '-lines', help='which lines from the '\
                'test file should be executed', action=LinesAction)
        group.add_argument('--groups', '-groups', help='which groups from '\
                'the test file should be executed', action=GroupsAction)
        group.add_argument('--compile', '--dry-run', action='store_true', \
                dest='compile', help='run suites without execution')
        group.add_argument('--discover-actions', action='store_true', \
                dest='discover_actions', help='goes over known modules and '\
                'discover all actions', default=False)

    def pre_test_result_reported(self, res, tc):
        if not tc.report:
            res._report = False
            return
        res.add_result_attribute('module_name', 'mod_name', 'Module Name', '')
        res.add_result_attribute('iter_num', 'serial', 'Iteration Number', '')
        # here should be added some code which will take care about [REPORT] section

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

    def pre_test_group(self, tg):
        pass

    def post_test_group(self, tg):
        pass

    def pre_test_case(self, tc):
        positive = tc.get(TestGroup.TEST_POSITIVE, 'none').lower()
        tc[TestGroup.TEST_POSITIVE] = {'none': None, 'true': True,
                                       'false': False}[positive]
        tc[TestGroup.TEST_REPORT] = get_attr_as_bool(tc, TestGroup.TEST_REPORT)
        if TestGroup.TEST_PARAMS not in tc:
            tc[TestGroup.TEST_PARAMS] = str()
        if TestGroup.TEST_FETCH_OUTPUT not in tc:
            tc[TestGroup.TEST_FETCH_OUTPUT] = None

    def post_test_case(self, tc):
        if tc.status in (tc.TEST_STATUS_PASSED, tc.TEST_STATUS_SKIPPED):
            if tc.status == tc.TEST_STATUS_SKIPPED and isinstance(tc.exc, DoNotRun):
                tc.report = False
                tc.status = tc.TEST_STATUS_PASSED
                logger.info("Test case '%s' will be not executed: %s", tc.test_name, tc.exc)

    def test_group_skipped(self, tg):
        pass

    def test_case_skipped(self, tc):
        pass

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(MATRIX_TEST_RUNNER_SEC, {})
        section_spec[TEST_MODULES] = "string_list("\
                "default=force_list(default=None)"
        section_spec[DISCOVER_ACTIONS] = "boolean(default=False)"
        spec[MATRIX_TEST_RUNNER_SEC] = section_spec

    @classmethod
    def is_enabled(cls, a, b):
        return True

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Matrix-based test runner plugin for ART'
        params['long_description'] = 'Plugin for ART. '\
                                'Allows to user run matrix based tests in ART framework.'
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.matrix_test_runner_plugin']


