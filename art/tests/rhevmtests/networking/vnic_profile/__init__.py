#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
VNIC profile feature test
"""

import logging
import rhevmtests.networking as networking
import rhevmtests.networking.config as config
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as net_help
logger = logging.getLogger("VNIC_Profile_Init")

#################################################


def setup_package():
    """
    Running cleanup and starting vm
    """
    networking.network_cleanup()
    logger.info(
        "Starting VM %s on host %s",
        config.VM_NAME[0], config.HOSTS[0]
    )

    if not net_help.run_vm_once_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0], wait_for_ip=True
    ):
        raise exceptions.NetworkException(
            "Cannot start VM %s on host %s" %
            (config.VM_NAME[0], config.HOSTS[0])
        )


def teardown_package():
    """
    Stopping vm
    """
    logger.info("Stopping VM %s", config.VM_NAME[0])
    if not ll_vms.stopVm(True, vm=config.VM_NAME[0]):
        logger.error("Failed to stop VM: %s", config.VM_NAME[0])
