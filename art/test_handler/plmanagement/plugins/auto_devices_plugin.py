from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.resources_listener import IResourcesListener
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation

logger = get_logger('auto_devices')

AD_ENABLED = 'auto_devices'
AD_CLEANUP = 'auto_devices_cleanup'
DEFAULT_STATE = False
STR_SECTION = 'STORAGE'
RUN_SECTION = 'RUN'


class AutoDevices(Component):
    implements(IResourcesListener, IConfigurable, IPackaging, IConfigValidation)

    """
    Plugin provides storage allocation tool.
    """
    name = "Auto Devices"
    enabled = 'no'

    def __init__(self):
        super(AutoDevices, self).__init__()
        self.su = None
        self.conf = None
        self.clean = 'yes'

    def configure(self, params, conf):
        logger.info("Configuring storages plugin.")
        self.conf = conf
        self.clean = conf.get(RUN_SECTION).as_bool(AD_CLEANUP)

    def add_options(self, parser):
        pass

    def on_hosts_cleanup_req(self):
        pass

    def on_storages_prep_request(self):
        logger.info("Preparing storages.")
        from art.test_handler.plmanagement.plugins import storage
        self.su = storage.StorageUtils(self.conf)
        self.su.storageSetup()
        self.su.updateConfFile()

    def on_storages_cleanup_request(self):
        logger.info("Cleaning storages.")
        if self.su is not None and self.clean:
            self.su.storageCleanup()
            self.su = None

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
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.auto_devices_plugin',
                'art.test_handler.plmanagement.plugins.storage']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(STR_SECTION, {})
        section_spec['host_group'] = "string(default=None)"
        spec[STR_SECTION] = section_spec

