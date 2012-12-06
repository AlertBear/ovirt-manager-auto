"""
--------------------
Remove vdsm packages Plugin
--------------------

This plugin removes vdsm, vdsm-cli and vdsm-python
packages from VDS machines defined in configuration file.

CLI Options:
------------
    --remove-vdsm   Enable the plugin and remove all vdsm related packages

Configuration Options:
----------------------
    | **[REMOVE_PACKAGES]**
    | **enabled** - to enable the plugin (true/false)
    | **packages** - packages names, default: vdsm, vdsm-cli, vdsm-python
"""

import logging
from art.test_handler.plmanagement import logger as root_logger
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement import common
from utilities.machine import Machine, LINUX

logger = logging.getLogger(root_logger.name+'.remove_vdsm')

PKG_SECTION = 'REMOVE_PACKAGES'
ENABLED = 'enabled'
PACKAGES = 'packages'
VDS = 'vds'
VDS_PASSWORD = 'vds_password'
DEFAULT_PACKAGES = ['vdsm', 'vdsm-cli', 'vdsm-python']
DEFAULT_STATE = False


class VdsmRemoval(Component):
    """
    Removes vdsm packages from hosts.
    """
    implements(IConfigurable, IPackaging)

    name = "Remove vdsm"
    priority = 1000

    def __init__(self):
        super(VdsmRemoval, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--remove-vdsm', action="store_true",
                           dest='remove_vdsm', help="remove vdsm packages",
                           default=False)

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        logger.info("Configuring remove-vdsm plugin.")

        vds_section = common.get_vds_section(conf)
        vds = conf[vds_section].as_list(VDS)
        vds_passwd = conf[vds_section].as_list(VDS_PASSWORD)
        user = 'root'
        packages = conf[PKG_SECTION].as_list(PACKAGES) if PKG_SECTION in conf \
            else DEFAULT_PACKAGES

        logger.info('Removing vdsm packages...')
        for name, passwd in zip(vds, vds_passwd):
            m = Machine(name, user, passwd).util(LINUX)
            if not m.removeRpm(packages, True):
                logger.error('Failed to remove vdsm packages from %s' % name)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[PKG_SECTION].as_bool(ENABLED) \
            if PKG_SECTION in conf else None
        return params.remove_vdsm or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'remove_vdsm'
        params['version'] = '1.0'
        params['author'] = 'Larisa Ustalov'
        params['author_email'] = 'lustalov@redhat.com'
        params['description'] = 'vdsm cleanup for ART'
        params['long_description'] = 'Plugin for ART which is responsible '\
               'for vdsm packages cleanup.'
        params['requires'] = ['art-utilities']
        params['py_modules'] = \
              ['art.test_handler.plmanagement.plugins.remove_vdsm_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(PKG_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[PACKAGES] = 'force_list(default=list(%s))' % \
            DEFAULT_PACKAGES
        spec[PKG_SECTION] = section_spec
