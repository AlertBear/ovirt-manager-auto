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
import time
import art.core_api.apis_utils as api_utils
from art.core_api import is_action
import art.core_api.validator as validator
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.data_struct.data_structures as ds
import art.rhevm_api.tests_lib.low_level.vms as vms
from art.test_handler.settings import opts
import art.core_api.apis_exceptions as exceptions
import concurrent.futures as futures

ELEMENT = 'vmpool'
COLLECTION = 'vmpools'
ENUMS = opts['elements_conf']['RHEVM Enums']
UTIL = test_utils.get_api(ELEMENT, COLLECTION)
VM_UTIL = test_utils.get_api('vm', 'vms')
CLUSTER_UTIL = test_utils.get_api('cluster', 'clusters')
TEMPLATE_UTIL = test_utils.get_api('template', 'templates')

VM_POOL = api_utils.getDS('VmPool')
TEMPLATE = api_utils.getDS('Template')

logger = logging.getLogger(__name__)

VM_ACTION_TIMEOUT = 600
VM_POOL_ACTION_TIMEOUT = 600


def _prepareVmPoolObject(**kwargs):

    pool = VM_POOL()

    name = kwargs.pop('name', None)
    if name:
        pool.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        pool.set_description(description)

    size = kwargs.pop('size', None)
    if size:
        pool.set_size(size)

    cluster = kwargs.pop('cluster', None)
    if cluster:
        pool.set_cluster(CLUSTER_UTIL.find(cluster))

    template = kwargs.pop('template', None)
    if template:
        templObj = TEMPLATE_UTIL.find(template)
        pool.set_template(TEMPLATE(id=templObj.id))

    id = kwargs.pop('id', None)
    if id:
        pool.set_id(id)

    prestarted_vms = kwargs.pop('prestarted_vms', None)
    if prestarted_vms is not None:
        pool.set_prestarted_vms(prestarted_vms)

    max_user_vms = kwargs.pop('max_user_vms', None)
    if max_user_vms is not None:
        pool.set_max_user_vms(max_user_vms)

    return pool


@is_action()
def addVmPool(positive, wait=True, **kwargs):
    """
    Description: create vm pool
    __Author__ = edolinin, slitmano
    :param positive: True if action is expected to succeed False otherwise
    :type positive: bool
    :param wait: If True wait until VMs in pool are down, False otherwise
    :type wait: bool
    :param name: vmpool name
    :type name: str
    :param size: number of vms in pool
    :type size: int
    :param template: name of the template to base the pool on
    :type template: str
    :param description: vm pool description
    :type description: str
    :param prestarted_vms: number of prestarted vms in the pool
    :type prestarted_vms: int
    :param max_user_vms: max number of vms per user in pool
    :param max_user_vms: int
    :return: True if action result == positive, False otherwise
    :rtype: bool
    """
    size = kwargs.get('size', 0)
    pool = _prepareVmPoolObject(**kwargs)
    pool, status = UTIL.create(pool, positive)

    if not pool or isinstance(pool, ds.Fault):
        return positive is False

    time.sleep(int(size) * 3)

    vms_in_pool = get_vms_in_pool(pool)
    if not validator.compareCollectionSize(
        vms_in_pool, int(size), UTIL.logger
    ):
        return False
    if wait and positive and status:
        for vm in vms_in_pool:
            if not VM_UTIL.waitForElemStatus(
                vm, ENUMS['vm_state_down'], VM_ACTION_TIMEOUT
            ):
                return False
    return status is positive


@is_action()
def updateVmPool(positive, vmpool, **kwargs):
    """
    Description: update vm pool
    Author: edolinin
    :param positive: True if action is to end successfully, False otherwise
    :type positive: bool
    :param vmpool: VM pool name.
    :type vmpool: str
    :param size: number of vms in pool
    :type size: int
    :param template: name of the template to base the pool on
    :type template: str
    :param prestarted_vms: number of prestarted vms in the pool
    :type prestarted_vms: int
    :param max_user_vms: max number of vms per user in pool
    :param max_user_vms: int
    :param description: vm pool description
    :type description: str
    :return: True if update status == positive, False otherwise
    :rtype: bool
    """
    size = kwargs.get('size', 0)
    pool = UTIL.find(vmpool)
    pool_template = pool.template.id
    kwargs['template'] = TEMPLATE_UTIL.find(pool_template, 'id').name
    pool_cluster = pool.cluster.id
    kwargs['cluster'] = CLUSTER_UTIL.find(pool_cluster, 'id').name
    kwargs['id'] = pool.id
    pool_new_object = _prepareVmPoolObject(**kwargs)

    pool, status = UTIL.update(pool, pool_new_object, positive)

    if size and pool:
        time.sleep(size * 3)
        vms_in_pool = get_vms_in_pool(pool)
        if not validator.compareCollectionSize(vms_in_pool, size, UTIL.logger):
            return False
    return status


def _control_vms_in_pool(
    positive, vm_pool, action, max_workers=2, threading=False
):
    """
    Description: Common function for starting, stopping and detaching
    all VMs in a pool
    __Author__ = edolinin, alukiano, slitmano
    :param vm_pool: name of the pool
    :type vm_pool: str
    :param action: action to run on VMs, can be start, stop or detach
    :type action: str
    :param max_workers: max number of threads to be used
    :type max_workers: int
    :param threading: determines with to use threads or not
    :type threading: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    if action == ENUMS['start_vm']:
        action_function = vms.startVm
        expected_status = ENUMS['vm_state_up']
    elif action == ENUMS['stop_vm']:
        action_function = vms.stopVm
        expected_status = ENUMS['vm_state_down']
    elif action == ENUMS['detach_vm']:
        action_function = vms.detachVm
        expected_status = ENUMS['vm_state_down']
    else:
        raise ValueError("Unsupported action given")

    vms_list = get_vms_in_pool_by_name(vm_pool)
    if threading:
        results = list()
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for vm_name in vms_list:
                results.append(executor.submit(action_function, True, vm_name))
        test_utils.raise_if_exception(results)
    else:
        for vm_name in vms_list:
            if not vms.changeVMStatus(
                positive, vm_name, action, expected_status
            ):
                logger.warning(
                    "Failed to set status: %s for vm: %s",
                    expected_status, vm_name
                )
                return False
        if not vms.waitForVmsStates(
            positive, vms_list, states=expected_status
        ):
            logger.warning(
                "At least one vm from pool: %s has the wrong state,"
                " expected: %s." % (vm_pool, expected_status)
            )
            return False
    return True


@is_action()
def start_vm_pool(positive, vm_pool):
    """
    Wrapper for starting all VMs in a pool
    :param positive: positive or negative result expected
    :type positive: bool
    :param vm_pool: name of the pool
    :type vm_pool: str
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(positive, vm_pool, "start")


@is_action()
def stopVmPool(positive, vm_pool):
    """
    Wrapper for stopping all VMs in a pool
    :param positive: positive or negative result expected
    :type positive: bool
    :param vm_pool: name of the pool
    :type vm_pool: str
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(positive, vm_pool=vm_pool, action="stop")


@is_action()
def detachVms(positive, vm_pool, stop_vms=False):
    """
    Wrapper for detaching all VMs in a pool
    :param positive: positive or negative result expected
    :type positive: bool
    :param vm_pool: name of the pool
    :type vm_pool: str
    :param stop_vms: False by default - stops vms before detaching from pool
    :type stop_vms: bool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    ret = True
    if stop_vms:
        ret = _control_vms_in_pool(positive, vm_pool, "stop")
    return ret and _control_vms_in_pool(positive, vm_pool, "detach")


def get_vms_in_pool(vm_pool):
    """
    Description: returns a list of vm objects attached to the vm_pool
    :param vm_pool: vm pool object
    :type VmPool object
    :return: list of VMs in pool (Vm objects)
    :rtype: list
    """
    vms_in_pool = list()
    for vm in VM_UTIL.get(absLink=False):
        if not hasattr(vm, "vmpool"):
            continue
        if vm.get_vmpool() and (vm.get_vmpool().get_id() == vm_pool.get_id()):
            vms_in_pool.append(vm)
    return vms_in_pool


def get_vms_in_pool_by_name(vm_pool):
    """
    Description: returns a list of the pool's vm names
    :param vm_pool: name of vm pool
    :type vm_pool: str
    :return: list of VM names
    :rtype: list
    """
    vm_pool_object = UTIL.find(vm_pool)
    vms_object_list = get_vms_in_pool(vm_pool_object)
    return [vm_obj.get_name() for vm_obj in vms_object_list]


@is_action()
def removeVmPool(positive, vmpool):
    """
    Description: remove vm pool
    Author: edolinin
    :param positive: positive or negative result expected
    :type positive: bool
    :param vmpool:  vmpool name
    :type vmpool: str
    :return: True if update status == positive, False otherwise
    :rtype: bool
    """
    pool = UTIL.find(vmpool)
    status = UTIL.delete(pool, positive)

    return status


def allocateVmFromPool(positive, vmpool):
    """
    Description: Allocate vm from pool
    :param positive: True if action is expected to succeed False otherwise
    :type positive: bool
    :param vmpool: VM pool name
    :type vmpool: str
    :return: True if update status == positive, False otherwise
    :rtype: bool
    """
    pool = UTIL.find(vmpool)

    return bool(UTIL.syncAction(pool, 'allocatevm', positive))


def does_vm_pool_exist(vmpool_name):
    """
    __Author__= slitmano
    Checks if a vm pool with given name exist
    :param vmpool_name: name of vm pool
    :type vmpool_name: str
    :return: True if vm pool exist, False if not
    :rtype: bool
    """
    try:
        UTIL.find(vmpool_name)
    except exceptions.EntityNotFound:
        return False
    return True


def get_vm_pool_size(vmpool):
    """
    __Author__ = slitmano
    function gets the size of the given vm_pool
    :param vmpool: name of the vmpool
    :type vmpool: str
    :return: returns the size of the vm pool, otherwise raises Entity not found
    :rtype: int
    :raises EntityNotFound
    """
    return UTIL.find(vmpool).get_size()


def get_vm_pool_number_of_prestarted_vms(vmpool):
    """
    __Author__ = slitmano
    function gets the number of prestarted vms defined for the pool
    :param vmpool: name of the vmpool
    :type vmpool: str
    :return: returns the  number of prestarted vms defined for the pool
     otherwise raises Entity not found
    :rtype: int
    :raises EntityNotFound
    """
    return UTIL.find(vmpool).get_prestarted_vms()


def get_vm_pool_max_user_vms(vmpool):
    """
    __Author__ = slitmano
    function gets max number of vms per user defined for the pool
    :param vmpool: name of the vmpool
    :type vmpool: str
    :return: returns the max number of vms per user defined for the pool
     otherwise raises Entity not found
    :rtype: int
    :raises EntityNotFound
    """
    return UTIL.find(vmpool).get_max_user_vms()


def get_vms_in_pool_by_states(vmpool, states):
    """
    __Author__ = slitmano
    This function returns all the vms in pool with state in states
    :param vmpool: Name of vmPool
    :type vmpool: str
    :param states: a list of possible states to check
    :type states: list
    :return: vm objects of vms in pool with state in states
    :rtype: vm object
    """
    if states is None:
        states = [ENUMS['vm_state_up'], ENUMS['vm_state_powering_up']]
    vm_pool_object = UTIL.find(vmpool)
    pool_vms = get_vms_in_pool(vm_pool_object)
    found_pool_vms = list()
    for vm in pool_vms:
        if vm.get_status().get_state() in states:
            found_pool_vms.append(vm)
    return found_pool_vms
