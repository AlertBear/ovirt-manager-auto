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

import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.utils.test_utils as utils
import art.rhevm_api.tests_lib.low_level.general as general
from art.core_api.apis_utils import data_st

MACPOOL_API = utils.get_api("mac_pool", "macpools")
RANGES = "ranges"


def get_mac_pool(pool_name):
    """
    Get MAC pool object due to given Pool name

    :param pool_name: MAC pool name
    :type pool_name: str
    :return: MAC pool object
    :rtype: MacPool object
    """
    return MACPOOL_API.find(pool_name)


def get_mac_pool_from_dc(dc_name):
    """
    Get MAC pool from the given DC

    :param dc_name: name of the DC
    :type dc_name: str
    :return: MAC pool object for that DC
    :rtype: MacPool object
    """
    dc_obj = ll_dc.get_data_center(dc_name)
    return MACPOOL_API.find(dc_obj.get_mac_pool().get_id(), "id")


def get_mac_pool_ranges_list(mac_pool_obj):
    """
    Get MAC pool ranges list

    :param mac_pool_obj: MAC pool object
    :type mac_pool_obj: MacPool object
    :return: MAC pool ranges list
    :rtype: list
    """
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
    return MACPOOL_API.get(absLink=False)


def get_mac_range_values(mac_pool_obj):
    """
    Get MAC pool values for each range
    :param mac_pool_obj: MAC pool object
    :type mac_pool_obj: MacPool object
    :return: MAC pool ranges list
    :rtype: list
    """
    ranges = get_mac_pool_ranges_list(mac_pool_obj)
    return [(i.get_from(), i.get_to()) for i in ranges]


def remove_mac_pool(mac_pool_name):
    """
    Remove MAC pool

    :param mac_pool_name: name of the MAC pool you want to remove
    :type mac_pool_name: str
    :return: True if remove of MAC pool succeeded, False otherwise
    :rtype: bool
    """
    mac_pool_obj = get_mac_pool(mac_pool_name)
    return MACPOOL_API.delete(mac_pool_obj, True)


def prepare_macpool_obj(**kwargs):
    """
    Prepare MacPool object
   :param kwargs:
        name: type=str
        ranges: type=list
        description: type=str
        allow_duplicates: type=bool
    :return: MAC pool instance
    :rtype: MacPool object
    """
    if kwargs.get(RANGES):
        kwargs[RANGES] = prepare_ranges_obj(kwargs[RANGES])
    mac_pool_obj = general.prepare_ds_object("MacPool", **kwargs)
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
    return filter(lambda x: x.get_default_pool(), mac_pool_list)[0]


def create_mac_pool(**kwargs):
    """
    Creates new MAC Pool

    :param kwargs:
        name: type=str
        ranges: type=list
        description: type=str
        allow_duplicates: type=bool
    :type kwargs: dict
    :return: True if create MAC pool succeeded, False otherwise
    :rtype: bool
    """
    mac_pool_obj = prepare_macpool_obj(**kwargs)
    return MACPOOL_API.create(mac_pool_obj, True)[1]


def update_mac_pool(**kwargs):
    """
    Update MAC Pool

    :param kwargs:
        :param mac_pool_name: current mac pool name
        :type mac_pool_name: str
        :param name: new mac pool name for update
        :type name: str
        :param ranges: list of mac ranges [(from_mac1, to_mac1), (..)]
        :type ranges: list
        :param description: description of the mac pool
        :type description: str
        :param allow_duplicates: True if allow duplicate, otherwise False
        :type allow_duplicates: bool
    :type kwargs: dict
    :return: True if MAC pool was updated, False otherwise
    :rtype: bool
    """
    mac_pool_obj = get_mac_pool(kwargs.pop("mac_pool_name"))
    mac_pool_obj_for_update = prepare_macpool_obj(**kwargs)
    return MACPOOL_API.update(mac_pool_obj, mac_pool_obj_for_update, True)[1]
