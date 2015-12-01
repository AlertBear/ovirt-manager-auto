#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature Init
"""
import config as c
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from rhevmtests.networking import network_cleanup

import logging
logger = logging.getLogger("MAC_Pool_Range_Per_DC_Init")


def setup_package():
    """
    Prepare environment
    """
    network_cleanup()

    logger.info("Create new setup with DC, cluster and host")
    if not hl_networks.create_basic_setup(
        datacenter=c.EXT_DC_0, storage_type=c.STORAGE_TYPE,
        version=c.COMP_VERSION, cluster=c.MAC_POOL_CL,
        cpu=c.CPU_NAME
    ):
        raise c.NET_EXCEPTION("Failed to create setup")

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        c.LAST_HOST, c.EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=c.LAST_HOST):
        raise c.NET_EXCEPTION("Cannot deactivate host %s" % c.LAST_HOST)
    if not ll_hosts.updateHost(
        positive=True, host=c.LAST_HOST, cluster=c.MAC_POOL_CL
    ):
        raise c.NET_EXCEPTION(
            "Cannot move host %s to Cluster %s" % (c.LAST_HOST, c.MAC_POOL_CL)
        )
    if not ll_hosts.activateHost(positive=True, host=c.LAST_HOST):
        raise c.NET_EXCEPTION("Cannot activate host %s" % c.LAST_HOST)

    logger.info("Add a Storage Domain for the new setup")
    if not hl_storagedomains.addNFSDomain(
        host=c.LAST_HOST, storage="Stor", data_center=c.EXT_DC_0,
        address=c.UNUSED_DATA_DOMAIN_ADDRESSES[0],
        path=c.UNUSED_DATA_DOMAIN_PATHS[0]
    ):
        raise c.NET_EXCEPTION("Couldn't add NFS storage Domain")

    logger.info("Create a new VM %s", c.MP_VM)
    if not ll_vms.addVm(
        positive=True, name=c.MP_VM, cluster=c.MAC_POOL_CL,
        display_type=c.VM_DISPLAY_TYPE
    ):
        raise c.NET_EXCEPTION("Failed to create VM: %s" % c.MP_VM)


def teardown_package():
    """
    Remove extra DC, Cluster, Storage, VM and move the Host to original Cluster
    """
    logger.info("Remove VM %s", c.MP_VM)
    if not ll_vms.removeVm(positive=True, vm=c.MP_VM):
        logger.error("Couldn't remove VM %s" % c.MP_VM)

    logger.info("Deactivate master Storage Domain on DC %s", c.EXT_DC_0)
    if not ll_storagedomains.deactivate_master_storage_domain(
        positive=True, datacenter=c.EXT_DC_0
    ):
        logger.error("Couldn't deactivate master storage Domain")

    logger.info("Remove DC %s", c.EXT_DC_0)
    if not ll_datacenters.removeDataCenter(
        positive=True, datacenter=c.EXT_DC_0
    ):
        logger.error("Couldn't remove DC %s", c.EXT_DC_0)

    logger.info("Remove Storage Domain")
    hl_storagedomains.remove_storage_domain(
        name="Stor", datacenter=None, host=c.LAST_HOST
    )

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        c.LAST_HOST, c.EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=c.LAST_HOST):
        logger.error("Cannot deactivate host %s", c.LAST_HOST)
    if not ll_hosts.updateHost(
        positive=True, host=c.LAST_HOST, cluster=c.CLUSTER_NAME[1]
    ):
        logger.error(
            "Cannot move host %s to Cluster %s", (
                c.LAST_HOST, c.CLUSTER_NAME[1]
            )
        )
    if not ll_hosts.activateHost(positive=True, host=c.LAST_HOST):
        logger.error("Cannot activate host %s", c.LAST_HOST)

    logger.info("Remove Cluster %s", c.MAC_POOL_CL)
    if not ll_clusters.removeCluster(positive=True, cluster=c.MAC_POOL_CL):
        logger.error("Couldn't remove Cluster %s", c.MAC_POOL_CL)
