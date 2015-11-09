#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for host network QoS job
"""
import logging
import config as conf

logger = logging.getLogger("Network_Host_QoS_Helper")


def cmp_qos_with_vdscaps(net, qos_dict, host=conf.VDS_HOSTS[0]):
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

    vds_caps_qos_dict = {}
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
