#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for label feature
"""

import logging

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.networks as ll_networks

logger = logging.getLogger("Labels_Helper")


def add_label_and_check_network_on_nic(
    positive, label, network_on_nic=True, add_net_to_label=True,
    networks=list(), host_nic_dict=None, vlan_nic=None, nic_list=list(),
    attach_to_host=True
):
    """
    Adding label to network or host and checking if network resides on Host NIC

    Args:
        positive (bool): True if add label should be succeed, False otherwise.
        label (str): Label name.
        network_on_nic (bool): True if network should be on host,
            False otherwise.
        add_net_to_label (bool): True if need to attach network to label,
            False if network already attached to label.
        networks (list):  Networks name.
        host_nic_dict (dict): Dictionary with hosts as keys and a list of host
            interfaces as a value for that key.
        vlan_nic (str): Build the name for tagged interface or bond.
        nic_list (list): List of NICs.
        attach_to_host: True if need to attach NIC to host,
            False if NIC already attached to host.

    Returns:
        bool: True if action was succeeded, False otherwise.
    """

    lb_net = networks if add_net_to_label else list()
    nic_host = host_nic_dict if attach_to_host else None
    res = hl_networks.create_and_attach_label(
        label=label, networks=lb_net, host_nic_dict=nic_host
    )
    if res != positive:
        return False

    for host in host_nic_dict.iterkeys():
        for i, network in enumerate(networks):
            nic = vlan_nic if vlan_nic else nic_list.pop(0)
            res = ll_networks.check_network_on_nic(
                network=network, host=host, nic=nic
            )
            if res != network_on_nic:
                return False
    return True
