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
from art.test_handler.settings import opts
from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.tests_lib.low_level.general as ll_general

SCH_POL_API = get_api('scheduling_policy', 'schedulingpolicies')
SCH_POL_UNITS_API = get_api('scheduling_policy_unit', 'schedulingpolicyunits')
FILTER_API = get_api('filter', 'filters')
WEIGHT_API = get_api('weight', 'weights')
BALANCE_API = get_api('balance', 'balances')
ENUMS = opts['elements_conf']['RHEVM Enums']
FILTER_TYPE = ENUMS['policy_unit_type_filter']
WEIGHT_TYPE = ENUMS['policy_unit_type_weight']
BALANCE_TYPE = ENUMS['policy_unit_type_balance']
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

SCHEDULING_POLICY = "scheduling policy"
SCHEDULING_POLICY_UNIT = "scheduling policy unit"

logger = logging.getLogger("art.ll_lib.scheduling_policies")


def get_scheduling_policies():
    """
    Get all scheduling policies

    Returns:
        list: Scheduling policies objects
    """
    logger.info("Get all scheduling policies")
    return SCH_POL_API.get(abs_link=False)


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


@ll_general.generate_logs(step=True)
def add_new_scheduling_policy(**kwargs):
    """
    Add new scheduling policy to the engine

    Keyword Args:
        name (str): Scheduling policy name
        description (str): Scheduling policy description
        properties (dict): Scheduling policy properties

    Returns:
        bool: True, if succeeds to create the scheduling policy,
            otherwise False
    """
    sch_pol_obj = _prepare_scheduling_policy_object(**kwargs)
    return SCH_POL_API.create(sch_pol_obj, True)[1]


def update_scheduling_policy(policy_name, **kwargs):
    """
    Update the scheduling policy

    Args:
        policy_name (str): Scheduling policy name

    Keyword Args:
        name (str): New scheduling policy name
        description (str): Scheduling policy description
        properties (dict): Scheduling policy properties

    Returns:
        bool: True, if succeeds to update the scheduling policy,
            otherwise False
    """
    old_sch_pol_obj = SCH_POL_API.find(policy_name)
    new_sch_pol_obj = _prepare_scheduling_policy_object(**kwargs)

    log_info, log_error = ll_general.get_log_msg(
        log_action="Update",
        obj_type=SCHEDULING_POLICY,
        obj_name=policy_name,
        **kwargs
    )

    logger.info(log_info)
    status = SCH_POL_API.update(old_sch_pol_obj, new_sch_pol_obj, True)[1]

    if not status:
        logger.error(log_error)

    return status


@ll_general.generate_logs(step=True)
def remove_scheduling_policy(policy_name):
    """
    Remove the scheduler policy

    Args:
        policy_name (str): Scheduler policy name

    Returns:
        bool: True, if the policy deleted successfully, otherwise False
    """
    sch_pol_obj = SCH_POL_API.find(policy_name)
    return SCH_POL_API.delete(sch_pol_obj, True)


def get_policy_unit(unit_name, unit_type):
    """
    Get policy unit by name and type

    Args:
        unit_name (str): Scheduling policy unit name
        unit_type (str): Scheduling policy unit type(filter, weight, balance)

    Returns:
        SchedulingPolicyUnit: SchedulingPolicyUnit instance
    """
    policy_units = SCH_POL_UNITS_API.get(abs_link=False)
    for unit in policy_units:
        if unit.get_name() == unit_name and unit.get_type() == unit_type:
            return unit
    logger.error(
        "No scheduling policy unit with name: %s and type: %s",
        unit_name, unit_type
    )
    return None


def get_sch_policy_units(policy_name, unit_type, get_href=False):
    """
    Get all scheduling policy units of the specific type
    from the scheduling policy

    Args:
        policy_name (str): Scheduling policy name
        unit_type (str): Scheduling policy unit type (filter, weight, balance)
        get_href (bool): Get list of object or link on collection

    Returns:
        list: Scheduling policy units objects or link on collection
    """
    policy_obj = SCH_POL_API.find(policy_name)
    return SCH_POL_API.getElemFromLink(
        policy_obj,
        link_name=UNIT_LINK[unit_type],
        attr=UNIT_ATTR[unit_type],
        get_href=get_href
    )


@ll_general.generate_logs(step=True)
def add_scheduling_policy_unit(
    policy_name, unit_name, unit_type, position=None, factor=None
):
    """
    Add the scheduling policy unit to the scheduling policy

    Args:
        policy_name (str): Scheduling policy name
        unit_name (str): Scheduling policy unit name
        unit_type (str): Scheduling policy unit type
            (filter, weight, load_balancing)
        position (int): Filter position
        factor (int): Weight unit factor

    Returns:
        bool: True, if succeeds to add scheduling policy unit
            to the scheduling policy, otherwise False
    """
    policy_unit_id = get_policy_unit(unit_name, unit_type).get_id()
    policy_units_link = get_sch_policy_units(
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

    return UNIT_API.get(unit_type).create(
        unit_obj, True, async=True, collection=policy_units_link
    )[1]


def get_scheduling_policy_id(scheduling_policy_name):
    """
    Get scheduling policy ID by name

    Args:
        scheduling_policy_name (str): Scheduling policy name

    Returns:
        str: Scheduling policy ID
    """
    scheduling_policies = get_scheduling_policies()

    for scheduling_policy in scheduling_policies:
        if scheduling_policy.get_name() == scheduling_policy_name:
            return scheduling_policy.get_id()
    return ""
