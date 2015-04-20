"""
Storage SPM negative
"""
import logging

from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.clusters import removeCluster
from art.rhevm_api.tests_lib.low_level.datacenters import removeDataCenter
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils.test_utils import get_api
from rhevmtests.storage.storage_spm_negative import config

LOGGER = logging.getLogger(__name__)

SD_API = get_api('storage_domain', 'storagedomains')


def _check_test_requirements(config):
    """
    Checks that it has two storage domains on different servers
    """
    if config.STORAGE_TYPE == config.ENUMS['storage_type_nfs']:
        server_list = config.PARAMETERS.as_list('data_domain_address')
        server_list.extend(config.PARAMETERS.as_list('master_export_address'))
    elif config.STORAGE_TYPE == config.ENUMS['storage_type_iscsi']:
        server_list = config.PARAMETERS.as_list('lun_address')
        server_list.extend(config.PARAMETERS.as_list('master_lun_address'))
    else:
        raise NotImplementedError("Unknown storage type %s" %
                                  config.STORAGE_TYPE)

    unique_servers = set(server_list)
    return len(unique_servers) > 1


def setup_package():
    """
    Prepares host in a cluster and creates all storage domain given by config.
    """
    if config.GOLDEN_ENV:
        return
    assert _check_test_requirements(config)
    luns = config.PARAMETERS.as_list('lun')
    domain_address = config.PARAMETERS.as_list('data_domain_address')
    config.PARAMETERS['lun'] = list()
    config.PARAMETERS['data_domain_address'] = list()
    LOGGER.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.PARAMETERS['vds'])
    build_setup(config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
                config.TESTNAME)
    config.PARAMETERS['lun'] = luns
    config.PARAMETERS['data_domain_address'] = domain_address
    LOGGER.info("Removing datacenter %s", config.DATA_CENTER_NAME)
    assert removeDataCenter(True, config.DATA_CENTER_NAME)


def teardown_package():
    """
    Removes unattached storage domains, host and cluster
    """
    if config.GOLDEN_ENV:
        return
    storage_domains = SD_API.get(absLink=False)
    host = config.PARAMETERS.as_list('vds')[0]
    unattached = [sd for sd in storage_domains
                  if sd.status is not None and sd.status.state ==
                  config.ENUMS['storage_domain_state_unattached']]
    for sd in unattached:
        LOGGER.info("Removing storage domain %s", sd.name)
        storagedomains.removeStorageDomain(True, sd.name, host, 'true')

    LOGGER.info("Putting host to maintenance")
    assert hosts.deactivateHost(True, host)
    LOGGER.info("Removing host")
    assert hosts.removeHost(True, host)
    LOGGER.info("Removing cluster")
    assert removeCluster(True, config.CLUSTER_NAME)
