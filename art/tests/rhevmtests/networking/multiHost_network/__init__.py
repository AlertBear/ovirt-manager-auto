#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MultiHost networking feature test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level import vms
import rhevmtests.networking.helper as net_help

logger = logging.getLogger("MultiHost_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    network_cleanup()
    logger.info(
        "Running on golden env, only starting VM %s at host %s",
        config.VM_NAME[0], config.HOSTS[0])

    if not net_help.run_vm_once_specific_host(
        vm=config.VM_NAME[0], host=config.HOSTS[0], wait_for_ip=True
    ):
        raise NetworkException(
            "Cannot start VM %s at host %s" %
            (config.VM_NAME[0], config.HOSTS[0])
        )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info(
        "Running on golden env, stopping VM %s", config.VM_NAME[0])
    if not vms.stopVm(True, vm=config.VM_NAME[0]):
        logger.error(
            "Failed to stop VM: %s", config.VM_NAME[0]
        )
