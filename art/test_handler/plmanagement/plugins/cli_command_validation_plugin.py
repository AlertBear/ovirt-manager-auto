"""
---------------
CLI command validation Plugin
---------------
This plugin provides option to turn off/on cli validation on single test level.
This plugin is triggered in pre and post test case step
Use cases:
1)In case of CLI_CONNECTION.validate_cli_command = True [default]:
- Turn off validation on test level
2)In case of CLI_CONNECTION.validate_cli_command = False (rare case,
  set by user):
- Turn on validation on test level

Test Case Configuration
-----------------------
<cli_validation>False</cli_validation>

CLI Options
-----------
  --with-validation Enables CLI command validation plugin

Configuration File Options
--------------------------
    |**[CLI_COMMAND_VALIDATION]**
    |**enabled** true/false; equivalent to --with-validation CLI option


From XML test sheet
+++++++++++++++++++
You can add <cli_validation> tag for each test_case.
Values: False - no cli validation
        True - with cli validation

From unittest suite
+++++++++++++++++++
In art.test_handler.tools module there is defined
cli_command_validation_decorator(cli_validation).
You can use it to decorate your functions.
"""

import threading
from art.test_handler.settings import opts
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import\
    IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import\
    ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.test_runner import TestCase

logger = get_logger('CLI command validation')
addlock = threading.Lock()
VALIDATION_OPTION = 'cli_validation'
CLI_VALIDATION_OPTION = 'CLI_COMMAND_VALIDATION'
DEFAULT_STATE = False
BOOLEAN_NEGATIVE = 'false'


def cli_command_validation_decorator(cli_validation):
    """
    cli_command_validation decorator
    """
    def decorator(func):
        setattr(func, VALIDATION_OPTION, cli_validation)
        return func
    return decorator


class CLICommandValidation(Component):
    """
    Plugin provides option to turn off CLI command validation on
    test resolution.
    """
    implements(IConfigurable, ITestCaseHandler, IConfigValidation, IPackaging)

    name = "CLI command validation"
    priority = 11999  # should be run before last

    def __init__(self):
        super(CLICommandValidation, self).__init__()
        self._disable_validation = False
        self.__register_functions()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-no-validation', action='store_true',
                           dest='validation_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        TestCase.add_elm_attribute('CLI_VALIDATION', VALIDATION_OPTION)
        self._opts_validation = opts['validate_cli_command']

    def __register_functions(self):
        from art.test_handler import tools
        setattr(tools, 'cli_command_validation_decorator',
                cli_command_validation_decorator)

    def pre_test_case(self, test_case):
        with addlock:
            try:
                is_validation = test_case[VALIDATION_OPTION].lower()
            except (KeyError, AttributeError):
                logger.warning("cli_validation parameter wasn't defined or"
                               " set, running according to conf file"
                               " configuration")
                is_validation = str(self._opts_validation)
            if is_validation.lower() == BOOLEAN_NEGATIVE:
                opts['validate_cli_command'] = False
                logger.warning("CLI command Validation disabled")
            else:
                opts['validate_cli_command'] = True
                logger.warning("CLI command Validation enabled")
            # Possible issue: if post_test_case of thread 1 will run just
            # after pre_test_case of thread 2, we will have a bug...
            # However severity of this bug is low...

    def post_test_case(self, test_case):
        with addlock:
            opts['validate_cli_command'] = self._opts_validation

    def test_case_skipped(self, test_case):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[CLI_VALIDATION_OPTION].as_bool('enabled')
        return params.validation_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Ilia Meerovich'
        params['author_email'] = 'imeerovi@redhat.com'
        params['description'] = 'CLI command validation Plugin for ART'
        params['long_description'] = cls.__doc__
        params['requires'] = []
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'cli_command_validation_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CLI_VALIDATION_OPTION, {})
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
