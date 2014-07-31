"""
IO feature test
"""
import logging
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.high_level.networks import create_basic_setup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.datacenters import removeDataCenter
from art.rhevm_api.tests_lib.low_level.clusters import removeCluster
from art.rhevm_api.tests_lib.low_level.hosts import removeHost

logger = logging.getLogger("IO_test")
#################################################


def setup_package():
    """
    Prepare environment:
    create 1 Data Center
    create 1 Cluster
    add 1 Host
    """
    logger.info("Create setup with datacenter, cluster and host")
    if not create_basic_setup(datacenter=config.DC_NAME[0],
                              storage_type=config.STORAGE_TYPE,
                              version=config.COMP_VERSION,
                              cluster=config.CLUSTER_NAME[0],
                              cpu=config.CPU_NAME, host=config.HOSTS[0],
                              host_password=config.HOSTS_PW):
        raise NetworkException("Failed to create setup")


def teardown_package():
    """
    Cleans environment by removing Host, Cluster and DC from the setup
    """
    if not removeHost(positive=True, host=config.HOSTS[0],
                      deactivate=True):
        raise NetworkException("Cannot remove host %s from Cluster %s" %
                               (config.HOSTS[0], config.CLUSTER_NAME[0]))

    if not removeCluster(positive=True, cluster=config.CLUSTER_NAME[0]):
        raise NetworkException("Cannot remove Cluster %s" %
                               config.CLUSTER_NAME[0])

    if not removeDataCenter(positive=True, datacenter=config.DC_NAME[0]):
        raise NetworkException("Cannot remove DC %s" % config.DC_NAME[0])
