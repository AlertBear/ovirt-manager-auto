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
from art.core_api.apis_utils import data_st
import art.rhevm_api.utils.test_utils as utils
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.general as ll_general

logger = logging.getLogger("art.ll_lib.mac_pool")

MACPOOL_API = utils.get_api("mac_pool", "macpools")
RANGES = "ranges"


@ll_general.generate_logs()
def get_mac_pool(pool_name):
    """
    Get pool object by given MAC pool_name

    Args:
        pool_name (str): MAC pool name

    Returns:
        MacPool: MacPool object
    """
    return MACPOOL_API.find(pool_name)


def get_mac_pool_from_cluster(cluster):
    """
    Get MAC pool from the given DC

    Args:
        cluster (str): Name of the cluster

    Returns:
        MacPool: MAC pool object for that DC
    """
    logger.info("Get MAC pool from cluster %s", cluster)
    cluster_obj = ll_clusters.get_cluster_object(cluster)
    return MACPOOL_API.find(cluster_obj.get_mac_pool().get_id(), "id")


def get_mac_pool_ranges_list(mac_pool_obj):
    """
    Get MAC pool ranges list

    Args:
        mac_pool_obj (MacPool): MAC pool object

    Returns:
        list: MAC pool ranges list
    """
    logger.info("Get MAC poll %s MAC ranges", mac_pool_obj.name)
    return mac_pool_obj.get_ranges().get_range()


def get_mac_pool_range_obj(mac_pool_obj, start, end):
    """
    Get MAC pool range object

    :param mac_pool_obj: MAC pool object
    :type mac_pool_obj: MacPool object
    :param start: Start MAC address of the range
    :type start: str
    :param end: End MAC address of the range
    :type end: str
    :return: Range object with given start, end limit
    :rtype: Range object
    """
    ranges = get_mac_pool_ranges_list(mac_pool_obj)
    for _range in ranges:
        if start == _range.get_from() and end == _range.get_to():
            return _range
    return None


def get_all_mac_pools():
    """
    Get the list of all MAC pools in the setup

    :return: list of MAC pool objects
    :rtype: list
    """
    logger.info("Get all MAC pools from setup")
    return MACPOOL_API.get(abs_link=False)


def get_mac_range_values(mac_pool_obj):
    """
    Get MAC pool values for each range

    Args:
        mac_pool_obj (MacPool): MAC pool object

    Returns:
        list: MAC pool ranges list
    """
    ranges = get_mac_pool_ranges_list(mac_pool_obj)
    return [(i.get_from(), i.get_to()) for i in ranges]


@ll_general.generate_logs()
def remove_mac_pool(mac_pool_name):
    """
    Remove mac_pool_name from engine

    Args:
        mac_pool_name (str): Name of the MAC pool to remove

    Returns:
        bool: True if remove of MAC pool succeeded, False otherwise
    """
    mac_pool_obj = get_mac_pool(pool_name=mac_pool_name)
    return MACPOOL_API.delete(entity=mac_pool_obj, positive=True)


def prepare_macpool_obj(**kwargs):
    """
    Prepare MacPool object

    Args:
        kwargs (dict): MAC pool parameters

    Keyword arguments:
        name (str): MAC pool name
        ranges (list): List of ranges when each element in the list is a
            tuple with (start_mac_address, end_mac_address)
        description (str): MAC pool description
        allow_duplicates (bool): Allow to use duplicate MACs from the pool

    Returns:
        MacPool: MAC pool object
    """
    if kwargs.get(RANGES):
        kwargs[RANGES] = prepare_ranges_obj(kwargs[RANGES])
    mac_pool_obj = ll_general.prepare_ds_object("MacPool", **kwargs)
    return mac_pool_obj


def prepare_ranges_obj(ranges_list):
    """
    Prepare ranges object

    :param ranges_list: list of ranges tuples
    :type ranges_list: list
    :return: Ranges object
    :rtype: Ranges instance
    """
    ranges = data_st.Ranges()
    for from_, to in ranges_list:
        ranges.add_range(prepare_range_obj(from_, to))
    return ranges


def prepare_range_obj(from_, to):
    """
    Prepare range object

    :param from_: starting MAC in range
    :type from_: str
    :param to: ending MAC in range
    :rtype to: str
    :return: Range object
    :rtype: Range instance
    """
    range_ = data_st.Range()
    range_.set_from(from_)
    range_.set_to(to)
    return range_


def get_default_mac_pool():
    """
    Get default MAC pool object

    :return: MAC pool instance
    :rtype: MacPool object
    """
    mac_pool_list = get_all_mac_pools()
    logger.info("Get default MAC pool from setup")
    return filter(lambda x: x.get_default_pool(), mac_pool_list)[0]


def create_mac_pool(name, ranges, positive=True, **kwargs):
    """
    Creates new MAC Pool

    Args:
        name (str): MAC pool name
        ranges (list): List of ranges when each element in the list is a
            tuple with (start_mac_address, end_mac_address)
        positive (bool): Expected result
        kwargs (dict): MAC pool parameters

    Keyword Arguments:
        description (str): MAC pool description
        allow_duplicates (bool): Allow to use duplicate MACs from the pool

    Returns:
        bool: True if create MAC pool succeeded, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Create", obj_name=name, obj_type="MAC pool",
        positive=positive, **kwargs
    )
    kwargs["name"] = name
    kwargs["ranges"] = ranges
    logger.info(log_info)
    mac_pool_obj = prepare_macpool_obj(**kwargs)
    res = MACPOOL_API.create(mac_pool_obj, positive)[1]
    if not res:
        logger.error(log_error)
    return res


@ll_general.generate_logs(step=True)
def update_mac_pool(mac_pool_name, **kwargs):
    """
    Update MAC Pool

    Args:
        mac_pool_name (str): Current mac pool name
        kwargs (dict): MAC pool parameters

    Keyword Args:
        param mac_pool_name (str): current mac pool name
        name (str: new mac pool name for update
        ranges (list): list of mac ranges [(from_mac1, to_mac1), (..)]
        description (str): description of the mac pool
        allow_duplicates (bool): Allow to use duplicate MACs from the pool

    Returns:
        bool: True if MAC pool was updated, False otherwise
    """
    mac_pool_obj = get_mac_pool(mac_pool_name)
    mac_pool_obj_for_update = prepare_macpool_obj(**kwargs)
    return MACPOOL_API.update(mac_pool_obj, mac_pool_obj_for_update, True)[1]
