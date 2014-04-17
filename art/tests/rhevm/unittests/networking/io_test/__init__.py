"""
IO feature test
"""

from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter
from art.rhevm_api.tests_lib.low_level.clusters import addCluster,\
    removeCluster
from art.rhevm_api.tests_lib.low_level.hosts import addHost, deactivateHost,\
    removeHost
#################################################


def setup_package():
    """
    Prepare environment:
    create 1 Data Center
    create 1 Cluster
    add 1 Host
    """
    import config

    if not addDataCenter(positive=True, name=config.DC_NAME,
                         storage_type=config.STORAGE_TYPE,
                         version=config.VERSION, local=False):
        raise NetworkException("Cannot create DC %s" % config.DC_NAME)

    if not addCluster(positive=True, name=config.CLUSTER_NAME,
                      data_center=config.DC_NAME, version=config.VERSION,
                      cpu=config.CPU_NAME):
        raise NetworkException("Cannot create Cluster %s" %
                               config.CLUSTER_NAME)

    if not addHost(positive=True,
                   name=config.HOSTS[0],
                   root_password=config.HOSTS_PW,
                   cluster=config.CLUSTER_NAME):
        raise NetworkException("Cannot add host %s to Cluster %s" %
                               (config.HOSTS[0], config.CLUSTER_NAME))


def teardown_package():
    """
    Cleans environment by removing Host, Cluster and DC from the setup
    """
    import config

    if not deactivateHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Cannot switch host %s to maintenance" %
                               config.HOSTS[0])

    if not removeHost(positive=True, host=config.HOSTS[0]):
        raise NetworkException("Cannot remove host %s from Cluster %s" %
                               (config.HOSTS[0], config.CLUSTER_NAME))

    if not removeCluster(positive=True, cluster=config.CLUSTER_NAME):
        raise NetworkException("Cannot remove Cluster %s" %
                               config.CLUSTER_NAME)

    if not removeDataCenter(positive=True, datacenter=config.DC_NAME):
        raise NetworkException("Cannot remove DC %s" % config.DC_NAME)
