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
    network_dict = {
        c.NETWORKS[1][0]: {
            "required": "false"
        },
        c.NETWORKS[2][0]: {
            "vlan_id": "2",
            "required": "false"
        },
        c.NETWORKS[3][0]: {
            "usages": "",
            "required": "false"
        },
        c.NETWORKS[4][0]: {
            "required": "false"
        },
        c.NETWORKS[5][0]: {
            "vlan_id": "5",
            "required": "false"
        },
        c.NETWORKS[6][0]: {
            "required": "false",
            "usages": ""
        },
        c.NETWORKS[7][0]: {
            "required": "false"
        },
        c.NETWORKS[8][0]: {
            "required": "false",
            "usages": "",
            "mtu": c.MTU[1]
        },
        c.NETWORKS[8][1]: {
            "required": "false",
            "vlan_id": "82",
            "mtu": c.MTU[0]
        },
        c.NETWORKS[9][0]: {
            "required": "false"
        },
        c.NETWORKS[10][0]: {
            "required": "false"
        },
        c.NETWORKS[11][0]: {
            "required": "false",
            "usages": ""
        },
        c.NETWORKS[11][1]: {
            "required": "false",
            "vlan_id": "111"
        },
        c.NETWORKS[11][2]: {
            "required": "false",
            "vlan_id": "112"
        },
        c.NETWORKS[12][0]: {
            "required": "false",
            "usages": ""
        },
        c.NETWORKS[12][1]: {
            "required": "false",
            "vlan_id": "121"
        },
        c.NETWORKS[12][2]: {
            "required": "false",
            "vlan_id": "122"
        },
        c.NETWORKS[14][0]: {
            "required": "false",
            "usages": ""
        },
        c.NETWORKS[15][0]: {
            "required": "false",
            "usages": ""
        },
        c.NETWORKS[15][1]: {
            "required": "false",
            "vlan_id": "151"
        },
        c.NETWORKS[15][2]: {
            "required": "false",
            "vlan_id": "152"
        }
    }
    logger.info(
        "Create and attach networks on %s/%s", c.DC_NAME, c.CLUSTER
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=c.DC_NAME, cluster=c.CLUSTER, network_dict=network_dict
    ):
        raise c.NET_EXCEPTION(
            "Failed to add networks to %s/%s" % (c.DC_NAME, c.CLUSTER)
        )
