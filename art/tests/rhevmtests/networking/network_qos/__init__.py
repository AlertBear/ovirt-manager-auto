#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Network QOS feature init
"""

import logging
from rhevmtests import networking
from rhevmtests.networking import config
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger("Network_VNIC_QoS_Init")

#################################################


def setup_package():
    """
    Running cleanup and starting vm
    """
    config.VDS_HOST = config.VDS_HOSTS[0]
    config.HOST = config.HOSTS[0]
    networking.network_cleanup()
    logger.info(
        "Starting VM %s on host %s", config.VM_NAME[0], config.HOSTS[0]
    )
    if not net_help.run_vm_once_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0], wait_for_ip=True
    ):
        raise config.NET_EXCEPTION(
            "Cannot start VM %s on host %s" %
            (config.VM_NAME[0], config.HOSTS[0])
        )


def teardown_package():
    """
    Stopping VM
    """
    logger.info(
        "Stopping VM %s", config.VM_NAME[0]
    )
    if not ll_vms.stopVms(vms=config.VM_NAME[0]):
        logger.error("Failed to stop VM: %s", config.VM_NAME[0])
