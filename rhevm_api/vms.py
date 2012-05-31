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
from copy import deepcopy
from framework_utils.apis_utils import data_st, TimeoutingSampler
from rhevm_api.test_utils import get_api, split
from utilities.utils import readConfFile
import re
from framework_utils.validator import compareCollectionSize
from framework_utils.apis_exceptions import APITimeout, EntityNotFound
from rhevm_api.networks import getClusterNetwork
from utilities.jobs import Job, JobsSet
from Queue import Queue
from threading import Thread

GBYTE = 1024*1024*1024
ELEMENTS = os.path.join(os.path.dirname(__file__), '../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
VM_ACTION_TIMEOUT = 180
VM_REMOVE_SNAPSHOT_TIMEOUT = 300
VM_IMAGE_OPT_TIMEOUT = 300
VM_SAMPLING_PERIOD = 3
BLANK_TEMPLATE = '00000000-0000-0000-0000-000000000000'
ADD_DISK_KWARGS = ['size', 'type', 'interface', 'format', 'bootable',
                   'sparse', 'wipe_after_deletion', 'propagate_errors']

VM_API = get_api('vm', 'vms')
CLUSTER_API = get_api('cluster', 'clusters')
TEMPLATE_API = get_api('template', 'templates')
HOST_API = get_api('host', 'hosts')
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')
DISKS_API = get_api('disk', 'disks')
NIC_API = get_api('nic', 'nics')
SNAPSHOT_API = get_api('snapshot', 'snapshots')
TAG_API = get_api('tag', 'tags')
CDROM_API = get_api('cdrom', 'cdroms')

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
    vm.set_memory_policy(data_st.MemoryPolicy(guaranteed=
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
    body = None
    force = kwargs.pop('force', None)
    if force:
        body = data_st.Action(force=True)

    vmObj = VM_API.find(vm)
    stopVM = kwargs.pop('stopVM', 'false')
    if stopVM.lower() == 'true' and vmObj.status.state.lower() != 'down':
        if not stopVm(positive, vm):
            return False
    status = VM_API.delete(vmObj, positive, body=body, element_name='action')

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

    Parameters:
        * vms - comma (and no space) separated string of VM names to wait for.
        * timeout - Time in seconds for the vms to disapear.
        * samplingPeriod - Time in seconds for sampling the vms list.
    '''
    t_start = time.time()
    vmsList = vms.split(',')
    QUERY = ' or '.join([ 'name="%s"' % vm for vm in vmsList ])
    while time.time() - t_start < timeout and 0 < timeout:
        foundVms = VM_API.query(QUERY)
        if not len(foundVms):
            logger.info("All %d VMs are gone.", len(vmsList))
            return positive
        time.sleep(samplingPeriod)
        
    remainingVmsNames = [vm.name for vm in foundVms]
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

    query = "name={0} and status={1} or name={0} and status=up".format(vm,
                                                    wait_for_status.lower())

    return VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT, sleep=10)

    
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
    query = 'name={0} and status=down'
    for vmObj in vmObjectsList:
        query =query.format(vm.get_name())
        querySt = VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT, sleep=DEF_SLEEP)
        resultsList.append(querySt)
       
    return all(resultsList)


def searchForVm(positive, query_key, query_val, key_name=None, expected_count=None):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''
    if not expected_count:
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


def migrateVm(positive, vm, host=None, wait=True):
    '''
    Migrate the VM.

    If the host was specified, after the migrate action was performed,
    the method is checking whether the VM status is UP or POWERING_UP
    and whether the VM runs on required destination host.

    If the host was not specified, after the migrate action was performed, the
    method is checking whether the VM is UP or POWERING_UP
    and whether the VM runs on host different to the source host.

    Author: edolinin, jhenner
    Parameters:
       * vm - name of vm
       * host - Name of the destionation host to migrate VM on, or
                None for RHEVM destination host autoselection.
       * wait - When True wait until end of action,
                     False return without waiting.
    Return: True if vm was migrated and test is positive,
            False otherwise.
    '''
    vmObj = VM_API.find(vm)
    actionParams = {}

    if not vmObj.get_host():
        logger.error('There is no host for vm {0}'.format(vm))
        return False
    
    sourceHostName = vmObj.get_host().get_name()
    migrateQuery = ''

    # If the host is not specified, we should let RHEVM to autoselect host.
    if host:
        destHostObj = HOST_API.find(host)
        actionParams['host'] = destHostObj
        # Check the vm to be UP or POWERING_UP and whether it is on the host we
        # wanted it to be.
        migrateQuery = "name={0} and status=powering_up or name={0} and status=up"\
                                                                .format(sourceHostName)
    else:
        # Check the vm to be UP or POWERING_UP and whether it moved.
        migrateQuery = "name={0} and status=!powering_up or name={0} and status!=up"\
                                                                .format(sourceHostName)

    if not VM_API.syncAction(vmObj, "migrate", positive, **actionParams):
        return False

    # Check the VM only if we do the positive test. We know the action status
    # failed so with fingers crossed we can assume that VM didn't migrate.
    if not wait or not positive:
        logger.warning('Not going to wait till VM migration completes. \
        wait=%s, positive=%s' % (str(wait), positive))
        return True

    VM_API.waitForQuery(migrateQuery, timeout=VM_ACTION_TIMEOUT, sleep=DEF_SLEEP)

    # Check whether we tried to migrate vm to different cluster
    # in this case we return False, since this action shouldn't be allowed.
    logger.info('Getting the VM host after VM migrated.')
    realDestHostObj = VM_API.find(vm).get_host()
    if vmObj.get_cluster().get_id() != realDestHostObj.get_cluster().get_id():
        return False

    if host:
        MSG = 'VM is on the destination host and is UP or POWERING_UP.'
        logger.info(MSG)
    else:
        MSG = 'VM host has changed and is UP or POWERING_UP.'
        logger.info(MSG)
    return True


def checkVmHasCdromAttached(positive, vmName):
    '''
    Check whether vm has cdrom attached
    Author: jvorcak
    Parameters:
       * vmName - name of the virtual machine
    Return (True if vm has at least one cdrom attached, False otherwise)
    '''
    vmObj = VM_API.find(vmName)
    cdroms = VM_API.getElemFromLink(vmObj, link_name='cdroms', attr='cdrom',
                                    get_href=True)

    if not cdroms:
        VM_API.logger.error('There are no cdroms attached to vm %s', vmName)
        return not positive
    return positive


def _prepareNicObj(**kwargs):


    nic = data_st.NIC()

    name = kwargs.pop('name', None)
    if name:
        nic.set_name(name)

    interface = kwargs.pop('interface', None)
    if interface:
        nic.set_interface(interface)

    mac_address = kwargs.pop('mac_address', None)
    if mac_address:
        nic.set_mac(data_st.MAC(address=mac_address))
        
    network = kwargs.pop('network', None)
    if network:
        cl = kwargs.pop('cluster', None)
        cl = CLUSTER_API.find(cl, 'id')
        clNet = getClusterNetwork(cl.name, network)
        nic.set_network(clNet)

    return nic

def getVmNics(vm):

    vmObj = VM_API.find(vm)
    return VM_API.getElemFromLink(vmObj, link_name='nics', attr='vm_nic', get_href=True)

def getVmNic(vm, nic):

    vmObj = VM_API.find(vm)
    return VM_API.getElemFromElemColl(vmObj, nic, 'nics', 'nic')


def addNic(positive, vm, **kwargs):
    '''
    Description: add nic to vm
    Author: edolinin
    Parameters:
       * vm - vm where nic should be added
       * name - nic name
       * network - network name
       * interface - nic type. available types: virtio, rtl8139 and e1000
                     (for 2.2 also rtl8139_virtio)
       * mac_address - nic mac address
    Return: status (True if nic was added properly, False otherwise)
    '''
    # TODO: Check whether there still is the type PV available.

    vmObj = VM_API.find(vm)
    expectedStatus = vmObj.get_status().get_state()
    
    cluster = vmObj.cluster.id
    kwargs['cluster'] = cluster
    nic = _prepareNicObj(**kwargs)
    vmNics = getVmNics(vm)

    nic, status = NIC_API.create(nic, positive, collection=vmNics)
    if positive and status:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)
    return status


def addVmNics(positive, vm, namePrefix, networks):
    '''
    Adding multipe nics with different network each one
    Author: atal
    Parameters:
        * vm - vm name
        * namePrefix - the prefix for each VM nic name
        * networks - list of network names
    return True with VM nic names list alse False with empty list
    '''
    vm_nics = []
    regex = re.compile('\w(\d+)', re.I)
    for net in networks:
        match = regex.search(net)
        if not match:
            return False, {'vmNics': None}
        name = namePrefix + str(match.group(1))
        vm_nics.append(name)
        if not addNic(positive, vm, name, net):
            return False, {'vmNics': None}
    return True, {'vmNics': vm_nics}


def updateNic(positive, vm, nic, **kwargs):
    '''
    Description: update nic of vm
    Author: edolinin
    Parameters:
       * vm - vm where nic should be updated
       * nic - nic name that should be updated
       * name - new nic name
       * network - network name
       * interface - nic type. available types: virtio, rtl8139 and e1000
                     (for 2.2 also rtl8139_virio)
       * mac_address - nic mac address
    Return: status (True if nic was updated properly, False otherwise)
    '''

    vmObj = VM_API.find(vm)
    cluster = vmObj.cluster.id
    kwargs['cluster'] = cluster
    
    nicNew = _prepareNicObj(**kwargs)
    nic = getVmNic(vm, nic)
   
    nic, status = NIC_API.update(nic, nicNew, positive)
    return status


def removeNic(positive, vm, nic):
    '''
    Description: remove nic from vm
    Author: edolinin
    Parameters:
       * vm - vm where nic should be removed
       * nic - nic name that should be removed
    Return: status (True if nic was removed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    nic = getVmNic(vm, nic)

    expectedStatus = vmObj.get_status().get_state()

    status = VM_API.delete(nic, positive)
    if positive and status:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)
    return status

def removeLockedVm(vm, vdc, vdc_pass, psql_username='postgres', psql_db='rhevm'):
    '''
    Remove locked vm with flag force=true
    Make sure that vm no longer exists, otherwise set it's status to down,
    and remove it
    Author: jvorcak
    Parameters:
       * vm - name of the VM
       * vdc - address of the setup
       * vdc_pass - password for the vdc
       * psql_username - psql username
       * psql_db - name of the DB
    '''
    vmObj = VM_API.find(vm)

    if removeVm(True, vmObj.get_name(), force='true'):
        return True

    # clean if vm has not been removed
    logger.error('Locked vm has not been removed with force flag')

    updateVmStatusInDatabase(vmObj.get_name(), 0, vdc, vdc_pass,
            psql_username, psql_db)

    return removeVm("true", vmObj.get_name())


def _getVmSnapshots(vm):
    vmObj = VM_API.find(vm)
    snapshots = SNAPSHOT_API.getElemFromLink(vmObj, get_href=True)
    return snapshots

def _getVmSnapshot(vm, snap):
    vmObj = VM_API.find(vm)
    return SNAPSHOT_API.getElemFromElemColl(vmObj, snap, 'snapshots',
                        'snapshot', prop='description')
    

def addSnapshot(positive, vm, description, wait=True):
    '''
    Description: add snapshot to vm
    Author: edolinin
    Parameters:
       * vm - vm where snapshot should be added
       * description - snapshot name
       * wait - wait untill finish when True or exist without waiting when False
    Return: status (True if snapshot was added properly, False otherwise)
    '''
    snapshot = data_st.Snapshot()
    snapshot.set_description(description)

    vmSnapshots = _getVmSnapshots(vm)
    snapshot, status = SNAPSHOT_API.create(snapshot, positive, collection=vmSnapshots)

    time.sleep(30)

    snapshot = _getVmSnapshot(vm, description)
    snapshotStatus = True
    if status and positive and wait:
        snapshotStatus = SNAPSHOT_API.waitForElemStatus(snapshot, 'ok', VM_IMAGE_OPT_TIMEOUT)
        if snapshotStatus:
            snapshotStatus = validateSnapshot(positive, vm, description)
    return status and snapshotStatus


def restoreSnapshot(positive, vm, description):
    '''
    Description: restore vm snapshot
    Author: edolinin
    Parameters:
       * vm - vm where snapshot should be restored
       * description - snapshot name
    Return: status (True if snapshot was restored properly, False otherwise)
    '''

    vmObj = VM_API.find(vm)
    snapshot = _getVmSnapshot(vm, description)
    expectedStatus = vmObj.status.state

    status = SNAPSHOT_API.syncAction(snapshot, "restore", positive)
    time.sleep(60)
    if status and positive:
        return SNAPSHOT_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)

    return status


def validateSnapshot(positive, vm, snapshot):
    '''
    Description: Validate snapshot if exist
    Author: egerman
    Parameters:
       * vm - vm where snapshot should be restored
       * snapshot - snapshot name
    Return: status (True if snapshot exist, False otherwise)
    '''
    return _getVmSnapshot(vm, snapshot) is not None


def removeSnapshot(positive, vm, description, timeout=VM_REMOVE_SNAPSHOT_TIMEOUT):
    '''
    Description: remove vm snapshot
    Author: jhenner
    Parameters:
       * vm          - vm where snapshot should be removed.
       * description - Snapshot description. Beware that snapshots aren't
                       uniquely identified by description.
       * timeout     - How long this would block until machine status switches
                       back to the one before deletion.
                       If timeout < 0, return immediately after getting the action
                       response, don't check the action on snapshot really did
                       something.
    Return: If positive:
                True iff snapshot was removed properly.
            If negative:
                True iff snapshot removal failed.
    '''

    snapshot = _getVmSnapshot(vm, description)
    
    if not SNAPSHOT_API.delete(snapshot, positive):
        return False

    if timeout < 0:
        return True
    args = vm, description
    if positive:
        # Wait until snapshot disappears.
        try:
            for ret in TimeoutingSampler(timeout, 5,  _getVmSnapshot, *args):
                if not ret:
                    logger.info('Snapshot %s disappeared.',
                                snapshot.description)
                    return True
            pass  # Unreachable
        except EntityNotFound:
            return True
        except APITimeout:
            logger.error('Timeouted when waiting snapshot %s disappear.',
                         snapshot.description)
            return False
    else:
        # Check whether snapshot didn't disappear.
        logger.info('Checking whether url %s exists.', snapshot.href)
        try:
            for ret in TimeoutingSampler(timeout, 5,  _getVmSnapshot, *args):
                if not ret:
                    logger.info('Snapshot %s disappeared.',
                                snapshot.description)
                    return False
            pass  # Unreachable
        except EntityNotFound:
            return True
        except APITimeout:
            logger.info(
                'Snapshot still exists (http status %d when checking url %s).'
            )
            return True


def runVmOnce(positive, vm, pause=None, display_type=None, stateless=None,
        cdrom_image=None, floppy_image=None, boot_dev=None, host=None,
        domainName=None, user_name=None, password=None):
    '''
    Description: run vm once
    Author: edolinin
    Parameters:
       * vm - name of vm
       * pause - if pause the vm after starting
       * display_type - type of display to use in start up
       * stateless - if vm should be stateless or not
       * cdrom_image - cdrom image to use
       * floppy_image - floppy image to use
       * boot_dev - boot device to use
       * domainName - name of the domain for VM
       * user_name - name of the user
       * password - password for specified user
    Return: status (True if vm was run properly, False otherwise)
    '''
    #TODO Consider merging this method with the startVm.
    vm_obj = VM_API.find(vm)

    vm_for_action = data_st.VM()
    if display_type:
        vm_for_action.set_display(data_st.Display(type_=display_type))
        
    if None is not stateless:
        vm_for_action.set_stateless(stateless)

    if None is not cdrom_image:
        cdrom = data_st.CdRom()
        vmCdroms = data_st.CdRoms()
        cdrom.set_file(data_st.File(id=cdrom_image))
        vmCdroms.add_cdrom(cdrom)
        vm_for_action.set_cdroms(vmCdroms)

    if None is not floppy_image:
        floppy = data_st.Floppy()
        floppies = data_st.Floppies()
        floppy.set_file(data_st.File(id=floppy_image))
        floppies.add_floppy(floppy)
        vm_for_action.set_floppies(floppies)

    if None is not boot_dev:
        boot_dev_seq = data_st.Boot()
        for dev in boot_dev.split(","):
            os = data_st.OperatingSystem()
            boot_dev_seq.set_dev(dev)
            vm_for_action.set_os(os.set_boot(boot_dev_seq))

    if None is not host:
        raise NotImplementedError(
                "Setting host in runVmOnce was discontinued.\n"
                "Please change the VM affinity with updateVm instead.\n"
                "Bug 743674 - runOnce doesn't start on the specific host"
        )

    if None is not domainName:
        domain = data_st.Domain()

        if password is None:
                logger.error('You have to specify password with username')
                return False

        if None is not user_name:
            domain.set_user(data_st.User(user_name=user_name, password=password))
            
        vm_for_action.set_domain(domain)

    # default value True
    status = True

    if pause:
        status = VM_API.syncAction(vm_obj, 'start', positive, pause=pause,
                                 vm=vm_for_action)
        if positive and status:
            # in case status is False we shouldn't wait for rest element status
            if pause.lower() == 'true':
                state = wait_for_status=ENUMS['vm_state_paused']
            else:
                state = ENUMS['vm_state_powering_up']
            return VM_API.waitForElemStatus(vm_obj, state,
                                                      VM_ACTION_TIMEOUT)
    else:
        status = VM_API.syncAction(vm_obj, 'start', positive, vm=vm_for_action)
        if positive and status:
            # in case status is False we shouldn't wait for rest element status
            return VM_API.waitForElemStatus(vm_obj,
                   ENUMS['vm_state_powering_up'], VM_ACTION_TIMEOUT)
    return status


def suspendVm(positive, vm, wait=True):
    '''
    Suspend VM.

    Wait for status UP, then the suspend action is performed and then it awaits status
    SUSPENDED, sampling every 10 seconds.

    Author: jhenner
    Parameters:
       * vm - name of vm
       * wait - wait until and of action when positive equal to True
    Return: status (True if vm suspended and test is positive, False otherwise)
    '''
    vmObj = VM_API.find(vm)
            
    async = 'false'
    if not wait:
        async = 'true'

    if not VM_API.syncAction(vmObj, 'suspend', positive, async=async):
        return False
    if wait and positive:
        return VM_API.waitForElemStatus(vmObj, 'suspended', VM_ACTION_TIMEOUT)


def suspendVms(vms):
    '''
    Suspend several vms simultaneously. Only action response is checked, no
    checking for vm SUSPENDED status is performed.

    Parameters:
      * vms - Names of VMs to suspend.
    Returns: True iff all VMs suspended.
    '''
    jobs = [Job(target=suspendVm, args=(True, vm)) for vm in split(vms)]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        if job.exception:
            status = False
            logger.error('Suspending vm %s failed: %s.',
                            job.args[1], job.exception)
        elif not job.result:
            status = False
            logger.error('Suspending vm %s failed.', job.args[1])
        else:
            logger.info('Suspending vm %s succeed.', job.args[1])
    return status


def shutdownVm(positive, vm):
    '''
    Description: shutdown vm
    Author: edolinin
    Parameters:
       * vm - name of vm
    Return: status (True if vm was stopped properly, False otherwise)
    '''
    return changeVMStatus(positive, vm, 'shutdown', 'down')


def migrateVm(positive, vm, host=None, wait=True):
    '''
    Migrate the VM.

    If the host was specified, after the migrate action was performed,
    the method is checking whether the VM status is UP or POWERING_UP
    and whether the VM runs on required destination host.

    If the host was not specified, after the migrate action was performed, the
    method is checking whether the VM is UP or POWERING_UP
    and whether the VM runs on host different to the source host.

    Author: edolinin, jhenner
    Parameters:
       * vm - name of vm
       * host - Name of the destionation host to migrate VM on, or
                None for RHEVM destination host autoselection.
       * wait - When True wait until end of action,
                     False return without waiting.
    Return: True if vm was migrated and test is positive,
            False otherwise.
    '''
    vmObj = VM_API.find(vm)
    if not vmObj.host:
        logger.error("VM has no attribute 'host': %s" % dir(vmObj))
        return False
    actionParams = {}
    sourceHostId = vmObj.host.id
    sourceHost = HOST_API.find(sourceHostId, 'id')


    # If the host is not specified, we should let RHEVM to autoselect host.
    query = 'name={0} and status=powering_up or name={0} and status=up'
    if host:
        destHostObj = HOST_API.find(host)
        actionParams['host'] = destHostObj
        # Check the vm to be UP or POWERING_UP and whether it is on the host we
        # wanted it to be.
        query = query.format(destHostObj.name)
    else:
        # Check the vm to be UP or POWERING_UP and whether it moved.
        query = query.format(sourceHost)
       
    if not VM_API.syncAction(vmObj, "migrate", positive, **actionParams):
        return False

    # Check the VM only if we do the positive test. We know the action status
    # failed so with fingers crossed we can assume that VM didn't migrate.
    if not wait or not positive:
        logger.warning('Not going to wait till VM migration completes. \
        wait=%s, positive=%s' % (str(wait), positive))
        return True

    if not VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT, sleep=10):
        return False

    # Check whether we tried to migrate vm to different cluster
    # in this case we return False, since this action shouldn't be allowed.
    logger.info('Getting the VM host after VM migrated.')
    realDestHostObj = VM_API.find(vm).host.id
    if vmObj.cluster.id != realDestHostObj.cluster.id:
        return False

    if host:
        MSG = 'VM is on the destination host and is UP or POWERING_UP.'
        logger.info(MSG)
    else:
        MSG = 'VM host has changed and is UP or POWERING_UP.'
        logger.info(MSG)
    return True


def ticketVm(positive, vm, expiry):
    '''
    Description: ticket vm
    Author: edolinin
    Parameters:
       * vm - vm to ticket
       * expiry - ticket expiration time
    Return: status (True if vm was ticketed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)

    ticket = data_st.Ticket()
    ticket.set_expiry(int(expiry))

    return VM_API.syncAction(vmObj, "ticket", positive, ticket=ticket)


def addTagToVm(positive, vm, tag):
    '''
    Description: add tag to vm
    Author: edolinin
    Parameters:
       * vm - vm to add tag to
       * tag - tag name
    Return: status (True if tag was added properly, False otherwise)
    '''
    
    vmObj = VM_API.find(vm)
    vmTags = VM_API.getElemFromLink(vmObj, link_name='tags', attr='tag', get_href=True)

    tagObj = data_st.Tag()
    tagObj.set_name(tag)

    tagObj, status = TAG_API.create(tagObj, positive, collection=vmTags)
    return status


def removeTagFromVm(positive, vm, tag):
    '''
    Description: remove tag from vm
    Author: edolinin
    Parameters:
       * vm - vm to remove tag from
       * tag - tag name
    Return: status (True if tag was removed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    tagObj = VM_API.getElemFromElemColl(vmObj, tag, 'tags', 'tag')
    return VM_API.delete(tagObj, positive)


def exportVm(positive, vm, storagedomain, exclusive='false',
             discard_snapshots='false'):
    '''
    Description: export vm to export storage domain
    Author: edolinin, jhenner
    Parameters:
       * vm - name of vm to export
       * storagedomain - name of export storage domain where to export vm to
       * exclusive - overwrite any existing vm of the same name
                       in the destination domain ('false' by default)
       * discard_snapshots - do not include vm snapshots
                               with the exported vm ('false' by default)
    Return: status (True if vm was exported properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    sd = data_st.StorageDomain(name=storagedomain)
    
    expectedStatus = vmObj.status.state

    actionParams = dict(storage_domain=sd, exclusive=exclusive,
                        discard_snapshots=discard_snapshots)
    status = VM_API.syncAction(vmObj, "export", positive, **actionParams)
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, 300)
    return status


def importVm(positive, vm, export_storagedomain, import_storagedomain,
             cluster):
    '''
    Description: import vm
    Author: edolinin
    Parameters:
       * vm - vm to import
       * datacenter - name of data center
       * export_storagedomain -storage domain where to export vm from
       * import_storagedomain -storage domain where to import vm to
    Return: status (True if vm was imported properly, False otherwise)
    '''
    expStorDomObj = STORAGE_DOMAIN_API.find(export_storagedomain)
    sdVms = VM_API.getElemFromLink(expStorDomObj, link_name='vms', attr='vm',
                                                            get_href=False)
    vmObj = VM_API.find(vm, collection=sdVms)

    expectedStatus = vmObj.status.state

    sd = data_st.StorageDomain(name=import_storagedomain)
    cl = data_st.Cluster(name=cluster)
  
    status = VM_API.syncAction(vmObj, "import", positive, storage_domain=sd, cluster=cl)
    #TODO: replac sleep with true diagnostic
    time.sleep(30)
    if status and positive:
        return util.waitForElemStatus(vmObj, expectedStatus, 300)
    return status


def moveVm(positive, vm, storagedomain, wait=True):
    '''
    Description: move vm to another storage domain
    Author: edolinin
    Parameters:
       * vm - name of vm
       * storagedomain - name of storage domain to move vm to
    Return: status (True if vm was moved properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    expectedStatus = vmObj.status.state
    storageDomainId = STORAGE_DOMAIN_API.find(storagedomain).id
    sd = data_st.StorageDomain(id=storageDomainId)
    
    async = 'false'
    if not wait:
        async = 'true'
    status = VM_API.syncAction(vmObj, "move", positive, storage_domain=sd, async=async)
    if positive and status and wait:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_IMAGE_OPT_TIMEOUT)
    return status


def changeCDWhileRunning(vm_name, cdrom_image):
    '''
    Description: Change cdrom image while vm is running
    Since the change is for current session only, there is
    no change in the API except of event, that's why there's no validation
    in this method.
    To check whether cdrom has been changed, event test must follow
    after this test case
    Author: jvorcak
    Parameters:
       * vm_name - name of the virtual machine
       * cdrom_image - image to be changed
    Return (True if reponse code is 200 for change request,
            False otherwise)
    '''
    vmObj = VM_API.find(vm_name)
    cdroms = CDROM_API.getElemFromLink(vmObj, link_name='cdroms',
                                             attr='cdrom', get_href=False)
    if not cdroms:
        VM_API.logger.error('There is no cdrom attached to vm')
        return False

    newCdrom = cdroms[0]
    newCdrom.set_file(data_st.File(id=cdrom_image))
    cdroms[0].set_href(cdroms[0].href + "?current")
    
    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, True)

    return status


def cloneVmFromTemplate(positive, name, template, cluster, timeout=VM_IMAGE_OPT_TIMEOUT,
                        clone='true', vol_sparse=None, vol_format=None):
    '''
    Description: clone vm from a pre-defined template
    Author: edolinin
    Parameters:
       * template - template name
       * cluster - cluster name
       * timeout - action timeout (depends on disk size or system load
       * clone - true/false - if true, template disk will be copied
       * vol_sparse - true/false - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
    Return: status (True if vm was cloned properly, False otherwise)
    '''
    vm = data_st.VM(name=name)

    templObj = TEMPLATE_API.find(template)
    vm.set_template(templObj)
   
    clusterObj = CLUSTER_API.find(cluster)
    vm.set_cluster(clusterObj)

    expectedVm = None
    diskArray = data_st.Disks()
    if clone and clone.lower() == 'true':
        diskArray.set_clone(clone)
        disks = DISKS_API.getElemFromLink(templObj, link_name='disks',
                                             attr='disk', get_href=False)
        for dsk in disks:
            disk = data_st.Disk(id=dsk.id)
            if vol_sparse:
                disk.set_sparse(vol_sparse)
            if vol_format:
                disk.set_format(vol_format)

            diskArray.add_disk(disk)
        vm.set_disks(diskArray)
        expectedVm = deepcopy(vm)
        expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))

    vm, status = VM_API.create(vm, positive, expectedEntity=expectedVm)

    if positive and status:
        return VM_API.waitForElemStatus(vm, "DOWN", timeout)
    return status
