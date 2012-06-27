import logging
from test_handler.plmanagement import logger as root_logger
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.resources_listener import IResourcesListener
from test_handler.plmanagement.interfaces.application import IConfigurable

logger = logging.getLogger(root_logger.name+'.host_cleanup')

class CleanUpHosts(Component):
    """
    Plugin provides cleanup procedure for hosts.
    """
    implements(IResourcesListener, IConfigurable)
    name = "CleanUp hosts"

    def __init__(self):
        super(CleanUpHosts, self).__init__()
        self.cleanup = None
        self.auto = False
        self.conf = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--cleanup', action="store_true", dest='cleanup', \
                help="enable cleanup functionality", default=None)

    def configure(self, params, conf):
        logger.info("Configuring hosts plugin.")
        self.auto = conf['RUN'].get('auto_devices','no') == "yes"
        self.conf = conf

    def on_storages_prep_request(self):
        pass

    def on_storages_cleanup_request(self):
        pass

    def on_hosts_cleanup_req(self):
        logger.info('Starting hosts cleanup process...')
        from utilities.host_utils import hostsCleanup
        if not hostsCleanup(self.conf['PARAMETERS'], self.auto):
            logger.error('Cleaning process was Failed.')
        logger.info('Finish Cleanup process')

    @classmethod
    def is_enabled(cls, params, conf):
        return conf.get('cleanup', None) or params.cleanup


