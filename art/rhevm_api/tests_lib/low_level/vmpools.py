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
import art.core_api.validator as validator
import art.rhevm_api.utils.test_utils as test_utils
from art.rhevm_api.tests_lib.low_level import (
    general as ll_general,
    vms as ll_vms,
)
from art.test_handler.settings import ART_CONFIG
import art.core_api.apis_exceptions as exceptions

ELEMENT = 'vm_pool'
COLLECTION = 'vmpools'
ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
UTIL = test_utils.get_api(ELEMENT, COLLECTION)
VM_UTIL = test_utils.get_api('vm', 'vms')
CLUSTER_UTIL = test_utils.get_api('cluster', 'clusters')
TEMPLATE_UTIL = test_utils.get_api('template', 'templates')

VM_POOL = api_utils.getDS('VmPool')
VM = api_utils.getDS('Vm')
TEMPLATE = api_utils.getDS('Template')

logger = logging.getLogger("art.ll_lib.vmpools")

VM_ACTION_TIMEOUT = 600
VM_POOL_ACTION_TIMEOUT = 600


def _prepareVmPoolObject(**kwargs):
    """
    Prepares the pool object

    Keyword Arguments:
        name (str): vmpool name
        size (int): number of vms in pool
        template (str): name of the template to base the pool on
        description (str): vm pool description
        prestarted_vms (int): number of prestarted vms in the pool
        max_user_vms (int): max number of vms per user in pool
        stateful (bool): pool state
        custom_cpu_model (str): Name of custom cpu model to start vm with
        custom_emulated_machine (str): Name of custom emulated machine type to
        Initialization (Initialization):  Initialization obj for cloud init

    Returns:
        VmPool: Returns a VmPool object with relevant attributes
    """
    pool = VM_POOL()
    vm = VM()

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

    type_ = kwargs.pop('type_', None)
    if type_:
        pool.set_type(type_)

    prestarted_vms = kwargs.pop('prestarted_vms', None)
    if prestarted_vms is not None:
        pool.set_prestarted_vms(prestarted_vms)

    max_user_vms = kwargs.pop('max_user_vms', None)
    if max_user_vms is not None:
        pool.set_max_user_vms(max_user_vms)

    stateful = kwargs.pop('stateful', None)
    if stateful is not None:
        pool.set_stateful(stateful)

    custom_cpu_model = kwargs.get("custom_cpu_model")
    if custom_cpu_model is not None:
        vm.set_custom_cpu_model(custom_cpu_model)

    custom_emulated_machine = kwargs.get("custom_emulated_machine")
    if custom_emulated_machine is not None:
        vm.set_custom_emulated_machine(custom_emulated_machine)

    # initialization
    initialization = kwargs.pop("initialization", None)
    if initialization:
        vm.set_initialization(initialization)

    pool.set_vm(vm)
    return pool


@ll_general.generate_logs(step=True)
def addVmPool(positive, wait=True, **kwargs):
    """
    Description: create vm pool

    __Author__ = edolinin, slitmano

    Args:
        positive (bool): True if action is expected to succeed False otherwise
        wait (bool): If True wait until VMs in pool are down, False otherwise

    Keyword Arguments:
        name (str): vmpool name
        size (int): number of vms in pool
        template (str): name of the template to base the pool on
        description (str): vm pool description
        prestarted_vms (int): number of prestarted vms in the pool
        max_user_vms (int): max number of vms per user in pool
        stateful (bool): pool state
        custom_cpu_model (str): Name of custom cpu model to start vm with
        custom_emulated_machine (str): Name of custom emulated machine type to
        Initialization (Initialization):  Initialization obj for cloud init

    Returns:
        bool: True if action result == positive, False otherwise
    """
    size = kwargs.get('size', 0)
    pool = _prepareVmPoolObject(**kwargs)
    pool, status = UTIL.create(pool, positive)

    if not status:
        return False

    if positive is False:
        return True

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


def updateVmPool(positive, vmpool, **kwargs):
    """
    Description: update vm pool.

    Author: edolinin.

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
    log_info, log_error = ll_general.get_log_msg(
        log_action="update", obj_type="vmpool", obj_name=vmpool,
        positive=positive, **kwargs
    )
    logger.info(log_info)
    pool, status = UTIL.update(pool, pool_new_object, positive)
    if not status:
        logger.error(log_error)
        return False
    if size and pool:
        time.sleep(size * 3)
        vms_in_pool = get_vms_in_pool(pool)
        if not validator.compareCollectionSize(vms_in_pool, size, UTIL.logger):
            return False
    return status


def get_vms_in_pool(vm_pool):
    """
    Description: returns a list of vm objects attached to the vm_pool

    :param vm_pool: vm pool object
    :type vm_pool: VmPool object
    :return: list of VMs in pool (Vm objects)
    :rtype: list
    """
    vms_in_pool = list()
    for vm in VM_UTIL.get(abs_link=False):
        if not hasattr(vm, "vm_pool"):
            continue
        if vm.get_vm_pool() and (
            vm.get_vm_pool().get_id() == vm_pool.get_id()
        ):
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


@ll_general.generate_logs(step=True)
def removeVmPool(positive, vmpool, wait=False):
    """
    Description: remove vm pool

    Author: edolinin

    :param positive: positive or negative result expected
    :type positive: bool
    :param vmpool:  vmpool name
    :type vmpool: str
    :param wait: If True wait for all vms in the pool to be removed, otherwise
        return delete status.
    :type wait: bool
    :return: True if status == positive, False otherwise.
    :rtype: bool
    """
    pool = UTIL.find(vmpool)
    pool_vms = get_vms_in_pool_by_name(vmpool)
    status = UTIL.delete(pool, positive)
    if wait and positive:
        try:
            ll_vms.waitForVmsGone(positive, pool_vms)
        except exceptions.APITimeout:
            return False
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
    if get_vm_pool_object(vmpool_name) is None:
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


def get_vm_pool_type(vmpool):
    """
    __Author__ = slitmano

    function returns the pool type (manual or automatic)

    :param vmpool: name of the vmpool
    :type vmpool: str
    :return: returns the pool type (manual or automatic)
    :rtype: str
    """
    return UTIL.find(vmpool).get_type()


def get_vms_in_pool_by_states(vmpool, states):
    """
    __Author__ = slitmano

    This function returns all the vms in pool with state in states

    :param vmpool: Name of vmPool
    :type vmpool: str
    :param states: a list of possible states to check
    :type states: list
    :return: vm objects of vms in pool with state in states
    :rtype: object
    """
    if states is None:
        states = [ENUMS['vm_state_up'], ENUMS['vm_state_powering_up']]
    vm_pool_object = UTIL.find(vmpool)
    pool_vms = get_vms_in_pool(vm_pool_object)
    found_pool_vms = list()
    for vm in pool_vms:
        if vm.get_status() in states:
            found_pool_vms.append(vm)
    return found_pool_vms


def get_vm_pool_object(vm_pool):
    """
    Returns the vm pool object corresponding to the input name, returns None
    if such vm pool name doesn't exist in the system.

    :param vm_pool: vm pool name
    :type vm_pool: str
    :return: The vm pool object if one exist, else None
    :rtype: object
    """
    try:
        vm_pool_obj = UTIL.find(vm_pool)
    except exceptions.EntityNotFound:
        return None
    return vm_pool_obj


def get_all_vm_pools():
    """
    Get list of vm pool objects from API

    Returns:
        list: Vm pool objects
    """
    logger.info("Getting all vm pools in the system")
    return UTIL.get(abs_link=False)


def get_all_vm_pools_names():
    """
    Get list of all VMPools names from API

    Returns:
        list: all VMPools names
    """
    return [vmpool.get_name() for vmpool in get_all_vm_pools()]
