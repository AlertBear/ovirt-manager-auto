from art.test_handler.plmanagement import (Component, implements, get_logger,
                                                                PluginError)
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation

from utilities.machine import Machine, LINUX

logger = get_logger('cpu_name_resolution')

SECTION_NAME = 'CPU_NAME_RESOLUTION'
PARAMETERS = 'PARAMETERS'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
CPU_NAME = 'cpu_name'
COMPATIBILITY_VERSION = 'compatibility_version'
DEFAULT_STATE = False
ENABLED = 'enabled'
DC_TYPE = 'data_center_type'


class CpuNameResolutionFailed(PluginError):
    pass


class AutoCpuNameResolution(Component):
    """
    Plugin adjusts config section for cpu_name attribute.
    It finds the maximum compatible cpu_name to use for the vds configured.
    """
    implements(IConfigurable, IPackaging, IConfigValidation)
    name = "Auto CPU name resolution"

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        from art.rhevm_api.utils.test_utils import get_api
        #getting cpu information from API
        compatibility_version = conf[PARAMETERS][COMPATIBILITY_VERSION]
        compatibility_version = compatibility_version.split('.')
        util = get_api('version', 'capabilities')
        versions = util.get(absLink=False)
        version = None
        for ver in versions:
            if (ver.get_major() == int(compatibility_version[0]) and
                ver.get_minor() == int(compatibility_version[1])):
                version = ver
                break
        if version is None:
            logger.warning('compatibility_version invalid')
            return

        cpus = version.get_cpus().get_cpu()
        cpus_model_mapping = dict()
        for cpu in cpus:
            #building a mapping from model_ to a dict
            name = cpu.get_id()
            level = cpu.get_level()
            model_name = 'model_'
            if 'Intel' in name:
                model_name += name.split(' ')[1]
                vendor = 'Intel'
            elif 'AMD' in name:
                model_name += name[4:].replace(' ', '_')
                vendor = 'AMD'
            else:
                raise CpuNameResolutionFailed('Unknown vendor of %s' % name)
            cpus_model_mapping[model_name] = {'name' : name, 'level' : level,
                                              'vendor' : vendor}


        #processing the hosts, looking for compatible cpu
        vds_section = PARAMETERS
        dc_val = conf[PARAMETERS][DC_TYPE].upper()
        if dc_val != 'NONE' and dc_val in conf:
            vds_section = dc_val

        vds_list = conf[vds_section].as_list(VDS)
        vds_passwd_list = conf[vds_section].as_list(VDS_PASSWORD)

        selected_cpu = None
        for name, passwd in  zip(vds_list, vds_passwd_list):
            m = Machine(name, 'root', passwd).util(LINUX)
            with m.ssh as ssh:
                rc, out, err = ssh.runCmd(['vdsClient', '-s', '0', 'getVdsCaps',
                        '|', 'grep', '-i', 'flags', '|', 'grep', '-o',
                        "'model_.*'"])
            out = out.strip()
            if not rc or not out:
                logger.warning("Failed to get CPU models of {0}: {1}".format(name, err))
                return
            host_cpu_models = out.split(',')
            host_model = max(host_cpu_models,
                key=lambda m: cpus_model_mapping.get(m, {}).get('level', -1))
            sel_host_cpu  = cpus_model_mapping.get(host_model)
            if sel_host_cpu is None:
                logger.warning('Unknown CPU of host {0}'.format(name))
                return
            if (selected_cpu is None or
                        (sel_host_cpu['vendor'] == selected_cpu['vendor'] and
                        sel_host_cpu['level'] < selected_cpu['level'])):
                selected_cpu = sel_host_cpu

        if selected_cpu is None:
            logger.warning('Failed to find compatible cpu')
            return
        par = conf.get(PARAMETERS, {})
        par[CPU_NAME] = selected_cpu['name']
        conf[PARAMETERS] = par
        logger.info("Updated config %s.%s = %s",
                PARAMETERS, CPU_NAME, par[CPU_NAME])

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-cpu-name-resolution',
                action='store_true', dest='cpu_name_enabled',
                help='enable plugin')

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(SECTION_NAME).as_bool(ENABLED)
        return params.cpu_name_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Gal Leibovici'
        params['author_email'] = 'gleibovi@redhat.com'
        params['description'] = 'Automatic CPU name resolution'
        params['long_description'] = "Plugin for ART, " \
                "which resolves compatible cpu_name of VDS machines."
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'cpu_name_resolution_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(SECTION_NAME, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        spec[SECTION_NAME] = section_spec
