#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Jumbo Frames init
"""

import logging
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as net_help
import art.test_handler.exceptions as exceptions

logger = logging.getLogger("Jumbo_frame_Init")


def setup_package():
    """
    Prepare environment
    Running cleanup an start vms
    """

    networking.network_cleanup()

    for i in range(2):
        logger.info(
            "Starting up VM %s on host %s", config.VM_NAME[i],
            config.HOSTS[i]
        )
        if not net_help.run_vm_once_specific_host(
                vm=config.VM_NAME[i], host=config.HOSTS[i]
        ):
            raise exceptions.NetworkException(
                "Cannot start VM %s on host %s" % (
                    config.VM_NAME[i], config.HOSTS[i]
                )
            )

    logger.info("Getting VMs IPs")
    for i in range(2):
        config.VM_IP_LIST.append(
            ll_vms.waitForIP(config.VM_NAME[i])[1]["ip"]
        )


def teardown_package():
    """
    Cleans the environment
    """
    local_dict = {
        config.NETWORKS[0]: {
            "mtu": config.MTU[3],
            "nic": 1,
            "required": "false"
        },
        config.NETWORKS[1]: {
            "mtu": config.MTU[3],
            "nic": 2,
            "required": "false"
        },
        config.NETWORKS[2]: {
            "mtu": config.MTU[3],
            "nic": 3,
            "required": "false"
        }
    }

    logger.info(
        "Setting all hosts NICs to MTU: %s", config.MTU[3]
    )
    if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
    ):
        logger.error(
            "Cannot set MTU %s on %s", config.MTU[3], config.VDS_HOSTS[:2]
        )

    logger.info("Cleaning hosts interface")
    if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[:2], network_dict={}, auto_nics=[0]
    ):
        logger.error("Failed to Clean hosts interfaces")

    logger.info(
        "Stopping VMs: %s, %s",
        config.VM_NAME[0], config.VM_NAME[1]
    )
    if not ll_vms.stopVms(vms=[config.VM_NAME[0], config.VM_NAME[1]]):
        logger.error(
            "Failed to stop VMs: %s %s",
            config.VM_NAME[0], config.VM_NAME[1]
        )
    if not hl_networks.remove_net_from_setup(
            host=config.VDS_HOSTS[:2], auto_nics=[0],
            data_center=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            all_net=True
    ):
        logger.error("Cannot remove networks from setup")
