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
from art.rhevm_api.tests_lib.low_level.networks import updateNetwork, \
    isVmNetwork
from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.exceptions import NetworkException
logger = logging.getLogger("Bridgeless_Network")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    logging.info("Add datacenter")
    if not addDataCenter(positive=True, name=config.DC_NAME,
                         storage_type=config.STORAGE_TYPE,
                         version=config.VERSION):
        raise NetworkException("Fail to add datacenter")

    logger.info("Add cluster")
    if not addCluster(positive=True, name=config.CLUSTER_NAME,
                      cpu=config.CPU_NAME, data_center=config.DC_NAME,
                      version=config.VERSION):
        raise NetworkException("Fail to add Cluster")

    logger.info("Add host")
    if not addHost(positive=True, name=config.HOSTS[0],
                   root_password=config.HOSTS_PW, cluster=config.CLUSTER_NAME):
        raise NetworkException("Fail to add host")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Remove DC/Cluster and host")
    if not removeDataCenter(positive=True, datacenter=config.DC_NAME):
        raise NetworkException("Fail to remove datacenter")

    if not deactivateHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Fail to set host to maintenance")

    if not removeHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Fail to remove host")

    if not removeCluster(positive=True, cluster=config.CLUSTER_NAME):
        raise NetworkException("Fail to remove cluster")
