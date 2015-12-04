#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for host network QoS job
"""
import logging
import config as conf
from art.core_api import apis_utils

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
    :raise: Network exception
    """
    if host is None:
        host = conf.VDS_HOSTS[0]
    logger.info("Compare vdsClient QoS values with %s", qos_dict)
    vds_caps_qos_dict = {}
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1, func=check_net_on_vdscaps,
        net=net
    )
    if not sample.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION(
            "Network %s doesn't exist in vdsCaps" % net
        )
    vds_caps_out = host.vds_client("getVdsCapabilities")
    qos = vds_caps_out["info"]["networks"][net]["hostQos"]["out"]
    for key in ("rt", "ul", "ls"):
        vds_caps_qos_dict[key] = qos[key]["m2"]

    logger.info("Compare provided host QoS values with VDSCaps values")
    if cmp(vds_caps_qos_dict, qos_dict):
        raise conf.NET_EXCEPTION(
            "Values in VdsCaps are %s, should be %s" %
            (qos_dict, vds_caps_qos_dict)
        )


def check_net_on_vdscaps(net, host=None):
    """
    Check if network exists on VdsCaps

    :param net: Network name
    :type net: str
    :param host: Host resource network resides on
    :type host: Resource.VDS
    :return: True if network exists on vdsCaps otherwise False
    :rtype: bool
    """
    if host is None:
        host = conf.VDS_HOSTS[0]
    vds_caps_out = host.vds_client("getVdsCapabilities")
    logger.info("%s", vds_caps_out["info"]["networks"])
    net_dict = vds_caps_out["info"]["networks"].get(net)
    if not net_dict:
        logger.error("%s is missing in vdsCaps", net)
        return False
    if not net_dict.get("hostQos"):
        logger.error("Host network QoS is missing for %s", net)
        return False
    return True
