#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import logging
from utilities.utils import MACRange
import art.rhevm_api.utils.test_utils as utils
from art.test_handler.settings import ART_CONFIG
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool

logger = logging.getLogger("art.hl_lib.mac_pool")

DEFAULT_MAC_POOL = 'Default'


def remove_ranges_from_mac_pool(mac_pool_name, range_list):
    """
    Remove ranges from the given MAC pool

    Args:
        mac_pool_name (str): Name of the MAC pool you want to remove range from
        range_list (list): List of tuples of (start, end) to remove from
            mac_pool

    Returns:
        bool: True if remove of range succeeded, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Remove", obj_type="MAC pool range(s)",
        obj_name=mac_pool_name, range_list=range_list
    )
    mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
    new_range_list = ll_mac_pool.get_mac_range_values(mac_pool_obj)
    for start, end in range_list:
        if ll_mac_pool.get_mac_pool_range_obj(mac_pool_obj, start, end):
            new_range_list.remove((start, end))

    new_mac_pool_obj = ll_mac_pool.prepare_macpool_obj(ranges=new_range_list)
    logger.info(log_info)
    res = ll_mac_pool.MACPOOL_API.update(
        mac_pool_obj, new_mac_pool_obj, True
    )[1]
    if not res:
        logger.error(log_error)
    return res


def add_ranges_to_mac_pool(mac_pool_name, range_list):
    """
    Add ranges to the given MAC pool

    Args:
        mac_pool_name (str): MAC pool name
        range_list (list): List of tuples of (start, end) to add to mac_pool

    Returns:
        bool: True if add of ranges succeeded, False otherwise
    """
    mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
    exist_ranges = ll_mac_pool.get_mac_range_values(mac_pool_obj)
    exist_ranges.extend(range_list)
    log_info, log_error = ll_general.get_log_msg(
        log_action="Add", obj_type="MAC pool range(s)", obj_name=mac_pool_name,
        range_list=range_list
    )
    logger.info(log_info)
    res = ll_mac_pool.update_mac_pool(
        mac_pool_name=mac_pool_name, ranges=exist_ranges
    )
    if not res:
        logger.error(log_error)
    return res


def update_ranges_on_mac_pool(mac_pool_name, range_dict):
    """
    Update range on the given MAC pool

    :param mac_pool_name: name of the MAC pool you want to update range on
    :type mac_pool_name: str
    :param range_dict: dict of original and update values for ranges
    :type range_dict: dict
    :return: True if update of range succeeded, False otherwise
    :rtype: bool
    """
    mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
    new_range_list = ll_mac_pool.get_mac_range_values(mac_pool_obj)

    for (orig_from, orig_to), (new_from, new_to) in range_dict.iteritems():
        if ll_mac_pool.get_mac_pool_range_obj(
                mac_pool_obj, orig_from, orig_to
        ):
            new_range_list.remove((orig_from, orig_to))
            new_range_list.append((new_from, new_to))
        else:
            return False
    new_mac_pool_obj = ll_mac_pool.prepare_macpool_obj(ranges=new_range_list)

    return ll_mac_pool.MACPOOL_API.update(
        mac_pool_obj, new_mac_pool_obj, True
    )[1]


def update_default_mac_pool(mac_range=None):
    """
    Update the Default MAC pool with MAC range
    Add the mac_range and remove all the other MAC ranges
    if mac_range is empty takes it from ART_CONFIG['PARAMETERS']['mac_range']

    :param mac_range: string of MAC range 'start_from_mac-to_mac'
                      for example: '00:1A:4A:16:88:85-00:1A:4A:16:88:98'
    :type mac_range: str
    :return: True if the update succeeded False otherwise
    :rtype: bool
    """
    if mac_range is None:
        mac_range = ART_CONFIG['PARAMETERS'].get('mac_range')
    utils.logger.debug("MAC range is: %s", mac_range)
    if mac_range:
        mac_range_obj = MACRange.from_string(mac_range)
        default_mac_pool = ll_mac_pool.get_default_mac_pool()
        default_mac_pool_range = ll_mac_pool.get_mac_range_values(
            default_mac_pool
        )

        utils.logger.info(
            "Add new range {0} to the Default MAC pool".format(mac_range)
        )
        if not add_ranges_to_mac_pool(
                mac_pool_name=DEFAULT_MAC_POOL,
                range_list=[(mac_range_obj.start, mac_range_obj.end)]
        ):
            utils.logger.error(
                "Failed to add new range to the Default MAC pool"
            )
            return False

        utils.logger.info("Remove all other ranges from Default MAC pool")
        if not remove_ranges_from_mac_pool(
                mac_pool_name=DEFAULT_MAC_POOL,
                range_list=default_mac_pool_range
        ):
            utils.logger.error(
                "Failed to remove all other ranges from Default MAC pool"
            )
            return False
        return True
    else:
        utils.logger.error(
            "Please check the mac_range under PARAMETERS in yours conf file "
            "or maybe the MAC broker didn't allocate MAC range"
        )
        return False
