#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature Init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Network/3_6_Network_MAC_PoolRangePer_DC
"""

import logging
import config as conf
from rhevmtests.networking import network_cleanup
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Init")


def setup_package():
    """
    Network cleanup
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_1_NAME = conf.HOSTS[1]
    network_cleanup()
    conf.DEFAULT_MAC_POOL_VALUES = ll_mac_pool.get_mac_range_values(
        ll_mac_pool.get_mac_pool(pool_name=conf.DEFAULT_MAC_POOL)
    )

    if not hl_networks.create_basic_setup(
        datacenter=conf.EXT_DC_0, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION, cluster=conf.MAC_POOL_CL, cpu=conf.CPU_NAME
    ):
        raise conf.NET_EXCEPTION()

    if not ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME):
        raise conf.NET_EXCEPTION()

    if not ll_hosts.updateHost(
        positive=True, host=conf.HOST_1_NAME, cluster=conf.MAC_POOL_CL
    ):
        raise conf.NET_EXCEPTION()

    if not ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME):
        raise conf.NET_EXCEPTION()

    if not hl_storagedomains.addNFSDomain(
        host=conf.HOST_1_NAME, storage=conf.MP_STORAGE,
        data_center=conf.EXT_DC_0, path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
        address=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
    ):
        raise conf.NET_EXCEPTION()

    if not ll_vms.createVm(
        positive=True, vmName=conf.MP_VM, cluster=conf.MAC_POOL_CL,
        storageDomainName=conf.MP_STORAGE, size=conf.VM_DISK_SIZE
    ):
        raise conf.NET_EXCEPTION()

    if not ll_templates.createTemplate(
        positive=True, vm=conf.MP_VM, cluster=conf.MAC_POOL_CL,
        name=conf.MP_TEMPLATE
    ):
        raise conf.NET_EXCEPTION()


def teardown_package():
    """
    Remove extra DC, Cluster, Storage, VM and move the Host to original Cluster
    """
    ll_vms.removeVm(positive=True, vm=conf.MP_VM)
    ll_storagedomains.deactivate_master_storage_domain(
        positive=True, datacenter=conf.EXT_DC_0
    )

    ll_datacenters.remove_datacenter(positive=True, datacenter=conf.EXT_DC_0)
    hl_storagedomains.remove_storage_domain(
        name=conf.MP_STORAGE, datacenter=None, host=conf.HOST_1_NAME
    )

    ll_hosts.deactivateHost(positive=True, host=conf.HOST_1_NAME)
    ll_hosts.updateHost(
        positive=True, host=conf.HOST_1_NAME, cluster=conf.CLUSTER_NAME[0]
    )

    ll_hosts.activateHost(positive=True, host=conf.HOST_1_NAME)
    ll_clusters.removeCluster(positive=True, cluster=conf.MAC_POOL_CL)

    logger.info("Updating Default MAC pool range if needed")
    curr_mac_pool_values = ll_mac_pool.get_mac_range_values(
        ll_mac_pool.get_mac_pool(pool_name=conf.DEFAULT_MAC_POOL)
    )
    if not curr_mac_pool_values == conf.DEFAULT_MAC_POOL_VALUES:
        hl_mac_pool.update_default_mac_pool()
