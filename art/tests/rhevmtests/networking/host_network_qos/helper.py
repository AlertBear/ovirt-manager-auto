#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for host network QoS job
"""
import logging

import rhevmtests.networking.config as net_conf
from art.core_api import apis_utils
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("Network_Host_QoS_Helper")


def cmp_qos_with_vdscaps(net, qos_dict, host=None):
    """
    Compares provided host network QoS values with the values in VDSCaps

    :param net: Network name to check host network QoS values for
    :type net: str
    :param qos_dict: Values to compare with the VDSCaps QoS values
    :type qos_dict: dict
    :param host: Host resource network resides on
    :type host: Resource.VDS
    :return: True/False
    :rtype: bool
    """
    if host is None:
        host = net_conf.VDS_HOSTS[0]

    logger.info("Compare vdsClient QoS values with %s", qos_dict)
    vds_caps_qos_dict = {}
    sample = apis_utils.TimeoutingSampler(
        timeout=net_conf.SAMPLER_TIMEOUT, sleep=1,
        func=network_helper.is_network_in_vds_caps, host_resource=host,
        network=net
    )
    if not sample.waitForFuncStatus(result=True):
        return False

    vds_caps_out = host.vds_client("getVdsCapabilities", json=True)
    out_networks = vds_caps_out.get("networks", {})
    qos = out_networks.get(net, {}).get("hostQos", {}).get("out", {})
    for key in ("rt", "ul", "ls"):
        vds_caps_qos_dict[key] = qos.get(key, {}).get("m2")

    logger.info("Compare provided host QoS values with VDSCaps values")
    if cmp(vds_caps_qos_dict, qos_dict):
        logger.error(
            "Values in VdsCaps are %s, should be %s", qos_dict,
            vds_caps_qos_dict
        )
        return False
    return True
