#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics
"""

import config as c
import logging
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking as network

logger = logging.getLogger("Cumulative_RX_TX_Statistics_Init")


def setup_package():
    """
    Create and attach sw1 to DC/CL/Host
    """
    network.network_cleanup()
    add_net_dict = {
        c.NET_0: {
            "required": "false"
        }
    }
    sn_dict = {
        "add": {
            "1": {
                "network": c.NET_0,
                "nic": None
            }
        }
    }
    logger.info("Create and attach %s to DC/Cluster", c.NET_0)
    if not hl_networks.createAndAttachNetworkSN(
        data_center=c.DC_0, cluster=c.CLUSTER_NAME[0],
        network_dict=add_net_dict
    ):
        raise c.NET_EXCEPTION(
            "Failed to create and attach %s to DC/Cluster" % c.NET_0
        )
    logger.info("Attaching %s to %s via SN", c.NET_0, c.HOSTS[0])
    for i in range(2):
        sn_dict["add"]["1"]["nic"] = c.VDS_HOSTS[i].nics[1]
        if not hl_host_network.setup_networks(host_name=c.HOSTS[i], **sn_dict):
            raise c.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" % (c.NET_0, c.HOSTS[i])
            )


def teardown_package():
    """
    1. Stop VM
    2. Remove sw1 from DC/CL/Host
    """
    logger.info("Stopping VMS: %s", c.VM_NAME[:2])
    if not ll_vms.stopVms(c.VM_NAME[:2]):
        logger.error("Failed to stop VMS: %s", c.VM_NAME[:2])

    for i in range(2):
        logger.info("Cleaning %s interfaces", c.HOSTS[i])
        if not hl_host_network.clean_host_interfaces(c.HOSTS[i]):
            logger.error("Failed to remove %s from %s", c.NET_0, c.HOSTS[i])

    logger.info("Removing all networks from %s", c.DC_0)
    if not hl_networks.remove_all_networks(
        datacenter=c.DC_0, mgmt_network=c.MGMT_BRIDGE
    ):
        logger.error("Failed to remove all networks from %s", c.DC_0)
