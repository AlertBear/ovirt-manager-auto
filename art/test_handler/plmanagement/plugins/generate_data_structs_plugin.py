"""
-------------------------------
Generate Data Structures Plugin
-------------------------------

Plugin downloads api.xsd from VDC and generates data_structures from it.
Put api.xsd according to defined path in RUN.api_xsd and data structures
according to RUN.data_struct_mod.

CLI Options:
------------
    --with-ds-gen enable plugin

Configuration Options:
----------------------
    [GENERATE_DS]
    enabled - to enable plugin (true/false)
"""

import os
import re
import art
from subprocess  import Popen, PIPE
from art.test_handler.plmanagement import Component, implements, get_logger,\
     PluginError
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.config_validator import\
              IConfigValidation
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.core_api.http import HTTPProxy
from art.test_handler.settings import opts


logger = get_logger('data_struct_gen')


REPO_PATH = os.path.dirname(art.__file__)
# TODO: should be replaced by generateDS package
GENERATE_DS_PATH = os.path.join(REPO_PATH, 'generateDS', 'generateDS.py')

DS_GEN_OPTIONS = "GENERATE_DS"

DEFAULT_STATE = False

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
        group.add_argument('--with-ds-gen', action='store_true', \
                dest='ds_gen_enabled', help="eniable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        xsd_path = self.__resolve_absolute_file_path(conf[RUN]['api_xsd'])
        logger.debug("Path to api.xsd :" + xsd_path)
        self.__download_xsd(xsd_path)

        ds_import_path = conf[RUN]['data_struct_mod']
        ds_rel_path = re.sub("^art.", '',ds_import_path)
        ds_rel_path = ds_rel_path.replace('.',  '/') + '.py'
        ds_full_path = self.__resolve_absolute_file_path(ds_rel_path)
        logger.debug("Path to data_structures:" + ds_full_path)
        self.__generate_ds(xsd_path, ds_full_path)

        __import__(ds_import_path, fromlist=[ds_import_path.rsplit('.', 1)])
        logger.info("Data structures were sucessfully updated")

    @classmethod
    def __resolve_absolute_file_path(cls, file_path):
        return os.path.join(os.path.dirname(art.__file__), file_path)


    @classmethod
    def __download_xsd(cls, file_path):
        proxy = HTTPProxy(opts)
        res = proxy.GET('/api?schema')
        reason = res.get('reason', 'no_reason')
        logger.debug("Fetch schema: code=%s, reason=%s", res['status'], reason)
        if res['status'] > 300:
            raise FailedToDonwloadSchema(reason)

        with open(file_path, 'w') as fh:
            fh.write(res['body'])

    @classmethod
    def __generate_ds(cls, xsd, ds_path):
        cmd = ['python', GENERATE_DS_PATH, '-f', '-o', ds_path, \
                '--member-specs=dict', xsd]

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        logger.debug("Generate DS: %s %s", out, err)
        if p.returncode:
            raise GenerateDSExecutionError(err)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[DS_GEN_OPTIONS].as_bool('enabled')
        return params.ds_gen_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Generate DS plugin for ART'
        params['long_description'] = cls.__doc__
        params['pip_deps'] = ['generateDS']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.bz_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(DS_GEN_OPTIONS, {})
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        spec[DS_GEN_OPTIONS] = section_spec

