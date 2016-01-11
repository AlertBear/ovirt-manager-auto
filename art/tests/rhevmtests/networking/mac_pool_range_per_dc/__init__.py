#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature Init
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
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Init")


def setup_package():
    """
    Prepare environment
    """
    network_cleanup()

    conf.DEFAULT_MAC_POOL_VALUES = ll_mac_pool.get_mac_range_values(
        ll_mac_pool.get_mac_pool(pool_name=conf.DEFAULT_MAC_POOL)
    )
    conf.LAST_HOST = conf.HOSTS[-1]
    logger.info("Create new setup with DC, cluster and host")
    if not hl_networks.create_basic_setup(
        datacenter=conf.EXT_DC_0, storage_type=conf.STORAGE_TYPE,
        version=conf.COMP_VERSION, cluster=conf.MAC_POOL_CL,
        cpu=conf.CPU_NAME
    ):
        raise conf.NET_EXCEPTION("Failed to create setup")

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        conf.LAST_HOST, conf.EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=conf.LAST_HOST):
        raise conf.NET_EXCEPTION("Cannot deactivate host %s" % conf.LAST_HOST)
    if not ll_hosts.updateHost(
        positive=True, host=conf.LAST_HOST, cluster=conf.MAC_POOL_CL
    ):
        raise conf.NET_EXCEPTION(
            "Cannot move host %s to Cluster %s" %
            (conf.LAST_HOST, conf.MAC_POOL_CL)
        )
    if not ll_hosts.activateHost(positive=True, host=conf.LAST_HOST):
        raise conf.NET_EXCEPTION("Cannot activate host %s" % conf.LAST_HOST)

    logger.info("Add a Storage Domain for the new setup")
    if not hl_storagedomains.addNFSDomain(
        host=conf.LAST_HOST, storage="Stor", data_center=conf.EXT_DC_0,
        address=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0],
        path=conf.UNUSED_DATA_DOMAIN_PATHS[0]
    ):
        raise conf.NET_EXCEPTION("Couldn't add NFS storage Domain")

    logger.info("Create a new VM %s", conf.MP_VM)
    if not ll_vms.addVm(
        positive=True, name=conf.MP_VM, cluster=conf.MAC_POOL_CL,
        display_type=conf.VM_DISPLAY_TYPE
    ):
        raise conf.NET_EXCEPTION("Failed to create VM: %s" % conf.MP_VM)


def teardown_package():
    """
    Remove extra DC, Cluster, Storage, VM and move the Host to original Cluster
    """
    logger.info("Remove VM %s", conf.MP_VM)
    if not ll_vms.removeVm(positive=True, vm=conf.MP_VM):
        logger.error("Couldn't remove VM %s" % conf.MP_VM)

    logger.info("Deactivate master Storage Domain on DC %s", conf.EXT_DC_0)
    if not ll_storagedomains.deactivate_master_storage_domain(
        positive=True, datacenter=conf.EXT_DC_0
    ):
        logger.error("Couldn't deactivate master storage Domain")

    logger.info("Remove DC %s", conf.EXT_DC_0)
    if not ll_datacenters.removeDataCenter(
        positive=True, datacenter=conf.EXT_DC_0
    ):
        logger.error("Couldn't remove DC %s", conf.EXT_DC_0)

    logger.info("Remove Storage Domain")
    hl_storagedomains.remove_storage_domain(
        name="Stor", datacenter=None, host=conf.LAST_HOST
    )

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        conf.LAST_HOST, conf.EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=conf.LAST_HOST):
        logger.error("Cannot deactivate host %s", conf.LAST_HOST)
    if not ll_hosts.updateHost(
        positive=True, host=conf.LAST_HOST, cluster=conf.CLUSTER_NAME[1]
    ):
        logger.error(
            "Cannot move host %s to Cluster %s", (
                conf.LAST_HOST, conf.CLUSTER_NAME[1]
            )
        )
    if not ll_hosts.activateHost(positive=True, host=conf.LAST_HOST):
        logger.error("Cannot activate host %s", conf.LAST_HOST)

    logger.info("Remove Cluster %s", conf.MAC_POOL_CL)
    if not ll_clusters.removeCluster(positive=True, cluster=conf.MAC_POOL_CL):
        logger.error("Couldn't remove Cluster %s", conf.MAC_POOL_CL)

    logger.info("Updating Default MAC pool range if needed")
    curr_mac_pool_values = ll_mac_pool.get_mac_range_values(
        ll_mac_pool.get_mac_pool(pool_name=conf.DEFAULT_MAC_POOL)
    )
    if not curr_mac_pool_values == conf.DEFAULT_MAC_POOL_VALUES:
        hl_mac_pool.update_default_mac_pool()
