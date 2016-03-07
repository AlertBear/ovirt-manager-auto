"""
-------------------------------
Generate Data Structures Plugin
-------------------------------

Plugin downloads api.xsd from VDC and generates data_structures from it.
Put api.xsd according to defined path in RUN.api_xsd and data structures
according to RUN.data_struct_mod.

CLI Options:
------------
    --with-ds-gen   Enable the plugin

Configuration Options:
----------------------
    | **[GENERATE_DS]**
    | **enabled** - to enable plugin (true/false)
    | **encoding** - to choose encoding from (ascii, utf-8)
"""

import os
import art
from art.test_handler.plmanagement import Component, implements, get_logger,\
    PluginError
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.plmanagement.interfaces.packaging import IPackaging


logger = get_logger('data_struct_gen')


REPO_PATH = os.path.dirname(art.__file__)
# TODO: should be replaced by generateDS package
GENERATE_DS_PATH = os.path.join(REPO_PATH, 'generateDS', 'generateDS.py')

DS_GEN_OPTIONS = "GENERATE_DS"
DEFAULT_STATE = False
VITAL = 'vital'
DEFAULT_VITAL = True
RUN = 'RUN'


class GenerateDSError(PluginError):
    pass


class FailedToDonwloadSchema(GenerateDSError):
    pass


class GenerateDSExecutionError(GenerateDSError):
    pass


class GenerateDataStructures(Component):
    """
    Plugin downloads api.xsd from VDC and generates data_structures from it.
    """
    implements(IConfigurable, IConfigValidation, IPackaging)

    name = "Generate DS"
    priority = -1000

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-ds-gen', action='store_true',
                           dest='ds_gen_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        #for mod in conf[RUN]['data_struct_mod'].replace(',', ' ').split(' '):
        #    self.__generate(mod)(conf)
        self.__generate(conf[RUN]['data_struct_mod'])(conf)

    def __generate(self, mod):
        path = []
        generate_method = None
        for sub_mod in mod.split('.'):
            path.append(sub_mod)
            m = __import__('.'.join(path), fromlist=[sub_mod])
            generate_method = getattr(m, 'generate_ds', None)
            if generate_method:
                return generate_method
        raise Exception("can not find generate_ds method")

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[DS_GEN_OPTIONS].as_bool('enabled')
        return params.ds_gen_enabled or conf_en

    @classmethod
    def is_vital(cls, conf):
        return conf.get(DS_GEN_OPTIONS).as_bool(VITAL)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Generate DS plugin for ART'
        params['long_description'] = cls.__doc__
#        params['pip_deps'] = ['generateDS'] # not used yet
        params['py_modules'] = ['art.test_handler.plmanagement.plugins'
                                '.generate_data_structs_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(DS_GEN_OPTIONS, {})
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[VITAL] = 'boolean(default=%s)' % DEFAULT_VITAL
        section_spec['encoding'] = 'option("ascii", "utf-8", default="utf-8")'
        section_spec['schema_url'] = (
            'string(default="/api?schema")'
        )
