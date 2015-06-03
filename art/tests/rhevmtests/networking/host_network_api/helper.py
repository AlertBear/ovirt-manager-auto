#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for Host Network API
"""

import config as c
import logging
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking as network
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.core_api.apis_utils as api_utils
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Helper")


def check_dummy_on_host(positive=True):
    """
    Check if dummy interfaces are exist/not exist on the host

    :param positive: True to check if dummy exist and False to make sure
                     it's not
    :type positive: bool
    :raise: NET_EXCEPTION
    """
    for_log = "exists" if positive else "not exists"
    log = "Dummy interface %s on engine" % for_log
    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(network.config.HOSTS[0])
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check if dummy0 %s on host via engine", for_log)
    sample = api_utils.TimeoutingSampler(
        timeout=network.config.SAMPLER_TIMEOUT, sleep=1,
        func=c.network_lib.check_dummy_on_host_interfaces,
        host_name=c.HOST_0, dummy_name="dummy0"
    )
    if not sample.waitForFuncStatus(result=positive):
        if positive:
            raise c.NET_EXCEPTION(log)
        else:
            logger.error(log)


def attach_network_attachment(
    network_dict, network, nic=None, positive=True
):
    """
    Attach network attachment to host NIC via NIC or host href

    :param network_dict: Network dict
    :type network_dict: dict
    :param network: Network name
    :type network: str
    :param nic: NIC name
    :type nic: str
    :param positive: Expected status
    :type positive: bool
    :raise: NetworkException
    """
    nic_log = nic if nic else network_dict.get("nic")
    logger.info(
        "Attaching %s to %s on %s", network, nic_log, c.HOST_0
    )
    network_to_attach = network_dict.pop("network")
    res = hl_host_network.add_network_to_host(
        host_name=c.HOST_0, network=network_to_attach, nic_name=nic,
        **network_dict
    )
    if res != positive:
        raise c.NET_EXCEPTION(
            "Failed to attach %s to %s on %s" % (network, nic_log, c.HOST_0)
        )


def prepare_networks_on_dc():
    """
    Create and attach all networks that are needed for all cases

    :raise: NetworkException
    """
    nets_dict = dict(dict(c.SN_DICT, **c.NIC_DICT), **c.HOST_DICT)
    logger.info(
        "Create and attach networks on %s/%s", c.DC_NAME, c.CLUSTER
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=c.DC_NAME, cluster=c.CLUSTER, network_dict=nets_dict
    ):
        raise c.NET_EXCEPTION(
            "Failed to add networks to %s/%s" % (c.DC_NAME, c.CLUSTER)
        )
