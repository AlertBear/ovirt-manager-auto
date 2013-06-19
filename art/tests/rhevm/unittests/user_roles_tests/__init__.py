#!/usr/bin/env python

"""
User level tests
"""

from art.rhevm_api.tests_lib.high_level import storagedomains as h_storagedomains
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts

def setup_package():
    """ Prepare environment """
    import config
    assert datacenters.addDataCenter(True, name=config.MAIN_DC_NAME,
                                     storage_type=config.MAIN_STORAGE_TYPE,
                                     version=config.PARAMETERS.get('compatibility_version'))
    assert clusters.addCluster(True, name=config.MAIN_CLUSTER_NAME,
                               cpu=config.PARAMETERS.get('cpu_name'),
                               data_center=config.MAIN_DC_NAME,
                               version=config.PARAMETERS.get('compatibility_version'))
    assert hosts.addHost(True, config.MAIN_HOST_NAME, root_password=config.HOST_ROOT_PASSWORD,
                         address=config.HOST_ADDRESS, cluster=config.MAIN_CLUSTER_NAME)
    assert h_storagedomains.addNFSDomain(config.MAIN_HOST_NAME, config.MAIN_STORAGE_NAME,
                                         config.MAIN_DC_NAME, config.NFS_STORAGE_ADDRESS,
                                         config.NFS_STORAGE_PATH)

def teardown_package():
    """ Clean environment """
    import config
    storagedomains.cleanDataCenter(True, config.MAIN_DC_NAME)