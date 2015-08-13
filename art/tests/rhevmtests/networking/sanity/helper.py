#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for Sanity job
"""

import logging
import config as conf
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

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


def prepare_networks_on_dc():
    """
    Create and attach all networks that are needed for all cases

    :raise: NetworkException
    """
    nets_dict = conf.NETS_DICT
    logger.info(
        "Create and attach networks on %s/%s", conf.DC_NAME, conf.CLUSTER
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_NAME, cluster=conf.CLUSTER, network_dict=nets_dict
    ):
        raise conf.NET_EXCEPTION(
            "Failed to add networks to %s/%s" % (conf.DC_NAME, conf.CLUSTER)
        )


def generate_vlan_id():
    """
    Generate unique VLAN id for cases

    :return: VLAN id
    :rtype: str
    """
    conf.VLAN_ID += 1
    return str(conf.VLAN_ID)
