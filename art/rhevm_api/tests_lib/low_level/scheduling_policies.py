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
from art.rhevm_api.utils.test_utils import get_api
from art.test_handler.settings import opts

SCH_POL_API = get_api('scheduling_policy', 'schedulingpolicies')
SCH_POL_UNITS_API = get_api('scheduling_policy_unit', 'schedulingpolicyunits')
FILTER_API = get_api('filter', 'filters')
WEIGHT_API = get_api('weight', 'weights')
BALANCE_API = get_api('balance', 'balances')
ENUMS = opts['elements_conf']['RHEVM Enums']
FILTER_TYPE = ENUMS['policy_unit_type_filter']
WEIGHT_TYPE = ENUMS['policy_unit_type_weight']
BALANCE_TYPE = ENUMS['policy_unit_type_load_balancing']
UNIT_API = {
    FILTER_TYPE: FILTER_API,
    WEIGHT_TYPE: WEIGHT_API,
    BALANCE_TYPE: BALANCE_API
}
UNIT_CLASS = {
    FILTER_TYPE: data_st.Filter,
    WEIGHT_TYPE: data_st.Weight,
    BALANCE_TYPE: data_st.Balance
}
UNIT_LINK = {
    FILTER_TYPE: 'filters',
    WEIGHT_TYPE: 'weights',
    BALANCE_TYPE: 'balances'
}
UNIT_ATTR = {
    FILTER_TYPE: 'filter',
    WEIGHT_TYPE: 'weight',
    BALANCE_TYPE: 'balance'
}

logger = logging.getLogger(__name__)


def _prepare_scheduling_policy_object(**kwargs):
    """
    Prepare scheduling policy object

    :param name: new name
    :type name: str
    :param description: description of new policy
    :type description: str
    :param properties: properties of new policy
    :type properties: dict
    :returns: SchedulingPolicy object
    :rtype: SchedulingPolicy instance
    """
    sch_pol_obj = data_st.SchedulingPolicy()
    if kwargs.get('properties'):
        properties = data_st.Properties()
        for name, value in kwargs.pop('properties').iteritems():
            property_obj = data_st.Property(name=name, value=value)
            properties.add_property(property_obj)
        sch_pol_obj.set_properties(properties)

    for key, value in kwargs.iteritems():
        if hasattr(sch_pol_obj, key):
            setattr(sch_pol_obj, key, value)

    return sch_pol_obj


def add_new_scheduling_policy(**kwargs):
    """
    Add new scheduling policy to engine

    :param name: new name
    :type name: str
    :param description: description of new policy
    :type description: str
    :param properties: properties of new policy
    :type properties: dict
    :returns: True, if policy created successfully, otherwise False
    :rtype: bool
    """
    sch_pol_obj = _prepare_scheduling_policy_object(**kwargs)

    _, status = SCH_POL_API.create(sch_pol_obj, True)
    return status


def update_scheduling_policy(policy_name, **kwargs):
    """
    Update scheduling policy

    :param policy_name: policy name
    :type policy_name: str
    :param name: new name
    :type name: str
    :param description: policy description
    :type description: str
    :param properties: policy properties
    :type properties: dict
    :returns: True, if policy updated successfully, otherwise False
    :rtype: bool
    """
    old_sch_pol_obj = SCH_POL_API.find(policy_name)
    new_sch_pol_obj = _prepare_scheduling_policy_object(**kwargs)

    _, status = SCH_POL_API.update(old_sch_pol_obj, new_sch_pol_obj, True)
    return status


def remove_scheduling_policy(policy_name):
    """
    Remove scheduling policy

    :param policy_name: policy name
    :type policy_name: str
    :returns: True, if policy deleted successfully, otherwise False
    :rtype: bool
    """
    sch_pol_obj = SCH_POL_API.find(policy_name)
    return SCH_POL_API.delete(sch_pol_obj, True)


def _get_policy_unit(unit_name, unit_type):
    """
    Get policy unit by name and by type

    :param unit_name: unit name
    :type unit_name: str
    :param unit_type: unit type
    :type unit_type: str
    :returns: policy unit or None
    :rtype: SchedulingPolicyUnit instance or None
    """
    policy_units = SCH_POL_UNITS_API.get(absLink=False)
    for unit in policy_units:
        if unit.get_name() == unit_name and unit.get_type() == unit_type:
            return unit
    logger.error(
        "No scheduling policy unit with name: %s and type: %s",
        unit_name, unit_type
    )
    return None


def _get_policy_units(policy_name, unit_type, attr=None, get_href=False):
    """
    Get all scheduling policy units of specific type from scheduling policy

    :param policy_name: name of scheduling policy
    :type policy_name: str
    :param unit_type: type of scheduling policy units
    :type unit_type: str
    :param attr: attribute to get (usually name of desired element)
    :type attr: str
    :param get_href: to get list of objects or link
    :type get_href: bool
    :returns: list of scheduling policy units object or link on collection
    :rtype: list
    """
    policy_obj = SCH_POL_API.find(policy_name)
    unit_link = UNIT_LINK.get(unit_type)
    return SCH_POL_API.getElemFromLink(
        policy_obj, link_name=unit_link, attr=attr, get_href=get_href
    )


def add_scheduling_policy_unit(
        policy_name, unit_name, unit_type, position=None, factor=None
):
    """
    Add new scheduling policy unit to scheduling policy

    :param policy_name: scheduling policy name
    :type policy_name: str
    :param unit_name: scheduling policy unit name
    :type unit_name: str
    :param unit_type: scheduling policy unit type
    (filter, weight, load_balancing)
    :type unit_type: str
    :param position: position of filter
    :type position: int
    :param factor: factor of weight module
    :type factor: int
    :returns: True, if policy unit added successfully, otherwise False
    :rtype: bool
    """
    policy_unit_id = _get_policy_unit(unit_name, unit_type).get_id()
    policy_units_link = _get_policy_units(
        policy_name, unit_type, get_href=True
    )
    pl_unit = data_st.SchedulingPolicyUnit(id=policy_unit_id)

    if unit_type is FILTER_TYPE and position:
        unit_obj = UNIT_CLASS.get(unit_type)(
            scheduling_policy_unit=pl_unit, position=position
        )
    elif unit_type is WEIGHT_TYPE and factor:
        unit_obj = UNIT_CLASS.get(unit_type)(
            scheduling_policy_unit=pl_unit, factor=factor
        )
    else:
        unit_obj = UNIT_CLASS.get(unit_type)(scheduling_policy_unit=pl_unit)

    _, status = UNIT_API.get(unit_type).create(
        unit_obj, True, async=True, collection=policy_units_link
    )
    return status


def remove_scheduling_policy_unit(policy_name, unit_name, unit_type):
    """
    Remove scheduling policy unit from scheduling policy

    :param policy_name: scheduling policy name
    :type policy_name: str
    :param unit_name: scheduling policy unit name
    :type unit_name: str
    :param unit_type: scheduling policy unit type
    (filter, weight, load_balancing)
    :type unit_type: str
    :returns: True, if policy unit removed successfully, otherwise False
    :rtype: bool
    """
    policy_unit_id = _get_policy_unit(unit_name, unit_type).get_id()
    policy_units = _get_policy_units(
        policy_name, unit_type, attr=UNIT_ATTR.get(unit_type)
    )
    policy_units_link = _get_policy_units(
        policy_name, unit_type, get_href=True
    )
    if not isinstance(policy_units, list):
        policy_units = [policy_units]

    for policy_unit in policy_units:
        if policy_unit.get_id() == policy_unit_id:
            # WA until bug 1144080 will fixed
            policy_unit_href = r'%s/%s' % (
                policy_units_link, policy_unit.get_id()
            )
            logger.info(policy_unit_href)
            policy_unit_obj = UNIT_CLASS.get(unit_type)(href=policy_unit_href)
            return SCH_POL_UNITS_API.delete(policy_unit_obj, True)

    logger.error("No policy unit %s under policy %s", unit_name, policy_name)
    return False