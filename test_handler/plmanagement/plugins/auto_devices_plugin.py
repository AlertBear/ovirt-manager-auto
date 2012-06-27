import logging
from test_handler.plmanagement import logger as root_logger
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.resources_listener import IResourcesListener
from test_handler.plmanagement.interfaces.application import IConfigurable

logger = logging.getLogger(root_logger.name+'.auto_devices')

AD_ENABLED = 'auto_devices'
AD_CLEANUP = 'auto_devices_cleanup'


class AutoDevices(Component):
    implements(IResourcesListener, IConfigurable)

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
        self.clean = conf['RUN'].get(AD_CLEANUP, 'yes').lower()
        self.enabled = conf['RUN'].get(AD_ENABLED, 'no').lower()
        logger.info("here -> clean: %s, enabled: %s", self.clean, self.enabled)

    def add_options(self, parser):
        pass

    def on_hosts_cleanup_req(self):
        pass

    def on_storages_prep_request(self):
        logger.info("Preparing storages.")
        from test_handler.plmanagement.plugins import storage
        self.su = storage.StorageUtils(self.conf)
        self.su.storageSetup()
        self.su.updateConfFile()

    def on_storages_cleanup_request(self):
        logger.info("Cleaning storages.")
        if self.su is not None and self.clean == 'yes':
            self.su.storageCleanup()
            self.su = None

    @classmethod
    def is_enabled(cls, params, conf):
        #logger.info("auto_devices: %s", cls.enabled)
        if conf is not None:
            return conf['RUN'].get(AD_ENABLED, 'no').lower() == 'yes'
        return True

