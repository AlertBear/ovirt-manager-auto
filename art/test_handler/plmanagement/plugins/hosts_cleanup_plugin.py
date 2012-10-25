"""
--------------------
Hosts Cleanup Plugin
--------------------

This plugin removes Storage and Network leftovers from your VDS hosts
machines as defined in your configuration file.

CLI Options:
------------
    --cleanup enable plugin and clean all (storage and network)
    --cleanup-storage enable plugin and clean storage only
    --cleanup-network enable plugin and clean network only
"""

import logging
from art.test_handler.plmanagement import logger as root_logger
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.resources_listener import IResourcesListener
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging


logger = logging.getLogger(root_logger.name+'.host_cleanup')

DEFAULT_STATE = False
AD_ENABLED = 'auto_devices'
CLEANUP = 'cleanup'
RUN_SECTION = 'RUN'

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
        group = group.add_mutually_exclusive_group()
        group.add_argument('--cleanup', action="store_true", dest='cleanup', \
                help="enable cleanup functionality, storage and network", \
                default=False)
        group.add_argument('--cleanup-storage', action="store_true", \
                dest='cleanup_str', help="cleanup storage only", default=False)
        group.add_argument('--cleanup-network', action="store_true", \
                dest='cleanup_net', help="cleanup network only", default=False)

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        logger.info("Configuring hosts plugin.")
        self.auto = conf.get(RUN_SECTION).as_bool(AD_ENABLED)
        self.conf = conf
        if not (params.cleanup_str or params.cleanup_net):
            self.storage, self.network = True
        elif params.cleanup_str:
            self.storage = True
            self.network = False
        elif params.cleanup_net:
            self.storage = False
            self.network = True
        else:
            self.storage, self.network = False
            assert False, "This case shouldn't occure"

    def on_storages_prep_request(self):
        pass

    def on_storages_cleanup_request(self):
        pass

    def on_hosts_cleanup_req(self):
        logger.info('Starting hosts cleanup process...')
        from utilities.host_utils import hostsCleanup
        if not hostsCleanup(self.conf['PARAMETERS'], self.auto, \
                storage=self.storage, network=self.network):
            logger.error('Cleaning process was Failed.')
        logger.info('Finish Cleanup process')

    @classmethod
    def is_enabled(cls, params, conf):
        return any((params.cleanup, params.cleanup_str, params.cleanup_net))

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
