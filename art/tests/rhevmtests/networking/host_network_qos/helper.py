#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper functions for host network QoS job
"""
import logging
import config as conf
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc

logger = logging.getLogger("Network_Host_QoS_Helper")


def remove_qos_from_dc():
    """
    Removes host network QoS from DC
    """
    if not ll_dc.delete_qos_from_datacenter(conf.DC_NAME, conf.QOS_NAME[0]):
        logger.error(
            "Couldn't delete the QoS %s from DC %s",
            conf.QOS_NAME[0], conf.DC_NAME
        )


def create_host_net_qos(**qos_dict):
    """
    Create a host network qos with provided parameters

    :param qos_dict: dict of host network qos values to create QoS with
    :type qos_dict: dict
    :raises: Network exception
    """
    logger.info(
        "Create new network host QoS profile with parameters %s", qos_dict
    )
    if not ll_dc.add_qos_to_datacenter(
        datacenter=conf.DC_NAME,
        qos_name=conf.QOS_NAME[0], qos_type=conf.HOST_NET_QOS_TYPE, **qos_dict
    ):
        raise conf.NET_EXCEPTION(
            "Couldn't create Host Network QOS under DC"
        )


def update_host_net_qos(**qos_dict):
    """
    Update host network qos parameters with given dict parameters

    :param qos_dict: dict of host network qos values to update
    :type qos_dict: dict
    :raises: Network exception
    """
    logger.info("Update network host QoS values with %s ", qos_dict)
    if not ll_dc.update_qos_in_datacenter(
        datacenter=conf.DC_NAME, qos_name=conf.QOS_NAME[0], **qos_dict
    ):
        raise conf.NET_EXCEPTION(
            "Couldn't update Network QOS under DC with provided parameters"
        )
