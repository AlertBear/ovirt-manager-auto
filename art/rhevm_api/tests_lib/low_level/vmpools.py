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
from concurrent.futures import ThreadPoolExecutor

import time
from art.core_api.apis_utils import getDS
from art.rhevm_api.utils import test_utils
from art.rhevm_api.data_struct.data_structures import Fault
from art.core_api.validator import compareCollectionSize
from art.rhevm_api.tests_lib.low_level import vms
from art.core_api import is_action

ELEMENT = 'vmpool'
COLLECTION = 'vmpools'
util = test_utils.get_api(ELEMENT, COLLECTION)
vmUtil = test_utils.get_api('vm', 'vms')
clUtil = test_utils.get_api('cluster', 'clusters')
templUtil = test_utils.get_api('template', 'templates')

VmPool = getDS('VmPool')
Template = getDS('Template')


def _prepareVmPoolObject(**kwargs):

    pool = VmPool()

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
        pool.set_cluster(clUtil.find(cluster))

    template = kwargs.pop('template', None)
    if template:
        templObj = templUtil.find(template)
        pool.set_template(Template(id=templObj.id))

    id = kwargs.pop('id', None)
    if id:
        pool.set_id(id)

    return pool


@is_action()
def addVmPool(positive, **kwargs):
    '''
    Description: create vm pool
    Author: edolinin
    Parameters:
     * name - vm pool name
     * size - number of vms in pool
     * cluster - vm pool cluster
     * template - template for vm creation
     * description - vm pool description
    Return: status (True if vm pool was added properly, False otherwise)
    '''
    size = kwargs.get('size', 0)
    pool = _prepareVmPoolObject(**kwargs)
    pool, status = util.create(pool, positive)

    if not pool or isinstance(pool, Fault):
        return positive is False

    time.sleep(int(size) * 3)

    vms_in_pool = []
    for vm in vmUtil.get(absLink=False):
        if not hasattr(vm, "vmpool"):
            continue
        if vm.get_vmpool() and (vm.get_vmpool().get_id() == pool.get_id()):
            vms_in_pool.append(vm)

    compareCollectionSize(vms_in_pool, int(size), util.logger)
    return status


@is_action()
def updateVmPool(positive, vmpool, **kwargs):
    '''
    Description: update vm pool
    Author: edolinin
    Parameters:
       * vmpool - name of vm pool that should be updated
       * name - new vm pool name
       * description - new vm pool description
    Return: status (True if vm pool was updated properly, False otherwise)
    '''
    size = kwargs.get('size', 0)
    pool = util.find(vmpool)
    poolTemp = pool.template.id
    kwargs['template'] = templUtil.find(poolTemp, 'id').name
    poolCl = pool.cluster.id
    kwargs['cluster'] = clUtil.find(poolCl, 'id').name
    kwargs['id'] = pool.id
    poolNew = _prepareVmPoolObject(**kwargs)

    pool, status = util.update(pool, poolNew, positive)

    if size and pool:
        time.sleep(size * 3)
        vms_in_pool = []
        for vm in vmUtil.get(absLink=False):
            if not hasattr(vm, "vmpool"):
                continue
            if vm.vmpool and vm.vmpool.id == pool.get_id():
                vms_in_pool.append(vm)

        compareCollectionSize(vms_in_pool, size, util.logger)

    return status


def _control_vms_in_pool(vm_pool, action, max_workers=2):
    """
    Description: Common function for starting, stopping and detaching
    all VMs in a pool

    :param vm_pool: name of the pool
    :param action: action to run on VMs, can be start, stop or detach
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    if action == "start":
        action_function = vms.startVm
    elif action == "stop":
        action_function = vms.stopVm
    elif action == "detach":
        action_function = vms.detachVm
    else:
        raise ValueError("Unsupported action given")

    pool = util.find(vm_pool)
    vms_list = []
    for vm in vmUtil.get(absLink=False):
        if vm.get_vmpool() and vm.get_vmpool().get_id() == pool.get_id():
            vms_list.append(vm.get_name())
    results = list()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for vm_name in vms_list:
            results.append(executor.submit(action_function, True, vm_name))
    test_utils.raise_if_exception(results)
    return True


@is_action()
def start_vm_pool(vm_pool):
    """
    Wrapper for starting all VMs in a pool

    :param vm_pool: name of the pool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(vm_pool, "start")


@is_action()
def stopVmPool(positive, vm_pool):
    """
    Wrapper for stopping all VMs in a pool

    :param vm_pool: name of the pool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(vm_pool, "stop")


@is_action()
def detachVms(positive, vm_pool):
    """
    Wrapper for detaching all VMs in a pool

    :param vm_pool: name of the pool
    :return: True if every operation was successful, False otherwise
    :rtype: bool
    """
    return _control_vms_in_pool(vm_pool, "detach")


@is_action()
def removePooledVms(positive, name, vm_total, vm_to_remove=-1):
    '''
    Description: Remove the VMs that were in a pool
    Author: adarazs
    Parameters:
      * name - base name of the pool
      * vm_total - the total number of VMs in the pool
      * vm_to_remove - the number of VMs to remove, starting from the
                       high end of the list (if it's -1, then remove all)
    Returns: True if all VMs were removed, false otherwise.
    '''
    vm_list = []
    for i in range(vm_total):
        vm_number = str(i + 1)
        vm_list.append("%s-%s" % (name, vm_number))
    if vm_to_remove == -1:
        vms_to_remove = ",".join(vm_list)
    else:
        vms_to_remove = ",".join(vm_list[-vm_to_remove:])
    return vms.removeVms(True, vms_to_remove)


@is_action()
def removeVmPool(positive, vmpool):
    '''
    Description: remove vm pool
    Author: edolinin
    Parameters:
       * vmpool - name of vm pool
    Return: status (True if vm pool was removed properly, False otherwise)
    '''

    pool = util.find(vmpool)
    status = util.delete(pool, positive)

    return status


@is_action()
def searchForVmPool(positive, query_key, query_val, key_name, **kwargs):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    return test_utils.searchForObj(
        util, query_key, query_val, key_name, **kwargs
    )


def allocateVmFromPool(positive, vmpool):
    '''
    Description: Allocate vm from pool
    Parameters:
      * vmpool - name of pool, where vm should be allocated
    Returns: True if operation was successful, false otherwise.
    '''
    pool = util.find(vmpool)

    return util.syncAction(pool, 'allocatevm', positive)


def removeWholeVmPool(positive, vmpool, size,
                      remove_vms=True, detach_timeout=5):
    """
    Description: Detach vms, remove them and remove vm pool.
    Parameters:
      * vmpool - name of pool which should be removed
      * size - number of vms in pool
      * remove_vms - remove all pooled vms
      * detach_timeout - how long wait for vms to be detached
    Returns: True if operation was successful, false otherwise.
    """
    ret = detachVms(positive, vmpool)
    if not ret:
        return not positive
    time.sleep(detach_timeout)
    if remove_vms:
        ret = removePooledVms(positive, vmpool, size)
        if not ret:
            return not positive
    ret = removeVmPool(positive, vmpool)
    if not ret:
        return not positive
    return positive