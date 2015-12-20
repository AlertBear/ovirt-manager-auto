#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for bridgeless
"""

import logging
import config as conf
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Bridgeless_Networks_Helper")


def create_networks_on_host(nic, net=None, slaves=list()):
    """
    Attach network to host NIC and create bond

    :param net: Network name
    :type net: str
    :param nic: NIC name
    :type nic: str
    :param slaves: "slaves": ["dummy2", "dummy3"]
    :type slaves: list
    :raise: NetworkException
    """

    local_dict = {
        "add": {
            "1": {
                "nic": nic
            }
        }
    }
    if slaves:
        local_dict["add"]["1"]["slaves"] = slaves
    if net:
        local_dict["add"]["1"]["network"] = net
        vlan_log = "with VLAN" if conf.NET_DICT[net].get("vlan_id") else ""

    log = (
        "Attach Non-VM %s network %s to" % (vlan_log, net) if net else "Create"
    )
    failed_log = "attach %s to" % net if net else "create"
    logger.info("%s %s on %s", log, nic, conf.HOST_0_NAME)
    if not hl_host_network.setup_networks(
        host_name=conf.HOST_0_NAME, **local_dict
    ):
        raise conf.NET_EXCEPTION(
            "Failed %s %s on %s" % (failed_log, nic, conf.HOST_0_NAME)
        )
