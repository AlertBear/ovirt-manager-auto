
import os
import re
import logging
from copy import copy
from configobj import ConfigObj
from socket import error as SocketError
from contextlib import contextmanager

from art.test_handler.plmanagement import Component, implements, ExtensionPoint, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import ITestParser, IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultExtension
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement import Interface
from art.test_handler.test_runner import TestCase, TestGroup, TestSuite, TestResult
from art.test_handler import exceptions as errors
from art.core_api.apis_exceptions import EntityNotFound, EngineTypeError
from art.test_handler.settings import opts

# TODO: solve <conf> element

TEST_CASES_SEPARATOR = '\n' + '=' * 80


logger = get_logger('matrix-test-composer')

NO_TB_EXCEPTIONS = (EntityNotFound,EngineTypeError)
RUN_SEC = 'RUN'

TEST_CASE = 'test_case'
TEST_ID = 'id'
TEST_SERIAL = 'serial'
TEST_NAME = 'test_name'
TEST_RUN = 'run'
TEST_DESCR = 'test_description'
TEST_ACTION = 'test_action'
TEST_PARAMS = 'parameters'
TEST_POSITIVE = 'positive'
TEST_REPORT = 'test_report'
TEST_FETCH_OUTPUT = 'fetch_output'
TEST_BZ_ID = 'bz'
TEST_VITAL = 'vital'
TEST_CONF = 'conf'


fetch_path = lambda x: os.path.abspath(\
        os.path.join(os.path.dirname(__file__), '..', '..', '..', x))
ACTIONS_PATH = fetch_path("conf/actions.conf")
ELEMENTS_PATH = fetch_path("conf/elements.conf")

START_GROUP = 'START_GROUP'
END_GROUP = 'END_GROUP'
_LOOP_INDEX = '#loop_index'

RHEVM_ENUMS = 'RHEVM Enums'
RHEVM_PERMITS = 'RHEVM Permits'
CONFIG_PARAMS = 'PARAMETERS'
REST_CONNECTION = 'REST_CONNECTION'



def assign_attributes(te, elm):
    te.test_name = elm[TEST_NAME]
    #te.description = elm[TEST_DESCR]


def get_attr_as_bool(elm, name, default='yes'):
    elm[name] = elm.get(name, default).lower().strip()
    if elm[name] in ('yes', '1', 'true'):
        return True
    return False


class DoNotRun(errors.SkipTest):
    pass


class IMatrixBasedParser(Interface):
    def is_able_to_run(self, test_identifier):
        """"""
    def provide_test_file(self):
        """"""


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

    def __init__(self, test_file, config, actions=None, elements=None):
        self.tf = test_file
        if actions is None:
            actions = ConfigObj(infile=ACTIONS_PATH)['ACTIONS']
        self.a = actions
        if elements is None:
            elements = ConfigObj(infile=ELEMENTS_PATH)
        self.e = elements[RHEVM_ENUMS]
        self.e.merge(elements[RHEVM_PERMITS])
        self.c = config[CONFIG_PARAMS]
        self.c.merge(config[REST_CONNECTION])
        self.c.merge(self.__get_data_center_config(config))
        self.f = {}

    def __get_data_center_config(self, config):
        # FIXME: ugly hardcoded variable
        dc_type_sec = config[CONFIG_PARAMS].get('data_center_type', 'none').lower()
        if dc_type_sec != 'none' and dc_type_sec in config:
            return config[dc_type_sec]
        return {}

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

            value = value.replace(place_holder, place_holder_val)

        # replace settings params (single values)
        vals = re.findall(r'{\w+}', value)
        for place_holder in vals:
            try:
                place_holder_val = self.c[place_holder.strip("{}")]
            except KeyError:
                logger.warn("Parameter %s doesn't exist." % (place_holder))
                #raise # it must be

            if not isinstance(place_holder_val, list):
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

            value = value.replace('{' + place_holder + '}', place_holder_val)

        # replace settings params, take list value as a single string element
        vals = re.findall(r'\[\w+\]', value)
        for place_holder in vals:
            try:
                place_holder_val = self.c.as_list(place_holder.strip("[]"))
            except KeyError:
                place_holder_val = place_holder
                logger.warn("Parameter %s doesn't exist." % (place_holder))
                #raise

            value = value.replace(place_holder, ",".join(place_holder_val))

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
                'loop': re.compile('loop[(](?P<range>.+)[)]', re.I),
                'fork': re.compile('forkfor[(](?P<range>.+)[)]', re.I),
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
            m = re.match('((?P<s>[0-9]+) *- *)?(?P<e>[0-9]+)', stm['range'])
            if m:
                try:
                    s = 0
                    if m.group('s') is not None:
                        s = int(m.group('s'))
                    e = int(m.group('e'))
                    return 'xrange(%s, %s)' % (s, e)
                except TypeError:
                    raise errors.WrongIterableParams(stm['range'])

            attrs = []
            for att in stm['range'].split(','):
                m = re.match('{(?P<holder>.+)}', att)
                if not m:
                    raise errors.WrongIterableParams(att)
                attrs.append(m.group('holder'))
            if not attrs:
                raise errors.WrongIterableParams(stm['range'])
            return attrs

        if 'loop' in matches:
            run_attr['loop'] = resolve_loop(matches['loop'])
        if 'fork' in matches:
            run_attr['forkfor'] = resolve_loop(matches['fork'])

        if not run_attr:
            raise errors.WrongIterableParams(run)

        return run_attr


    def resolve_func_path(self, func_name):
        '''
        Prepare the funcName and modPath for executing
        from {modPath} import {funcName}
        '''
        try:
            test_action = self.a[func_name].rsplit(".")
        except KeyError:
            logger.error("Action is not implemented yet '{0}'".format(func_name))
            raise errors.CanNotResolveActionPath(func_name)

        mod_path = '.'.join(test_action[:-1])
        func_name = test_action[-1]
        return mod_path, func_name

    @classmethod
    def generate_suites(cls, test_file, config, actions=None, elements=None):
        suites = []
        for s_name, s_attr in test_file.get_suites():
            tc = TestComposer(test_file, config, actions, elements)
            s = MatrixTestSuite(s_name, tc)
            for attr in s_attr:
                setattr(s, attr, s_attr[attr])
            suites.append(s)
        return suites


class MatrixTestCase(TestCase):
    def __init__(self, tc, elm):
        super(MatrixTestCase, self).__init__()
        self.tc = tc
        self.excpexted_exc = ()
        self.local_scope = {}
        self.conf = None
        for key, val in elm.items():
            self[key] = val


    @classmethod
    def _run(cls, run, tc):
        cmd = '%s' % run.get('run', 'True')
        if 'ifaction' in run:
            mod, func = tc.resolve_func_path(run['ifaction']['action'])
            exec("from {0} import {1}".format(mod, func))
            params = run['ifaction']['params']
            not_ = run['ifaction']['run']
            cmd += " and (%s %s(%s))" % (not_, func, params)
        if 'if' in run:
            cmd += " and %s" % run['if']

        # Expose fetch_output into local namespace
        fetch_output = tc.f
        try:
            logger.debug("compossed <run> expression: %s", cmd)
            res = eval(cmd)
            #res = True
        except Exception as ex:
            logger.warn("<run> expression failed: '%s' -> %s", cmd, ex)
            res = False
        finally:
            if not res:
                raise DoNotRun("<run> expression evalued as False: %s" % cmd)

    def __call__(self):
        if self.conf:
            with self.change_config(self.conf):
                self.__run_test_case()
        else:
            self.__run_test_case()

    def __run_test_case(self):
        self._run(self.run, self.tc)

        self.test_name = self.tc.resolve_place_holders(self.test_name, self.local_scope)
        logger.info(self.format_attr(TEST_NAME))
        logger.info(self.format_attr(TEST_SERIAL))
        logger.info(self.format_attr(TEST_ID))
        self.parameters = self.tc.resolve_place_holders(self.parameters, self.local_scope)

        if self.positive is not None:
            self.parameters = "%s, %s" % (self.positive, self.parameters)
        #if self.positive is True:
        #    self.parameters = "'true', %s" % self.parameters
        #elif self.positive is False:
        #    self.parameters = "'false', %s" % self.parameters
        logger.info(self.format_attr(TEST_POSITIVE))

        self.mod_path, self.test_action = self.tc.resolve_func_path(self.test_action)
        logger.info(self.format_attr(TEST_ACTION))
        logger.info(self.format_attr(TEST_PARAMS))
        self.mod_name = self.mod_path.split('.')[-1].capitalize()
        exec("from %s import %s" % (self.mod_path, self.test_action))

        cmd = "%s(%s)" % (self.test_action, self.parameters)
        res = None

        # Expose fetch_output into local_scope
        fetch_output = self.tc.f
        try:
            logger.info("Running command: %s", cmd)
            res = eval(cmd)
            #res = (True, {})
            self.status = self.TEST_STATUS_PASSED
        except self.excpexted_exc as ex:
            logger.info("Handled expected exception: %s", ex)
            self.status = self.TEST_STATUS_PASSED
        except NO_TB_EXCEPTIONS as ex:
            self.status = self.TEST_STATUS_FAILED
            logger.error(ex)
        except SocketError:
            raise
        except Exception as ex:
            self.status = self.TEST_STATUS_ERROR
            logger.error("Test Case execution failed", exc_info=True)

        if res is None:
            return
        if not isinstance(res, tuple):
            res = (res, {})

        if self.positive is not None and not res[0]:
            self.status = self.TEST_STATUS_FAILED

        if self.fetch_output:
            self.__fetch_output(res[1])

    def __fetch_output(self, results):
        self.fetch_output = self.tc.resolve_place_holders(self.fetch_output, self.local_scope)
        fetch_output = self.fetch_output.split('->')
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

    @classmethod
    def _create_elm(cls, elm, tc):
        case = MatrixTestCase(tc, elm)
        run = tc.parse_run_attr(elm[TEST_RUN])
        return MatrixTestCase._resolve_run_attr(run, case)


class MatrixTestGroup(TestGroup):
    def __init__(self, tc, elm, elms):
        super(MatrixTestGroup, self).__init__()
        self.elm = elm
        self.tc = tc
        self.elms = elms
        self.conf = None
        self.local_scope = {}

    def __iter__(self):
        conf = self.conf
        if conf is None:
            conf = str()

        with MatrixTestCase.change_config(conf):
            MatrixTestCase._run(self.run, self.tc)

            it = iter(self.elms)
            while True:
                elm = it.next()
                group_name = self.tc.group_starts(elm[TEST_NAME])
                if group_name:
                    elm[TEST_NAME] = group_name
                    te = MatrixTestGroup._create_elm(elm, it, self.tc, \
                            self.local_scope)
                    #te.local_scope.update(self.local_scope)
                    yield te
                else:# FIXME: add check for unexpected ending group
                    te = MatrixTestCase._create_elm(elm, self.tc)
                    te.local_scope.update(self.local_scope)
                    yield te

    @classmethod
    def _create_elm(cls, elm, it, tc, local_scope=None):
        name = elm[TEST_NAME]
        try:
            elms = []
            while True:
                next_elm = it.next()
                if tc.group_ends(next_elm[TEST_NAME]) == name:
                    break
                elms.append(next_elm)
        except StopIteration as ex:
            raise errors.TestComposeError("missing end_group: '%s'" % name)
        g = MatrixTestGroup(tc, elm, elms)# missing local_scope
        if local_scope is not None:
            g.local_scope.update(local_scope)
        assign_attributes(g, elm) #FIXME: seems to be redundant
        run = tc.parse_run_attr(elm[TEST_RUN])
        g = MatrixTestCase._resolve_run_attr(run, g)
        return g


class MatrixLoopElm(MatrixTestGroup):
    def __init__(self, loop, test_elm):
        super(MatrixLoopElm, self).__init__(test_elm.tc, test_elm, [])
        self.loop = loop
        self.elm = test_elm
        #self.local_scope = copy(getattr(test_elm, 'local_scope', {}))
        #if self.local_scope is None:
        #    self.local_scope = {}
        if test_elm.local_scope is None:
            self.local_scope = {}
        else:
            self.local_scope = copy(test_elm.local_scope)

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
                elm.local_scope[_LOOP_INDEX] = str(loop_id)
                for key, val in vals.items():
                    elm.local_scope["{"+key+"}"] = val
                yield elm
                loop_id += 1
        else:
            for ind in eval(self.loop):
                elm = copy(self.elm)
                elm.local_scope = copy(self.local_scope)
                elm.loop_index = ind
                # expose loop_index to local_scope
                elm.local_scope[_LOOP_INDEX] = str(ind)
                yield elm


class MatrixTestSuite(TestSuite):

    def __init__(self, name, tc):
        super(MatrixTestSuite, self).__init__()
        self.tc = tc
        self.it = tc.tf.iter_suite(name)

    def __iter__(self):
        while True:
            yield self.__compose_element(self.it)

    def __compose_element(self, it):
        elm = it.next()
        group_name = self.tc.group_starts(elm[TEST_NAME])
        if group_name:
            elm[TEST_NAME] = group_name
            te = MatrixTestGroup._create_elm(elm, it, self.tc)
            return te
        else:
            return MatrixTestCase._create_elm(elm, self.tc)


class MatrixBasedTestComposer(Component):
    """
    Plugin allows to test_runner be able to run matrix_based tests
    """
    implements(ITestParser, IConfigurable, IResultExtension, ITestCaseHandler)
    parsers = ExtensionPoint(IMatrixBasedParser)
    name = 'Matrix Based Test Composer'
    enabled = True

    def __init__(self):
        self.parser = None

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
            self.suites = [x for x in TestComposer.generate_suites(test_file, self.conf)]
        try:
            return self.suites.pop()
        except IndexError:
            return None

    def configure(self, params, conf):
        if self.parser is None:
            MatrixBasedTestComposer.enabled = False
            return
        self.conf = conf
        TestResult.ATTRIBUTES['module_name'] = \
                ('mod_name', None, None)
        TestResult.ATTRIBUTES['iter_num'] = \
                ('serial', "Iteration number", None)
        TestResult.ATTRIBUTES[TEST_PARAMS] = \
                (TEST_PARAMS, "Test parameters", None)
        TestResult.ATTRIBUTES[TEST_POSITIVE] = \
                (TEST_POSITIVE, "Test positive", None)
        TestResult.ATTRIBUTES[TEST_ACTION] = \
                (TEST_ACTION, "Test action", None)
        TestResult.ATTRIBUTES[TEST_REPORT] = \
                (TEST_REPORT, "Report test", None)

    @classmethod
    def add_options(cls, parser):
        pass

    def pre_test_result_reported(self, res, tc):
        if not tc.test_report:
            res._report = False
            return
        res.module_name = tc.mod_name
        # here should be added some code which will take care about [REPORT] section

        logger.info(TEST_CASES_SEPARATOR)

    def pre_test_case(self, tc):
        logger.info(TEST_CASES_SEPARATOR)

    def post_test_case(self, tc):
        if tc.status == tc.TEST_STATUS_PASSED or tc.status == tc.TEST_STATUS_SKIPPED:
            st_msg = logger.info
            if tc.status == tc.TEST_STATUS_SKIPPED and isinstance(tc.exc, DoNotRun):
                tc.test_report = False
                tc.status = tc.TEST_STATUS_PASSED
                logger.info("Test case '%s' will not executed: %s", tc.test_name, tc.exc)
        elif tc.status == tc.TEST_STATUS_UNDEFINED:
            st_msg = logger.warn
        else:
            st_msg = logger.error
        st_msg(tc.format_attr('status'))

    def test_case_skipped(self, tc):
        pass

    @classmethod
    def is_enabled(cls, a, b):
        #return cls.enabled
        return True

