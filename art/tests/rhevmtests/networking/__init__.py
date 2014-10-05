# coding=utf-8
"""
network team init file
"""
import logging
from art.rhevm_api.tests_lib.high_level.networks import (
    remove_all_networks, createAndAttachNetworkSN,
    ENUMS
)
from art.rhevm_api.tests_lib.low_level.vms import get_vm_state
from art.test_handler.exceptions import NetworkException
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
                raise NetworkException("Failed to activate host: %s" % host)

        logger.info("Removing all networks")
        for dc in config.DC_NAME:
            if not remove_all_networks(dc):
                raise NetworkException("Failed to remove networks from DC: %s"
                                       % dc)

        logger.info("Clean hosts interfaces")
        if not createAndAttachNetworkSN(host=config.HOSTS, network_dict={},
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Failed to clean hosts interfaces")

        logger.info("Stop all Vms if needed")
        for vm in config.VM_NAME:
            if get_vm_state(vm) != ENUMS["vm_state_down"]:
                if not stopVm(True, vm):
                    raise NetworkException("Failed to stop VM: %s" % vm)
