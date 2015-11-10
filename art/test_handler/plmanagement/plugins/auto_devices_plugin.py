"""
-------------------
Auto Devices Plugin
-------------------

This plugin creates storage devices before the test starts and remove all
these devices after the test finishes.

Configuration Options
---------------------
To enable this plugin add the following parameter to the RUN section:
    * auto_devices=yes

To clean the devices after the test finished use the following parameter in
RUN section:
    * auto_devices_cleanup=yes|all  - to always clean the devices
    * auto_devices_cleanup=no - to never clean the devices
    * auto_devices_cleanup=pass - to clean devices only if test passes
    * auto_devices_cleanup=fail - to clean devices only if test fails

In your settings.conf file add a section STORAGE and fill it with
the following parameters:

    | **[STORAGE]**
    | # to enable/disable load balancing
    | **devices_load_balancing** =  capacity|random|no|false
    | **storage_pool** = <list_of_storage_servers_ips>

    | # possible keys for nfs devices:
    | **nfs_server** = <nfs_server_name>
    | **nfs_devices** = <number_of_nfs_devices>

    | # possible keys for export nfs devices:
    | **export_server** = <nfs_server_name>
    | **export_devices** = <number_of_export_devices>
    |
    | # possible keys for iso nfs devices:
    | **iso_server** = <nfs_server_name>
    | **iso_devices** = <number_of_iso_devices>
    |
    | # possible keys for iscsi devices:
    | **iscsi_server** = <iscsi_server_name>
    | **iscsi_devices** = <number_of_iscsi_devices>
    | **devices_capacity** = <devices_capacity>
    |
    | # possible keys for fcp devices:
    | **fcp_server** = <fcp_server_name>
    | **fcp_devices** = <number_of_iscsi_devices>
    | **devices_capacity** = <devices_capacity>
    |
    | # possible keys for local
    | **local_devices** = <device_path>
    | **local_server** = <host_name> # optional, default is first vds server

To replace the storage configuration file define its fullpath name via the
environment variable STORAGE_CONF_FILE

export STORAGE_CONF_FILE=/mypath/myfile.conf
"""

import re
import os
import storage
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.resources_listener import \
    IResourcesListener
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.plmanagement.interfaces.tests_listener import\
    ITestSuiteHandler
from art.test_handler.exceptions import VitalTestFailed

logger = get_logger('auto_devices')

AD_ENABLED = 'auto_devices'
AD_CLEANUP = 'auto_devices_cleanup'
DEFAULT_STATE = False
STR_SECTION = 'STORAGE'
RUN_SECTION = 'RUN'
LB_ENABLED = 'devices_load_balancing'
STORAGE_POOL = 'storage_pool'
CONF_PATH_ENV = 'STORAGE_CONF_FILE'
STORAGE_ROLE = 'storage_role'


class AutoDevices(Component):
    """
    Plugin provides storage allocation tool.
    """
    implements(IResourcesListener, IConfigurable, IPackaging,
               IConfigValidation, ITestSuiteHandler)

    name = "Auto Devices"

    def __init__(self):
        super(AutoDevices, self).__init__()
        self.su = None
        self.conf = None
        self.clean = None

    def configure(self, params, conf):
        logger.info("Configuring storages plugin.")
        self.conf = conf
        self.cleanup = conf[RUN_SECTION][AD_CLEANUP]

    def add_options(self, parser):
        pass

    def on_hosts_cleanup_req(self):
        pass

    def on_storages_prep_request(self):
        logger.info("Preparing storages.")
        self.su = storage.StorageUtils(self.conf, os.getenv(CONF_PATH_ENV))
        try:
            self.su.storageSetup()
        except Exception as ex:
            logger.error(str(ex), exc_info=True)
            raise VitalTestFailed('Storage device creation')

        self.su.updateConfFile()

    def pre_test_suite(self, suite):
        pass

    def post_test_suite(self, suite):
        if re.match('all|yes', self.cleanup):
            self.clean = True
        elif self.cleanup == 'no':
            self.clean = False
        else:
            self.clean = (self.cleanup == suite.status.lower())

    def on_storages_cleanup_request(self):
        if self.su is not None and self.clean:
            logger.info("Cleaning storages.")
            self.su.storageCleanup()
            self.su = None
        else:
            logger.info("No cleaning storages")

    @classmethod
    def is_enabled(cls, params, conf):
        return conf.get(RUN_SECTION).as_bool(AD_ENABLED)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Storage provisioning plugin for ART'
        params['long_description'] = 'Plugin for ART which provides '\
            'Storage provisioning functionality.'
        # FIXME: Can not set version for art-storage-api
        params['requires'] = ['art-storage-api', 'pysnmp']
        params['py_modules'] = [
            'art.test_handler.plmanagement.plugins.auto_devices_plugin',
            'art.test_handler.plmanagement.plugins.storage']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(STR_SECTION, {})
        section_spec[STORAGE_POOL] = "force_list(default=None)"
        section_spec[STORAGE_ROLE] = "string(default='')"
        # TODO: remove false, it remained for backward compatibility
        section_spec[LB_ENABLED] = \
            "option('capacity', 'random', 'no', 'false', default=random)"
        spec[STR_SECTION] = section_spec
        run_spec = spec.get(RUN_SECTION, {})
        run_spec[AD_ENABLED] = "boolean(default=False)"
        run_spec[AD_CLEANUP] = \
            "option('pass', 'fail', 'all', 'yes', 'no', default='all')"
        spec[RUN_SECTION] = run_spec
