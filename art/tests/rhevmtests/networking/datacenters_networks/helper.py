#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for datacenters networks
"""

import logging
import config as conf
import art.rhevm_api.tests_lib.low_level.networks as ll_networks

logger = logging.getLogger("Datacenters_Networks_Helper")


def create_net_in_datacenter(net_num=5, dc=conf.DC_NAMES[0], prefix='dc1_net'):
        """
        Create networks under datacenters
        :param net_num: number of networks to create
        :type net_num: int
        :param dc: datacenter name
        :type dc: str
        :param prefix: Prefix for network name
        :type prefix: str
        :raise: NetworkException
        :return: list of networks that created under datacenter
        :rtype: list
        """
        logger.info("Create %s networks under %s", net_num, dc)
        dc_net_list = ll_networks.create_networks_in_datacenter(
            datacenter=dc, num_of_net=net_num, prefix=prefix
        )
        if not dc_net_list:
            raise conf.NET_EXCEPTION(
                "Fail to create %s network on %s" % (net_num, dc)
            )
        return dc_net_list


def delete_net_in_datacenter(dc=conf.DC_NAMES[0], mgmt_net=conf.MGMT_BRIDGE):
        """
        Remove network from the setup.
        :param dc: datacenter name
        :type dc: str
        :param mgmt_net: management network
        :type mgmt_net: str
        """

        logger.info("Remove all networks from DC %s", dc)
        if not ll_networks.delete_networks_in_datacenter(dc, mgmt_net):
                logger.error("Fail to delete all networks from DC")
