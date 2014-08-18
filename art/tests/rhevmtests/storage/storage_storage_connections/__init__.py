"""
https://tcms.engineering.redhat.com/plan/9985

Test suite for managing storage connections

Test suite is valid only for RHEV-M 3.3+
"""

import logging

from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections
from rhevmtests.storage.storage_storage_connections import config

LOGGER = logging.getLogger(__name__)
sd_api = test_utils.get_api('storage_domain', 'storagedomains')


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
        the config file
    """
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
        basename=config.TESTNAME,
        local=config.STORAGE_TYPE == config.ENUMS['storage_type_local'])
    # for iscsi tests we want to have an empty DC
    if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
        # if there is an automatically added iso domain - remove it
        sds = sd_api.get(absLink=False)
        for sd in sds:
            # Don't remove sds by providers
            if sd.get_storage().get_type() not in \
                    config.STORAGE_TYPE_PROVIDERS:
                assert storagedomains.removeStorageDomain(
                    True, sd.get_name(), config.HOSTS[0])
    if config.STORAGE_TYPE == 'nfs':
        # remove second host, we will need it for manual copying sds
        assert hosts.deactivateHost(True, config.HOSTS[1])
        assert hosts.removeHost(True, config.HOSTS[1])


def teardown_module():
    """ removes created datacenter, storages etc.
    """
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
