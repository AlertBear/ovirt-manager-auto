"""
--------------------
Remove packages Plugin
--------------------

This plugin removes packages installed on hosts.
Names of packages should be defined in the configuration file.

CLI Options:
------------
    --remove-packages   Enable the plugin and remove all the defined packages

Configuration Options:
----------------------
    | **[REMOVE_PACKAGES]**
    | **enabled** - to enable the plugin (true/false)
    | **packages** - packages names
"""

import logging
from art.test_handler.plmanagement import logger as root_logger
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from utilities.machine import Machine, LINUX

logger = logging.getLogger('%s.remove_packages' % root_logger.name)

PARAMETERS = 'PARAMETERS'
PKG_SECTION = 'REMOVE_PACKAGES'
ENABLED = 'enabled'
PACKAGES = 'packages'
VDS = 'vds'
VDS_PASSWORD = 'vds_password'
DEFAULT_PACKAGES = ['vdsm', 'vdsm-cli', 'vdsm-python', 'vdsm-xmlrpc']
DEFAULT_STATE = False


class PackagesRemoval(Component):
    """
    Removes packages from hosts.
    """
    implements(IConfigurable, IPackaging, IConfigValidation)

    name = "Remove packages"
    priority = 1000

    def __init__(self):
        super(PackagesRemoval, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--remove-packages', action="store_true",
                           dest='remove_packages', help="remove packages",
                           default=False)

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        logger.info("Configuring remove-packages plugin.")

        vds = conf[PARAMETERS].as_list(VDS)
        vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)
        user = 'root'
        packages = conf[PKG_SECTION].as_list(PACKAGES) if PKG_SECTION in conf \
            else DEFAULT_PACKAGES

        logger.info('Removing packages... %s', ', '.join(packages))
        for name, passwd in zip(vds, vds_passwd):
            m = Machine(name, user, passwd).util(LINUX)
            for pkg in packages:
                if m.checkRpm(pkg):
                    if not m.removeRpm(pkg, True):
                        logger.error('Failed to remove package %s from %s',
                                     pkg, name)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[PKG_SECTION].as_bool(ENABLED) \
            if PKG_SECTION in conf else None
        return params.remove_packages or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Larisa Ustalov'
        params['author_email'] = 'lustalov@redhat.com'
        params['description'] = 'packages cleanup for ART'
        params['long_description'] = 'Plugin for ART which is responsible '\
            'for packages cleanup.'
        params['requires'] = ['art-utilities']
        params['py_modules'] = \
              ['art.test_handler.plmanagement.plugins.remove_packages_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(PKG_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[PACKAGES] = 'force_list(default=list(%s))' % \
            ','.join(DEFAULT_PACKAGES)
        spec[PKG_SECTION] = section_spec
