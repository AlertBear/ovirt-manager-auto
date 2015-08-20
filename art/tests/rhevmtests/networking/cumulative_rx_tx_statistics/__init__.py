#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cumulative Network Usage Statistics
"""

import config as conf
import logging
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import rhevmtests.networking as network
from art.core_api.apis_utils import TimeoutingSampler
import helper


logger = logging.getLogger("Cumulative_RX_TX_Statistics_Init")


def setup_package():
    """
    Create and attach sw1 to DC/CL/Host
    """
    network.network_cleanup()
    add_net_dict = {
        conf.NET_0: {
            "required": "false",
        }
    }
    sn_dict = {
        "add": {
            "1": {
                "network": conf.NET_0,
                "nic": None,
                "ip": conf.BASIC_IP_DICT_PREFIX,
            }
        }
    }
    logger.info("Create and attach %s to DC/Clusters", conf.NET_0)
    for dc, cl in ((conf.DC_0, conf.CL_0), (None, conf.CL_1)):
        if not hl_networks.createAndAttachNetworkSN(
            data_center=dc, cluster=cl, network_dict=add_net_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to create and attach %s to DC/Cluster" % conf.NET_0
            )

    logger.info(
        "Attaching %s to %s and %s via SN",
        conf.NET_0, conf.LAST_HOST, conf.HOSTS[-2]
    )
    for i in range(2, 4):
        sn_dict["add"]["1"]["nic"] = conf.VDS_HOSTS[i].nics[1]
        conf.BASIC_IP_DICT_PREFIX["ip_prefix"]["address"] = conf.HOST_IPS[i-2]
        if not hl_host_network.setup_networks(
            host_name=conf.HOSTS[i], **sn_dict
        ):
            raise conf.NET_EXCEPTION(
                "Failed to attach %s to %s via SN" %
                (conf.NET_0, conf.HOSTS[i])
            )

    sample = TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=hl_networks.checkICMPConnectivity,
        host=conf.VDS_HOSTS[-2].ip, user=conf.HOSTS_USER,
        password=conf.HOSTS_PW, ip=conf.HOST_IPS[1]
    )
    if not sample.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION("Couldn't ping %s " % conf .HOST_IPS[1])
    logger.info("Increase rx/tx statistics on Host NICs by sending ICMP")
    helper.send_icmp([
        (conf.VDS_HOSTS[-2], conf.HOST_IPS[0]),
        (conf.VDS_HOSTS[-1], conf.HOST_IPS[1])
    ])


def teardown_package():
    """
    1. Stop VM
    2. Remove sw1 from DC/CL/Host
    """
    logger.info("Stopping VMS: %s", conf.VM_NAME[3:])
    if not ll_vms.stopVms(conf.VM_NAME[3:]):
        logger.error("Failed to stop VMS: %s", conf.VM_NAME[3:])

    for i in range(2, 4):
        logger.info("Cleaning %s interfaces", conf.HOSTS[i])
        if not hl_host_network.clean_host_interfaces(conf.HOSTS[i]):
            logger.error(
                "Failed to remove %s from %s", conf.NET_0, conf.HOSTS[i]
            )

    logger.info("Removing all networks from %s", conf.DC_0)
    if not hl_networks.remove_all_networks(
        datacenter=conf.DC_0, mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error("Failed to remove all networks from %s", conf.DC_0)
