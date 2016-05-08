#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for Sanity job
"""

import logging
import config as conf
from art.rhevm_api.utils import test_utils
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Sanity_Helper")


def run_vm_on_host():
    """
    Run first VM once on the first host

    :raise: conf.NET_EXCEPTION
    """
    if not net_help.run_vm_once_specific_host(
        vm=conf.VM_0, host=conf.HOST_0_NAME, wait_for_up_status=True
    ):
        raise conf.NET_EXCEPTION()


def stop_vm():
    """
    Stop first VM
    """
    if not ll_vms.stopVm(positive=True, vm=conf.VM_0):
        logger.error("Failed to stop VM %s", conf.VM_0)


def engine_config_set_ethtool_and_queues():
    """
    Set queues and ethtool support on engine via engine-config

    :raise: exceptions.NetworkException
    """
    logger.info(
        "Configuring engine to support ethtool opts for %s version",
        conf.COMP_VERSION
    )
    cmd = [
        "UserDefinedNetworkCustomProperties=ethtool_opts=.*",
        "--cver=%s" % conf.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd, restart=False):
        raise conf.NET_EXCEPTION(
            "Failed to set ethtool via engine-config"
        )


def send_setup_networks(sn_dict):
    """
    Send setupNetworks to host

    :param sn_dict: setupNetworks networks dict
    :type sn_dict: dict
    :raise: conf.NET_EXCEPTION
    """
    if not hl_host_network.setup_networks(conf.HOST_0_NAME, **sn_dict):
        raise conf.NET_EXCEPTION()
