#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for IO_test
"""

import logging
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("IO_Networks_Helper")


def create_networks(positive, params, type_):
    """
    Create network.

    Args:
        positive (bool): True if action should succeed, False otherwise.
        params (list): Network params.
        type_ (str): The type of network params, for example 'vlan_id'.

    Returns:
        bool: True if create network succeeded, False otherwise.
    """

    for index, param in enumerate(params):
        local_dict = {
            "%s_%s" % (type_, index): {
                type_: param
            }
        }

        res = hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_0, network_dict=local_dict
        )
        return res == positive
