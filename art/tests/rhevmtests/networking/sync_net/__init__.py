"""
Sync network feature test
"""

import logging
from rhevmtests import config
from art.rhevm_api.tests_lib.low_level.hosts import removeHost
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.datacenters import removeDataCenter
from art.rhevm_api.tests_lib.low_level.clusters import removeCluster
from art.rhevm_api.tests_lib.high_level.networks import create_basic_setup

logger = logging.getLogger("Sync")

#################################################


def setup_package():
    """
    Prepare environment
    """
    logger.info("Create setup with datacenter, cluster and host")
    for i in range(2):
        host = config.HOSTS[0] if i == 0 else None
        if not create_basic_setup(datacenter=config.DC_NAME[i],
                                  storage_type=config.STORAGE_TYPE,
                                  version=config.COMP_VERSION,
                                  cluster=config.CLUSTER_NAME[i],
                                  cpu=config.CPU_NAME, host=host,
                                  host_password=config.HOSTS_PW):
            raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Removing DC/Cluster and host")
    for i in range(2):
        if not removeDataCenter(positive=True, datacenter=config.DC_NAME[i]):
            raise NetworkException("Failed to remove datacenter")

        if i == 0:
            if not removeHost(positive=True, host=config.HOSTS[0],
                              deactivate=True):
                raise NetworkException("Failed to remove host")

        if not removeCluster(positive=True, cluster=config.CLUSTER_NAME[i]):
            raise NetworkException("Failed to remove cluster")
