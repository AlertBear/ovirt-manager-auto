#!/usr/bin/env python
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from rhevmtests.system.user_roles_tests import config
from art.rhevm_api.tests_lib.low_level import (
    storagedomains, clusters, datacenters, hosts
)


def setup_package():
    """ Prepare environment """
    if not config.GOLDEN_ENV:
        assert datacenters.addDataCenter(
            True,
            name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION,
        )
        assert clusters.addCluster(
            True,
            name=config.CLUSTER_NAME[0],
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME[0],
            version=config.COMP_VERSION,
        )
        assert hosts.addHost(
            True,
            config.HOSTS[0],
            root_password=config.HOSTS_PW,
            address=config.HOSTS_IP[0],
            cluster=config.CLUSTER_NAME[0],
        )
        assert h_sd.addNFSDomain(
            config.HOSTS[0],
            config.STORAGE_NAME[0],
            config.DC_NAME[0],
            config.ADDRESS[0],
            config.PATH[0],
        )

    config.MASTER_STORAGE = storagedomains.get_master_storage_domain_name(
        config.DC_NAME[0]
    )
    if config.GOLDEN_ENV:
        config.STORAGE_NAME = storagedomains.getStorageDomainNamesForType(
            config.DC_NAME[0],
            config.STORAGE_TYPE_NFS,
        )
    else:
        config.STORAGE_NAME = [config.MASTER_STORAGE, 'nfs_1']


def teardown_package():
    """ Clean environment """
    if not config.GOLDEN_ENV:
        storagedomains.cleanDataCenter(True, config.MAIN_DC_NAME)
