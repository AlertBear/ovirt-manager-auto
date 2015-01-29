"""
-------------------------------
Golden Environment Plugin
-------------------------------

Plugin runs tests on pre-prepared environment.

CLI Options:
------------
    --preparedEnv enables this plugin

Configuration Options:
----------------------
    | **[GOLDEN_ENV]**
    | **enabled** - enable plugin (true/false)
"""

import logging
import yaml

from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

logger = logging.getLogger('golden_env')

GOLDEN_ENV = "GOLDEN_ENV"
PREPARED_ENV = "prepared_env"
GOLDEN_ENV_DEF = "env_definition"
RUN = 'RUN'


class RunOnGoldenEnvironment(Component):
    """
    Plugin runs tests on pre-prepared environment. It just changes
    configuration of the tests
    """
    implements(IConfigurable, IConfigValidation, IPackaging)

    name = "Golden Env"
    priority = -500

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument(
            '--prepared_env', action='store_true', default=False,
            dest='golden_env', help="enable plugin")
        group.add_argument(
            "--prepared_env_definition", dest="golden_env_definition",
            default=None, help="file with env definition")

    def _read_config(self, filename):
        with open(filename, "r") as handle:
            env_definition = yaml.load(handle)
        return env_definition

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        config_file = conf[GOLDEN_ENV][GOLDEN_ENV_DEF]
        if params.golden_env_definition is not None:
            config_file = params.golden_env_definition
        env_definition = self._read_config(config_file)
        logger.info("Golden env definition: %s", env_definition)
        conf[PREPARED_ENV] = env_definition

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Katarzyna Jachim'
        params['author_email'] = 'kjachim@redhat.com'
        params['description'] = 'Run tests on golden environment'
        params['long_description'] = cls.__doc__
        params['requires'] = ['PyYAML']
        params['py_modules'] = [
            'art.test_handler.plmanagement.plugins.golden_env_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(GOLDEN_ENV, {})
        section_spec['enabled'] = 'boolean(default=False)'
        section_spec[GOLDEN_ENV_DEF] = 'string(default="")'
        spec[GOLDEN_ENV] = section_spec

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[GOLDEN_ENV].as_bool('enabled')
        return params.golden_env or conf_en
