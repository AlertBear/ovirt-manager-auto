#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Linking feature test
"""

import logging
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.helper as net_help

logger = logging.getLogger("Linking_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    local_dict = {
        config.VLAN_NETWORKS[0]: {
            "vlan_id": config.VLAN_ID[0], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[1]: {
            "vlan_id": config.VLAN_ID[1], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[2]: {
            "vlan_id": config.VLAN_ID[2], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[3]: {
            "vlan_id": config.VLAN_ID[3], "nic": 1, "required": "false"
        },
        config.VLAN_NETWORKS[4]: {
            "vlan_id": config.VLAN_ID[4], "nic": 1, "required": "false"
        }
    }

    networking.network_cleanup()
    logger.info(
        "Start VM %s on host %s", config.VM_NAME[0], config.HOSTS[0]
    )

    if not net_help.run_vm_once_specific_host(
        vm=config.VM_NAME[0], host=config.HOSTS[0], wait_for_up_status=True
    ):
        raise exceptions.NetworkException(
            "Cannot start VM %s at host %s" %
            (config.VM_NAME[0], config.HOSTS[0])
        )

    if not hl_networks.createAndAttachNetworkSN(
        data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
        host=config.VDS_HOSTS[0], network_dict=local_dict,
        auto_nics=[0, 1]
    ):
        raise exceptions.NetworkException("Cannot create and attach networks")


def teardown_package():
    """
    Cleans the environment
    """

    logger.info("Stop VM %s and remove VLAN networks", config.VM_NAME[0])
    if not ll_vms.stopVm(True, vm=config.VM_NAME[0]):
        logger.error("Failed to stop VM: %s", config.VM_NAME[0])

    if not hl_networks.remove_net_from_setup(
        host=config.HOSTS[0], data_center=config.DC_NAME[0], all_net=True,
        mgmt_network=config.MGMT_BRIDGE
    ):
        logger.error("Failed to remove all networks beside MGMT")
