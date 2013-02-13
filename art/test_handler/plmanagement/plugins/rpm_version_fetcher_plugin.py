"""
------------------------
RPM version fetcher
------------------------

Plugin easilly connect to machines and fetch relevant rpm's versions.

CLI Options:
------------
    --version-fetcher   Enable plugin

Configuration Options:
----------------------
    | **[VERSION_FETCHER]**
    | **enabled**   to enable the plugin (true/false)
    | **host**       list of rpms to check on VDC machine
    | **vds**       list of rpms to check on VDS machine
"""

import re
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import \
        IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation
from utilities.machine import Machine, LINUX

logger = get_logger('validate_events')
CONFIG_SECTION = 'VERSION_FETCHER'
ENABLED = 'enabled'
VDC_PARAMS = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
VDS = 'vds'
VDC = 'host'
VDC_PASSWD = 'vdc_root_password'
VDS_PASSWORD = 'vds_password'


class VersionFetcher(Component):
    """
    Plugin easilly connect to machines and fetch relevant rpm's versions.
    """
    implements(IConfigurable, IApplicationListener, IPackaging,
            IConfigValidation)
    name = "Version fetcher"

    def __init__(self):
        super(VersionFetcher, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--version-fetcher', action='store_true', \
                dest='version_fetcher', help="enable plugin", default=False)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(CONFIG_SECTION).as_bool(ENABLED)
        number = len(conf.get(CONFIG_SECTION).as_list(VDC))
        number += len(conf.get(CONFIG_SECTION).as_list(VDS))
        return (params.version_fetcher or conf_en) and number

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        vdc_passwd = conf[PARAMETERS][VDC_PASSWD]
        vdc = conf[VDC_PARAMS][VDC]
        vds = conf[PARAMETERS].as_list(VDS)
        vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)
        if len(vds_passwd) < len(vds):
            vds_passwd = [vds_passwd[0]] * len(vds)
        user = 'root'

        self.vdc = Machine(vdc, user, vdc_passwd).util(LINUX)
        self.vds = []

        for name, passwd in  zip(vds, vds_passwd):
            self.vds.append(Machine(name, user, passwd).util(LINUX))

        self.vdc_rpms = conf.get(CONFIG_SECTION).as_list(VDC)
        self.vds_rpms = conf.get(CONFIG_SECTION).as_list(VDS)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.replace(' ', '-').lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = cls.__doc__.strip().replace('\n', ' ')
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'\
                'rpm_version_fetcher_plugin']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CONFIG_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=False)'
        section_spec[VDC] = 'string_list(default=list())'
        section_spec[VDS] = 'string_list(default=list())'

    def on_application_start(self):
        pass

    def on_plugins_loaded(self):
        pass

    def on_application_exit(self):
        error_msg = "%s: Failed to get version of rpms %s: %s"
        try:
            vdc_rpms = self.__get_version_info(self.vdc, *self.vdc_rpms)
        except Exception as ex:
            logger.error(error_msg, self.vdc.host, self.vdc_rpms, ex)
        else:
            self.__print_versions("VDC", vdc_rpms)

        vds_rpms = set()
        for vds in self.vds:
            try:
                vds_rpms |= self.__get_version_info(vds, *self.vds_rpms)
            except Exception as ex:
                logger.error(error_msg, vds.host, self.vds_rpms, ex)
        self.__print_versions("VDS", vds_rpms)

    def __get_version_info(self, machine, *rpms):
        names = set()
        msg = "%s: Can not fetch rpm version %s: %s"
        with machine.ssh  as ssh:
            for rpm_name in rpms:
                cmd = ['rpm', '-qa', rpm_name]
                try:
                    rc, out, err = ssh.runCmd(cmd)
                except Exception as ex:
                    logger.error(msg, machine.host, rpm_name, ex)
                else:
                    out = out.strip()
                    if out:
                        names.add(out)
        return names

    def __print_versions(self, prefix, rpms):
        for name in rpms:
            logger.info("Version from %s is %s", prefix, name)
