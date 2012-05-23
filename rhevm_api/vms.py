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

import os.path
import time
import logging
from utils.apis_utils import data_st
from rhevm_api.test_utils import get_api
from utils.apis_utils import TimeoutingSampler
from utilities.utils import readConfFile
import re
from utils.validator import compareCollectionSize
from utils.apis_exceptions import APITimeout

GBYTE = 1024*1024*1024
ELEMENTS = os.path.join(os.path.dirname(__file__), '../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
VM_ACTION_TIMEOUT = 180
VM_IMAGE_OPT_TIMEOUT = 300
VM_SAMPLING_PERIOD = 3
ADD_DISK_KWARGS = ['size', 'type', 'interface', 'format', 'bootable',
                   'sparse', 'wipe_after_deletion', 'propagate_errors']

VM_API = get_api('vm', 'vms')
CLUSTER_API = get_api('cluster', 'clusters')
TEMPLATE_API = get_api('template', 'templates')
HOST_API = get_api('host', 'hosts')
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')
DISKS_API = get_api('disk', 'disks')
logger = logging.getLogger(__package__ + __name__)


def _prepareVmObject(**kwargs):

    add = kwargs.pop('add', False)

    vm = data_st.VM(name=kwargs.pop('name', None),
                    description=kwargs.pop('description', None),
                    memory=kwargs.pop('memory', GBYTE if add else None))

    #cluster
    cluster_name = kwargs.pop('cluster', DEFAULT_CLUSTER if add else None)
    cluster_id = kwargs.pop('clusterUuid', None)
    search_by = NAME_ATTR
    if cluster_id:
        cluster_name = cluster_id
        search_by = ID_ATTR
    if cluster_name:
        cluster = CLUSTER_API.find(cluster_name, search_by)
        vm.set_cluster(cluster)

    # cpu topology
    cpu_socket = kwargs.pop('cpu_socket', 1 if add else None)
    cpu_cores = kwargs.pop('cpu_cores', 1 if add else None)
    vm.set_cpu(data_st.CPU(topology=data_st.CpuTopology(sockets=cpu_socket,
            cores=cpu_cores)))

    # os options
    os = data_st.OperatingSystem(type_=kwargs.pop('os_type',
        ENUMS['unassigned'] if add else None))
    for opt_name in 'kernel', 'initrd', 'cmdline':
        opt_val = kwargs.pop(opt_name, None)
        setattr(os, opt_name, opt_val)
    boot_seq = kwargs.pop('boot', 'hd' if add else None)
    if boot_seq:
        boot_seq = boot_seq.split()
        os.set_boot([data_st.Boot(dev=boot_dev) for boot_dev in boot_seq])
    vm.set_os(os)

    # template
    template_name = kwargs.pop('template', 'Blank' if add else None)
    template_id = kwargs.pop('templateUuid', None)
    search_by = NAME_ATTR
    if template_id:
        template_name = template_id
        search_by = ID_ATTR
    if template_name:
        template = TEMPLATE_API.find(template_name, search_by)
        vm.set_template(template)

    # type
    vm.set_type(kwargs.pop('type', ENUMS['vm_type_desktop'] if add else None))

    # display
    display_type = kwargs.pop('display_type',
        ENUMS['display_type_spice'] if add else None)
    display_monitors = kwargs.pop('display_monitors', 1 if add else None)
    vm.set_display(data_st.Display(type_=display_type,
            monitors=display_monitors))

    # stateless
    vm.set_stateless(kwargs.pop('stateless', None))

    # high availablity
    ha = kwargs.pop('highly_available', None)
    ha_priority = kwargs.pop('availablity_priority', None if add else None)
    vm.set_high_availability(data_st.HighAvailability(enabled=ha,
            priority=ha_priority))

    # custom properties
    custom_prop = kwargs.pop('custom_properties', None)
    if custom_prop:
        vm.set_custom_properties(_createCustomPropertiesFromArg(custom_prop))

    # memory policy
    vm.set_memory_policy(data_st.VmMemoryPolicy(guaranteed=
        kwargs.pop('memory_guaranteed', None)))

    # placement policy
    ppolicy = data_st.VmPlacementPolicy(affinity=
        kwargs.pop('placement_affinity', None))
    phost = kwargs.pop('placement_host', None)
    if phost and phost != ENUMS['placement_host_any_host_in_cluster']:
        aff_host = HOST_API.find(phost)
        ppolicy.set_host(aff_host)
    vm.set_placement_policy(ppolicy)

    # storagedomain
    sd_name = kwargs.pop('storagedomain', None)
    if sd_name:
        sd = STORAGE_DOMAIN_API.find(sd_name)
        vm.set_storage_domain(sd)

    # domain name
    vm.set_domain(data_st.Domain(name=kwargs.pop('domainName', None)))
    return vm

def _createCustomPropertiesFromArg(prop_arg):
    cps = data_st.CustomProperties()
    props = prop_arg.split(';')
    for prop in props:
        try:
            name, value = prop.split('=', 1)
        except ValueError:
            E = "Custom Properties should be in form " \
                "'name1=value1;name2=value2'. Got '%s' instead."
            raise Exception(E % arg)
        cps.add_custom_property(data_st.CustomProperty(name=name, value=value))
    return cps


def addVm(positive, **kwargs):
    '''
    Description: add new vm
    Parameters:
       * name - name of a new vm
       * description - vm description
       * cluster - vm cluster
       * memory - vm memory size in bytes
       * cpu_socket - number of cpu sockets
       * cpu_cores - number of cpu cores
       * os_type - OS type of new vm
       * boot - type of boot
       * template - name of template that should be used
       * type - vm type (SERVER or DESKTOP)
       * display_type - type of vm display (VNC or SPICE)
       * display_monitors - number of display monitors
       * kernel - kernel path
       * initrd - initrd path
       * cmdline - kernel paramters
       * placement_affinity - vm to host affinity
       * placement_host - host that the affinity holds for
       * highly_available - if to set high-availablity for vm
       * availablity_priority - availablity priority
       * custom_properties - custom properties set to the vm
       * stateless - if vm stateless or not
       * templateUuid - id of template to be used
       * memory_guaranteed - size of guaranteed memory in bytes
       * wait - When True wait until end of action,False return without waiting
       * clusterUuid - uuid of cluster
       * storagedomain - name of storagedomain
       * disk_type - type of disk to add to vm
       * disk_clone - defines whether disk should be cloned from template
       * disk parameters - same as in addDisk function
       * domainName = sys.prep domain name
    Return: status (True if vm was added properly, False otherwise)
    '''
    kwargs.update(add=True)
    vmObj = _prepareVmObject(**kwargs)
    vmObj, status = VM_API.create(vmObj, positive)
    return status

def updateVm(positive, vm, **kwargs):
    '''
    Description: update existed vm
    Parameters:
       * vm - name of vm
       * name - new vm name
       * description - new vm description
       * data_center - new vm data center
       * cluster - new vm cluster
       * memory - vm memory size in bytes
       * cpu_socket - number of cpu sockets
       * cpu_cores - number of cpu cores
       * os_type - OS type of new vm
       * boot - type of boot
       * template - name of template that should be used
       * type - vm type (SERVER or DESKTOP)
       * display_type - type of vm display (VNC or SPICE)
       * display_monitors - number of display monitors
       * kernel - kernel path
       * initrd - initrd path
       * cmdline - kernel parameters
       * highly_available - set high-availability for vm ('true' or 'false')
       * ha_priority - priority for high-availability (an integer in range
                       0-100 where 0 - Low, 50 - Medium, 100 - High priority)
       * custom_properties - custom properties set to the vm
       * stateless - if vm stateless or not
       * memory_guaranteed - size of guaranteed memory in bytes
       * domainName = sys.prep domain name
       * placement_affinity - vm to host affinity
       * placement_host - host that the affinity holds for
    Return: status (True if vm was updated properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    vmNewObj = _prepareVmObject(**kwargs)
    vmNewObj, status = VM_API.update(vmObj, vmNewObj, positive)
    return status

def removeVm(positive, vm, **kwargs):
    '''
    Description: remove vm
    Parameters:
       * vm - name of vm
       * force - force remove if True
       * stopVM - stop VM before removal
       * wait - wait for removal if True
       * timeout - waiting timeout
       * waitTime - waiting time interval
    Return: status (True if vm was removed properly, False otherwise)
    '''
    opts = dict()
    force = kwargs.pop('force', None)
    if force:
        action = data_st.Action(force=True)
        opts.update(action=action)

    vmObj = VM_API.find(vm)
    stopVM = kwargs.pop('stopVM', 'false')
    if stopVM.lower() == 'true' and vmObj.status.state.lower() != 'down':
        if not stopVm(positive, vm):
            return False
    status = VM_API.delete(vmObj, positive, **opts)

    wait = kwargs.pop('wait', False)
    if positive and wait and status:
        return waitForVmsGone(positive, vm, kwargs.pop('timeout', 60),
                kwargs.pop('waitTime', 10))
    return status

def removeVmAsynch(positive, tasksQ, resultsQ, stopVm=False):
    '''
    Removes the cluster. It's supposed to be a worker of Thread.
    Author: jhenner
    Parameters:
        * tasksQ - A input Queue of VM names to remove
        * resultsQ - A output Queue of tuples tuple(VM name, VM removal status).
        * stopVm - if True will attempt to stop VM before actually remove it (False by default)
    '''
    vm = tasksQ.get(True)
    status = False
    try:
        vmObj = VM_API.find(vm)
        if stopVm and vmObj.status.state.lower() != 'down':
            if not stopVm(positive, vm):
                logger.error("failed to stop vm %s before async removal", vm)
                return

        status = VM_API.delete(vmObj, positive)
    except EntityNotFound as e:
        logger.error(str(e))
    finally:
        resultsQ.put((vm, status))
        tasksQ.task_done()

def removeVms(positive, vms, stop='false'):
    '''
    Removes the VMs specified by `vms` commas separated list of VM names.
    Author: jhenner
    Parameters:
        * vms - Comma (no space) separated list of VM names.
        * stop - will attempt to stop VMs if 'true' ('false' by default)
    '''
    assert positive
    tasksQ = Queue()
    resultsQ = Queue()
    threads = set()
    vmsList = split(vms)
    num_worker_threads = len(vmsList)
    for i in range(num_worker_threads):
        t = Thread(target=removeVmAsynch, name='VM removing',
                args=(positive, tasksQ, resultsQ, (stop.lower() == 'true')))
        threads.add(t)
        t.daemon = False
        t.start()

    for vm in vmsList:
        tasksQ.put(vm)
    tasksQ.join() # block until all tasks are done
    logger.info(threads)
    for t in threads:
        t.join()

    status = True
    while not resultsQ.empty():
        vm, removalOK = resultsQ.get()
        if removalOK:
            logger.info("VM '%s' deleted asynchronously." % vm)
        else:
            logger.error("Failed to asynchronously remove VM '%s'." % vm)
        status &= removalOK
    return status and waitForVmsGone(positive, vms)

def waitForVmsGone(positive, vms, timeout=30, samplingPeriod=5):
    '''
    Wait for VMs to disappear from the setup. This function will block up to `timeout`
    seconds, sampling the VMs list every `samplingPeriod` seconds, until no VMs
    specified by names in `vms` exists.

    Author: jhenner
    Parameters:
        * vms - comma (and no space) separated string of VM names to wait for.
        * timeout - Time in seconds for the vms to disapear.
        * samplingPeriod - Time in seconds for sampling the vms list.
    '''
    t_start = time.time()
    # Construct a xpath query. For VMs Default and RestVM it would be:
    # /vms/vm[./name="Default" or ./name="RestVM"]
    vmsList = vms.split(',')
    QUERY = '/vms/vm[%s]' % \
                ' or '.join([ './name="%s"' % vm for vm in vmsList ])
    while time.time() - t_start < timeout and 0 < timeout:
        remainingVms = VM_API.getAndXpathEval(VM_API.get(absLink=False), QUERY)
        logger.info("Waiting for %d VMs to disappear.", len(remainingVms))
        if not len(remainingVms):
            logger.info("All %d VMs are gone.", len(vmsList))
            return positive
        time.sleep(samplingPeriod)
    remainingVmsNames = [vm.name for vm in remainingVms]
    logger.error("VMs %s didn't disappear until timeout." % remainingVmsNames)
    return not positive

def changeVMStatus(positive, vm, action, expectedStatus, async='true'):
    '''
    Description: change vm status
    Author: edolinin
    Parameters:
       * positive - indicates positive/negative test's flow
       * vm - name of vm
       * action - action that should be run on vm (start/stop/suspend/shutdown)
       * expectedStatus - status of vm in case the action succeeded
       * async - don't wait for VM status if 'true' ('false' by default)
    Return: status (True if vm status is changed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)

    asyncMode = async.lower() == 'true'
    status = VM_API.syncAction(vmObj, action, positive, async)
    if status and positive and not asyncMode:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)
    return status

def startVm(positive, vm, wait_for_status=ENUMS['vm_state_powering_up']):
    '''
    Description: start vm
    Author: edolinin
    Parameters:
       * vm - name of vm
       * wait_for_status - vm status should wait for (default is "powering_up")

           List of available statuses/states of VM:
           [unassigned, up, down, powering_up, powering_down,
           paused, migrating_from, migrating_to, unknown,
           not_responding, wait_for_launch, reboot_in_progress,
           saving_state, restoring_state, suspended,
           image_illegal, image_locked]

    NOTE: positive="false" or wait_for_status=None implies no wait for VM status
    Return: status (True if vm was started properly, False otherwise)
    '''
    if not positive:
        wait_for_status = None

    vmObj = VM_API.find(vm)

    if not VM_API.syncAction(vmObj, 'start', positive):
        return False

    if wait_for_status is None:
        return True

    sampler = TimeoutingSampler(VM_ACTION_TIMEOUT, 10, VM_API.getAndXpathEval)
    sampler.func_args = (vmObj,
                         '/vm[status/state="%s"]' % wait_for_status.lower())
    try:
        for statusOk in sampler:
            if statusOk:
                return True
    except APITimeout as e:
        logger.error('Timeouted when waiting for vm %s status to be %s',
                     vm, wait_for_status)
        return False

def startVms(vms, wait_for_status=ENUMS['vm_state_powering_up']):
    '''
    Start several vms simultaneously. Only action response is checked, no
    checking for vm UP status is performed.

    Parameters:
      * vms - Names of VMs to start.
    Returns: True iff all VMs started.
    '''
    jobs = [Job(target=startVm, args=(True, vm, wait_for_status)) for vm in split(vms)]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        if job.exception:
            status = False
            logger.error('Starting vm %s failed: %s.',
                            job.args[1], job.exception)
        elif not job.result:
            status = False
            logger.error('Starting %s failed.', job.args[1])
        else:
            logger.info('Starting vm %s succeed.', job.args[1])
    return status

def stopVm(positive, vm, async='false'):
    '''
    Description: stop vm
    Author: edolinin
    Parameters:
       * vm - name of vm
       * async - stop VM asynchronously if 'true' ('false' by default)
    Return: status (True if vm was stopped properly, False otherwise)
    '''
    return changeVMStatus(positive, vm, 'stop', 'DOWN', async)

def stopVms(vms, wait='true'):
    '''
    Stop vms.
    Author: mbenenso
    Parameters:
       * vms - comma separated list of VM names
       * wait - if 'true' will wait till the end of stop action ('true' by default)
    Return: True iff all VMs stopped, False otherwise
    '''
    vmObjectsList = []
    vms = split(vms)
    wait = wait.lower() == 'true'
    async = 'false' if not wait else 'true'
    for vm in vms:
        stopVm(True, vm, async)
        try:
            vmObj = VM_API.find(vm)
        except EntityNotFound:
            logger.error("failed to find VM %s" % vm)
        else:
            vmObjectsList.append(vmObj)

    if not wait:
        return True

    resultsList = []
    for vmObj in vmObjectsList:
        sampler = TimeoutingSampler(VM_ACTION_TIMEOUT, 5, VM_API.getAndXpathEval)
        sampler.func_args = (vmObj, '/vm[status/state="down"]')
        try:
            for statusOk in sampler:
                if statusOk:
                    resultsList.append(True)
                    break
        except APITimeout:
            resultsList.append(False)

    return all(resultsList)


def searchForVm(positive, query_key, query_val, key_name):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    expected_count = 0
    vms = VM_API.get(absLink=False)

    for vm in vms:
        vmProperty = getattr(vm, key_name)
        if re.match(r'(.*)\*$',query_val):
            if re.match(r'^' + query_val, vmProperty):
                expected_count = expected_count + 1
        else:
            if vmProperty == query_val:
                expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_vms = VM_API.query(contsraint)
    status = compareCollectionSize(query_vms, expected_count, VM_API.logger)

    return status


def detachVm(positive, vm):
    '''
    Description: run detach vm action
    Author: edolinin
    Parameters:
       * vm - name of vm
    Return: status (True if vm was detached properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    expectedStatus = vmObj.get_status().get_state()

    status = VM_API.syncAction(vmObj, "detach", positive)
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)
    return status


def _getVmDisks(vm):
    vmObj = VM_API.find(vm)
    disks = VM_API.getElemFromLink(vmObj, link_name='disks', attr='disk',
                                    get_href=True)
    return VM_API.get(disks, 'disk')


def addDisk(positive, vm, size, wait=True, storagedomain=None,
            timeout=VM_IMAGE_OPT_TIMEOUT, **kwargs):
    '''
    Description: add disk to vm
    Parameters:
        * vm - vm name
        * size - disk size
        * wait - wait until finish if True or exit without waiting
        * storagedomain - storage domain name(relevant only for the first disk)
        * timeout - waiting timeout
       * kwargs:
        * type - disk type
        * interface - disk interface
        * format - disk format type
        * sparse - if disk sparse or preallocated
        * bootable - if disk bootable or not
        * wipe_after_deletion - if disk should be wiped after deletion or not
        * propagate_errors - if propagate errors or not
    Return: status (True if disk was added properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    disk = data_st.Disk(size=size, format=ENUMS['format_cow'],
                        interface=ENUMS['interface_ide'], sparse=True)

    # replace disk params from kwargs
    for param_name in ADD_DISK_KWARGS:
        param_val = kwargs.pop(param_name, None)
        if param_val is not None:
            setattr(disk, param_name, param_val)

    # Report the unknown arguments that remains.
    if 0 < len(kwargs):
        E = "addDisk() got an unexpected keyword arguments %s"
        raise TypeError(E % kwargs)

    if storagedomain:
        sd = STORAGE_DOMAIN_API.find(storagedomain)
        diskSds = data_st.StorageDomains()
        diskSds.add_storage_domain(sd)
        disk.set_storage_domains(diskSds)

    disks = DISKS_API.getElemFromLink(vmObj, get_href=True)
    disk, status = DISKS_API.create(disk, positive, collection=disks)
    if status and positive and wait:
        return VM_API.waitForElemStatus(vmObj, "DOWN", timeout)
    return status


def removeDisk(positive, vm, disk, wait=True):
    '''
    Description: remove disk from vm
    Parameters:
       * vm - vm name
       * disk - name of disk that should be removed
       * wait - wait until finish if True
    Return: True if disk was removed properly, False otherwise
    '''
    for d in _getVmDisks(vm):
        if d.name.lower() == disk.lower():
            status = VM_API.delete(d, positive)

    diskExist = True
    if positive and status and wait:
        startTime = time.time()
        logger.debug('Waiting for disk to be removed.')
        while diskExist:
            disks = _getVmDisks(vm)
            disks = filter(lambda x: x.name.lower() == disk.lower(), disks)
            diskExist = bool(disks)
            if VM_IMAGE_OPT_TIMEOUT < time.time() - startTime:
                raise APITimeout('Timeouted when waiting for disk to be removed')
            time.sleep(VM_SAMPLING_PERIOD)

    return not diskExist


def removeDisks(positive, vm, num_of_disks, wait=True):
    '''
    Description: remove certain number of disks from vm
    Parameters:
      * vm - vm name
      * num_of_disks - number of disks that should be removed
      * wait - wait until finish if True
    Return: status (True if disks were removed properly, False otherwise)
    '''
    rc = True
    disks = _getVmDisks(vm)
    if disks:
        cnt = int(num_of_disks)
        actual_cnt = len(disks)
        cnt_rm = actual_cnt if actual_cnt < cnt else cnt
        for i in xrange(cnt_rm):
            disk = disks.pop()
            rc = rc and removeDisk(positive, vm, disk.name, wait)
    return rc
