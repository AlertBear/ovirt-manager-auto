# coding=utf-8
"""
network team init file
"""
import logging
from art.rhevm_api.tests_lib.high_level.networks import (
    remove_all_networks, createAndAttachNetworkSN,
    ENUMS
)
from art.rhevm_api.tests_lib.low_level.networks import remove_label
from art.rhevm_api.tests_lib.low_level.vms import get_vm_state
import config
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from art.rhevm_api.tests_lib.low_level.vms import stopVm

logger = logging.getLogger("GE_Network_clean")


def teardown_package():
    """
    Cleans GE after Network jobs
    """
    if config.GOLDEN_ENV:
        logger.info("Setting hosts UP if needed")
        for host in config.HOSTS:
            if not activate_host_if_not_up(host):
                logger.error("Failed to activate host: %s", host)

        logger.info("Removing all networks")
        for dc in config.DC_NAME:
            if not remove_all_networks(dc):
                logger.error("Failed to remove networks from DC: %s", dc)

        logger.info("Clean hosts interfaces")
        if not createAndAttachNetworkSN(
                host=config.VDS_HOSTS, network_dict={}, auto_nics=[0]
        ):
            logger.error("Failed to clean hosts interfaces")

        logger.info("Stop all Vms if needed")
        for vm in config.VM_NAME:
            if get_vm_state(vm) != ENUMS["vm_state_down"]:
                if not stopVm(True, vm):
                    logger.error("Failed to stop VM: %s", vm)

        logger.info("Clean all host interfaces from the labels")
        if not remove_label(host_nic_dict={
            config.HOSTS[0]: config.VDS_HOSTS[0].nics,
            config.HOSTS[1]: config.VDS_HOSTS[1].nics
        }):
            logger.error("Couldn't remove labels from Hosts")
