"""
SLA test
"""

import logging

import art.rhevm_api.tests_lib.low_level.datacenters as datacenters_l
import art.rhevm_api.tests_lib.high_level.datacenters as datacenters_h
import art.rhevm_api.tests_lib.low_level.hosts as hosts_l
import art.rhevm_api.tests_lib.low_level.storagedomains as storage
import art.rhevm_api.tests_lib.low_level.clusters as clusters_l

import art.test_handler.exceptions as errors
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger("SLA")

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    import config
    if not (datacenters_l.addDataCenter(positive=True,
                                        name=config.DC_name,
                                        storage_type=config.STORAGE_TYPE,
                                        version=config.version)):
        raise errors.DataCenterException("Cannot add data center")
    if not (clusters_l.addCluster(positive=True,
                                  name=config.cluster_name,
                                  cpu=config.cpu_name,
                                  data_center=config.DC_name,
                                  version=config.version)):
        raise errors.ClusterException("Cannot add cluster")
    if not (hosts_l.addHost(positive=True,
                            name=config.hosts[0],
                            root_password=config.hosts_pw[0],
                            cluster=config.cluster_name,
                            wait=True)):
        raise errors.HostException("Cannot add host")
    if not (storage.addStorageDomain(positive=True,
                                     name=config.data_name,
                                     type=ENUMS['storage_dom_type_data'],
                                     storage_type=config.STORAGE_TYPE,
                                     host=config.hosts[0],
                                     address=config.data_addresses[0],
                                     path=config.data_paths[0])):
        raise errors.StorageDomainException("Cannot add domain")
    if not (storage.attachStorageDomain(positive=True,
                                        datacenter=config.DC_name,
                                        storagedomain=config.data_name)):
        raise errors.StorageDomainException("Cannot attach "
                                            "domain to data center")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not (storage.deactivateStorageDomain(positive=True,
                                            datacenter=config.DC_name,
                                            storagedomain=config.data_name,
                                            wait=True)):
        raise errors.StorageDomainException("Cannot deactivate storage domain")
    if not (datacenters_l.removeDataCenter(positive=True,
                                           datacenter=config.DC_name)):
        raise errors.DataCenterException("Cannot remove data center")
    if not (storage.removeStorageDomain(positive=True,
                                        storagedomain=config.data_name,
                                        host=config.hosts[0],
                                        format="True")):
        raise errors.StorageDomainException("Cannot remove storage domain")
    if not (hosts_l.deactivateHost(positive=True,
                                   host=config.hosts[0])):
        raise errors.HostException("Cannot set host to maintenance")
    if not (hosts_l.removeHost(positive=True,
                               host=config.hosts[0])):
        raise errors.HostException("Cannot remove host")
    if not (clusters_l.removeCluster(positive=True,
                                     cluster=config.cluster_name)):
        raise errors.ClusterException("Cannot remove cluster")
