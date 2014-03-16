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

    logger.info("Updating mgmt_net to Non-VM network")
    if not updateNetwork(positive=True, network=config.MGMT_BRIDGE,
                         data_center=config.DC_NAME, usages=""):
        raise NetworkException("Fail to set mgmt_net as Non-VM network")

    logger.info("Check that mgmt_net is Non-VM network")
    sample = TimeoutingSampler(timeout=60, sleep=1,
                               func=isVmNetwork, host=config.HOSTS[0],
                               user=config.HOSTS_USER,
                               password=config.HOSTS_PW,
                               net_name=config.MGMT_BRIDGE, conn_timeout=200)

    if not sample.waitForFuncStatus(result=False):
        raise NetworkException("mgmt_net is not Non-VM network")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Updating mgmt_net to VM network")
    if not updateNetwork(positive=True, network=config.MGMT_BRIDGE,
                         data_center=config.DC_NAME, usages="vm"):
        raise NetworkException("Fail to set mgmt_net as VM network")

    logger.info("Check that mgmt_net is VM network")
    sample = TimeoutingSampler(timeout=60, sleep=1,
                               func=isVmNetwork, host=config.HOSTS[0],
                               user=config.HOSTS_USER,
                               password=config.HOSTS_PW,
                               net_name=config.MGMT_BRIDGE, conn_timeout=200)

    if not sample.waitForFuncStatus(result=True):
        raise NetworkException("mgmt_net is not VM network")

    logger.info("Remove DC/Cluster and host")
    if not removeDataCenter(positive=True, datacenter=config.DC_NAME):
        raise NetworkException("Fail to remove datacenter")

    if not deactivateHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Fail to set host to maintenance")

    if not removeHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Fail to remove host")

    if not removeCluster(positive=True, cluster=config.CLUSTER_NAME):
        raise NetworkException("Fail to remove cluster")
