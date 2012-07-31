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
import os.path
from Queue import Queue
import re
import time
from copy import deepcopy

from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api, split, \
            cobblerAddNewSystem, cobblerSetLinuxHostName
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.rhevm_api.tests_lib.networks import getClusterNetwork
from art.test_handler.settings import opts
from threading import Thread
from utilities.jobs import Job, JobsSet
from utilities.utils import readConfFile
from utilities.machine import Machine
from art.rhevm_api.utils.test_utils import searchForObj, getImageByOsType, \
    convertMacToIpAddress, checkHostConnectivity

GBYTE = 1024 * 1024 * 1024
ELEMENTS = os.path.join(os.path.dirname(__file__), '../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEF_SLEEP = 10
VM_ACTION_TIMEOUT = 180
VM_REMOVE_SNAPSHOT_TIMEOUT = 300
VM_IMAGE_OPT_TIMEOUT = 300
VM_SAMPLING_PERIOD = 3
BLANK_TEMPLATE = '00000000-0000-0000-0000-000000000000'
ADD_DISK_KWARGS = ['size', 'type', 'interface', 'format', 'bootable',
                   'sparse', 'wipe_after_deletion', 'propagate_errors']
VM_WAIT_FOR_IP_TIMEOUT = 600

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
NETWORK_API = get_api('network', 'networks')

logger = logging.getLogger(__package__ + __name__)
xpathMatch = XPathMatch(VM_API)


class DiskNotFound(Exception):
    pass


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
        vm.set_template(data_st.Template(id=template.id))

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
        ppolicy.set_host(data_st.Host(id=aff_host.id))
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
            raise Exception(E % prop_arg)
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

    wait = kwargs.pop('wait', True)
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
        logger.warn(str(e))
        status = True
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
        status = status and removalOK
    return waitForVmsGone(positive, vms) and status


def waitForVmsGone(positive, vms, timeout=60, samplingPeriod=10):
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
    vmsList = split(vms)
    QUERY = ' or '.join(['name="%s"' % vm for vm in vmsList])
    while time.time() - t_start < timeout and 0 < timeout:
        foundVms = VM_API.query(QUERY)
        if not len(foundVms):
            logger.info("All %d VMs are gone.", len(vmsList))
            return positive
        time.sleep(samplingPeriod)

    remainingVmsNames = [vm.name for vm in foundVms]
    logger.error("VMs %s didn't disappear until timeout." % remainingVmsNames)
    return not positive


def waitForVmsStates(positive, names, states='up', *args, **kwargs):
    '''
    Wait until all of the vms identified by names exist and have the desired
    status.
    Parameters:
        * names - A comma separated names of the hosts with status to wait for.
        * states - A state of the hosts to wait for.
    Author: jhenner
    '''
    names = split(names)
    for vm in names:
        VM_API.find(vm)

    query = ' and '.join(['name="%s" and status=%s' % (vm, states) for vm in names])

    return VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT, sleep=10)


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
                                    wait_for_status.lower().replace('_', ''))

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
        query = query.format(vmObj.get_name())
        querySt = VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT, sleep=DEF_SLEEP)
        resultsList.append(querySt)

    return all(resultsList)


def searchForVm(positive, query_key, query_val, key_name=None, **kwargs):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    return searchForObj(VM_API, query_key, query_val, key_name, **kwargs)


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
                                    get_href=False)
    return disks


def _getVmDiskById(vm, diskId):
    """
    Description: Searches for vm's disk by id
    Author: jlibosva
    Parameters"
        * vm - Name of vm we want disk from
        * diskId - disk's id
    Return: Disk object
    """
    disks = _getVmDisks(vm)
    found = [disk for disk in disks if disk.get_id() == diskId]
    if not found:
        raise DiskNotFound("Disk with id %s was not found in vm's %s disk \
collection" % (diskName, vm))

    return found[0]


def _getVmFirstDiskByName(vm, diskName, idx=0):
    """
    Description: Searches for vm's disk by name
                 Name is not unique!
    Author: jlibosva
    Parameters"
        * vm - Name of vm we want disk from
        * diskId - disk's id
        * idx - index of found disk to return
    Return: Disk object
    """
    """
    """
    disks = _getVmDisks(vm)
    found = [disk for disk in disks if disk.get_name() == diskName]
    if not found:
        raise DiskNotFound("Disk %s was not found in vm's %s disk collection" %
                           (diskName, vm))
    return found[idx]


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
        return DISKS_API.waitForElemStatus(disk, "OK", timeout)
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
            if disks is None:
                return False
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


def waitForDisksStat(vm, stat='OK', timeout=VM_IMAGE_OPT_TIMEOUT):
    '''
    Wait for VM disks status
    Author: atal
    Parameters:
        * vm - vm name
        * stat = status we are waiting for
        * timeout - waiting period.
    Return True if all events passed, otherwize False
    '''
    status = True
    disks = _getVmDisks(vm)
    for disk in disks:
        status = DISKS_API.waitForElemStatus(disk, stat, timeout)
    return status


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

    nic_obj = data_st.NIC()

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'interface' in kwargs:
        nic_obj.set_interface(kwargs.get('interface'))

    if 'mac_address' in kwargs:
        nic_obj.set_mac(data_st.MAC(address=kwargs.get('mac_address')))

    if 'network' in kwargs:
        nic_obj.set_network(data_st.Network(name=kwargs.get('network')))

    if 'active' in kwargs:
        nic_obj.set_active(kwargs.get('active'))

    if 'port_mirroring' in kwargs:
        networks_obj = data_st.Networks()
        networks = kwargs.get('port_mirroring').split(',')
        for network in networks:
            networks_obj.add_network(data_st.Network(name=network))
        nic_obj.set_port_mirroring(data_st.PortMirroring(networks=networks_obj))

    return nic_obj


def getVmNics(vm):

    vm_obj = VM_API.find(vm)
    return VM_API.getElemFromLink(vm_obj, link_name='nics', attr='vm_nic', get_href=True)


def getVmNic(vm, nic):

    vm_obj = VM_API.find(vm)
    return VM_API.getElemFromElemColl(vm_obj, nic, 'nics', 'nic')


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
       * active - Boolean attribute which present nic hostplug state
       * port_mirroring - string of networks separated by comma and include
         which we'd like to listen to
    Return: status (True if nic was added properly, False otherwise)
    '''

    vm_obj = VM_API.find(vm)
    expectedStatus = vm_obj.get_status().get_state()

    nic_obj = _prepareNicObj(**kwargs)
    nics_coll = getVmNics(vm)

    res, status = NIC_API.create(nic_obj, positive, collection=nics_coll)

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(vm_obj, expectedStatus, VM_ACTION_TIMEOUT)
    return status


def isVmNicActive(vm, nic):
    '''
    Description: Check if VM NIC is active
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name
    return: True if nic is active, False otherwise.
    '''
    nic_obj = getVmNic(vm, nic)

    return nic_obj.get_active() == True


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
        if not addNic(positive, vm, name=name, network=net):
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
       * active - Boolean attribute which present nic hostplug state
       * port_mirroring - string of networks separated by comma and include
         which we'd like to listen to
    Return: status (True if nic was updated properly, False otherwise)
    '''

    nic_new = _prepareNicObj(**kwargs)
    nic_obj = getVmNic(vm, nic)

    nic, status = NIC_API.update(nic_obj, nic_new, positive)
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
    vm_obj = VM_API.find(vm)
    nic_obj = getVmNic(vm, nic)

    expectedStatus = vm_obj.get_status().get_state()

    status = NIC_API.delete(nic_obj, positive)

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(vm_obj, expectedStatus, VM_ACTION_TIMEOUT)
    return status


def hotPlugNic(positive, vm, nic):
    '''
    Description: implement hotPlug nic.
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name to plug.
    Return: True in case of succeed, False otherwise
    '''
    nic_obj = getVmNic(vm, nic)

    return NIC_API.syncAction(nic_obj, "activate", positive)


def hotUnplugNic(positive, vm, nic):
    '''
    Description: implement hotUnplug nic.
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name to plug.
    Return: True in case of succeed, False otherwise
    '''
    nic_obj = getVmNic(vm, nic)

    return NIC_API.syncAction(nic_obj, "deactivate", positive)


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


def _getVmSnapshots(vm, get_href=True):
    vmObj = VM_API.find(vm)
    return SNAPSHOT_API.getElemFromLink(vmObj, get_href=get_href)


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
        snapshotStatus = SNAPSHOT_API.waitForElemStatus(snapshot, 'ok',
                    VM_IMAGE_OPT_TIMEOUT, collection=_getVmSnapshots(vm, False))
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
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, VM_ACTION_TIMEOUT)

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
            for ret in TimeoutingSampler(timeout, 5, _getVmSnapshot, *args):
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
            for ret in TimeoutingSampler(timeout, 5, _getVmSnapshot, *args):
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
        os = data_st.OperatingSystem()
#        boot_dev_seq = data_st.Boot()
        for dev in boot_dev.split(","):
#            boot_dev_seq.set_dev(dev)
            os.add_boot(data_st.Boot(dev=dev))
        vm_for_action.set_os(os)

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

    if not VM_API.waitForElemStatus(vmObj, 'up', VM_ACTION_TIMEOUT):
        return False

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

    # If the host is not specified, we should let RHEVM to autoselect host.
    if host:
        destHostObj = HOST_API.find(host)
        actionParams['host'] = data_st.Host(id=destHostObj.id)

    if not VM_API.syncAction(vmObj, "migrate", positive, **actionParams):
        return False

    # Check the VM only if we do the positive test. We know the action status
    # failed so with fingers crossed we can assume that VM didn't migrate.
    if not wait or not positive:
        logger.warning('Not going to wait till VM migration completes. \
        wait=%s, positive=%s' % (str(wait), positive))
        return True

    if not VM_API.waitForElemStatus(vmObj, 'powering_up', 300):
        return False

    # Check whether we tried to migrate vm to different cluster
    # in this case we return False, since this action shouldn't be allowed.
    logger.info('Getting the VM host after VM migrated.')
    realDestHostId = VM_API.find(vm).host.id
    realDestHostObj = HOST_API.find(realDestHostId, 'id')
    if vmObj.cluster.id != realDestHostObj.cluster.id:
        return False

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
             cluster, name=None):
    '''
    Description: import vm
    Author: edolinin
    Parameters:
       * vm - vm to import
       * cluster - name of cluster
       * export_storagedomain -storage domain where to export vm from
       * import_storagedomain -storage domain where to import vm to
       * name - new name of imported VM
    Return: status (True if vm was imported properly, False otherwise)
    '''
    expStorDomObj = STORAGE_DOMAIN_API.find(export_storagedomain)
    sdVms = VM_API.getElemFromLink(expStorDomObj, link_name='vms', attr='vm',
                                                            get_href=False)
    vmObj = VM_API.find(vm, collection=sdVms)

    expectedStatus = vmObj.status.state

    sd = data_st.StorageDomain(name=import_storagedomain)
    cl = data_st.Cluster(name=cluster)

    actionParams = {
        'storage_domain': sd,
        'cluster': cl
    }

    actionName = 'import'
    if opts['engine'] == 'sdk':
        actionName = 'import_vm'

    if name is not None:
        newVm = data_st.VM()
        newVm.name = name
        newVm.snapshots = data_st.Snapshots()
        newVm.snapshots.collapse_snapshots = True
        actionParams['clone'] = True
        actionParams['vm'] = newVm

    status = VM_API.syncAction(vmObj, actionName, positive, **actionParams)

    #TODO: replac sleep with true diagnostic
    time.sleep(30)
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, expectedStatus, 300)
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


def checkVmStatistics(positive, vm):
    '''
    Description: check existence and format of vm statistics values
    Author: edolinin
    Parameters:
        * vm - vm where to check statistics
    Return: status (True if all statistics appear and in correct format,
                    False otherwise)
    '''
    status = True
    vmObj = VM_API.find(vm)

    expectedStatistics = ['memory.installed', 'memory.used',
                          'cpu.current.guest', 'cpu.current.hypervisor',
                          'cpu.current.total']

    numOfExpStat = len(expectedStatistics)
    statistics = VM_API.getElemFromLink(vmObj, link_name='statistics', attr='statistic')

    for stat in statistics:
        datum = str(stat.get_values().get_value()[0].get_datum())
        if not re.match('(\d+\.\d+)|(\d+)', datum):
            logger.error('Wrong value for ' + stat.get_name() + ': ' + datum)
            status = False
        else:
            logger.info('Correct value for ' + stat.get_name() + ': ' + datum)

        if stat.get_name() in expectedStatistics:
            expectedStatistics.remove(stat.get_name())

    if len(expectedStatistics) == 0:
        logger.info('All ' + str(numOfExpStat) + ' statistics appear')
    else:
        logger.error('The following statistics are missing: ' + str(expectedStatistics))
        status = False

    return status


def createVm(positive, vmName, vmDescription, cluster='Default', nic=None, nicType=None,
        mac_address=None, storageDomainName=None, size=None, diskType=ENUMS['disk_type_data'],
        volumeType='true', volumeFormat=ENUMS['format_cow'],
        diskInterface=ENUMS['interface_ide'], bootable='true',
        wipe_after_deletion='false', start='false', template='Blank',
        templateUuid=None, type=ENUMS['vm_type_desktop'],
        os_type='UNASSIGNED', memory=1073741824, cpu_socket=1, cpu_cores=1,
        display_type=ENUMS['display_type_spice'], installation=False, slim=False,
        user=None, password=None, attempt=60, interval=60,
        cobblerAddress=None, cobblerUser=None, cobblerPasswd=None, async=False,
        hostname=None, network='rhevm', useAgent=False):
    '''
    The function createStartVm adding new vm with nic,disk and started new created vm.
        vmName = VM name
        vmDescription = Decription of VM
        cluster = cluster name
        nic = nic name
        storageDomainName = storage doamin name
        size = size of disk (in bytes)
        diskType = disk type (SYSTEM,DATA)
        volumeType = true its mean sparse (thin provision) ,false - preallocated.
        volumeFormat = format type (COW)
        diskInterface = disk interface (VIRTIO or IDE ...)
        bootable = True when disk bootable otherwise False
        wipe_after_deletion = Can be true or false
        type - vm type (SERVER or DESKTOP)
        start = in case of true the function start vm
        template = name of already created template or Blank (start from scratch)
        display_type - type of vm display (VNC or SPICE)
        installation - true for install os and check connectivity in the end
        slim - true for slim os(relevant to installation)
        user - user to connect to vm after installation
        password - password to connect to vm after installation
        attempt- attempts to connect after installation
        inerval - interval between attempts
        useAgent - Set to 'true', if desired to read the ip from VM (agent exist on VM)
    return values : Boolean value (True/False ) True in case of success otherwise False
    '''
    ip = False
    if not addVm(positive, name=vmName, description=vmDescription, cluster=cluster,
            template=template, templateUuid=templateUuid, os_type=ENUMS[os_type.lower()],
            type=type, memory=memory, cpu_socket=cpu_socket,
            cpu_cores=cpu_cores, display_type=display_type, async=async):
        return False

    if nic:
        if not addNic(positive, vm=vmName, name=nic, interface=nicType,
                      mac_address=mac_address, network=network):
            return False

    if template == 'Blank' and storageDomainName and templateUuid == None:
        if not addDisk(positive, vm=vmName, size=size, storagedomain=storageDomainName, type=diskType, sparse=volumeType,
                            interface=diskInterface, format=volumeFormat, bootable=bootable, wipe_after_deletion=wipe_after_deletion):
            return False

    if installation == True:
        (status, res) = getImageByOsType(positive, os_type, slim)
        if not status:
            return False

        if not unattendedInstallation(positive, vmName,
                            cobblerAddress, cobblerUser, cobblerPasswd,
                            image=res['osBoot'], floppyImage=res['floppy'],
                            nic=nic, hostname=hostname):
            return False

        if useAgent:
            ip = waitForIP(vmName)

        return checkVMConnectivity(positive, vmName, os_type,
                                   attempt=attempt, interval=interval,
                                   nic=nic, user=user , password=password,
                                   ip=ip)

    else:
        if (start.lower() == 'true'):
            if not startVm(positive, vmName):
                return False

        return True


def waitForIP(vm, timeout=600, sleep=DEF_SLEEP):
    '''
    Description: Waits until agent starts reporting IP address
    Author: jlibosva
    Parameters:
       * vm - name of the virtual machine
       * timeout - how long to wait
       * sleep - polling interval
    Return: First IP occurence or False if no ip has been found
    '''
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(sleep)
        guest_info = VM_API.find(vm).get_guest_info()
        if guest_info is not None:
            return guest_info.get_ips().get_ip()[0].get_address()

    return False


#TODO: replace with generic "async create requests" mechanism
def createVms(positive, amount=2, **kwargs):
    """
    Create and start (if specified) multiple VMs.
    NOTE: this is a temporary solution for create multiple
        VMs request, should be replaced in the near future.
    Author: mbenenso
    Parameters:
       * amount - amount of VMs to create
       * **kwargs - exact set of parameters as for @createVM function
    Return: list of createVm results for each VM
    """
    targetsList = ['createVm'] * amount
    paramsList = []
    for i in xrange(amount):
        currParams = deepcopy(kwargs)
        currParams['positive'] = positive
        currParams['vmName'] += "_%s" % i
        currParams["async"] = True
        paramsList.append(currParams)
    return runParallel(targetsList, paramsList)


def getVmMacAddress(positive, vm, nic='nic1'):
    '''Function return mac address of vm with specific nic'''
    try:
        nicObj = getVmNic(vm, nic)
    except EntityNotFound:
        return False, {'macAddress': None}
    return True, {'macAddress': str(nicObj.mac.address)}


def unattendedInstallation(positive, vm, cobblerAddress, cobblerUser,
                           cobblerPasswd, image, floppyImage=None,
                           nic='nic1', hostname=None):
    '''
    Description: install VM with answer file:
    unattended floppy disk for windows.
    via PXE for rhel.
    Author: Tomer
    Parameters:
       * vm - VM with clean bootable hard disk.
       * image- cdrom image for windows or profile for rhel.
       * floppyImage- answer file for windows.
       * nic- nic name to find out mac address- relevant for rhel only.
    Return: status (True if VM started to insall OS, False otherwise).
    '''
    boot_dev = 'cdrom'
    if re.search('rhel', image, re.I):
        status, mac = getVmMacAddress(positive, vm, nic=nic)
        if not cobblerAddNewSystem(cobblerAddress, cobblerUser, cobblerPasswd,
                                   mac=mac['macAddress'], osName=image):
            return False

        if hostname:
            if not cobblerSetLinuxHostName(cobblerAddress, cobblerUser, cobblerPasswd,
                                           name=mac['macAddress'], hostname=hostname):
                return False

        boot_dev = 'hd,network'
        image = None
    return runVmOnce(positive, vm, cdrom_image=image, floppy_image=floppyImage,
                     boot_dev=boot_dev)


def waitUntilQuery(vm, query, timeout=VM_IMAGE_OPT_TIMEOUT,
                   sleep=VM_SAMPLING_PERIOD):
    """
    Description: Waits until object given by query above VM is found
    Parameters:
        * vm - name of vm
        * query - query above given VM
        * timeout - how long should wait
        * sleep - polling interval
    Author: jlibosva
    Return: True if VM was found in given timeout interval, false otherwise
    """
    query = ' and '.join(["name=%s" % vm, query]) if query else "name=%s" % vm

    return VM_API.waitForQuery(query, timeout=timeout, sleep=sleep)


def activateVmDisk(positive, vm, diskAlias=None, diskId=None, wait=True):
    """
    Description: Activates vm's disk
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    return changeVmDiskState(positive, vm, 'activate', diskAlias, diskId,
                             wait)


def deactivateVmDisk(positive, vm, diskAlias=None, diskId=None, wait=True):
    """
    Description: Deactivates vm's disk
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    return changeVmDiskState(positive, vm, 'deactivate', diskAlias, diskId,
                             wait)


def changeVmDiskState(positive, vm, action, diskAlias, diskId, wait):
    """
    Description: Change vm's disk active state
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * action - activate or deactivate
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    if diskAlias is None and diskId is None:
        VM_API.logger.error("Disk must be specified either by alias or ID")
        return False

    disk = _getVmDiskById(vm, diskId) if diskId is not None else \
           _getVmFirstDiskByName(vm, diskAlias)

    status = DISKS_API.syncAction(disk, action, positive)
    if status and wait:
        return DISKS_API.waitForElemStatus(disk, 'ok', 300)
    return status


def waitForVmDiskStatus(vm, active, diskAlias=None, diskId=None,
                        timeout=VM_ACTION_TIMEOUT, sleep=DEF_SLEEP):
    """
    Description: Waits for desired status of disk within VM (active,
                 deactivated)
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * active - boolean True if active, False if deactivated
        * diskAlias - name of the disk
        * diskId - disk's id
        * timeout - timeout
        * sleep - polling interval
    Return: True if desired state was reached, False on timeout
    """
    if diskAlias is None and diskId is None:
        VM_API.logger.error("Disk must be specified either by alias or ID")
        return False

    getFunc, diskDesc = (_getVmDiskById, diskId) if diskId is not None else \
           (_getVmFirstDiskByName, diskAlias)

    disk = getFunc(vm, diskDesc)
    cur_state = disk.get_active()

    t_start = time.time()
    while time.time() - t_start < timeout and cur_state != active:
        time.sleep(sleep)
        disk = getFunc(vm, diskDesc)
        cur_state = disk.get_active()

    return cur_state == active


def checkVMConnectivity(positive, vm, osType, attempt=1, interval=1,
                        nic='nic1', user=None, password=None, ip=False):
    '''
    Description: check VM Connectivity
    Author: tomer
    Editor: atal
    Parameters:
       * vm - vm name
       * osType - os type element rhel/windows.
       * attempt - number of attempts to connect .
       * interval - interval between attempts
       * ip - if supplied, check VM connectivity by this IP.
    Return: status (True if succeed to connect to VM, False otherwise).
    '''
    vlan = None
    if re.search('rhel', osType, re.I):
        osType = 'linux'
    elif re.search('win', osType, re.I):
        osType = 'windows'
    else:
        VM_API.logger.error('Wrong value for osType: Should be rhel or windows ')
        return False

    if not ip:
        status, mac = getVmMacAddress(positive, vm, nic=nic)
        if not status:
            return False
        status, vlan = getVmNicVlanId(vm, nic)
        status, ip = convertMacToIpAddress(positive, mac=mac['macAddress'],
                                           vlan=vlan['vlan_id'])
        if not status:
            return False
        ip = ip['ip']
    status, res = checkHostConnectivity(positive, ip,
                                       user=user, password=password,
                                       osType=osType, attempt=attempt,
                                       interval=interval)
    VM_API.logger.info('VM: %s TYPE: %s, IP: %s, VLAN: %s, NIC: %s \
                Connectivity Status: %s' % (vm, osType, ip, vlan, nic, status))
    return status


def checkMultiVMsConnectivity(positive, vms, osType, attempt=1, interval=1,
                              nic='nic1', user=None, password=None):
    '''
    Description: check Multi VMs Connectivity
    Author: Tomer
    Editor: atal
    Parameters:
       * vms - string of VMs seperate by comma or space.
       * osType - os type element rhel/windows.
       * attempt - number of attempts to connect .
       * interval - interval between attempts
    Return: status (True if al vm succeed, False otherwise).
    '''
    status = True
    for vm in split(vms):
        if not checkVMConnectivity(positive, vm, osType, attempt,
                                   interval, nic, user, password):
            VM_API.logger.error('Missing connectivity with %s, nic %s' % (vm, nic))
            status = False
    return status


def checkVmMultiNicsConnectivity(positive, vm, osType, nics, attempt=1,
                                 interval=1, user=None, password=None):
    '''
    checking VM multiple nics connectivity
    Author: atal
    Parameters:
        * vm - vm name
        * osType - OS type name
        * nics - a list of VM nics nam (a name like "nic162"
                                        represent vlan 162)
        * attampt/insterval - a retry params
        * user - remote host user login
        * password - remote host password login
    return True/False
    '''
    status = True
    for nic in nics:
        if not checkVMConnectivity(positive, vm, osType, attempt,
                                   interval, nic, user, password):
            VM_API.logger.error('No connection to %s on %s' % (vm, nic))
            status = False
    return status


def addMultiNicsToVM(positive, vm, nicTypes, network, nicPrefix='vmNic'):
    '''
    Adding multiple Nics to vm with different randome type.
    Author: atal
    Parameters:
        * vm - vm name
        * nicTypes - straing, contains different nic types separated by ','
                     (exp: 'e1000,virtio')
        * nicPrefix - prefix for the nic name.
    Return: status (True if vm was moved properly, False otherwise)
    '''
    for idx, item in enumerate(nicTypes.split(',')):
        status = addNic(positive, vm=vm, name=nicPrefix + str(idx),
                        network=network, interface=item.strip())
    return status


def getVmNicAttr(vm, nic, attr):
    '''
    get host's nic attribute value
    Author: atal
    Parameters:
       * host - name of a host
       * nic - name of nic we'd like to check
       * attr - attribute of nic we would like to recive.
                attr can dive deeper as a string with DOTS ('.').
    return: True if the function succeeded, otherwise False
    '''
    try:
        nic_obj = getVmNic(vm, nic)
    except EntityNotFound:
        return False, {'attrValue': None}

    for tag in attr.split('.'):
        try:
            nic_obj = getattr(nic_obj, tag)
        except AttributeError as err:
            VM_API.logger.error(str(err))
            return False, {'attrValue': None}
    return True, {'attrValue': nic_obj}


def addIfcfgFile(positive, vm, user, password, nic='nic1', nic_name='eth1',
                 onboot='yes', bootProto='dhcp', nic_ip='',
                 nic_netmask='255.255.255.0', nic_gateway=''):
    '''
    Only for Linux VM
    Adding network ifcfg file to support new added nic
    Author: atal
        * vm - vm name
        * user/password - vm credentials
        * nic - connectint through VM nic (exp 'nic1')
        * nic_name - new network name (ifcfg-<nic>)
        * vlan - vlan id in case phisical nic connected to network switch
        * onboot/bootProto/nic_ip/nic_netmask/nic_gateway -
          Regular initscripts parameters
    return: True if the function succeeded, otherwise False
    '''
    status, mac = getVmMacAddress(positive, vm, nic=nic)
    if not status:
        return False
    res, vlan = getVmNicVlanId(vm, nic)
    status, ip = convertMacToIpAddress(positive, mac=mac['macAddress'],
                                       vlan=vlan['vlan_id'])
    if not status:
        return False

    vm = Machine(ip['ip'], user, password).util('linux')
    status = vm.addNicConfFile(nic_name, onboot, bootProto, nic_ip,
                               nic_netmask, nic_gateway)
    VM_API.logger.info('Adding nic: %s to VM: %s Status: %s' % (nic_name, vm, status))
    return status


def getVmHost(vm):
    '''
    Explore which host is running the VM
    Author: atal
    parameter:
        * vm - vm name
    return - tuple (True, hostname in dict or False, None)
    '''
    try:
        vm_obj = VM_API.find(vm)
        host_obj = HOST_API.find(vm_obj.host.id, 'id')
    except EntityNotFound:
        return False, {'vmHoster': None}
    return True, {'vmHoster': host_obj.get_name()}


def getVmNicVlanId(vm, nic='nic1'):
    '''
    Get nic vlan id if configured
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name
    Return: tuple (True and {'vlan_id': id} in case of success
                   False and {'vlan_id': 0} otherwise)
    '''
    try:
        nic_obj = getVmNic(vm, nic)
        net_obj = NETWORK_API.find(nic_obj.network.id, 'id')
    except EntityNotFound:
        return False, {'vlan_id': 0}

    try:
        return True, {'vlan_id': int(net_obj.vlan.id)}
    except AttributeError:
        VM_API.logger.warning('%s network doesnt contain vlan id.' % net_obj.get_name())
    return False, {'vlan_id': 0}


def validateVmDisks(positive, vm, sparse, format):
    '''
    Description - validate vm disks characteristics (for identical disks)
    TBD - add support for mixed disks
    Author: lustalov
        * vm - vm name
        * sparse - disk allocation type (true/false)
        * format - disk format (COW/RAW)
    Return: status (True/False)
    '''
    vmObj = VM_API.find(vm)
    disks = VM_API.getElemFromLink(vmObj, link_name='disks', attr='disk',
                                   get_href=False)

    for disk in disks:
        if disk.get_sparse() != sparse:
            logger.error("VM disk %s allocation type %s is not as expected: %s"
                        % (disk.id, str(disk.get_sparse()), str(sparse)))
            return not positive
        if disk.get_format().lower() != format.lower():
            logger.error("VM disk %s format %s is not as expected: %s" %
                         (disk.id, disk.format, format))
            return not positive
    return positive


