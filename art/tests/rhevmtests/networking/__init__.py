# coding=utf-8
"""
network team init file
"""
import logging
from art.rhevm_api.tests_lib.high_level.networks import (
    remove_all_networks, createAndAttachNetworkSN,
    ENUMS)
from art.rhevm_api.tests_lib.low_level.vms import get_vm_state
from art.rhevm_api.utils.test_utils import (
    engine_set_mac_range,
    engine_get_mac_range
)
from art.test_handler.exceptions import NetworkException
import config
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from art.rhevm_api.tests_lib.low_level.vms import stopVm
logger = logging.getLogger("GE_Network_clean")

DEFAULT_GE_MAC_RANGE = engine_get_mac_range(config.VDC_HOST,
                                            config.VDC_ROOT_USER,
                                            config.VDC_ROOT_PASSWORD)


def setup_package():
    """
    Prepare GE environment for network jobs
    """
    if config.GOLDEN_ENV:
        logger.info("Setting network MAC range")
        if not engine_set_mac_range(config.VDC_HOST, config.VDC_ROOT_USER,
                                    config.VDC_ROOT_PASSWORD,
                                    config.NETWORK_GE_MAC_RANGE):
            raise NetworkException("Fail to set network MAC range")


def teardown_package():
    """
    Cleans GE environment after Network jobs
    """
    if config.GOLDEN_ENV:
        logger.info("Setting hosts UP if needed")
        for host in config.HOSTS:
            if not activate_host_if_not_up(host):
                raise NetworkException("Fail to activate host: %s" % host)

        logger.info("Removing all networks")
        for dc in config.DC_NAME:
            if not remove_all_networks(dc):
                raise NetworkException("Fail to remove networks from DC: %s"
                                       % dc)

        logger.info("Clean hosts interfaces")
        if not createAndAttachNetworkSN(host=config.HOSTS, network_dict={},
                                        auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Fail to clean hosts interfaces")

        logger.info("Stop all Vms if needed")
        for vm in config.VM_NAME:
            if get_vm_state(vm) != ENUMS["vm_state_down"]:
                if not stopVm(True, vm):
                    raise NetworkException("Fail to stop VM: %s" % vm)

        logger.info("Setting back GE MAC range")
        if not engine_set_mac_range(config.VDC_HOST,
                                    config.VDC_ROOT_USER,
                                    config.VDC_ROOT_PASSWORD,
                                    DEFAULT_GE_MAC_RANGE):
            raise NetworkException("Fail to set network MAC range")
