"""
High-level functions above data-center
"""

import logging

import art.rhevm_api.tests_lib.low_level.clusters as clusters
import art.rhevm_api.tests_lib.low_level.datacenters as datacenters
import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.storagedomains as storagedomains
from art.rhevm_api.tests_lib.low_level.disks import getStorageDomainDisks,\
    deleteDisk
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.storagedomains import getDCStorages
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
    datacenter_name = config.get('DC_NAME', 'datacenter_%s' % basename)
    cluster_name = config.get('CLUSTER_NAME', 'cluster_%s' % basename)
    config['DC_NAME'] = datacenter_name
    config['CLUSTER_NAME'] = cluster_name

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


def clean_all_disks_from_dc(datacenter, exception_list=None):
    """
    Description: Removes all disks in DC's storage domain. If exception_list
    is given, the disks names in that list will remain in the setup
    Author: ratamir
    Parameters:
    * datacenter - data center name
    * exception_list - List of disks names that should remain in the setup
    """
    sdObjList = getDCStorages(datacenter, False)

    for storage_domain in sdObjList:
        LOGGER.info('Find any floating disks in storage domain %s',
                    storage_domain.get_name())
        floating_disks = getStorageDomainDisks(storage_domain.get_name(),
                                               False)
        if floating_disks:
            floating_disks_list = [disk.get_id() for disk in
                                   floating_disks if
                                   (disk.get_alias() not in exception_list)]
            for disk in floating_disks_list:
                LOGGER.info('Removing floating disk %s', disk)
                if not deleteDisk(True, alias=disk, async=False, disk_id=disk):
                    return False
            LOGGER.info('Ensuring all disks are removed')
            wait_for_jobs()
            LOGGER.info('All floating disks removed successfully')
        else:
            LOGGER.info('No floating disks found in storage domain %s',
                        storage_domain.get_name())