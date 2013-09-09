"""
--------------------------------
Auto-host Nics Resolution Plugin
--------------------------------

Plugin adjusts config section for host_nics attribute.
It will replace host_nics in PARAMETERS section with values fetched from vds

CLI Options:
------------
    --with-host-nics-resolution  Enable the plugin

Configuration Options:
----------------------
    | **[HOST_NICS_RESOLUTION]**
    | **enabled**   to enable the plugin (true/false)
"""

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.configurator import IConfigurator
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import IConfigValidation
from utilities.machine import Machine, LINUX

logger = get_logger('host_nic_resolution')

SECTION_NAME = 'HOST_NICS_RESOLUTION'
PARAMETERS = 'PARAMETERS'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
HOST_NICS = 'host_nics'
ENABLED = 'enabled'
VITAL = 'vital'
DEFAULT_VITAL = True

class NicResolutionFailed(PluginError):
    pass


class AutoHostNicsResolution(Component):
    """
    Plugin adjusts config section for host_nics attribute.
    """
    implements(IConfigurable, IPackaging, IConfigValidation, IConfigurator)
    name = "Auto-host nics resolution"

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        self.vds = conf[PARAMETERS].as_list(VDS)
        self.vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)

    def configure_app(self, conf):
        # FIXME: what if there will be two hosts host1: em[0-9], host2: eth[
        # 0-9]
        nics = set()
        for name, passwd in zip(self.vds, self.vds_passwd):
            m = Machine(name, 'root', passwd).util(LINUX)
            rc, out = m.runCmd(
                ['ls', '-la', '/sys/class/net', '|', 'grep', "'pci'", '|',
                 'grep', '-o', "'[^/]*$'"])
            out = out.strip()
            if not rc or not out:
                raise NicResolutionFailed(out)
            nics |= set(out.splitlines())

        if not nics:
            raise NicResolutionFailed("no nics found")

        par = conf.get(PARAMETERS, {})
        par[HOST_NICS] = sorted(nics)
        conf[PARAMETERS] = par
        logger.info("updated config %s.%s = %s", PARAMETERS, HOST_NICS,
                    par[HOST_NICS])


    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-host-nics-resolution', \
                action='store_true', dest='host_nics_enabled', \
                help="enable plugin")

    @classmethod
    def is_enabled(cls, params, conf):
        en = conf.get(SECTION_NAME).as_bool(ENABLED)
        return params.host_nics_enabled or en

    @classmethod
    def is_vital(cls, conf):
        return conf.get(SECTION_NAME).as_bool(VITAL)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'hosts-nics-resolution'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Auto-nics resolution for ART'
        params['long_description'] = 'Plugin for ART which takes care about '\
                'nics names resolution on VDS machines.'
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.host_nic_resolution_plugin']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(SECTION_NAME, {})
        section_spec[ENABLED] = 'boolean(default=false)'
        section_spec[VITAL] = 'boolean(default=%s)' % DEFAULT_VITAL
        spec[SECTION_NAME] = section_spec

