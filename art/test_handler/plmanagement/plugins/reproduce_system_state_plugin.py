"""
---------------
Reproduce system state Plugin
---------------
This plugin provides option to reproduce system state.
This plugin is triggered in pre or post test case step


CLI Options
-----------
  --with-repro  Enables reproduce system state plugin
  --test_name   Test name of test case
  --stop_position   Position to stop ART run: could be before or after

Configuration File Options
--------------------------
    | **[REPRODUCE SYSTEM STATE]**
    | **enabled** true/false; equivalent to --with-repro CLI option
    | **stop_position** before/after equivalent to --stop_position CLI option
    | **test_name** string with name of the test that ART will be stopped
    |           before or after running it equivalent to --test_name CLI option
    | **signal** string with signal that will be passed to ART
"""

import os
import signal
import re
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import\
    IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import\
    ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation

logger = get_logger('reproduce system state')

REPRO_OPTION = 'REPRODUCE_SYSTEM_STATE'
DEFAULT_STATE = False
DEFAULT_SIGNAL = 'SIGSTOP'
DEFAULT_STOP_POSITION = 'after'
SIGNAL_OPTIONS = ['SIGSTOP', 'SIGTERM', 'SIGKILL']
STOP_POSITION_OPTIONS = ['before', 'after']


class ReproduceSystemState(Component):
    """
    Plugin provides option to reproduce system state.
    """
    implements(IConfigurable, ITestCaseHandler, IConfigValidation, IPackaging)

    name = "Reproduce system state"
    enabled = True
    depends_on = []

    def __init__(self):
        super(ReproduceSystemState, self).__init__()

    def _stop_art_run(self, stop_position, test_case):
        if self._stop_position == stop_position and \
                test_case.test_name in self._test_names_list:
            msg = "ART stopped {0} '{1}' with {2}, system is ready for debug".\
                format(self._stop_position, test_case.test_name, self._signal)
            logger.warning(msg)
            os.kill(os.getpid(), getattr(signal, self._signal))

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-repro', action='store_true',
                           dest='repro_enabled', help="enable plugin")
        group.add_argument('--test_name', action='store',
                           dest='test_name', help="Name of test case or comma "
                           "separated list of test_names (in this case use "
                           "SIGSTOP and resume with SIGCONT)")
        group.add_argument('--stop_position', action='store',
                           dest='stop_position', choices=STOP_POSITION_OPTIONS,
                           default=DEFAULT_STOP_POSITION,
                           help="Position to stop ART run: "
                           "could be before or after")
        group.add_argument('--signal', action='store', dest='signal_',
                           choices=SIGNAL_OPTIONS, default=DEFAULT_SIGNAL,
                           help="signal that will be passed "
                           " to ART")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        repro_cfg = conf.get(REPRO_OPTION)
        self._test_names_list = repro_cfg['test_name'] or \
            [test.strip() for test in params.test_name.split(',')]
        self._stop_position = \
            params.stop_position or repro_cfg['stop_position']
        self._signal = params.signal_ or repro_cfg['signal']

    def pre_test_case(self, test_case):
        self._stop_art_run('before', test_case)

    def post_test_case(self, test_case):
        self._stop_art_run('after', test_case)

    def test_case_skipped(self, test_case):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[REPRO_OPTION].as_bool('enabled')
        return params.repro_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Ilia Meerovich'
        params['author_email'] = 'imeerovi@redhat.com'
        params['description'] = 'Reproduce system state plugin for ART'
        params['long_description'] = 'Plugin for ART. '\
            'Provides reproduction of needed system state.'
        params['requires'] = []
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'reproduce_system_state_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(REPRO_OPTION, {})
        section_spec['test_name'] = "force_list(default=list())"
        section_spec['stop_position'] = 'option({0}, default="{1}")'.\
            format(re.sub('[\[\]]', '', str(STOP_POSITION_OPTIONS)),
                   DEFAULT_STOP_POSITION)
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['signal'] = 'option({0}, default="{1}")'.\
            format(re.sub('[\[\]]', '', str(SIGNAL_OPTIONS)), DEFAULT_SIGNAL)
