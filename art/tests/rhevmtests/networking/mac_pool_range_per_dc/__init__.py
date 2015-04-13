#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature Init
"""
import logging
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as exceptions
from rhevmtests.networking import network_cleanup, config

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Init")

LAST_HOST = config.HOSTS[-1]
EXT_DC_0 = config.EXTRA_DC[0]
MP_VM = config.MP_VM_NAMES[0]


def setup_package():
    """
    Prepare environment
    """

    network_cleanup()

    logger.info("Create new setup with DC, cluster and host")
    if not hl_networks.create_basic_setup(
        datacenter=EXT_DC_0, storage_type=config.STORAGE_TYPE,
        version=config.COMP_VERSION, cluster=config.MAC_POOL_CL,
        cpu=config.CPU_NAME
    ):
        raise exceptions.NetworkException("Failed to create setup")

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        LAST_HOST, EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=LAST_HOST):
        raise exceptions.NetworkException(
            "Cannot deactivate host %s" % LAST_HOST
        )
    if not ll_hosts.updateHost(
        positive=True, host=LAST_HOST, cluster=config.MAC_POOL_CL
    ):
        raise exceptions.NetworkException(
            "Cannot move host %s to Cluster %s" %
            (LAST_HOST, config.MAC_POOL_CL)
        )
    if not ll_hosts.activateHost(positive=True, host=LAST_HOST):
        raise exceptions.NetworkException(
            "Cannot activate host %s" % LAST_HOST
        )

    logger.info("Add a Storage Domain for the new setup")
    if not hl_storagedomains.addNFSDomain(
        host=LAST_HOST, storage="Stor", data_center=EXT_DC_0,
        address=config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
        path=config.UNUSED_DATA_DOMAIN_PATHS[0]
    ):
        raise exceptions.NetworkException("Couldn't add NFS storage Domain")

    logger.info("Create a new VM %s", MP_VM)
    if not ll_vms.addVm(positive=True, name=MP_VM, cluster=config.MAC_POOL_CL):
        raise exceptions.NetworkException("Failed to create VM: %s" % MP_VM)


def teardown_package():
    """
    Remove extra DC, Cluster, Storage, VM and move the Host to original Cluster
    """

    logger.info("Remove VM %s", MP_VM)
    if not ll_vms.removeVm(positive=True, vm=MP_VM):
        logger.error("Couldn't remove VM %s" % MP_VM)

    logger.info("Deactivate master Storage Domain on DC %s", EXT_DC_0)
    if not ll_storagedomains.deactivate_master_storage_domain(
        positive=True, datacenter=EXT_DC_0
    ):
        logger.error("Couldn't deactivate master storage Domain")

    logger.info("Remove DC %s", EXT_DC_0)
    if not ll_datacenters.removeDataCenter(positive=True, datacenter=EXT_DC_0):
        logger.error("Couldn't remove DC %s", EXT_DC_0)

    logger.info("Remove Storage Domain")
    hl_storagedomains.remove_storage_domain(
        name="Stor", datacenter=None, host=LAST_HOST
    )

    logger.info(
        "Deactivate host %s, move it to DC %s and reactivate it",
        LAST_HOST, EXT_DC_0
    )
    if not ll_hosts.deactivateHost(positive=True, host=LAST_HOST):
        logger.error("Cannot deactivate host %s", LAST_HOST)
    if not ll_hosts.updateHost(
        positive=True, host=LAST_HOST, cluster=config.CLUSTER_NAME[1]
    ):
        logger.error(
            "Cannot move host %s to Cluster %s",
            (LAST_HOST, config.CLUSTER_NAME[1])
        )
    if not ll_hosts.activateHost(positive=True, host=LAST_HOST):
        logger.error("Cannot activate host %s", LAST_HOST)

    logger.info("Remove Cluster %s", config.MAC_POOL_CL)
    if not ll_clusters.removeCluster(
        positive=True, cluster=config.MAC_POOL_CL
    ):
        logger.error("Couldn't remove Cluster %s", config.MAC_POOL_CL)
