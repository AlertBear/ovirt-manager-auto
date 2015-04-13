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

import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool


def remove_ranges_from_mac_pool(mac_pool_name, range_list):
    """
    Remove ranges from the given MAC pool

    :param mac_pool_name: name of the MAC pool you want to remove range from
    :type mac_pool_name: str
    :param range_list: list of tuples of (start, end) to remove from mac_pool
    :type range_list: list
    :return: True if remove of range succeeded, False otherwise
    :rtype: bool
    """
    mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
    mac_pool_obj_for_update = ll_mac_pool.get_mac_pool(mac_pool_name)
    range_objs = ll_mac_pool.get_mac_pool_ranges_list(mac_pool_obj_for_update)
    for start, end in range_list:
        range_ = ll_mac_pool.get_mac_pool_range_obj(
            mac_pool_obj_for_update, start, end
        )
        if range_:
            range_objs.remove(range_)
    return ll_mac_pool.MACPOOL_API.update(
        mac_pool_obj, mac_pool_obj_for_update, True
    )[1]


def add_ranges_to_mac_pool(mac_pool_name, range_list):
    """
    Add ranges to the given MAC pool

    :param mac_pool_name: MAC pool name
    :type mac_pool_name: str
    :param range_list: list of tuples of (start, end) to add to mac_pool
    :type range_list: list
    :return: True if add of ranges succeeded, False otherwise
    :rtype: bool
    """

    mac_pool_obj = ll_mac_pool.get_mac_pool(mac_pool_name)
    mac_pool_obj_for_update = ll_mac_pool.get_mac_pool(mac_pool_name)
    range_objs = ll_mac_pool.get_mac_pool_ranges_list(mac_pool_obj_for_update)
    for start, end in range_list:
        range_objs.append(ll_mac_pool.prepare_range_obj(start, end))
    return ll_mac_pool.MACPOOL_API.update(
        mac_pool_obj, mac_pool_obj_for_update, True
    )[1]


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
    mac_pool_obj_for_update = ll_mac_pool.get_mac_pool(mac_pool_name)
    for (orig_from, orig_to), (new_from, new_to) in range_dict.iteritems():
        range_ = ll_mac_pool.get_mac_pool_range_obj(
            mac_pool_obj_for_update, orig_from, orig_to
        )
        if range_:
            range_.set_from(new_from)
            range_.set_to(new_to)
        else:
            return False
    return ll_mac_pool.MACPOOL_API.update(
        mac_pool_obj, mac_pool_obj_for_update, True
    )[1]
