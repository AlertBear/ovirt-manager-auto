#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for Sanity job
"""

import logging
import config as conf
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Sanity_Helper")


def check_dummy_on_host_interfaces(dummy_name):
    """
    Check if dummy interface if on host via engine

    :param dummy_name: Dummy name
    :type dummy_name: str
    :return: True/False
    :rtype: bool
    """
    host_nics = ll_hosts.getHostNicsList(conf.HOST_0)
    for nic in host_nics:
        if dummy_name == nic.name:
            return True
    return False


def prepare_networks_on_dc_cluster():
    """
    Create all networks that are needed for all cases on DC and cluster

    :raise: NetworkException
    """
    logger.info(
        "Create %s on %s/%s", conf.NETS_DICT, conf.DC_NAME, conf.CLUSTER
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_NAME, cluster=conf.CLUSTER,
        network_dict=conf.NETS_DICT
    ):
        raise conf.NET_EXCEPTION(
            "Failed to add %s to %s/%s" %
            (conf.NETS_DICT, conf.DC_NAME, conf.CLUSTER)
        )


def run_vm_on_host():
    """
    Run first VM once on the first host

    :raise: conf.NET_EXCEPTION
    """
    if not net_help.run_vm_once_specific_host(
        vm=conf.VM_0, host=conf.HOST_0, wait_for_ip=True
    ):
        raise conf.NET_EXCEPTION(
            "Cannot start VM %s on host %s" % (conf.VM_0, conf.HOST_0)
        )


def stop_vm():
    """
    Stop first VM
    """
    logger.info("Stop VM %s", conf.VM_0)
    if not ll_vms.stopVm(positive=True, vm=conf.VM_0):
        logger.error("Failed to stop VM %s", conf.VM_0)
