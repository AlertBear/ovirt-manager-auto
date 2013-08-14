"""
https://tcms.engineering.redhat.com/plan/9985

Test suite for managing storage connections

Test suite is valid only for RHEV-M 3.3+
"""

import logging

from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections

LOGGER = logging.getLogger(__name__)
sd_api = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        the config file
    """
    import config
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.DATA_CENTER_TYPE,
        basename=config.BASENAME)
    # if there is an automatically added iso domain - remove it
    sds = sd_api.get(absLink=False)
    for sd in sds:
        storagedomains.removeStorageDomain(True, sd.name, config.HOSTS[0])


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    import config
    if not storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME):
        LOGGER.info("Tear down - removing data center")
        ll_dc.removeDataCenter(True, config.DATA_CENTER_NAME)
        for host in config.HOSTS:
            LOGGER.info("Tear down - deactivating host")
            hosts.deactivateHost(True, host)
            LOGGER.info("Tear down - removing host")
            hosts.removeHost(True, host)
        LOGGER.info("Tear down - removing cluster")
        clusters.removeCluster(True, config.PARAMETERS['cluster_name'])
    LOGGER.info("Removing orphaned connections")
    storageconnections.remove_all_storage_connections()
