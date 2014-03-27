"""
Bridgeless network feature test
"""

import logging
from art.rhevm_api.tests_lib.low_level.clusters import addCluster, \
    removeCluster
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter
from art.rhevm_api.tests_lib.low_level.hosts import addHost, removeHost, \
    deactivateHost
from art.test_handler.exceptions import NetworkException
logger = logging.getLogger("Bridgeless_Network")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    logging.info("Adding datacenter")
    if not addDataCenter(positive=True, name=config.DC_NAME,
                         storage_type=config.STORAGE_TYPE,
                         version=config.VERSION):
        raise NetworkException("Failed to add datacenter")

    logger.info("Adding cluster")
    if not addCluster(positive=True, name=config.CLUSTER_NAME,
                      cpu=config.CPU_NAME, data_center=config.DC_NAME,
                      version=config.VERSION):
        raise NetworkException("Failed to add Cluster")

    logger.info("Adding host")
    if not addHost(positive=True, name=config.HOSTS[0],
                   root_password=config.HOSTS_PW, cluster=config.CLUSTER_NAME):
        raise NetworkException("Failed to add host")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Removing DC/Cluster and host")
    if not removeDataCenter(positive=True, datacenter=config.DC_NAME):
        raise NetworkException("Failed to remove datacenter")

    if not deactivateHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Failed to set host to maintenance")

    if not removeHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Failed to remove host")

    if not removeCluster(positive=True, cluster=config.CLUSTER_NAME):
        raise NetworkException("Failed to remove cluster")
