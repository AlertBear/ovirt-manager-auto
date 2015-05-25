#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature helper
"""
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import config as c
import logging
logger = logging.getLogger("MAC_Pool_Range_Per_DC_Helper")


def create_mac_pool(
    mac_pool_name=c.MAC_POOL_NAME[0], mac_pool_ranges=list(), positive=True
):
    """
    Create MAC pool with MAC pool range

    :param mac_pool_name: Name of the MAC pool
    :type mac_pool_name: str
    :param mac_pool_ranges: List of ranges for the MAC pool
    :type mac_pool_ranges: list
    :param positive: Expected result
    :type positive: bool
    :raise: NetworkException
    """
    log = "Cannot" if positive else "Can"
    mac_pool_ranges = (
        [c.MAC_POOL_RANGE_LIST[0]] if not mac_pool_ranges else mac_pool_ranges
    )
    logger.info("Create MAC pool %s", mac_pool_name)
    status = ll_mac_pool.create_mac_pool(
        name=mac_pool_name,
        ranges=mac_pool_ranges
    )
    if status != positive:
        raise c.NET_EXCEPTION(
            "%s create new MAC pool %s" % (log, mac_pool_name)
        )


def update_dc_with_mac_pool(dc=c.DC_NAME[0], mac_pool_name=c.MAC_POOL_NAME[0]):
    """
    Update DC with MAC pool

    :param dc: Name of the DC to update with MAC pool
    :type dc: str
    :param mac_pool_name: Name of the MAC pool
    :type mac_pool_name: str
    :raise: NetworkException
    """
    logger.info(
        "Update the DC %s with MAC pool %s", c.DC_NAME[0], c.MAC_POOL_NAME[0]
    )
    if not ll_dc.updateDataCenter(
        True, datacenter=c.DC_NAME[0],
        mac_pool=ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[0])
    ):
        raise c.NET_EXCEPTION(
            "Couldn't update DC %s with MAC pool %s" %
            (c.DC_NAME[0], c.MAC_POOL_NAME[0])
        )


def remove_mac_pool(mac_pool_name=c.MAC_POOL_NAME[0]):
    """
    Remove MAC pool

    :param mac_pool_name: MAC pool name
    :type mac_pool_name: str
    :return: True if remove succeeded. False otherwise
    :rtype: bool
    """
    logger.info("Remove MAC pool %s ", mac_pool_name)
    if not ll_mac_pool.remove_mac_pool(mac_pool_name):
        logger.error(
            "Couldn't remove MAC pool %s", c.MAC_POOL_NAME[0]
        )
        return False
    return True
