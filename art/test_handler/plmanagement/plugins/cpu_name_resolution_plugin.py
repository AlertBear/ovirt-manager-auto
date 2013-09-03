"""
--------------------------
Cpu Name Resolution Plugin
--------------------------

This plugin adjusts config section for cpu_name attribute.
It finds the maximum compatible cpu_name to use for the vds configured and
puts it into PARAMETERS.cpu_name value.

CLI Options:
------------
    --with-cpu-name-resolution  Enable the plugin

Configuration File Options:
---------------------------
    | **[CPU_NAME_RESOLUTION]**
    | **enabled** To enable the plugin (true/false)
"""

import re

from art.test_handler.plmanagement import (Component, implements, get_logger,
                                           PluginError)
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import \
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
VITAL = 'vital'
DEFAULT_VITAL = True

MODEL_RE = re.compile(r'model_[A-Za-z_1-9]+')
MIN_MODEL = {'Intel': "model_Conroe", 'AMD': "model_Opteron_G1"}


class CpuNameResolutionFailed(PluginError):
    pass


class CpuPluginError(Exception):
    pass


class AutoCpuNameResolution(Component):
    """
    Plugin adjusts config section for cpu_name attribute.
    It finds the maximum compatible cpu_name to use for the vds configured.
    """
    implements(IConfigurable, IPackaging, IConfigValidation)
    name = "Auto CPU name resolution"

    def get_cpu_model(self, name, passwd):
        """Get the cpu model of the host"""

        m = Machine(name, 'root', passwd).util(LINUX)
        logger.debug("Running vdsClient on {0}".format(name))
        with m.ssh as ssh:
            rc, out, err = ssh.runCmd(['vdsClient', '-s', '0', 'getVdsCaps'])
            out = out.strip()
            err = err.strip()
            if rc or not out:
                raise CpuPluginError('Failed to get CPU models of {0}. '
                                     'Failed running vdsClient on host. '
                                     'Error message: {1} '
                                     'vdsClient output: {2}'.format(name, err,
                                                                    out))
        host_cpu_models = MODEL_RE.findall(out)
        if not host_cpu_models:
            raise CpuPluginError('Failed to get CPU models of {0}'
                                 ' vdsClient output: {1}'.format(name, out))
        host_model = max(host_cpu_models,
                         key=lambda m: self.cpus_model_mapping.get(m, {}).get(
                             'level', -1))
        logger.debug("{0}: cpu model is {1}".format(name, host_model))
        sel_host_cpu = self.cpus_model_mapping.get(host_model)
        if sel_host_cpu is None:
            raise CpuPluginError(
                'Unknown CPU of {0}'.format(name))
        return sel_host_cpu

    def get_vendor_fallback(self, name, passwd):
        """Getting CPU vendor's fallback"""

        m = Machine(name, 'root', passwd).util(LINUX)
        with m.ssh as ssh:
            rc, out, err = ssh.runCmd(['cat', '/proc/cpuinfo', '|',
                                       'grep', 'vendor_id', '|', 'uniq'])
            out = out.strip()
            err = err.strip()
            if rc or not out:
                return None

        vendor = None
        if 'Intel' in out:
            vendor = 'Intel'
        elif 'AMD' in out:
            vendor = 'AMD'
        fallback = self.cpus_model_mapping.get(MIN_MODEL.get(vendor))
        if not fallback:
            logger.debug(
                "Couldn't get vendor of cpu. Output was: %s".format(out))
            raise CpuNameResolutionFailed("Failed to get vendor fallback.")
        return fallback

    def build_mapping(self, cpus):
        """Build mapping between api response to vdsClient output"""

        self.cpus_model_mapping = dict()
        for cpu in cpus:
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
                raise CpuPluginError('Unknown vendor of %s' % name)
            self.cpus_model_mapping[model_name] = {'name': name,
                                                   'level': level,
                                                   'vendor': vendor}

    def get_cpus_from_api(self, compatibility_version):
        """Get the supported cpus from api"""

        from art.rhevm_api.utils.test_utils import get_api

        util = get_api('version', 'capabilities')
        versions = util.get(absLink=False)
        version = None
        for ver in versions:
            if (ver.get_major() == int(compatibility_version[0]) and
                        ver.get_minor() == int(compatibility_version[1])):
                version = ver
                break
        else:
            raise CpuPluginError(
                'compatibility_version invalid')
        cpus = version.get_cpus().get_cpu()
        return cpus

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        #getting cpu information from API
        compatibility_version = conf[PARAMETERS][COMPATIBILITY_VERSION]
        compatibility_version = compatibility_version.split('.')

        try:
            cpus = self.get_cpus_from_api(compatibility_version)
            self.build_mapping(cpus)
        except CpuPluginError as ex:
            logger.warning(ex)
            return

        vds_list = conf[PARAMETERS].as_list(VDS)
        vds_passwd_list = conf[PARAMETERS].as_list(VDS_PASSWORD)

        selected_cpu = None
        try:
            for name, passwd in zip(vds_list, vds_passwd_list):
                host_cpu = self.get_cpu_model(name, passwd)
                if (selected_cpu is None or
                        (host_cpu['vendor'] == selected_cpu['vendor'] and
                                 host_cpu['level'] < selected_cpu[
                                 'level'])):
                    selected_cpu = host_cpu
        except CpuPluginError as ex:
            logger.debug(ex)
            logger.warning("Failed to resolve cpu name. "
                           "Falling back to vendor default...")
            selected_cpu = self.get_vendor_fallback(vds_list[0],
                                                    vds_passwd_list[0])
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
    def is_vital(cls, conf):
        return conf.get(SECTION_NAME).as_bool(VITAL)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Gal Leibovici'
        params['author_email'] = 'gleibovi@redhat.com'
        params['description'] = 'Automatic CPU name resolution'
        params['long_description'] = "Plugin for ART, " \
                                     "which resolves compatible cpu_name of " \
                                     "VDS machines."
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'cpu_name_resolution_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(SECTION_NAME, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[VITAL] = 'boolean(default=%s)' % DEFAULT_VITAL
        spec[SECTION_NAME] = section_spec
