#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Host Network QOS feature init
"""

import logging
import config as conf
from rhevmtests import networking
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Network_Host_QoS_Init")


def setup_package():
    """
    Running cleanup
    """
    networking.network_cleanup()
    conf.VDS_HOSTS_1 = conf.VDS_HOSTS[0]
    conf.HOST_1_NICS = conf.VDS_HOSTS_1.nics
    conf.HOST_1_IP = conf.HOSTS_IP[0]
    conf.HOST_1 = conf.HOSTS[0]
    logger.info(
        "Add %s to %s/%s", conf.NETS_DICT, conf.DC_NAME, conf.CLUSTER_1
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_NAME, cluster=conf.CLUSTER_1,
        network_dict=conf.NETS_DICT
    ):
        raise conf.NET_EXCEPTION(
            "Failed to add networks to %s/%s" % (conf.DC_NAME, conf.CLUSTER_1)
        )


def teardown_package():
    """
    Removes networks from setup
    """
    logger.info("Remove networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=conf.HOST_1, data_center=conf.DC_NAME,
        all_net=True, mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove %s from %s and %s",
            conf.NETS_DICT, conf.DC_NAME, conf.HOST_1
        )
