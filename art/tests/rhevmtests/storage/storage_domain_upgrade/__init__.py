"""
Storage domain upgrade
"""
from concurrent.futures import ThreadPoolExecutor
import logging

import art.rhevm_api.tests_lib.low_level.clusters as llclusters
import art.rhevm_api.tests_lib.low_level.datacenters as lldatacenters
import art.rhevm_api.tests_lib.low_level.hosts as llhosts
import art.rhevm_api.tests_lib.low_level.storagedomains as llstoragedomains
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler import exceptions
from rhevmtests.storage.storage_domain_upgrade import config

LOGGER = logging.getLogger("storage-domain-upgrade")

HOST_API = get_api('host', 'hosts')


def setup_package():
    """
    Prepares environment:
        1) creates data-center with temporary cluster
        2) adds host to temporary cluster
    """
    LOGGER.info("Running package setup")
    assert lldatacenters.addDataCenter(
        True, name='temp_dc', storage_type=config.ENUMS['storage_type_nfs'],
        version='3.2')
    assert llclusters.addCluster(
        True, name=config.TMP_CLUSTER_NAME, cpu=config.PARAMETERS['cpu_name'],
        data_center='temp_dc', version='3.2')
    host_install_results = list()
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for host, pwd in zip(config.PARAMETERS.as_list('vds'),
                             config.PARAMETERS.as_list('vds_password')):
            host_install_results.append(executor.submit(llhosts.addHost,
                                        True, name=host, root_password=pwd,
                                        cluster=config.TMP_CLUSTER_NAME,
                                        wait=True))
    for index, result in enumerate(host_install_results):
        LOGGER.info("Checking status of host %s installation",
                    config.PARAMETERS.as_list('vds')[index])
        if result.exception():
            raise result.exception()
        if not result.result():
            raise exceptions.HostException(
                "Failed to install host %s" %
                config.PARAMETERS.as_list('vds')[index])
    LOGGER.info("Package setup finished")


def teardown_package():
    """
    Cleans the environment
    """
    LOGGER.info("Running package teardown")
    assert llstoragedomains.removeDataCenter(True, 'temp_dc')
    for host in HOST_API.get(absLink=False):
        if host.status.state != config.ENUMS['host_state_maintenance']:
            assert llhosts.deactivateHost(True, host.name)
        assert llhosts.removeHost(True, host.name)
    assert llclusters.removeCluster(True, config.TMP_CLUSTER_NAME)
    LOGGER.info("Package teardown finished")
