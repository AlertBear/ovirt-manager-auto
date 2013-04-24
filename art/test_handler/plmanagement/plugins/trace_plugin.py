"""
---------------
Trace Plugin
---------------

This plugin allows to you trace flow of test execution

CLI Options
-----------
    --with-trace  Enables plugin

Configuration File Options
--------------------------
    | **[TRACE]**
    | **enabled**  true/false; equivalent to with-trace CLI option
    | **included_modules**  list of regular expressions which calls should
                            be traced
    | **excluded_modules**  list of regular expressions which calls shouldn't
                            be traced

"""

import re
import sys
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.plmanagement.interfaces.tests_listener import\
    ITestCaseHandler, ITestGroupHandler

logger = get_logger('trace')


CONFIG_SECTION = "TRACE"
ENABLED = 'enabled'
IN_MODULES = 'included_modules'
EX_MODULES = 'excluded_modules'


class Tracer(object):
    """
    Class filters function calls and prints them
    """
    def __init__(self, include, exclude):
        super(Tracer, self).__init__()
        self.include = include
        self.exclude = exclude

    def is_tracked_module(self, module_name):
        for module in self.exclude:
            if module.match(module_name):
                return False
        for module in self.include:
            if module.match(module_name):
                return True
        return False

    def __call__(self, frame, event, args):
        if event != 'call' or '__name__' not in frame.f_globals:
            return self

        func_name = frame.f_code.co_name
        func_object = frame.f_globals.get(frame.f_code.co_name, None)
        if not func_name or not func_object: # this excludes method_calls
            return self

        module = "%s.%s" % (frame.f_globals['__name__'], func_name)
        if not self.is_tracked_module(module):
            return   # we don't need to track this scope

        variables = dict((x, y) for x, y in frame.f_locals.items()
                         if x in frame.f_code.co_varnames)

        variables = ", ".join("%s=%s" % (x, y) for x, y in variables.items())
        logger.info("%s(%s)", module, variables)

        return self

    def activate(self):
        sys.settrace(self)

    def deactivate(self):
        sys.settrace(None)


class TraceTest(Component):
    """
    Plugin allows to you trace test execution
    """
    implements(IConfigurable, ITestCaseHandler, IConfigValidation, IPackaging,\
               ITestGroupHandler)

    name = "Trace test"

    def __init__(self):
        super(TraceTest, self).__init__()
        self.tracer = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-trace', action='store_true',
                           dest='trace_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        config = conf.get(CONFIG_SECTION)

        in_modules = [re.compile(x, re.I) for x in config.as_list(IN_MODULES)]
        ex_modules = [re.compile(x, re.I) for x in config.as_list(EX_MODULES)]

        self.tracer = Tracer(in_modules, ex_modules)

    def pre_test_case(self, test_case):
        self.tracer.activate()

    def post_test_case(self, test_case):
        self.tracer.deactivate()

    def test_case_skipped(self, test_case):
        pass

    def pre_test_group(self, test_group):
        self.tracer.activate()

    def post_test_group(self, test_group):
        self.tracer.deactivate()

    def test_group_skipped(self, test_group):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[CONFIG_SECTION].as_bool(ENABLED)
        return params.trace_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Trace plugin for ART'
        params['long_description'] = cls.__doc__
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'trace_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CONFIG_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=False)'
        section_spec[IN_MODULES] = "list(default=list('^.*rhevm_api[.].*$'))"
        section_spec[EX_MODULES] = "list(default=list('.*data_struct.*', "\
            "'.*[.]get_api.*'))"
