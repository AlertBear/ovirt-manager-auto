import logging
from art.test_handler.plmanagement import logger as root_logger
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.resources_listener import IResourcesListener
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

logger = logging.getLogger(root_logger.name+'.host_cleanup')

class CleanUpHosts(Component):
    """
    Plugin provides cleanup procedure for hosts.
    """
    implements(IResourcesListener, IConfigurable, IPackaging)
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

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'hosts-cleanup'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Hosts cleanup for ART'
        params['long_description'] = 'Plugin for ART which is responsible '\
                'for clear VDS machines.'
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.hosts_cleanup_plugin']


