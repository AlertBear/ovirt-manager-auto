"""
High-level functions above data-center
"""

import logging

import art.rhevm_api.tests_lib.low_level.clusters as clusters
import art.rhevm_api.tests_lib.low_level.datacenters as datacenters
import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.storagedomains as storagedomains
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts

LOGGER = logging.getLogger(__name__)
ENUMS = opts['elements_conf']['RHEVM Enums']


def build_setup(config, storage, storage_type, basename="testname",
                local=False):
    """
    Description: Creates a setup based on what's specified in the config
    Parameters:
        * config - dict containing setup specification ([PARAMETERS] section)
        * storage - dict containing storage specification ([{storage}] section)
        * storage_type - type of storage to use (NFS, ISCSI, FCP, LOCALFS)
        * basename - baseword for naming objects in setup
    Returns names of created storage domains
    """
    datacenter_name = config.get('dc_name', 'datacenter_%s' % basename)
    cluster_name = config.get('cluster_name', 'cluster_%s' % basename)
    config['dc_name'] = datacenter_name
    config['cluster_name'] = cluster_name

    if not datacenters.addDataCenter(True, name=datacenter_name,
                                     storage_type=storage_type, local=local,
                                     version=config['compatibility_version']):
        raise errors.DataCenterException("addDataCenter %s with storage type "
                                         "%s and version %s failed." %
                                         (datacenter_name, storage_type,
                                         config['compatibility_version']))
    LOGGER.info("Datacenter %s was created successfully", datacenter_name)

    if not clusters.addCluster(True, name=cluster_name,
                               cpu=config['cpu_name'],
                               data_center=datacenter_name,
                               version=config['compatibility_version']):
        raise errors.ClusterException("addCluster %s with cpu_type %s and "
                                      "version %s to datacenter %s failed" %
                                      (cluster_name, config['cpu_name'],
                                      config['compatibility_version'],
                                      datacenter_name))
    LOGGER.info("Cluster %s was created successfully", cluster_name)

    hosts.add_hosts(config.as_list('vds'), config.as_list('vds_password'),
                    cluster_name)

    return storagedomains.create_storages(
        storage, storage_type, config.as_list('vds')[0], datacenter_name)
