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

from core_api.apis_utils import getDS
from rhevm_api.utils.test_utils import get_api
import re
from core_api.validator import compareCollectionSize
from vms import detachVm, startVm, stopVm, removeVms
import time
import re
from utilities.jobs import Job, JobsSet
from rhevm_api.utils.test_utils import searchForObj

ELEMENT = 'vmpool'
COLLECTION = 'vmpools'
util = get_api(ELEMENT, COLLECTION)
vmUtil = get_api('vm', 'vms')
clUtil = get_api('cluster', 'clusters')
templUtil = get_api('template', 'templates')

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

    if not pool:
        return positive == False

    time.sleep(int(size)*3)

    vms_in_pool = []
    for vm in vmUtil.get(absLink=False):
        if not hasattr(vm, "vmpool"):
            continue
        if vm.get_vmpool() and (vm.get_vmpool().get_id() == pool.get_id()):
            vms_in_pool.append(vm)

    compareCollectionSize(vms_in_pool, int(size), util.logger)
    return status


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
        time.sleep(size*3)
        vms_in_pool = []
        for vm in vmUtil.get(absLink=False):
            if not hasattr(vm, "vmpool"):
                continue
            if vm.vmpool and vm.vmpool.id == pool.get_id():
                vms_in_pool.append(vm)

        compareCollectionSize(vms_in_pool, size, util.logger)

    return status


def _controlVMsInPool(positive, vmpool, action):
    '''
    Description: Common function for starting, stopping and detaching
    all VMs in a pool.
    Author: adarazs
    Parameters:
      * vmpool - name of the pool
      * action - action to run on VMs, can be start, stop or detach
    Returns: True if every operation was successful, false otherwise.
    '''
    if action == "start":
        action_function = startVm
    elif action == "stop":
        action_function = stopVm
    elif action == "detach":
        action_function = detachVm
    else:
        raise ValueError("Unsupported action given")
    
    pool = util.find(vmpool)

    vms = []
    for vm in vmUtil.get(absLink=False):
        if vm.get_vmpool() and vm.get_vmpool().get_id() == pool.get_id():
            vms.append(vm.get_name())
            
    jobs = [Job(target=action_function, args=(True, vm)) for vm in vms]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        if not job.result:
            status = False
            util.logger.error('Operation %s failed on VM %s', action, job.args[1])
    return status


def startVmPool(positive, vmpool):
    '''
    Description: Wrapper for starting all VMs in a pool.
    Author: adarazs
    Parameters:
      * vmpool - name of the pool
    Returns: True if every operation was successful, false otherwise.
    '''
    return _controlVMsInPool(positive, vmpool, "start")


def stopVmPool(positive, vmpool):
    '''
    Description: Wrapper for stopping all VMs in a pool.
    Author: adarazs
    Parameters:
      * vmpool - name of the pool
    Returns: True if every operation was successful, false otherwise.
    '''
    return _controlVMsInPool(positive, vmpool, "stop")


def detachVms(positive, vmpool):
    '''
    Description: Wrapper for detaching all VMs in a pool.
    Author: adarazs
    Parameters:
      * vmpool - name of the pool
    Returns: True if every operation was successful, false otherwise.
    '''
    return _controlVMsInPool(positive, vmpool, "detach")


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
    vm_decimal_places = len(str(vm_total))
    vmlist = []
    for i in range(vm_total):
        vm_number = str(i + 1).zfill(vm_decimal_places)
        vmlist.append("%s-%s" % (name, vm_number))
    if vm_to_remove == -1:
        vms = ",".join(vmlist)
    else:
        vms = ",".join(vmlist[-vm_to_remove:])
    return removeVms(True, vms)


def removeVmPool(positive, vmpool):
    '''
    Description: remove vm pool
    Author: edolinin
    Parameters:
       * vmpool - name of vm pool
    Return: status (True if vm pool was removed properly, False otherwise)
    '''

    pool = util.find(vmpool)
    status = util.delete(pool,positive)

    return status


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

    return searchForObj(util, query_key, query_val, key_name, **kwargs)

