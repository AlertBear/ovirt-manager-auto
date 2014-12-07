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
import shlex
from concurrent.futures import ThreadPoolExecutor
import logging
from operator import and_
from Queue import Queue
import random
import os
import re
import time
from threading import Thread
from art.core_api import is_action
from art.core_api.apis_exceptions import (
    APITimeout, EntityNotFound, TestCaseError,
)
from art.core_api.apis_utils import data_st, TimeoutingSampler, getDS
from art.rhevm_api.tests_lib.high_level.disks import delete_disks
from art.rhevm_api.tests_lib.low_level.disks import (
    _prepareDiskObject, getVmDisk, getObjDisks, get_other_storage_domain,
    waitForDisksState, get_disk_storage_domain_name,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.networks import (
    getVnicProfileObj, MGMT_NETWORK,
)
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.rhevm_api.utils.test_utils import (
    searchForObj, getImageByOsType, convertMacToIpAddress,
    checkHostConnectivity, update_vm_status_in_database, get_api, split,
    waitUntilPingable, restoringRandomState, waitUntilGone,
)
from art.rhevm_api.utils.provisioning_utils import ProvisionProvider
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.xpath_utils import XPathMatch, XPathLinks
from art.test_handler.settings import opts
from art.test_handler.exceptions import CanNotFindIP
from art.test_handler import exceptions
from utilities.jobs import Job, JobsSet
from utilities.utils import pingToVms, makeVmList
from utilities.machine import Machine, LINUX


ENUMS = opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEF_SLEEP = 10
VM_SNAPSHOT_ACTION = 600
VM_ACTION_TIMEOUT = 600
VM_REMOVE_SNAPSHOT_TIMEOUT = 1200
VM_DISK_CLONE_TIMEOUT = 720
VM_IMAGE_OPT_TIMEOUT = 900
VM_INSTALL_TIMEOUT = 1800
CLONE_FROM_SNAPSHOT = 1500
VM_SAMPLING_PERIOD = 3

SNAPSHOT_SAMPLING_PERIOD = 5
SNAPSHOT_APPEAR_TIMEOUT = 120
FILTER_DEVICE = '[sv]d'
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
DD_TIMEOUT = 1500

BLANK_TEMPLATE = '00000000-0000-0000-0000-000000000000'
ADD_DISK_KWARGS = ['size', 'type', 'interface', 'format', 'bootable',
                   'sparse', 'wipe_after_delete', 'propagate_errors',
                   'alias', 'active', 'read_only']
VM_WAIT_FOR_IP_TIMEOUT = 600
SNAPSHOT_TIMEOUT = 15 * 60
PREVIEW = ENUMS['preview_snapshot']
UNDO = ENUMS['undo_snapshot']
COMMIT = ENUMS['commit_snapshot']
LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']

VM_API = get_api('vm', 'vms')
VNIC_PROFILE_API = get_api('vnic_profile', 'vnicprofiles')
DC_API = get_api('data_center', 'datacenters')
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
WATCHDOG_API = get_api('watchdog', 'watchdogs')
CAP_API = get_api('version', 'capabilities')
Snapshots = getDS('Snapshots')

logger = logging.getLogger(__name__)
xpathMatch = is_action('xpathVms', id_name='xpathMatch')(XPathMatch(VM_API))
xpathVmsLinks = is_action(
    'xpathVmsLinks', id_name='xpathVmsLinks')(XPathLinks(VM_API))


ProvisionContext = ProvisionProvider.Context()


class DiskNotFound(Exception):
    pass


def _prepareVmObject(**kwargs):

    add = kwargs.pop('add', False)
    description = kwargs.pop('description', None)
    if description is None or description == '':
        vm = data_st.VM(name=kwargs.pop('name', None))
    else:
        vm = data_st.VM(name=kwargs.pop('name', None), description=description)

    # snapshot
    snapshot_name = kwargs.pop('snapshot', None)
    if snapshot_name:
        add = False
        vms = VM_API.get(absLink=False)
        for vmachine in vms:
            try:
                snObj = _getVmSnapshot(vmachine.name, snapshot_name)
            except EntityNotFound:
                pass
            else:
                snapshots = Snapshots()
                snapshots.add_snapshot(snObj)
                vm.set_snapshots(snapshots)
                break

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

    # cluster
    cluster_name = kwargs.pop('cluster', DEFAULT_CLUSTER if add else None)
    cluster_id = kwargs.pop('clusterUuid', None)
    search_by = NAME_ATTR
    if cluster_id:
        cluster_name = cluster_id
        search_by = ID_ATTR
    if cluster_name:
        cluster = CLUSTER_API.find(cluster_name, search_by)
        vm.set_cluster(cluster)

    # memory
    vm.memory = kwargs.pop('memory', None)

    # cpu topology & cpu pinning
    cpu_socket = kwargs.pop('cpu_socket', None)
    cpu_cores = kwargs.pop('cpu_cores', None)
    vcpu_pinning = kwargs.pop('vcpu_pinning', None)
    cpu_mode = kwargs.pop('cpu_mode', None)
    if cpu_socket or cpu_cores or vcpu_pinning is not None or \
       cpu_mode is not None:
        cpu = data_st.CPU()
        if cpu_socket or cpu_cores:
            cpu.set_topology(topology=data_st.CpuTopology(sockets=cpu_socket,
                                                          cores=cpu_cores))
        if vcpu_pinning is not None and vcpu_pinning == "":
            cpu.set_cpu_tune(data_st.CpuTune())
        elif vcpu_pinning:
            cpu.set_cpu_tune(
                data_st.CpuTune(
                    [
                        data_st.VCpuPin(
                            elm.keys()[0],
                            elm.values()[0]
                        ) for elm in vcpu_pinning
                    ]
                )
            )
        if cpu_mode is not None and cpu_mode == "":
            cpu.set_mode("CUSTOM")
        elif cpu_mode:
            cpu.set_mode(cpu_mode)
        vm.set_cpu(cpu)

    # os options
    apply_os = False
    os_type = kwargs.pop('os_type', None)
    if os_type is not None:
        os_type = ENUMS.get(os_type.lower(), os_type.lower())
        apply_os = True
    os_type = data_st.OperatingSystem(type_=os_type)
    for opt_name in 'kernel', 'initrd', 'cmdline':
        opt_val = kwargs.pop(opt_name, None)
        if opt_val:
            apply_os = True
            setattr(os_type, opt_name, opt_val)
    boot_seq = kwargs.pop('boot', None)
    if boot_seq:
        if isinstance(boot_seq, basestring):
            boot_seq = boot_seq.split()
        os_type.set_boot([data_st.Boot(dev=boot_dev) for boot_dev in boot_seq])
        apply_os = True
    if apply_os:
        vm.set_os(os_type)

    # type
    vm.set_type(kwargs.pop('type', None))

    # display monitors and type
    display_type = kwargs.pop('display_type', None)
    display_monitors = kwargs.pop('display_monitors', None)
    if display_monitors or display_type:
        vm.set_display(data_st.Display(type_=display_type,
                                       monitors=display_monitors))

    # stateless
    vm.set_stateless(kwargs.pop('stateless', None))

    # high availablity
    ha = kwargs.pop('highly_available', None)
    ha_priority = kwargs.pop('availablity_priority', None)
    if ha is not None or ha_priority:
        vm.set_high_availability(
            data_st.HighAvailability(enabled=ha,
                                     priority=ha_priority))

    # custom properties
    custom_prop = kwargs.pop('custom_properties', None)
    if custom_prop:
        vm.set_custom_properties(createCustomPropertiesFromArg(custom_prop))

    # memory policy memory_guaranteed
    guaranteed = kwargs.pop('memory_guaranteed', None)
    if guaranteed:
        vm.set_memory_policy(data_st.MemoryPolicy(guaranteed))

    # placement policy: placement_affinity & placement_host
    affinity = kwargs.pop('placement_affinity', None)
    phost = kwargs.pop('placement_host', None)
    if phost or affinity:
        ppolicy = data_st.VmPlacementPolicy()
        if affinity:
            ppolicy.set_affinity(affinity)
        if phost and phost == ENUMS['placement_host_any_host_in_cluster']:
            ppolicy.set_host(data_st.Host())
        elif phost:
            aff_host = HOST_API.find(phost)
            ppolicy.set_host(data_st.Host(id=aff_host.id))
        vm.set_placement_policy(ppolicy)

    # storagedomain
    sd_name = kwargs.pop('storagedomain', None)
    if sd_name:
        sd = STORAGE_DOMAIN_API.find(sd_name)
        vm.set_storage_domain(sd)

    #  domain_name
    domain_name = kwargs.pop('domainName', None)
    if domain_name:
        vm.set_domain(data_st.Domain(name=domain_name))

    # disk_clone
    disk_clone = kwargs.pop('disk_clone', None)
    if disk_clone and disk_clone.lower() == 'true':
        disk_array = data_st.Disks()
        disk_array.set_clone(disk_clone)
        vm.set_disks(disk_array)

    # quota
    quota_id = kwargs.pop('quota', None)
    if quota_id == '':
        vm.set_quota(data_st.Quota())
    elif quota_id:
        vm.set_quota(data_st.Quota(id=quota_id))

    # payloads
    payloads = kwargs.pop('payloads', None)
    if payloads:
        payload_array = []
        payload_files = data_st.Files()
        for payload_type, payload_fname, payload_file_content in payloads:
            payload_file = data_st.File(name=payload_fname,
                                        content=payload_file_content)
            payload_files.add_file(payload_file)
            payload = data_st.Payload(payload_type, payload_files)
            payload_array.append(payload)
        payloads = data_st.Payloads(payload_array)
        vm.set_payloads(payloads)

    # delete protection
    protected = kwargs.pop('protected', None)
    if protected is not None:
        vm.set_delete_protected(protected)

    # copy_permissions
    copy_permissions = kwargs.pop('copy_permissions', None)
    if copy_permissions:
        perms = data_st.Permissions()
        perms.set_clone(True)
        vm.set_permissions(perms)

    # initialization
    initialization = kwargs.pop('initialization', None)
    if initialization:
        vm.set_initialization(initialization=initialization)

    # timezone
    vm.timezone = kwargs.pop('timezone', None)

    return vm


def createCustomPropertiesFromArg(prop_arg):
    """
    Create custom properties object
    :param prop_arg: Custom properties to create (send clear to remove any
    configured custom properties)
    :type prop_arg: str
    :return: cps
    :rtype: object
    """
    cps = data_st.CustomProperties()
    if prop_arg == "clear":
        return cps

    props = prop_arg.split(';')
    for prop in props:
        try:
            name, value = prop.split('=', 1)
        except ValueError:
            e = "Custom Properties should be in form " \
                "'name1=value1;name2=value2'. Got '%s' instead."
            raise Exception(e % prop_arg)
        cps.add_custom_property(
            data_st.CustomProperty(name=name, value=value)
        )
    return cps


@is_action()
def addVm(positive, wait=True, **kwargs):
    '''
    Description: add new vm (without starting it)
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
       * vcpu_pinning - vcpu pinning affinity (dictionary)
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
       * quota - vm quota
       * snapshot - description of snapshot to use. Causes error if not unique
       * copy_permissions - True if perms should be copied from template
       * timeout - waiting timeout
       * protected - true if VM is delete protected
    Return: status (True if vm was added properly, False otherwise)
    '''
    kwargs.update(add=True)
    vmObj = _prepareVmObject(**kwargs)
    status = False

    # Workaround for framework validator:
    #     if disk_clone==false Tempalte_Id will be set to BLANK_TEMPLATE
    # expectedVm = deepcopy(vmObj)
    expectedVm = _prepareVmObject(**kwargs)

    if False in [positive, wait]:
        vmObj, status = VM_API.create(vmObj, positive,
                                      expectedEntity=expectedVm)
        return status

    disk_clone = kwargs.pop('disk_clone', None)

    wait_timeout = kwargs.pop('timeout', VM_ACTION_TIMEOUT)
    if disk_clone and disk_clone.lower() == 'true':
        expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
        wait_timeout = VM_DISK_CLONE_TIMEOUT

    vmObj, status = VM_API.create(vmObj, positive, expectedEntity=expectedVm)

    if status:
        status = VM_API.waitForElemStatus(vmObj, "DOWN", wait_timeout)

    return status


@is_action()
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
       * cpu_mode - mode of cpu
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
       * availablity_priority - priority for high-availability (an integer in
                   range 0-100 where 0 - Low, 50 - Medium, 100 - High priority)
       * custom_properties - custom properties set to the vm
       * stateless - if vm stateless or not
       * memory_guaranteed - size of guaranteed memory in bytes
       * domainName = sys.prep domain name
       * placement_affinity - vm to host affinity
       * placement_host - host that the affinity holds for
       * quota - vm quota
       * protected - true if vm is delete protected
       * watchdog_model - model of watchdog card (ib6300)
       * watchdog_action - action of watchdog card
       * timezone - set to timezone out of product possible timezones.
                    There must be a match between timezone and OS.
       * compare - disable or enable validation for update
    Return: status (True if vm was updated properly, False otherwise)
    '''
    vm_obj = VM_API.find(vm)
    vm_new_obj = _prepareVmObject(**kwargs)
    compare = kwargs.get('compare', True)
    vm_new_obj, status = VM_API.update(vm_obj, vm_new_obj, positive,
                                       compare=compare)

    watchdog_model = kwargs.pop('watchdog_model', None)
    watchdog_action = kwargs.pop('watchdog_action', None)

    if status and watchdog_model is not None:
        status = updateWatchdog(vm, watchdog_model, watchdog_action)

    return status


@is_action()
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
    vmStatus = vmObj.get_status().get_state().lower()
    stopVM = kwargs.pop('stopVM', 'false')
    if str(stopVM).lower() == 'true' and vmStatus != ENUMS['vm_state_down']:
        if not stopVm(positive, vm):
            return False
    status = VM_API.delete(vmObj, positive, body=body, element_name='action')

    wait = kwargs.pop('wait', True)
    if positive and wait and status:
        return waitForVmsGone(positive, vm, kwargs.pop('timeout', 60),
                              kwargs.pop('waitTime', 10))
    return status


def removeVmAsynch(positive, tasksQ, resultsQ, stopVmBool=False):
    '''
    Removes the cluster. It's supposed to be a worker of Thread.
    Author: jhenner
    Parameters:
        * tasksQ - A input Queue of VM names to remove
        * resultsQ - A output Queue of tuples tuple(VM name, VM removal status)
        * stopVm - if True will attempt to stop VM before actually remove it
                   (False by default)
    '''
    vm = tasksQ.get(True)
    status = False
    try:
        vmObj = VM_API.find(vm)
        if stopVmBool and vmObj.status.state.lower() != 'down':
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


@is_action()
def removeVms(positive, vms, stop='false', timeout=180):
    '''
    Removes the VMs specified by `vms` commas separated list of VM names.
    Author: jhenner
    Parameters:
        * vms - a list or a string list separated by comma of vms
        * stop - will attempt to stop VMs if 'true' ('false' by default)
        * timeout -in secs, used for waitForVmsGone
    '''
    assert positive
    tasksQ = Queue()
    resultsQ = Queue()
    threads = set()
    if isinstance(vms, basestring):
        # 'vm1, vm2' -> [vm1, vm2]
        vmsList = split(vms)
    else:
        vmsList = vms
    if not vmsList:
        raise ValueError("vms cannot be empty")

    if str(stop).lower() == 'true':
        stopVms(vmsList)

    for i in vmsList:
        t = Thread(target=removeVmAsynch, name='VM removing',
                   args=(positive, tasksQ, resultsQ))
        threads.add(t)
        t.daemon = False
        t.start()

    for vm in vmsList:
        tasksQ.put(vm)

    tasksQ.join()  # block until all tasks are done
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
    return waitForVmsGone(positive, vmsList, timeout=timeout) and status


def waitForVmsGone(positive, vms, timeout=60, samplingPeriod=10):
    '''
    Wait for VMs to disappear from the setup. This function will block up to
    `timeout` seconds, sampling the VMs list every `samplingPeriod` seconds,
    until no VMs specified by names in `vms` exists.

    Parameters:
        * vms - comma (and no space) separated string of VM names to wait for
                or list of names
        * timeout - Time in seconds for the vms to disapear.
        * samplingPeriod - Time in seconds for sampling the vms list.
    '''
    return waitUntilGone(positive, vms, VM_API, timeout, samplingPeriod)


@is_action()
def waitForVmsStates(positive, names, states=ENUMS['vm_state_up'], *args,
                     **kwargs):
    '''
    Wait until all of the vms identified by names exist and have the desired
    status.
    Parameters:
        * names - List or comma separated string of VM's names with
                  status to wait for.
        * states - A state of the vms to wait for.
    Author: jhenner
    Return True if all events passed, otherwise False
    '''
    if isinstance(names, basestring):
        names = split(names)
    for vm in names:
        VM_API.find(vm)

    for vm in names:
        if not waitForVMState(vm, states):
            return False
    return True


@is_action()
def waitForVMState(vm, state='up', **kwargs):
    '''
    Wait until vm has the desired status
    Author: atal
    Parameters:
        * vm - name of vm
        * state - vm status should wait for (default is "powering_up")
          List of available statuses/states of VM:
          [unassigned, up, down, powering_up, powering_down,
          paused, migrating_from, migrating_to, unknown,
          not_responding, wait_for_launch, reboot_in_progress,
          saving_state, restoring_state, suspended,
          image_illegal, image_locked]
    Return True if event passed, otherwise False
    '''
    query = "name={0} and status={1}".format(
        vm, state.lower().replace('_', ''))

    return VM_API.waitForQuery(query, **kwargs)


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
        return VM_API.waitForElemStatus(vmObj, expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


def restartVm(vm, wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, async='false',
              wait_for_status=ENUMS['vm_state_up'], placement_host=None):
    '''
    Description: Stop and start vm.
    Parameters:
      * vm - name of vm
      * wait_for_ip - True/False wait for ip
      * timeout - timeout of wait for vm
      * async - stop VM asynchronously if 'true' ('false' by default)
      * wait_for_status - status which should have vm after starting it
      * placement_host - host where the vm should be started
    '''
    if not checkVmState(True, vm, ENUMS['vm_state_down']):
        if not stopVm(True, vm, async=async):
            return False
    return startVm(True, vm, wait_for_status=wait_for_status,
                   wait_for_ip=True, timeout=timeout,
                   placement_host=placement_host)


@is_action()
def startVm(positive, vm, wait_for_status=ENUMS['vm_state_powering_up'],
            wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, placement_host=None):
    """
    Start VM
    :param vm: name of vm
    :type vm: str
    :param wait_for_status: vm status should wait for (default is
    "powering_up") list of available statuses/states of VM:
           [unassigned, up, down, powering_up, powering_down,
           paused, migrating_from, migrating_to, unknown,
           not_responding, wait_for_launch, reboot_in_progress,
           saving_state, restoring_state, suspended,
           image_illegal, image_locked, None]
    :type wait_for_status: str
    :param wait_for_ip: wait for VM ip
    :type wait_for_ip: bool
    :param timeout: timeout to wait for ip to start
    :type timeout: int
    :param placement_host: host where the VM should start
    :type placement_host: str
    :return: status (True if vm was started properly, False otherwise)
    :rtype: bool
    """
    if not positive:
        wait_for_status = None

    vmObj = VM_API.find(vm)

    if placement_host:
        logging.info("Update vm %s to run on host %s", vm, placement_host)
        if not updateVm(True, vm, placement_host=placement_host):
            return False

    if not VM_API.syncAction(vmObj, 'start', positive):
        return False

    if wait_for_status is None:
        return True

    query = "name={0} and status={1} or name={0} and status=up".format(
        vm, wait_for_status.lower().replace('_', ''))
    started = VM_API.waitForQuery(query, timeout=timeout, sleep=10)
    if started and wait_for_ip:
        started = waitForIP(vm)[0]
        if started != positive:
            VM_API.logger.error("waitForIP returned %s, positive is set to %s",
                                started, positive)

    return started == positive


@is_action()
def startVms(vms, wait_for_status=ENUMS['vm_state_powering_up']):
    '''
    Start several vms simultaneously. Only action response is checked, no
    checking for vm UP status is performed.

    Parameters:
      * vms - Names of VMs to start.
    Returns: True iff all VMs started.
    '''
    if isinstance(vms, basestring):
        vms = split(vms)
    jobs = [Job(target=startVm,
                args=(True, vm, wait_for_status)) for vm in vms]
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


@is_action()
def stopVm(positive, vm, async='false'):
    '''
    Description: stop vm
    Author: edolinin
    Parameters:
       * vm - name of vm
       * async - stop VM asynchronously if 'true' ('false' by default)
    Return: status (True if vm was stopped properly, False otherwise)
    '''
    collect_vm_logs(vm)
    return changeVMStatus(positive, vm, 'stop', 'DOWN', async)


@is_action()
def stopVms(vms, wait='true'):
    '''
    Stop vms.
    Author: mbenenso
    Parameters:
       * vms - comma separated string of VM names or list
       * wait - if 'true' will wait till the end of stop action
               ('true' by default)
    Return: True iff all VMs stopped, False otherwise
    '''
    vmObjectsList = []
    if isinstance(vms, basestring):
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
    query_fmt = 'name={0} and status=down'
    for vmObj in vmObjectsList:
        query = query_fmt.format(vmObj.get_name())
        querySt = VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT,
                                      sleep=DEF_SLEEP)
        resultsList.append(querySt)

    return all(resultsList)


@is_action()
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


@is_action()
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
        return VM_API.waitForElemStatus(vmObj, expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


def getVmDisks(vm):
    """
    Description: Returns list of a vm's disks as data_structs objects, sorted
    according to the disks' aliases
    Parameters:
        * vm - name of the vm to get disks
    Return: list of disk objects attached to the vm
    Raises: EntityNotFound if vm does not exist
    """
    vmObj = VM_API.find(vm)
    disks = VM_API.getElemFromLink(vmObj, link_name='disks', attr='disk',
                                   get_href=False)
    disks.sort(key=lambda disk: disk.get_alias())
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
    disks = getVmDisks(vm)
    found = [disk for disk in disks if disk.get_id() == diskId]
    if not found:
        raise DiskNotFound("Disk with id %s was not found in vm's %s disk \
collection" % (diskId, vm))

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
    disks = getVmDisks(vm)
    found = [disk for disk in disks if disk.get_name() == diskName]
    if not found:
        raise DiskNotFound("Disk %s was not found in vm's %s disk collection" %
                           (diskName, vm))
    return found[idx]


@is_action('addDiskToVm')
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
        * sparse - if disk sparse or pre-allocated
        * bootable - if disk bootable or not
        * wipe_after_delete - if disk should be wiped after deletion or not
        * propagate_errors - if propagate errors or not
        * quota - disk quota
        * active - automatically activate the disk
        * alias - alias for the disk
        * description - description for the disk
        * read_only - if disk should be read only
        * shareable = True if disk should be shared, False otherwise
        * provisioned_size - disk's provisioned size
    Return: status (True if disk was added properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    disk = data_st.Disk(size=size, format=ENUMS['format_cow'],
                        interface=ENUMS['interface_ide'], sparse=True,
                        alias=kwargs.pop('alias', None),
                        description=kwargs.pop('description', None),
                        active=kwargs.get('active', True))

    # replace disk params from kwargs
    for param_name in ADD_DISK_KWARGS:
        param_val = kwargs.pop(param_name, None)
        if param_val is not None:
            logger.debug("addDisk parameter %s is %s", param_name, param_val)
            setattr(disk, param_name, param_val)
            logger.debug("%s is not none", param_val)

    # read_only
    read_only = kwargs.pop('read_only', None)
    if read_only is not None:
        disk.set_read_only(read_only)

    # shareable
    shareable = kwargs.pop('shareable', None)
    if shareable is not None:
        disk.set_shareable(shareable)

    # provisioned_size
    provisioned_size = kwargs.pop('provisioned_size', None)
    if provisioned_size is not None:
        disk.set_provisioned_size(provisioned_size)

    # quota
    quota_id = kwargs.pop('quota', None)
    if quota_id == '':
        disk.set_quota(data_st.Quota())
    elif quota_id:
        disk.set_quota(data_st.Quota(id=quota_id))

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


@is_action()
def removeDisk(positive, vm, disk, wait=True):
    '''
    Description: remove disk from vm
    Parameters:
       * vm - vm name
       * disk - name of disk that should be removed
       * wait - wait until finish if True
    Return: True if disk was removed properly, False otherwise
    '''
    diskExist = False
    for d in getVmDisks(vm):
        if d.name.lower() == disk.lower():
            status = VM_API.delete(d, positive)
            diskExist = True

    if not diskExist:
        raise EntityNotFound("Disk %s not found in vm %s" % (disk, vm))
    if positive and status and wait:
        startTime = time.time()
        logger.debug('Waiting for disk to be removed.')
        while diskExist:
            disks = getVmDisks(vm)
            if disks is None:
                return False
            disks = filter(lambda x: x.name.lower() == disk.lower(), disks)
            diskExist = bool(disks)
            if VM_IMAGE_OPT_TIMEOUT < time.time() - startTime:
                raise APITimeout(
                    'Timeouted when waiting for disk to be removed')
            time.sleep(VM_SAMPLING_PERIOD)

    return not diskExist


@is_action()
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
    disks = getVmDisks(vm)
    if disks:
        cnt = int(num_of_disks)
        actual_cnt = len(disks)
        cnt_rm = actual_cnt if actual_cnt < cnt else cnt
        for i in xrange(cnt_rm):
            disk = disks.pop()
            rc = rc and removeDisk(positive, vm, disk.name, wait)
    return rc


@is_action()
def waitForDisksStat(vm, stat='OK', timeout=VM_IMAGE_OPT_TIMEOUT):
    '''
    Wait for VM disks status
    Author: atal
    Parameters:
        * vm - vm name
        * stat = status we are waiting for
        * timeout - waiting period.
    Return True if all events passed, otherwise False
    '''
    status = True
    disks = getVmDisks(vm)
    for disk in disks:
        status = DISKS_API.waitForElemStatus(disk, stat, timeout)
    return status


@is_action()
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
        VM_API.logger.warning('There are no cdroms attached to vm %s', vmName)
        return not positive
    return positive


def _prepareNicObj(**kwargs):
    nic_obj = data_st.NIC()
    vnic_profile_obj = data_st.VnicProfile()

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'interface' in kwargs:
        nic_obj.set_interface(kwargs.get('interface'))

    if 'mac_address' in kwargs:
        nic_obj.set_mac(data_st.MAC(address=kwargs.get('mac_address')))

    if 'active' in kwargs:
        nic_obj.set_active(kwargs.get('active'))

    if 'plugged' in kwargs:
        nic_obj.set_plugged(str(kwargs.get('plugged')).lower())

    if 'linked' in kwargs:
        nic_obj.set_linked(kwargs.get('linked'))

    if 'network' in kwargs:
        vm_obj = VM_API.find(kwargs['vm'])
        cluster_id = vm_obj.get_cluster().get_id()
        cluster_obj = CLUSTER_API.find(cluster_id, attribute='id')

        if kwargs.get('network') is None:
            nic_obj.set_vnic_profile(vnic_profile_obj)
        else:
            vnic_profile_obj = getVnicProfileObj(kwargs.get('vnic_profile')
                                                 if 'vnic_profile' in kwargs
                                                 else
                                                 kwargs.get('network'),
                                                 kwargs.get('network'),
                                                 cluster_obj.get_name())

            nic_obj.set_vnic_profile(vnic_profile_obj)

    return nic_obj


@is_action()
def getVmNics(vm):

    vm_obj = VM_API.find(vm)
    return VM_API.getElemFromLink(vm_obj,
                                  link_name='nics',
                                  attr='vm_nic',
                                  get_href=True)


def getVmNic(vm, nic):

    vm_obj = VM_API.find(vm)
    return VM_API.getElemFromElemColl(vm_obj, nic, 'nics', 'nic')


@is_action()
def addNic(positive, vm, **kwargs):
    '''
    Description: add nic to vm
    Author: edolinin
    Parameters:
       * vm - vm where nic should be added
       * name - nic name
       * network - network name
       * vnic_profile - the VNIC profile that will be selected for the NIC
       * interface - nic type. available types: virtio, rtl8139 and e1000
                     (for 2.2 also rtl8139_virtio)
       * mac_address - nic mac address
       * active - Boolean attribute which present nic hostplug state
       * plugged - shows if VNIC is plugged/unplugged
       * linked - shows if VNIC is linked or not
    Return: status (True if nic was added properly, False otherwise)
    '''

    vm_obj = VM_API.find(vm)
    expectedStatus = vm_obj.get_status().get_state()

    nic_obj = _prepareNicObj(vm=vm, **kwargs)
    nics_coll = getVmNics(vm)

    res, status = NIC_API.create(nic_obj, positive, collection=nics_coll)

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(vm_obj,
                                        expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


@is_action()
def updateVmDisk(positive, vm, disk, **kwargs):
    '''
    Description: Update already existing vm disk
    Parameters:
      * vm - vm where disk should be updated
      * disk - name of the disk that should be updated
      * alias - new name of the disk
      * interface - IDE or virtio
      * bootable - True or False whether disk should be bootable
      * shareable - True or False whether disk should be sharable
      * size - new disk size in bytes
      * quota - disk quota
    Author: omachace
    Return: Status of the operation's result dependent on positive value
    '''
    disk_obj = _getVmFirstDiskByName(vm, disk)
    new_disk = _prepareDiskObject(**kwargs)

    disk, status = DISKS_API.update(disk_obj, new_disk, positive)
    return status


@is_action()
def updateNic(positive, vm, nic, **kwargs):
    '''
    Description: update nic of vm
    Author: edolinin
    Parameters:
       * vm - vm where nic should be updated
       * nic - nic name that should be updated
       * name - new nic name
       * network - network name
       * vnic_profile - the VNIC profile that will be selected for the NIC
       * interface - nic type. available types: virtio, rtl8139 and e1000
                     (for 2.2 also rtl8139_virio)
       * mac_address - nic mac address
       * active - Boolean attribute which present nic hostplug state
       * plugged - shows if VNIC is plugged/unplugged
       * linked - shows if VNIC is linked or not
    Return: status (True if nic was updated properly, False otherwise)
    '''
    nic_new = _prepareNicObj(vm=vm, **kwargs)
    nic_obj = getVmNic(vm, nic)

    nic, status = NIC_API.update(nic_obj, nic_new, positive)
    return status


@is_action()
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
        return VM_API.waitForElemStatus(vm_obj, expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


@is_action()
def hotPlugNic(positive, vm, nic):
    '''
    Description: implement hotPlug nic.
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name to plug.
    Return: True in case of succeed, False otherwise
    '''
    try:
        nic_obj = getVmNic(vm, nic)
    except EntityNotFound:
        logger.error('Entity %s not found!' % nic)
        return not positive

    return NIC_API.syncAction(nic_obj, "activate", positive)


@is_action()
def hotUnplugNic(positive, vm, nic):
    '''
    Description: implement hotUnplug nic.
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name to plug.
    Return: True in case of succeed, False otherwise
    '''
    try:
        nic_obj = getVmNic(vm, nic)
    except EntityNotFound:
        logger.error('Entity %s not found!' % nic)
        return not positive

    return NIC_API.syncAction(nic_obj, "deactivate", positive)


@is_action()
def remove_locked_vm(vm_name, vdc, vdc_pass,
                     psql_username=RHEVM_UTILS_ENUMS['RHEVM_DB_USER'],
                     psql_db=RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
                     psql_password=RHEVM_UTILS_ENUMS['RHEVM_DB_PASSWORD']):
    """
    Remove locked vm with flag force=true
    Make sure that vm no longer exists, otherwise set it's status to down,
    and remove it
    Author: jvorcak
    Parameters:
       * vm_name - name of the VM
       * vdc - address of the setup
       * vdc_pass - password for the vdc
       * psql_username - psql username
       * psql_db - name of the DB
    """
    vm_obj = VM_API.find(vm_name)

    if removeVm(True, vm_obj.get_name(), force='true'):
        return True

    # clean if vm has not been removed
    logger.error('Locked vm has not been removed with force flag')

    update_vm_status_in_database(vm_obj.get_name(), 0, vdc, vdc_pass,
                                 psql_username, psql_db, psql_password)

    return removeVm("true", vm_obj.get_name())


def _getVmSnapshots(vm, get_href=True):
    vmObj = VM_API.find(vm)
    return SNAPSHOT_API.getElemFromLink(vmObj, get_href=get_href)


def _getVmSnapshot(vm, snap, all_content=False):
    if all_content:
        backup_header = SNAPSHOT_API.api.headers.get('All-content', False)
        SNAPSHOT_API.api.headers['All-content'] = True
    try:
        vm_obj = VM_API.find(vm)
        returned_object = SNAPSHOT_API.getElemFromElemColl(vm_obj, snap,
                                                           'snapshots',
                                                           'snapshot',
                                                           prop='description')
    finally:
        if all_content:
            SNAPSHOT_API.api.headers['All-content'] = backup_header
    return returned_object


@is_action()
def addSnapshot(positive, vm, description, wait=True, persist_memory=None,
                disks_lst=None):
    '''
    Description: add snapshot to vm
    Author: edolinin, ratamir
    Parameters:
       * vm - vm where snapshot should be added
       * description - snapshot name
       * wait - wait until finish when True or exist without waiting when False
       * persist_memory - True to save memory state snapshot, default is False
       * disks_lst - if not None, this list of disks names will be included in
         snapshot's disks (Single disk snapshot)
    Return: status (True if snapshot was added properly, False otherwise)
    '''
    snapshot = data_st.Snapshot()
    snapshot.set_description(description)
    snapshot.set_persist_memorystate(persist_memory)

    if disks_lst:
        disks_coll = data_st.Disks()
        for disk in disks_lst:

            diskObj = DISKS_API.find(disk)

            disk = data_st.Disk()
            disk.set_id(diskObj.get_id())

            disks_coll.add_disk(disk)

        snapshot.set_disks(disks_coll)

    vmSnapshots = _getVmSnapshots(vm)

    snapshot, status = SNAPSHOT_API.create(snapshot, positive,
                                           collection=vmSnapshots,
                                           compare=wait)

    if wait:
        wait_for_jobs()

    try:
        snapshot = _getVmSnapshot(vm, description)
    except EntityNotFound:
        return False == positive

    snapshotStatus = True
    if status and positive and wait:
        snapshotStatus = SNAPSHOT_API.waitForElemStatus(
            snapshot, 'ok', VM_IMAGE_OPT_TIMEOUT,
            collection=_getVmSnapshots(vm, False))
        if snapshotStatus:
            snapshotStatus = validateSnapshot(positive, vm, description)
    return status and snapshotStatus


@is_action()
def validateSnapshot(positive, vm, snapshot):
    '''
    Description: Validate snapshot if exist
    Author: egerman
    Parameters:
       * vm - vm where snapshot should be restored
       * snapshot - snapshot name
    Return: status (True if snapshot exist, False otherwise)
    '''
    try:
        _getVmSnapshot(vm, snapshot)
        return True
    except EntityNotFound:
        return False


@is_action()
def removeSnapshot(positive, vm, description,
                   timeout=VM_REMOVE_SNAPSHOT_TIMEOUT):
    '''
    Description: remove vm snapshot
    Author: jhenner
    Parameters:
       * vm          - vm where snapshot should be removed.
       * description - Snapshot description. Beware that snapshots aren't
                       uniquely identified by description.
       * timeout     - How long this would block until machine status switches
                       back to the one before deletion.
                       If timeout < 0, return immediately after getting the
                       action response, don't check the action on snapshot
                       really did something.
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
    args = (VM_API.find(vm), snapshot.id, 'snapshots', 'snapshot')
    kwargs = {'prop': 'id'}
    if positive:
        # Wait until snapshot disappears.
        try:
            for ret in TimeoutingSampler(
                    timeout, 5, SNAPSHOT_API.getElemFromElemColl, *args,
                    **kwargs):
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
            for ret in TimeoutingSampler(
                    timeout, 5, SNAPSHOT_API.getElemFromElemColl, *args,
                    **kwargs):
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


@is_action()
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
    # TODO Consider merging this method with the startVm.
    vm_obj = VM_API.find(vm)

    vm_for_action = data_st.VM()
    if display_type:
        vm_for_action.set_display(data_st.Display(type_=display_type))

    if None is not stateless:
        vm_for_action.set_stateless(stateless)

    if cdrom_image:
        cdrom = data_st.CdRom()
        vm_cdroms = data_st.CdRoms()
        cdrom.set_file(data_st.File(id=cdrom_image))
        vm_cdroms.add_cdrom(cdrom)
        vm_for_action.set_cdroms(vm_cdroms)

    if floppy_image:
        floppy = data_st.Floppy()
        floppies = data_st.Floppies()
        floppy.set_file(data_st.File(id=floppy_image))
        floppies.add_floppy(floppy)
        vm_for_action.set_floppies(floppies)

    if boot_dev:
        os_type = data_st.OperatingSystem()
        # boot_dev_seq = data_st.Boot()
        for dev in boot_dev.split(","):
            # boot_dev_seq.set_dev(dev)
            os_type.add_boot(data_st.Boot(dev=dev))
        vm_for_action.set_os(os_type)

    if host:
        host_obj = HOST_API.find(host)
        placement_policy = data_st.VmPlacementPolicy(host=host_obj)
        vm_for_action.set_placement_policy(placement_policy)

    if domainName:
        domain = data_st.Domain()
        domain.set_name(domainName)

        if user_name and password is not None:
            domain.set_user(data_st.User(user_name=user_name,
                                         password=password))

        vm_for_action.set_domain(domain)

    if pause:
        status = VM_API.syncAction(vm_obj, 'start', positive, pause=pause,
                                   vm=vm_for_action)
        if positive and status:
            # in case status is False we shouldn't wait for rest element status
            if pause.lower() == 'true':
                state = ENUMS['vm_state_paused']
            else:
                state = ENUMS['vm_state_powering_up']
            return VM_API.waitForElemStatus(vm_obj, state, VM_ACTION_TIMEOUT)
    else:
        status = VM_API.syncAction(vm_obj, 'start', positive, vm=vm_for_action)
        if positive and status:
            # in case status is False we shouldn't wait for rest element status
            return VM_API.waitForElemStatus(
                vm_obj,
                ENUMS['vm_state_powering_up'] + " " + ENUMS['vm_state_up'],
                VM_ACTION_TIMEOUT)
    return status


@is_action()
def suspendVm(positive, vm, wait=True):
    '''
    Suspend VM.

    Wait for status UP, then the suspend action is performed and then it awaits
    status SUSPENDED, sampling every 10 seconds.

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
    return True


@is_action()
def shutdownVm(positive, vm, async='true'):
    '''
    Description: shutdown vm
    Author: edolinin
    Parameters:
       * vm - name of vm
       * async - if false, wait for VM to shutdown
    Return: status (True if vm was stopped properly, False otherwise)
    '''
    collect_vm_logs(vm)
    return changeVMStatus(positive, vm, 'shutdown', 'down', async=async)


@is_action()
def migrateVm(positive, vm, host=None, wait=True, force=False):
    '''
    Migrate the VM.

    If the host was specified, after the migrate action was performed,
    the method is checking whether the VM status is UP and whether
    the VM runs on required destination host.

    If the host was not specified, after the migrate action was performed, the
    method is checking whether the VM is UP and whether the VM runs
    on host different to the source host.

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
    if not vmObj.get_host():
        logger.error("VM has no attribute 'host': %s" % dir(vmObj))
        return False
    actionParams = {}

    # If the host is not specified, we should let RHEVM to autoselect host.
    if host:
        destHostObj = HOST_API.find(host)
        actionParams['host'] = data_st.Host(id=destHostObj.id)

    if force:
        actionParams['force'] = True

    if not VM_API.syncAction(vmObj, "migrate", positive, **actionParams):
        return False

    # Check the VM only if we do the positive test. We know the action status
    # failed so with fingers crossed we can assume that VM didn't migrate.
    if not wait or not positive:
        logger.warning('Not going to wait till VM migration completes. \
        wait=%s, positive=%s' % (str(wait), positive))
        return True

    # Barak: change status to up from powering up, since all migrations ends in
    # up, but diskless VM skips the powering_up phase
    if not VM_API.waitForElemStatus(vmObj, 'up', 300):
        return False

    # Check whether we tried to migrate vm to different cluster
    # in this case we return False, since this action shouldn't be allowed.
    logger.info('Getting the VM host after VM migrated.')
    realDestHostId = VM_API.find(vm).host.id
    realDestHostObj = HOST_API.find(realDestHostId, 'id')
    if vmObj.cluster.id != realDestHostObj.cluster.id:
        logger.error('VM migrated to a different cluster')
        return False

    # Validating that the vm did migrate to a diffrent host
    if vmObj.host.id == realDestHostId:
        logger.error('VM stayed on the same host')
        return False

    return True


@is_action()
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


@is_action()
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
    vmTags = VM_API.getElemFromLink(vmObj, link_name='tags', attr='tag',
                                    get_href=True)

    tagObj = data_st.Tag()
    tagObj.set_name(tag)

    tagObj, status = TAG_API.create(tagObj, positive, collection=vmTags)
    return status


@is_action()
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


@is_action()
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


@is_action()
def importVm(positive, vm, export_storagedomain, import_storagedomain,
             cluster, name=None, async=False):
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
    expectedName = vmObj.get_name()

    sd = data_st.StorageDomain(name=import_storagedomain)
    cl = data_st.Cluster(name=cluster)

    actionParams = {
        'storage_domain': sd,
        'cluster': cl,
        'async': async
    }

    actionName = 'import'
    if opts['engine'] in ('cli', 'sdk'):
        actionName = 'import_vm'

    if name is not None:
        newVm = data_st.VM()
        newVm.name = name
        newVm.snapshots = data_st.Snapshots()
        newVm.snapshots.collapse_snapshots = True
        actionParams['clone'] = True
        actionParams['vm'] = newVm
        expectedName = name

    status = VM_API.syncAction(vmObj, actionName, positive, **actionParams)

    if async:
        return status

    if status and positive:
        return waitForVMState(expectedName, expectedStatus)
    return status


@is_action()
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
    status = VM_API.syncAction(
        vmObj, "move", positive, storage_domain=sd, async=async)
    if positive and status and wait:
        return VM_API.waitForElemStatus(
            vmObj, expectedStatus, VM_IMAGE_OPT_TIMEOUT)
    return status


@is_action()
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
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.CdRom()
    newCdrom.set_file(data_st.File(id=cdrom_image))

    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, True, current=True)

    return status


def attach_cdrom_vm(positive, vm_name, cdrom_image):
    """
    Attach a cdrom image to a vm
    Author: cmestreg
     * vm_name: name of the vm
     * cdrom_image: name of the image to attach to
    Returns: True in case of success/False otherwise
    """
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.CdRom()
    newCdrom.set_file(data_st.File(id=cdrom_image))

    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, positive)
    return status


def eject_cdrom_vm(vm_name):
    """
    Eject the CD/DVD from the vm

    :param vm_name: name of the vm
    :type vm_name: str
    :return True in case of success/False otherwise
    :rtype bool
    """
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.CdRom()
    # Eject action is done through setting the File property to empty
    newCdrom.set_file(data_st.File())

    # Is important to pass current=True so the action takes place in the
    # current execution
    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, True, current=True)
    return status


def getCdRomsObjList(vm_name, href=False):
    """
    Description: Returns a list of cdrom objects
    Author: cmestreg
    Parameters:
        * vm_name: name of the vm
        * href: boolean, return href link or not
    Returns a list of cdrom object
    """
    vmObj = VM_API.find(vm_name)
    return CDROM_API.getElemFromLink(vmObj, link_name='cdroms',
                                     attr='cdrom', get_href=href)


def remove_cdrom_vm(positive, vm_name):
    """
    Description: Removes the cdrom object from the vm
    Author: cmestreg
    Parameters:
        * vm_name: name of the vm to remove the cdrom from
    Returns: True is action succeeded, False otherwise
    """
    cdroms = getCdRomsObjList(vm_name)
    return CDROM_API.delete(cdroms[0], positive)


def _createVmForClone(
        name, template=None, cluster=None, clone=None, vol_sparse=None,
        vol_format=None, storagedomain=None, snapshot=None, vm_name=None):
    """
    Description: helper function - creates VM objects for VM_API.create call
                 when VM is created from template, sets all required attributes
    Author: kjachim
    Parameters:
       * template - template name
       * name - vm name
       * cluster - cluster name
       * clone - true/false - if true, template disk will be copied
       * vol_sparse - true/false - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
       * storagedomain - storage domain to clone the VM disk
       * snapshot - description of the snapshot to clone
       * vm_name - name of the snapshot's vm
    Returns: VM object
    """
    # TBD: Probaly better split this since the disk parameter is not that
    # similar for template and snapshots
    vm = data_st.VM(name=name)
    if template:
        templObj = TEMPLATE_API.find(template)
        vm.set_template(templObj)
        disks_from = templObj
    elif snapshot and vm_name:
        # better pass both elements and don't search in all vms
        snapshotObj = _getVmSnapshot(vm_name, snapshot)
        snapshots = Snapshots()
        snapshots.add_snapshot(snapshotObj)
        vm.set_snapshots(snapshots)
        disks_from = snapshotObj
    else:
        raise ValueError("Either template or snapshot and vm parameters "
                         "must be set")

    clusterObj = CLUSTER_API.find(cluster)
    vm.set_cluster(clusterObj)
    diskArray = data_st.Disks()
    diskArray.set_clone(clone.lower())

    disks = DISKS_API.getElemFromLink(disks_from, link_name='disks',
                                      attr='disk', get_href=False)
    for dsk in disks:
        if template:
            disk = data_st.Disk(id=dsk.get_id())
        else:
            disk = data_st.Disk()
            disk.set_image_id(dsk.get_id())
        storage_domains = data_st.StorageDomains()
        if vol_sparse is not None:
            disk.set_sparse(vol_sparse)
        if vol_format is not None:
            disk.set_format(vol_format)
        if storagedomain is not None:
            sd = [STORAGE_DOMAIN_API.find(storagedomain)]
        else:
            # StorageDomain property is needed when include any disk
            # on the request
            sd = []
            for elem in dsk.get_storage_domains().get_storage_domain():
                sd.append(
                    STORAGE_DOMAIN_API.find(
                        elem.get_id(), attribute="id")
                )
        for elem in sd:
            storage_domains.add_storage_domain(elem)
        disk.storage_domains = storage_domains
        diskArray.add_disk(disk)
    vm.set_disks(diskArray)
    return vm


@is_action()
def cloneVmFromTemplate(positive, name, template, cluster,
                        timeout=VM_IMAGE_OPT_TIMEOUT, clone=True,
                        vol_sparse=None, vol_format=None, wait=True,
                        storagedomain=None):
    '''
    Description: clone vm from a pre-defined template
    Author: edolinin
    Parameters:
       * name - vm name
       * template - template name
       * cluster - cluster name
       * timeout - action timeout (depends on disk size or system load
       * clone - true/false - if true, template disk will be copied
       * vol_sparse - True/False - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
    Return: status (True if vm was cloned properly, False otherwise)
    '''
    clone = str(clone).lower()
    # don't even try to use deepcopy, it will fail
    expectedVm = _createVmForClone(name, template, cluster, clone, vol_sparse,
                                   vol_format, storagedomain)
    newVm = _createVmForClone(name, template, cluster, clone, vol_sparse,
                              vol_format, storagedomain)

    if clone == 'true':
        expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    vm, status = VM_API.create(newVm, positive, expectedEntity=expectedVm)
    if positive and status and wait:
        return VM_API.waitForElemStatus(vm, "DOWN", timeout)
    return status


@is_action()
def cloneVmFromSnapshot(positive, name, cluster, vm, snapshot,
                        storagedomain=None, wait=True, sparse=True,
                        vol_format=ENUMS['format_cow'],
                        timeout=VM_IMAGE_OPT_TIMEOUT, compare=True):
    '''
    Description: clone vm from a snapshot
    Author: cmestreg
    Parameters:
       * name - vm name
       * cluster - cluster name
       * vm - name of vm where the snapshot was taken
       * snapshot - snapshot to clone from
       * wait
       * timeout - action timeout
       * compare - True if need validator to work
    Return: True if vm was cloned properly, False otherwise
    '''
    # don't even try to use deepcopy, it will fail
    expectedVm = _createVmForClone(
        name, cluster=cluster, clone="true", vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm)
    newVm = _createVmForClone(
        name, cluster=cluster, clone="true", vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm)

    expectedVm.set_snapshots(None)
    expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    vm, status = VM_API.create(newVm, positive, expectedEntity=expectedVm,
                               compare=compare)
    if positive and status and wait:
        return VM_API.waitForElemStatus(vm, "DOWN", timeout)
    return status


@is_action()
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
    statistics = VM_API.getElemFromLink(vmObj, link_name='statistics',
                                        attr='statistic')

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
        logger.error(
            'The following statistics are missing: %s',
            expectedStatistics,
        )
        status = False

    return status


@is_action()
def createVm(positive, vmName, vmDescription, cluster='Default', nic=None,
             nicType=None, mac_address=None, storageDomainName=None, size=None,
             diskType=ENUMS['disk_type_data'], volumeType='true',
             volumeFormat=ENUMS['format_cow'], diskActive=True,
             diskInterface=ENUMS['interface_virtio'], bootable='true',
             wipe_after_delete='false', start='false', template='Blank',
             templateUuid=None, type=None, os_type=None, memory=None,
             cpu_socket=None, cpu_cores=None, cpu_mode=None, display_type=None,
             installation=False, slim=False, user=None, password=None,
             attempt=60, interval=60, cobblerAddress=None, cobblerUser=None,
             cobblerPasswd=None, image=None, async=False, hostname=None,
             network=MGMT_NETWORK, vnic_profile=None, useAgent=False,
             placement_affinity=None, placement_host=None, vcpu_pinning=None,
             highly_available=None, availablity_priority=None, vm_quota=None,
             disk_quota=None, plugged='true', linked='true', protected=None,
             copy_permissions=False, custom_properties=None,
             watchdog_model=None, watchdog_action=None):
    '''
    Description: The function createStartVm adding new vm with nic,disk
                 and started new created vm.
    Parameters:
        vmName = VM name
        vmDescription = Description of VM
        cluster = cluster name
        nic = nic name
        storageDomainName = storage domain name
        size = size of disk (in bytes)
        diskType = disk type (SYSTEM, DATA)
        volumeType = true means sparse (thin provision),
                     false - pre-allocated
        volumeFormat = format type (COW)
        diskInterface = disk interface (VIRTIO or IDE ...)
        bootable = True when disk bootable otherwise False
        wipe_after_delete = Can be true or false
        type - vm type (SERVER or DESKTOP)
        start = in case of true the function start vm
        template = name of already created template or Blank
                   (start from scratch)
        display_type - type of vm display (VNC or SPICE)
        installation - true for install os and check connectivity in the end
        user - user to connect to vm after installation
        password - password to connect to vm after installation
        attempt- attempts to connect after installation
        interval - interval between attempts
        osType - type of OS as it appears in art/conf/elements.conf
        useAgent - Set to 'true', if desired to read the ip from VM
                   (agent exist on VM)
        placement_affinity - vm to host affinity
        placement_host - host that the affinity holds for
        vcpu_pinning - vcpu pinning affinity (dictionary)
        vm_quota - quota for vm
        disk_quota - quota for vm disk
        plugged - shows if specific VNIC is plugged/unplugged
        linked - shows if specific VNIC is linked or not
        protected - true if VM is delete protected
        cpu_mode - cpu mode
        cobbler* - backward compatibility with cobbler provisioning,
                   should be removed
        network - The network that the VM's VNIC will be attached to. (If
                  'vnic_profile' is not specified as well, a profile without
                  port mirroring will be selected for the VNIC arbitrarily
                  from the network's profiles).
        vnic_profile - The VNIC profile to set on the VM's VNIC. (It should be
                       for the network specified above).
        watchdog_model - model of watchdog card
        watchdog_action - action of watchdog card
    return values : Boolean value (True/False )
                    True in case of success otherwise False
    '''
    ip = False
    if not addVm(positive, name=vmName, description=vmDescription,
                 cluster=cluster, template=template, templateUuid=templateUuid,
                 os_type=os_type, type=type, memory=memory,
                 cpu_socket=cpu_socket, cpu_cores=cpu_cores,
                 display_type=display_type, async=async,
                 placement_affinity=placement_affinity,
                 placement_host=placement_host, vcpu_pinning=vcpu_pinning,
                 highly_available=highly_available,
                 availablity_priority=availablity_priority, quota=vm_quota,
                 protected=protected, cpu_mode=cpu_mode,
                 copy_permissions=copy_permissions,
                 custom_properties=custom_properties):
        return False

    if nic:
        profile = vnic_profile if vnic_profile is not None else network
        if not addNic(positive, vm=vmName, name=nic, interface=nicType,
                      mac_address=mac_address,
                      network=network,
                      vnic_profile=profile, plugged=plugged, linked=linked):
                return False

    if template == 'Blank' and storageDomainName and templateUuid is None:
        if not addDisk(positive, vm=vmName, size=size, type=diskType,
                       storagedomain=storageDomainName, sparse=volumeType,
                       interface=diskInterface, format=volumeFormat,
                       bootable=bootable, quota=disk_quota,
                       wipe_after_delete=wipe_after_delete,
                       active=diskActive):
            return False

    if watchdog_action and watchdog_model:
        if not addWatchdog(vmName, watchdog_model, watchdog_action):
            return False

    if installation:
        floppy = None
        if image is None:
            status, res = getImageByOsType(positive, os_type, slim)
            if not status:
                return False
            image = res['osBoot']
            floppy = res['floppy']

        try:
            if not unattendedInstallation(
                positive, vmName, image, nic=nic, floppyImage=floppy,
                hostname=hostname,
            ):
                return False
            if not waitForVMState(vmName):
                return False
            mac = getVmMacAddress(positive, vmName, nic=nic)
            if not mac[0]:
                return False
            mac = mac[1]['macAddress']

            if not waitForSystemIsReady(
                mac,
                interval=interval,
                timeout=VM_INSTALL_TIMEOUT
            ):
                return False

            if useAgent:
                ip = waitForIP(vmName)[1]['ip']

            logger.debug("%s has ip %s", vmName, ip)
            if not checkVMConnectivity(
                positive, vmName, os_type, attempt=attempt, interval=interval,
                nic=nic, user=user, password=password, ip=ip,
            ):
                return False
        finally:
            # FIXME: it doesn't work when it runs in parallel
            ProvisionContext.clear()
        return True
    else:
        if (start.lower() == 'true'):
            if not startVm(positive, vmName):
                return False

        return True


@is_action()
def waitForIP(vm, timeout=1800, sleep=DEF_SLEEP):
    '''
    Description: Waits until agent starts reporting IP address
    Author: jlibosva
    Parameters:
       * vm - name of the virtual machine
       * timeout - how long to wait
       * sleep - polling interval
    Return: Tupple ( True/False whether it obtained the IP,
                     IP if fetched or None)
    '''
    guest_info = None
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(sleep)
        guest_info = VM_API.find(vm).get_guest_info()
        if guest_info is not None:
            ips = guest_info.get_ips()
            if ips is None:
                continue
            ip = ips.get_ip()
            if not ip:
                continue
            ip = ip[0].get_address()
            VM_API.logger.debug("Got IP %s for %s", ip, vm)
            return True, {'ip': ip}

    if guest_info is None:
        logger.error(
            "%s: rhevm-guest-agent wasn't installed or it is stopped", vm
        )
    else:
        logger.error("Guest agent doesn't provide IP for vm %s", vm)

    return False, {'ip': None}


@is_action()
def getVmMacAddress(positive, vm, nic='nic1'):
    '''Function return mac address of vm with specific nic'''
    try:
        nicObj = getVmNic(vm, nic)
    except EntityNotFound:
        VM_API.logger.error("Vm %s doesn't have nic '%s'", vm, nic)
        return False, {'macAddress': None}
    return True, {'macAddress': str(nicObj.mac.address)}


def check_vnic_on_vm_nic(vm, nic='nic1', vnic='rhevm'):
    """
    Check for vnic parameter value if this profile resides on the nic
    parameter
    **Author**: gcheresh

    **Parameters**:
        * *vm* - vm name to check for VNIC profile name on
        * *nic* - NIC on VM to check the VNIC profile on
        * *vnic* - vnic name to check on the NIC of VM
    **Returns**: True if VNIC profile with 'vnic' name is located on the nic
    of the vm
    """
    try:
        nic = getVmNic(vm, nic)
    except EntityNotFound:
        VM_API.logger.error("Vm %s doesn't have nic '%s'", vm, nic)
        return False
    if nic.get_vnic_profile():
        vnic_obj = VNIC_PROFILE_API.find(nic.get_vnic_profile().get_id(),
                                         attribute='id')
        return vnic_obj.get_name() == vnic
    # for NIC that doesn't have VNIC profile on it
    else:
        return vnic is None


@is_action()
def waitForSystemIsReady(mac, interval=60, timeout=VM_INSTALL_TIMEOUT):
    logger.info(
        "Wait until system %s has status != %s, checking every %s",
        mac, ProvisionContext.STATUS_BUILD, interval,
    )
    try:
        for status in TimeoutingSampler(
            timeout, interval, ProvisionContext.get_system_status, mac,
        ):
            logger.info(
                "Status of system %s is %s", mac, status,
            )
            if status == ProvisionContext.STATUS_ERROR:
                logger.error("Status of system is error, aborting ...")
                return False
            elif status != ProvisionContext.STATUS_BUILD:
                # NOTE: It can happen that guest doesn't provide reports,
                # so can not test on STATUS_READY
                break
    except APITimeout:
        logger.error(
            "System %s doesn't have desired status != %s in timeout %s", mac,
            ProvisionContext.STATUS_BUILD, VM_INSTALL_TIMEOUT,
        )
        return False
    return True


@is_action()
def removeSystem(mac, cobblerAddress=None, cobblerUser=None,
                 cobblerPasswd=None):
    '''
    Description: remove system from provisioning provider:
    Author: imeerovi
    Parameters:
       * mac - mac address of system to remove
       * cobbler* - backward compatibility with cobbler provisioning,
                    should be removed
    Return: True if remove succseeded and False otherwise.
    '''
    return ProvisionProvider.remove_system(mac)


@is_action()
def unattendedInstallation(positive, vm, image, nic='nic1', hostname=None,
                           floppyImage=None, cobblerAddress=None,
                           cobblerUser=None, cobblerPasswd=None):
    '''
    Description: install VM with answer file:
    unattended floppy disk for windows.
    via PXE for rhel.
    Author: imeerovi
    Parameters:
       * vm - VM with clean bootable hard disk.
       * nic- nic name to find out mac address- relevant for rhel only.
       * image- cdrom image for windows or profile for rhel.
       * floppyImage- answer file for windows.
       * cobbler* - backward compatibility with cobbler provisioning,
                    should be removed
    Return: status (True if VM started to insall OS, False otherwise).
    '''
    if re.search('rhel', image, re.I):
        status, mac = getVmMacAddress(positive, vm, nic=nic)
        if not status:
            return False
        if not ProvisionContext.add_system(
            mac=mac['macAddress'],
            os_name=image
        ):
            return False
        if hostname:
            if not ProvisionContext.set_host_name(
                name=mac['macAddress'],
                hostname=hostname
            ):
                return False

        boot_dev = 'hd,network'
        return runVmOnce(positive, vm, boot_dev=boot_dev)
    else:
        boot_dev = 'cdrom'
        return runVmOnce(
            positive, vm, cdrom_image=image, floppy_image=floppyImage,
            boot_dev=boot_dev,
        )


@is_action()
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


@is_action()
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

    if diskId is not None:
        disk = _getVmDiskById(vm, diskId)
    else:
        disk = _getVmFirstDiskByName(vm, diskAlias)

    status = DISKS_API.syncAction(disk, action, positive)
    if status and wait:
        if positive:
            # wait until the disk is really (de)activated
            active = True if action == 'activate' else False
            # always use disk.id
            return waitForVmDiskStatus(
                vm, active, diskId=disk.get_id(), timeout=300) == positive
        else:
            # only wait for the disk to be again in 'ok' state
            return DISKS_API.waitForElemStatus(disk, 'ok', 300)
    return status


@is_action()
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


@is_action()
def checkVMConnectivity(
    positive, vm, osType, attempt=1, interval=1, nic='nic1', user=None,
    password=None, ip=False, timeout=1800
):
    """
    Check VM Connectivity
    :param positive: Expected result
    :type positive: bool
    :param vm: vm name
    :type vm: str
    :param osType: os type element rhel/windows.
    :type osType: str
    :param attempt: number of attempts to connect
    :type attempt: int
    :param interval:  interval between attempts
    :type interval: int
    :param nic: NIC to get IP from
    :type nic: str
    :param user: Username
    :type user: str
    :param password: Password for Username
    :type password: str
    :param ip:  if supplied, check VM connectivity by this IP.
    :type ip: str
    :param timeout: timeout to wait for IP
    :type timeout: int
    :return: True if succeed to connect to VM, False otherwise).
    :rtype: bool
    """
    vlan = None
    if re.search('rhel', osType, re.I):
        osType = 'linux'
    elif re.search('win', osType, re.I):
        osType = 'windows'
    else:
        VM_API.logger.error(
            'Wrong value for osType: Should be rhel or windows')
        return False

    if not ip:
        agent_status, ip = waitForIP(vm=vm, timeout=timeout)
        # agent should be installed so convertMacToIpAddress is irrelevant
        if not agent_status:
            status, mac = getVmMacAddress(positive, vm, nic=nic)
            if not status:
                return False
            status, vlan = getVmNicVlanId(vm, nic)
            status, ip = convertMacToIpAddress(
                positive, mac=mac['macAddress'], vlan=vlan['vlan_id']
            )
            if not status:
                return False
        ip = ip['ip']

    status, res = checkHostConnectivity(
        positive, ip,  user=user, password=password, osType=osType,
        attempt=attempt, interval=interval
    )
    VM_API.logger.info(
        "VM: %s TYPE: %s, IP: %s, VLAN: %s, NIC: %s Connectivity Status: %s",
        vm, osType, ip, vlan, nic, status
    )
    return status


@is_action()
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


@is_action()
def getVmNicPortMirroring(positive, vm, nic='nic1'):
    '''
    Get nic port mirror network
    Author: gcheresh
    Parameters:
        * vm - vm name
        * nic - nic name
    Return: True if port_mirroring is enabled on NIC, otherwise False
    '''
    nic_obj = getVmNic(vm, nic)
    return bool(nic_obj.get_port_mirroring()) == positive


@is_action()
def getVmNicPlugged(vm, nic='nic1'):
    '''
    Get nic plugged parameter value of the NIC
    **Author**: gcheresh
    **Parameters**:
        *  *vm* - vm name
        *  *nic* - nic name
    **Returns**: True if NIC is plugged, otherwise False
    '''
    nic_obj = getVmNic(vm, nic)
    return nic_obj.get_plugged()


@is_action()
def getVmNicLinked(vm, nic='nic1'):
    '''
    Get nic linked parameter value of the NIC
    **Author**: gcheresh
    **Parameters**:
        *  *vm* - vm name
        *  *nic* - nic name
    **Returns**: True if NIC is linked, otherwise False
    '''
    nic_obj = getVmNic(vm, nic)
    return nic_obj.get_linked()


def getVmNicNetwork(vm, nic='nic1'):
    '''
    Check if NIC contains network
    **Author**: gcheresh
    **Parameters**:
        *  *vm* - vm name
        *  *nic* - nic name
    **Returns**: True if NIC contains non-empty network object
                or False for Empty network object
    '''
    nic_obj = getVmNic(vm, nic)

    return bool(nic_obj.get_network())


def checkVmNicProfile(vm, vnic_profile_name, nic='nic1'):
    '''
    Check if VNIC profile 'vnic_profile_name' exist on the given VNIC
    **Author**: gcheresh
    **Parameters**:
        *  *vm* - vm name
        *  *vnic_profile_name - name of the vnic_profile to test
        *  *nic* - nic name
    **Returns**: True if vnic_profile_name exists on nic,
                 False otherwise
    '''
    nic_obj = getVmNic(vm, nic)
    if vnic_profile_name is None:
        if nic_obj.get_vnic_profile():
            return False
        return True

    all_profiles = VNIC_PROFILE_API.get(absLink=False)
    for profile in all_profiles:
        if profile.get_name() == vnic_profile_name:
            return profile.get_id() == nic_obj.get_vnic_profile().get_id()


@is_action()
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
        VM_API.logger.warning("%s network doesn't contain vlan id.",
                              net_obj.get_name())
    return False, {'vlan_id': 0}


@is_action()
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
            logger.error(
                "VM disk %s allocation type %s is not as expected: %s",
                disk.id, disk.get_sparse(), sparse)
            return not positive
        if disk.get_format().lower() != format.lower():
            logger.error("VM disk %s format %s is not as expected: %s",
                         disk.id, disk.format, format)
            return not positive
    return positive


@is_action()
def checkVmState(positive, vmName, state, host=None):
    '''
    This method verifies whether vm is in the specified state on the specified
    host
    Parameters:
       * vmName - name of the vm
       * host - name of the host
       * state - expected state
    Return - True if vm is in the specified state on the specified host
             False otherwise
    '''
    vmObj = VM_API.find(vmName)
    general_check = True if vmObj.get_status().get_state() == state else False
    if host:
        hostObj = HOST_API.find(host)
        return positive == (vmObj.host.id == hostObj.id and general_check)
    else:
        return positive == general_check


@is_action()
def removeVmFromExportDomain(positive, vm, datacenter,
                             export_storagedomain):
    '''
    Description: removes a vm, from export domain
    Author: istein
    Parameters:
       * vm - name of vm to remove from export domain
       * datacenter - name of data center
       * export_storagedomain - export domain containing the exported vm
    Return: status (True if vm was removed properly, False otherwise)
    '''

    expStorDomObj = STORAGE_DOMAIN_API.find(export_storagedomain)
    vmObj = VM_API.getElemFromElemColl(expStorDomObj, vm)

    status = VM_API.delete(vmObj, positive)
    # replac sleep with true diagnostic
    time.sleep(30)
    return status


@is_action()
def waitForVmsDisks(vm, disks_status=ENUMS['disk_state_ok'], timeout=600,
                    sleep=10):
    """
    Description: Waits until all vm's disks are in given state
    Author: jlibosva
    Parameters:
        * vm_name - name of VM
        * disks_status - desired state of all disks
    Returns: True on success, False on timeout
    """
    vm = VM_API.find(vm)

    start_time = time.time()
    disks_to_wait = [disk for disk in
                     DISKS_API.getElemFromLink(vm, get_href=False)
                     if disk.get_status() is not None and
                     disk.get_status().get_state() != disks_status]
    while disks_to_wait and time.time() - start_time < timeout:
        time.sleep(sleep)
        disks_to_wait = [disk for disk in
                         DISKS_API.getElemFromLink(vm, get_href=False)
                         if disk.get_status() is not None and
                         disk.get_status().get_state() != disks_status]

    return False if disks_to_wait else True


@is_action()
def getVmPayloads(positive, vm, **kwargs):
    '''
    Description: returns the payloads object from certain vm
    Author: talayan
    Parameters:
    * positive = TRUE/FALSE
    * vm - vm name to retreive payloads property from
    Return: status, element obj or None if not found
    '''
    name_query = "name=%s" % vm
    try:
        vm_obj = VM_API.query(name_query, all_content=True)[0]
    except IndexError:
        logger.error('Entity %s not found!' % vm)
        return False, {'property_obj': None}

    property_object = vm_obj.get_payloads()
    if property_object is None:
        logger.error('Property payloads not found in entity %s!' % vm)
        return False, {'property_object': None}

    return True, {'property_object': property_object}


@is_action('pingVm')
@LookUpVMIpByName('vm_ip', 'name_vm')
def pingVm(vm_ip=None):
    '''
    Ping VM.

    retreives ip for vmName using LookUpVMIpByName and sends
    totally VM_PING_ATTEMPTS_COUNT ICMP Echo requests, expecting at least one
    ICMP Echo reply.

    returns: True iff at least one reply per IP is received,
             False otherwise.
    '''

    ips = [vm_ip]
    return waitUntilPingable(ips)


@is_action()
def migrateVmsSimultaneously(positive, vm_name, range_low, range_high, hosts,
                             useAgent, seed=None):
    '''
    Migrate several VMs between the hosts, taking random one.
    Original Author: jhenner
    Modified Author: bdagan
    Parameters:
       * vms - name of vm
       * hosts    - A comma separated list of hosts hostnames/ip-addreses to
                    migrate vm between.
       * useAgent - Wait for guest_info to appear. Set this to True when
                    you need to ensure an IP address reported by guest agent
                    should be used. Note that after the VM migration, there is
                    some delay until the guest IP reappears.
       * seed     - A seed for pseudo-random generator. If None, the generator
                    will not be seeded, nor the status will be recovered after
                    test finish.
    Return: True if all migrations performed with no error detected.
    '''
    assert positive
    PING_ATTEMPTS = 10

    hostsObjs = [HOST_API.find(host) for host in set(split(hosts))]
    if len(hostsObjs) < 2:
        raise TestCaseError(
            'There is less then 2 hosts. Migrations impossible!')
    all_hosts_ids = set(hostObj.id for hostObj in hostsObjs)

    vmsObjs = [
        VM_API.find(vm) for vm in makeVmList(vm_name, range_low, range_high)]
    if not vmsObjs:
        raise TestCaseError('No vm to migrate on.')

    if useAgent:
        vm_ips = [waitForIP(vmObj.name)[1]['ip'] for vmObj in vmsObjs]
    else:
        vm_ips = [LookUpVMIpByName('ip', 'name').get_ip(vmObj.name)
                  for vmObj in vmsObjs]

    waitUntilPingable(vm_ips)

    # Save the state of the random generator and seed it with the `seed`
    # constant. The state should get recovered before
    # thiLookUpVMIpByName('ip', 'name').get_ip(vmObj.name)s method returns.

    with restoringRandomState(seed):
        for vmObj in vmsObjs:
            # Get the host to migrate the vm on.
            try:
                oldHostId = vmObj.host.id
            except AttributeError as ex:
                MSG = ("The VM {0} is probably not running "
                       "since it has no attribute 'host'. ex: " + str(ex))
                raise TestCaseError(MSG.format(vmObj.name))

            # Pick a new host.
            hostCandidates = all_hosts_ids - set((oldHostId,))
            vmObj.host.id = random.choice(list(hostCandidates))

        # Ping before
        MSG = 'Pinging {0} before the migration.'
        logger.info(MSG.format(sorted(vm_ips)))
        pingResult = pingToVms(vm_ips, PING_ATTEMPTS)
        dead_machines = [ip for ip, alive in pingResult.iteritems()
                         if not alive]
        if dead_machines:
            MSG = "IPs {0} seems to be dead before the migration."
            raise TestCaseError(MSG.format(dead_machines))
            # need to change the error

        # Migrate
        actions_states = [
            VM_API.syncAction(vmObj, "migrate", positive, host=vmObj.host)
            for vmObj in vmsObjs
        ]

        for vm, action_succeed in zip(vmsObjs, actions_states):
            # Check migration and VM status.
            if not action_succeed:
                MSG = 'Failed to migrate VM %s from %s to host %s.'
                raise TestCaseError(MSG % (vm.name, oldHostId, vm.host.id))

        # Wait for all migrated VMs are UP.
        def vmsUp(state):
            StateResults = (
                VM_API.find(vm.name).status.state.lower() == state
                for vm in vmsObjs)
            return reduce(and_, StateResults)

        logger.info('Waiting for all migrated machines UP.')
        for state in ['migrating', 'up']:
            sampler = TimeoutingSampler(VM_ACTION_TIMEOUT, 10, vmsUp, state)
            sampler.timeout_exc_args = (
                'Timeouted when waiting for all VMs UP after the migration.',)
            for statusOk in sampler:
                if statusOk:
                    break

        logger.info('Checking whether VMs really migrated.')
        for vm in vmsObjs:
            if vm.href == VM_API.find(vm.name).host.href:
                # need to check if it works on SDK
                MSG = 'VM is on same host as it was before migrating.'
                raise TestCaseError(MSG)
            logger.info('VM {0} migrated.'.format(vm.name))

        # Ping after.
        MSG = 'Pinging {0} after the migration.'
        logger.info(MSG.format(sorted(vm_ips)))
        pingResult = pingToVms(vm_ips, PING_ATTEMPTS)
        dead_machines = [ip for ip, alive in pingResult.iteritems()
                         if not alive]
        if dead_machines:
            MSG = "IPs {0} seems to be dead after the migration."
            raise TestCaseError(MSG.format(dead_machines))

        logger.info('Succeed to migrate all the VMs.')
        return True


@is_action('moveVmDisk')
def move_vm_disk(vm_name, disk_name, target_sd, wait=True,
                 timeout=VM_IMAGE_OPT_TIMEOUT, sleep=DEF_SLEEP):
    """
    Description: Moves disk of vm to another storage domain
    Parameters:
        * vm_name - Name of the disk's vm
        * disk_name - Name of the disk
        * target_sd - Name of storage domain disk should be moved to
        * wait - whether should wait until disk is ready
        * timeout - timeout for waiting
        * sleep - polling interval while waiting
    Throws: DiskException if syncAction returns False (syncAction should raise
            exception itself instead of returning False)
    """
    logger.info("Moving disk %s of vm %s to storage domain %s", disk_name,
                vm_name, target_sd)
    sd = STORAGE_DOMAIN_API.find(target_sd)
    disk = getVmDisk(vm_name, disk_name)
    if not DISKS_API.syncAction(disk, 'move', storage_domain=sd,
                                positive=True):
        raise exceptions.DiskException(
            "Failed to move disk %s of vm %s to storage domain %s" %
            (disk_name, vm_name, target_sd))
    if wait:
        for disk in TimeoutingSampler(timeout, sleep, getVmDisk, vm_name,
                                      disk_name):
            if disk.status.state == ENUMS['disk_state_ok']:
                return


def wait_for_vm_states(vm_name, states=[ENUMS['vm_state_up']],
                       timeout=VM_WAIT_FOR_IP_TIMEOUT, sleep=DEF_SLEEP):
    """
    Description: Waits by polling API until vm is in desired state
    Parameters:
        * vm_name - name of the vm
        * states - list of desired state
    Throws:
        APITimeout when vm won't reach desired state in time
    """
    sampler = TimeoutingSampler(timeout, sleep, VM_API.find, vm_name)
    for vm in sampler:
        if vm.status.state in states:
            break


def start_vms(vm_list, max_workers=2,
              wait_for_status=ENUMS['vm_state_powering_up'],
              wait_for_ip=True):
    """
    Starts all vms in vm_list. Throws an exception if it fails

    :param vm_list: list of vm names
    :param max_workers: In how many threads should vms start
    :param wait_for_status: from ENUMS, to which state we wait for
    :param wait_for_ip: Boolean, wait to get an ip from the vm
    :raises: VMException
    """
    results = list()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for machine in vm_list:
            vm_obj = VM_API.find(machine)
            if vm_obj.get_status().get_state() == ENUMS['vm_state_down']:
                logger.info("Starting vm %s", machine)
                results.append(executor.submit(startVm, True,
                                               machine, wait_for_status,
                                               wait_for_ip,
                                               ))
    for machine, res in zip(vm_list, results):
        if res.exception():
            logger.error("Got exception while starting vm %s: %s", machine,
                         res.exception())
            raise res.exception()
        if not res.result():
            raise exceptions.VMException("Cannot start vm %s" % machine)


@is_action('waitForVmSnapshots')
def wait_for_vm_snapshots(vm_name, states,
                          timeout=SNAPSHOT_TIMEOUT, sleep=DEF_SLEEP):
    """
    Description: Waits until all vm's snapshots are in one of given states
    Parameters:
        * vm_name - name of the vm
        * states - list of desired snapshots' state
        * timeout - maximum amount of time this operation can take
        * sleep - polling period
    """
    def _get_unsatisfying_snapshots(vm_name, states):
        """
        Returns all snapshots that are not in any of state from states
        """
        snapshots = _getVmSnapshots(vm_name, False)
        return [snapshot for snapshot in snapshots
                if snapshot.snapshot_status not in states]
    logger.info("Waiting untill all snapshots of %s vm are in one of following"
                "states: %s", vm_name, states)
    for not_wanted_snaps in TimeoutingSampler(
            timeout, sleep, _get_unsatisfying_snapshots, vm_name, states):
        if not not_wanted_snaps:
            return


def collect_vm_logs(vm_name, root_passwd='qum5net'):
    """
    Collects /var/log/messages from vm
    and put it in logdir

    Parameters:
        * *vm_name* - name of the vm
        * *root_passwd* - password of root user of the vm

    **Returns**: True/False whether succeed in collecting the logs
    """
    vm = VM_API.find(vm_name)
    os_type = vm.get_os().get_type().lower()
    if not ('linux' in os_type or 'rhel' in os_type):
        # no logs from non-linux machines
        return False

    vm_ip = None

    try:
        vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
        logger.info('Got ip %s', vm_ip)
    except CanNotFindIP:
        logger.warning(
            "failed to get vm logs from vm %s: No IP found", vm_name)
        return False
    except Exception as e:
        logger.error('Could not get vm logs from vm %s - unexpected exception '
                     'encountered: %s', vm_name, e)
        return False

    m = Machine(vm_ip, 'root', root_passwd).util(LINUX)
    log_dest = os.path.join(opts['logdir'], '{0}-messages.log'.format(vm_name))

    # hack, to be fixed when moving to logging.config
    # logging the error in debug instead of error
    class tempfilter(logging.Filter):
        def filter(self, record):
            if record.msg == '%s: failed copy %s from %s, err: %s':
                logger.warning("failed to copy logs from vm logs from vm %s",
                               vm_name)
                logger.debug(record.getMessage())
                return False
            return True

    tmpfilter = tempfilter()
    util_logger = logging.getLogger('util')
    util_logger.addFilter(tmpfilter)

    success = m.copyFrom('/var/log/messages', log_dest)

    util_logger.removeFilter(tmpfilter)
    if not success:
        logger.warning("failed to copy logs from vm logs from vm %s", vm_name)
        return False
    return True


@is_action()
def restoreSnapshot(positive, vm, description, ensure_vm_down=False,
                    restore_memory=False):
    """
    Description: restore vm snapshot
    Author: edolinin
    Parameters:
       * vm - vm where snapshot should be restored
       * description - snapshot name
       * ensure_vm_down - True if vm should enforce to be down before restore
       * restore_memory - True if should restore vm memory
    Return: status (True if snapshot was restored properly, False otherwise)
    """
    return perform_snapshot_action(positive, vm, description, 'restore',
                                   ensure_vm_down,
                                   restore_memory=restore_memory)


def preview_snapshot(positive, vm, description, ensure_vm_down=False,
                     restore_memory=False, disks_lst=None):
    """
    Description: preview vm snapshot
    Author: gickowic
    Parameters:
       * vm - vm where snapshot should be previewed
       * description - snapshot name
       * ensure_vm_down - True if vm should enforce to be down before preview
       * restore_memory - True if should restore vm memory
       * disks_lst - list of disk in case of custom preview
    Return: status (True if snapshot was previewed properly, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
        waitForVMState(vm, state=ENUMS['vm_state_down'])
    return snapshot_action(positive, vm, PREVIEW, description,
                           restore_memory=restore_memory, disks_lst=disks_lst)


def undo_snapshot_preview(positive, vm, ensure_vm_down=False):
    """
    Description: Undo a snapshot preview
    Author: gickowic
    Parameters:
       * vm - vm where snapshot preview should be undone
       * ensure_vm_down - True if vm should enforce to be down before undo
    Return: status (True if snapshot preview was undone, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
        waitForVMState(vm, state=ENUMS['vm_state_down'])
    return snapshot_action(positive, vm, UNDO)


def commit_snapshot(positive, vm, ensure_vm_down=False,
                    restore_memory=False):
    """
    Description: Commit a vm snapshot (must be currently in preview)
    Author: gickowic
    Parameters:
       * vm - vm where snapshot should be commited
       * description - snapshot name that is currently previewed
       * ensure_vm_down - True if vm should enforce to be down before commit
       * restore_memory - True if should restore vm memory
    Return: status (True if snapshot was committed properly, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
        waitForVMState(vm, state=ENUMS['vm_state_down'])
    return snapshot_action(positive, vm, COMMIT,
                           restore_memory=restore_memory)


def perform_snapshot_action(positive, vm, description, action,
                            ensure_vm_down=False, restore_memory=False):
    """
    Description: Perform action on a given snapshot
    Author: gickowic
    Parameters:
       * vm - vm where snapshot should be previewed
       * description - snapshot description
       * action - action to perform, as a string. One of:
         [restore, preview, undo, commit]
    Return: status (True if action was performed successfully, False otherwise)
    """
    vmObj = VM_API.find(vm)
    snapshot = _getVmSnapshot(vm, description)
    if ensure_vm_down:
        if not checkVmState(True, vm, ENUMS['vm_state_down'], host=None):
            if not stopVm(positive, vm, async='true'):
                return False
    status = SNAPSHOT_API.syncAction(snapshot, action, positive,
                                     restore_memory=restore_memory)
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, ENUMS['vm_state_down'],
                                        VM_ACTION_TIMEOUT)

    return status


def snapshot_action(positive, vm, action,
                    description=None, restore_memory='false', disks_lst=None):
    """
    Function that performs snapshot actions
    Author: ratamir
    Parameters:
        * vm - vm name which snapshot belongs to
        * action - snapshot operation to execute (string - 'commit_snapshot',
                   'undo_snapshot', 'undo_snapshot')
        * description - snapshot description (In case of custom preview,
                        this snapshot description is the one the vm
                        configuration is taken from)
        * restore_memory - True if restore memory required
        * disks_lst - in case of custom preview, provide list of
          tuple of desired disks and snapshots
          (i.e. disk_name, snap_description) to be part of the preview
    Return: True if operation succeeded, False otherwise
    """
    vmObj = VM_API.find(vm)
    action_args = {'entity': vmObj,
                   'action': action,
                   'positive': positive}

    if action == PREVIEW:
        snapshot = _getVmSnapshot(vm, description)
        snap = data_st.Snapshot(id=snapshot.get_id())
        action_args['snapshot'] = snap
        action_args['restore_memory'] = restore_memory

        # In case of custom preview
        if disks_lst:
            disks_coll = data_st.Disks()
            for disk, snap_desc in disks_lst:

                new_disk = data_st.Disk()

                if snap_desc == 'Active VM':
                    diskObj = getVmDisk(vm, disk)
                    snap_id = _getVmSnapshot(vm, snap_desc)
                    new_disk.set_snapshot(snap_id)

                else:
                    snap_disks = get_snapshot_disks(vm, snap_desc)
                    diskObj = [d for d in snap_disks if
                               (d.get_alias() == disk)][0]

                    new_disk.set_snapshot(diskObj.get_snapshot())

                new_disk.set_id(diskObj.get_id())
                new_disk.set_image_id(diskObj.get_image_id())

                disks_coll.add_disk(new_disk)

            action_args['disks'] = disks_coll
    status = VM_API.syncAction(**action_args)
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, ENUMS['vm_state_down'],
                                        VM_SNAPSHOT_ACTION)

    return status


def is_snapshot_with_memory_state(vm_name, snapshot):
    """
    Description: Check if snapshot contains memory state (according to the
    snapshot's information)
    Author: gickowic
    Parameters:
        * vm_name - name of the vm
        * snapshot - name of the snapshot to check
    * returns - True iff vm contains the snapshot and it has memory state
    """
    snapshotObj = _getVmSnapshot(vm_name, snapshot)
    return snapshotObj.get_persist_memorystate()


def is_pid_running_on_vm(vm_name, pid, user, password):
    """
    Description: Checks if a process with given pid is running on the vm
    Author: gickowic
    Parameters:
        * vm_name - name of the vm
        * pid - pid of the process to search for
        * user - username used to login to vm
        * password - password for the user
    """
    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
    logger.debug('Got ip %s for vm %s', vm_ip, vm_name)
    vm_machine_object = Machine(vm_ip, user, password).util(LINUX)
    return vm_machine_object.isProcessExists(pid)


def kill_process_by_pid_on_vm(vm_name, pid, user, password):
    """
    Description: Kills a process with given pid if it is running on the vm
    Author: gickowic
    Parameters:
        * vm_name - name of the vm
        * pid - pid of the process to search for
        * user - username used to login to vm
        * password - password for the user
    Return
    """
    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
    vm_machine_object = Machine(vm_ip, user, password).util(LINUX)
    return vm_machine_object.killProcess(pid)


@is_action('runCmdOnVm')
def run_cmd_on_vm(vm_name, cmd, user, password, timeout=15):
    """
    Description: Runs given command on given VM
    Parameters:
        * vm_name - VM name in RHEV-M
        * cmd - command to run - should be a string, not a list of tokens,
                for example 'ps -A', not ['ps', '-A']
        * user - username used to login to vm
        * password - password for the user
    """
    vm_ip = get_vm_ip(vm_name)
    rc, out = runMachineCommand(
        True, ip=vm_ip, user=user, password=password, cmd=cmd, timeout=timeout)
    logger.debug("cmd output: %s, exit code: %s", out, rc)
    return rc, out


@is_action()
def check_VM_disk_state(vm_name, disk_alias):
    """
    Description: Check disk state
    Author: ratamir
    Parameters:
        * vm_name - string containing vm name
        * disk_alias - string containing disk name

    Return: True if the disk is active, False otherwise
    """

    disks = getVmDisks(vm_name)
    disks = [disk for disk in disks if disk.get_alias() == disk_alias]
    if not disks:
        raise DiskNotFound('Disk %s not found in vm %s' %
                           (disk_alias, vm_name))
    disk = disks[0]
    return disk.get_active()


@is_action()
def get_vm_state(vm_name):
    """
    Description: Get vm state
    Author: ratamir
    Parameters:
        * vm_name - string containing vm name

    Return: state of vm
    """
    vm_obj = VM_API.find(vm_name)
    return vm_obj.get_status().get_state()


def wait_for_vm_migrate(vm, host, **kwargs):
    """
    Wait until vm migrate on given host
    **Author**: alukiano

    **Parameters**:
        * *vm* - vm name
        * *host* - host name
    **Returns**: True if event passed, otherwise False
    """
    query = "name={0} and host={1}".format(vm, host.lower().strip())
    return VM_API.waitForQuery(query, **kwargs)


def check_vm_migration(vm, host, time_to_wait):
        """
        Check if vm migrated on given host in defined time
        **Author**: alukiano

        **Parameters**:
            * *vm* - vm for migration name
            * *host* - destination host name
            * *time_to_wait - migration waiting time
        **Returns**: True, migration_duration if event passed,
         otherwise False, migration_duration
        """
        start_time = time.time()
        logger.info("Wait until vm %s will migrate on host %s", vm, host)
        result = wait_for_vm_migrate(vm, host, timeout=time_to_wait)
        migration_duration = time.time() - start_time
        if not result:
            logger.error("Process of migration failed")
            return False, None
        logger.info("Process of migration takes %f seconds",
                    migration_duration)
        return True, migration_duration


def no_vm_migration(vm, host, time_to_wait):
        """
        Check that no migration happened
        **Author**: alukiano

        **Parameters**:
            * *vm* - vm for migration name
            * *host* - source host name
            * *time_to_wait - migration waiting time
        **Returns**: True, host if no migration occurred,
         otherwise False, host
        """
        logger.info("Wait %f seconds", time_to_wait)
        time.sleep(time_to_wait)
        logger.info("Check if vm %s still on old host %s", vm, host)
        result, vm_host = getVmHost(vm)
        if not result:
            logger.error("Failed to get vm %s host", vm)
            return False
        if vm_host.get("vmHoster") != host:
            logger.error("Vm %s migrated on host %s",
                         vm, vm_host.get("vmHoster"))
            return False
        logger.info("After %s seconds, vm %s still on old host %s",
                    time_to_wait, vm, host)
        return True


def maintenance_vm_migration(vm, src_host, dst_host):
        """
        Put source host to maintenance, and check if host migrated to
        destination host
        **Author**: alukiano

        **Parameters**:
            * *vm* - vm for migration name
            * *src_host* - source host name
            * *dst_host - destination host
        **Returns**: True if vm migrated on destination host,
         otherwise False
        """
        import hosts
        logger.info("Put host %s to maintenance mode", src_host)
        if not hosts.deactivateHost(True, src_host):
            logger.error("Deactivation of host %s failed", src_host)
            return False
        logger.info("Check to which host vm %s was migrated", vm)
        result, vm_host = getVmHost(vm)
        if vm_host.get("vmHoster") != dst_host:
            logger.error("Vm %s migrated on host %s and not on host %s",
                         vm, vm_host.get("vmHoster"), dst_host)
            return False
        return True


def get_snapshot_disks(vm, snapshot):
    """
    Description: Return the disks contained in a snapshot
    Author: ratamir
    Parameters:
        * vm - vm name
        * snapshot - snapshot's description

    Return: list of disks, or raise EntityNotFound exception
    """
    snap_obj = _getVmSnapshot(vm, snapshot)
    disks = DISKS_API.getElemFromLink(snap_obj)
    return disks


def get_vm_snapshot_ovf_obj(vm, snapshot):
    """
    Description: Return ovf file of vm
    - The ovf itself is in:
        snaps.get_initialization().get_configuration().get_data()
    Author: ratamir
    Parameters:
        * vm - vm name
        * snapshot - snapshot's description

    Return: ovf configuration object, or raise EntityNotFound exception
    """
    snap_obj = _getVmSnapshot(vm, snapshot, all_content=True)
    return snap_obj.get_initialization()


def get_vm_snapshots(vm):
    """
    Description: Return vm's snapshots
    Author: ratamir
    Parameters:
        * vm - vm name
    Return: list of snapshots, or raise EntityNotFound exception
    """
    snapshots = _getVmSnapshots(vm, get_href=False)
    return snapshots


def create_vm_from_ovf(new_vm_name, cluster_name, ovf, compare=False):
    """
    Description: Creates a vm from ovf configuration file
    * The ovf configuration can be retrieved via 'get_vm_ovf_file' method

    Author: ratamir
    Parameters:
        * new_vm_name - name for the restored vm
        * cluster - name of the cluster that the vm should create in
        * ovf - ovf object. can retrieved from 'get_vm_snapshot_ovf_obj'
        * compare - If True, run compareElements, otherwise not.
    Return: True if operation succeeded, or False otherwise
    """
    restored_vm_obj = _prepareVmObject(name=new_vm_name, cluster=cluster_name,
                                       initialization=ovf)
    _, status = VM_API.create(restored_vm_obj, True, compare=compare)
    return status


def get_vm_ip(vm_name):
    """
    Description: get vm ip by name
    Author: ratamir
    Parameters:
        * vm_name - vm name
    Return: ip address of a vm, or raise EntityNotFound exception
    """
    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
    return vm_ip


def stop_vms_safely(vms_list, async=False, max_workers=2):
    """
    Description: Stops vm after checking that it is not already in down
    state
    Author: ratamir
    Parameters:
        * vms_list - list of vm names
        * async - True if operation should be async or False otherwise
        * max_workers - The maximum number of threads that can be used
    """
    results = list()
    async = str(async).lower()
    logger.info("Stops vms: %s", vms_list)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for vm in vms_list:
            if not get_vm_state(vm) == ENUMS['vm_state_down']:
                results.append(executor.submit(stopVm(True, vm, async=async)))

    for vm, res in zip(vms_list, results):
        if not res:
            raise exceptions.VMException("Failed to stop vm %s" % vm)


def attach_snapshot_disk_to_vm(disk_obj, vm_name, async=False, activate=True):
    """
    Attaching a snapshot disk to a vm
    Author: ratamir
    Parameters:
        * disk_obj - disk object to attach
        * vm_name - name of the vm that the disk should be attached to
        * async - True if operation should be async
        * activate - True if the disk should be activated after attachment

    Return:
        True if operation succeeded, False otherwise
    """

    new_disk_obj = _prepareDiskObject(id=disk_obj.get_id(),
                                      active=activate,
                                      snapshot=disk_obj.get_snapshot())
    vmDisks = getObjDisks(vm_name)
    diskObj, status = DISKS_API.create(new_disk_obj, True,
                                       collection=vmDisks, async=async)
    return status


def attach_backup_disk_to_vm(src_vm, backup_vm, snapshot_description,
                             async=True, activate=True):
    """
    Attaching a backup disk to a vm
    Author: ratamir
    Parameters:
        * src_vm - name of vm with the disk that should be attached
        * backup_vm - name of the vm that the disk should attach to
        * snapshot_description - snapshot description where the disk
          is located in
        * async - True if operation should be async
    Return:
        True if operation succeeded, False otherwise
    """
    status = True
    disks_objs = get_snapshot_disks(src_vm, snapshot_description)
    for disk_obj in disks_objs:
        logger.info("Attach disk %s of vm %s to vm %s",
                    disk_obj.get_alias(), src_vm, backup_vm)
        status = attach_snapshot_disk_to_vm(disk_obj, backup_vm, async=async,
                                            activate=activate)

        if not status:
            logger.info("Failed to attach disk %s of vm %s to vm %s",
                        disk_obj.get_alias(), src_vm, backup_vm)
            return status
        logger.info("Succeeded to attach disk %s of vm %s to vm %s",
                    disk_obj.get_alias(), src_vm, backup_vm)

    return status


def getVmTemplateId(vm):
    """
    Returns vm's template id
    **Author**: cmestreg

    **Parameters**:
        * *vm* - vm's name
    **Returns**: id of the template, or raise VMException if entity not found
    """
    try:
        vmObj = VM_API.find(vm)
    except EntityNotFound:
        raise exceptions.VMException("Cannot find vm with name %s" % vm)
    return vmObj.get_template().id


def get_vm_boot_sequence(vm_name):
    """
    Get vm boot sequence
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: list of vm boot devices
    """
    vm_obj = get_vm_obj(vm_name)
    boots = vm_obj.get_os().get_boot()
    return [boot.get_dev() for boot in boots]


def remove_all_vms_from_cluster(cluster_name, skip=None):
    """
    Stop if need and remove all exists vms from specific cluster

    :param cluster_name: cluster name
    :param skip: list of names of vms which should be left
    :return: True, if all vms removed from cluster, False otherwise
    :rtype: bool
    """
    if skip is None:
        skip = []
    vms_in_cluster = []
    cluster_name_query = "name=%s" % cluster_name
    cluster_obj = CLUSTER_API.query(cluster_name_query)[0]
    all_vms_obj = VM_API.get(absLink=False)
    for vm_obj in all_vms_obj:
        if vm_obj.get_cluster().get_id() == cluster_obj.get_id():
            if vm_obj.get_name() not in skip:
                vms_in_cluster.append(vm_obj.get_name())
    stop_vms_safely(vms_in_cluster)
    if not removeVms(True, vms_in_cluster):
        return False
    return True


def get_vm_display_port(vm_name):
    """
    Get vm display port
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm display port or None
    """
    vm_obj = get_vm_obj(vm_name)
    return vm_obj.get_display().get_port()


def get_vm_display_address(vm_name):
    """
    Get vm display address
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm display address or None
    """
    vm_obj = get_vm_obj(vm_name)
    return vm_obj.get_display().get_address()


def get_vm_obj(vm_name):
    """
    Get vm object by name
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm object
    """
    vm_name_query = "name=%s" % vm_name
    return VM_API.query(vm_name_query)[0]


# Create this function as duplicate for function removeDisk
# with additional functionality to remove all disks from vm
def remove_vm_disks(vm_name, disk_name=None):
    """
    Remove all disks from given vm, if disk name not specified,
    else remove only given disk from vm
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
        * *disk_name - disk name to remove,
                       if specified method will remove just this disk
    **Returns**: True, if removed all disks successfully, otherwise False
    """
    vm_disks = [disk.get_name() for disk in getVmDisks(vm_name)]
    if disk_name:
        vm_disks = [disk for disk in vm_disks if disk == disk_name]
    return delete_disks(vm_disks)


def _prepareWatchdogObj(watchdog_model, watchdog_action):

    watchdogObj = data_st.WatchDog()

    watchdogObj.set_action(watchdog_action)
    watchdogObj.set_model(watchdog_model)

    return watchdogObj


@is_action()
def getWatchdogModels(name, vm_flag):
    '''
    Description: get all available watchdog models
    Author: lsvaty
    Parameters:
      * name -  name of vm or template
      * vm_flag - True  if first parameter contains the name of vm
                  False if first parameter contains the name of template
    Return: List of available  models in current version of cluster
    '''
    models = list()
    obj = None
    if vm_flag:
        obj = VM_API.find(name)
    else:
        obj = TEMPLATE_API.find(name)

    clust_version = obj.get_cluster().get_version()
    cap = CAP_API.get(absLink=False)

    # default for 3.3DC (first watchdog)
    mn, mj = 3, 3

    if clust_version:
        mn = clust_version.get_minor()
        mj = clust_version.get_version().get_major()

    versions = [v for v in cap if v.get_major() == mj and v.get_minor() == mn]
    for watchdog_model in versions[0].get_watchdog_models().get_model():
        models.append(watchdog_model)
    if models:
        return True, {'watchdog_models': models}
    else:
        return False, {'watchdog_models': None}


@is_action()
def addWatchdog(vm, watchdog_model, watchdog_action):
    """
    Description: Add watchdog card to VM
    Parameters:
        * vm_name - Name of the watchdog's vm
        * watchdog_model - model of watchdog card
        * watchdog_action - action of watchdog card
    Return: status (True if watchdog card added successfully. False otherwise)
    """
    vmObj = VM_API.find(vm)
    status = False

    if watchdog_action and watchdog_model:
        vmWatchdog = VM_API.getElemFromLink(vmObj, link_name='watchdogs',
                                            get_href=True)

        watchdogObj = _prepareWatchdogObj(watchdog_model, watchdog_action)
        watchdogObj, status = WATCHDOG_API.create(watchdogObj, True,
                                                  collection=vmWatchdog)

    return status


@is_action()
def updateWatchdog(vm, watchdog_model, watchdog_action):
    """
    Description: Add watchdog card to VM
    Parameters:
        * vm_name - Name of the watchdog's vm
        * watchdog_model - model of watchdog card
        * watchdog_action - action of watchdog card
    Return: status (True if watchdog card added successfully. False otherwise)
    """
    vmObj = VM_API.find(vm)
    vmWatchdog = VM_API.getElemFromLink(vmObj, link_name='watchdogs',
                                        attr='watchdog', get_href=False)

    status, models = getWatchdogModels(vm, True)
    if not status:
        return False

    if watchdog_model in models['watchdog_models']:
        if not vmWatchdog:
            return addWatchdog(vm, watchdog_model, watchdog_action)
        else:
            watchdogObj = _prepareWatchdogObj(watchdog_model,
                                              watchdog_action)
            return WATCHDOG_API.update(vmWatchdog[0],
                                       watchdogObj,
                                       True)[1]
    if vmWatchdog:
        return VM_API.delete(vmWatchdog[0], True)
    return True


def get_vm_machine(vm_name, user, password):
    '''
    Obtain VM machine from vm name for LINUX machine
    Author: lsvaty
    Parameters:
        * vm - vm name
        * user - user of vm
        * password - password for user
    Return value: vm machine
    '''
    status, got_ip = waitForIP(vm_name, timeout=600, sleep=10)
    if not status:
        status, mac = getVmMacAddress(True, vm_name,
                                      nic='nic1')
        if not status:
            return False
        status, vlan = getVmNicVlanId(vm_name, 'nic1')
        status, got_ip = convertMacToIpAddress(True, mac=mac['macAddress'],
                                               vlan=vlan['vlan_id'])
        if not status:
            return False
    return Machine(got_ip['ip'], user, password).util(LINUX)


def reboot_vms(vms):
    """
    Atomic Reboot vms (stop && start)

    :param vms: list of vms
    :return: False if vms failed to start
    :rtype: bool
    """
    stop_vms_safely(vms)
    return startVms(vms)


@is_action()
def extend_vm_disk_size(positive, vm, disk, **kwargs):
    """
    Description: extend already existing vm disk
    Parameters:
      * vm - vm where disk should be updated
      * disk - disk name that should be updated
      * provisioned_size - new disk size in bytes
    Author: ratamir
    Return: Status of the operation's result dependent on positive value
    """
    disk_obj = _getVmFirstDiskByName(vm, disk)
    new_disk = _prepareDiskObject(**kwargs)
    if positive:
        # Expecting to succeed: in this case the validator will verify that
        # the returned object is like the expected one. update() operation is
        # async so the returned object is not the updated one. The returned
        # object in this case is a locked disk with the original size (i.e
        # before the resize).
        # To bypass the object comparison, use compare=False
        disk, status = DISKS_API.update(disk_obj, new_disk, True,
                                        compare=False)
    else:
        # Expecting to fail: in this case the validator is disabled so no
        # further manipulation is needed
        disk, status = DISKS_API.update(disk_obj, new_disk, False)
    return status


@is_action('liveMigrateVmDisk')
def live_migrate_vm_disk(vm_name, disk_name, target_sd,
                         timeout=VM_IMAGE_OPT_TIMEOUT*2,
                         sleep=SNAPSHOT_SAMPLING_PERIOD, wait=True):
    """
    Description: Moves vm's disk. Starts disk movement then waits until new
    snapshot appears. Then waits for disk is locked, which means
    migration started. Waits until migration is finished, which is
    when disk is moved to up.
    Author: ratamir
    Parameters:
        * vm_name - Name of the disk's vm
        * disk_name - Name of the disk
        * target_sd - Name of storage domain disk should be moved to
        * timeout - timeout for waiting
        * sleep - polling interval while waiting
        * wait - if should wait for operation to finish
    Throws:
        * DiskException if something went wrong
        * APITimeout if waiting for snapshot was longer than 20 seconds
    """
    def _wait_for_new_storage_domain(vm_name, disk_name, new_sd):
        """
        Waits until disk disk_name isn't placed on new_sd
        """
        migrated_disk = getVmDisk(vm_name, disk_name)
        target_domain = STORAGE_DOMAIN_API.find(
            migrated_disk.storage_domains.storage_domain[0].get_id(), 'id')
        return target_domain.name == new_sd
    logger.info("Migrating disk %s of vm %s to domain %s", disk_name, vm_name,
                target_sd)
    move_vm_disk(vm_name, disk_name, target_sd, timeout=timeout, wait=wait)
    if wait:
        sampler = TimeoutingSampler(timeout, sleep,
                                    _wait_for_new_storage_domain,
                                    vm_name, disk_name, target_sd)
        for sample in sampler:
            if sample:
                break
        waitForDisksState([disk_name], timeout=timeout)
        wait_for_jobs()


@is_action('liveMigrateVm')
def live_migrate_vm(vm_name, timeout=VM_IMAGE_OPT_TIMEOUT*2, wait=True,
                    ensure_on=True):
    """
    Description: Live migrate all vm's disks
    Author: ratamir
    Parameters:
        * vm_name - name of the vm
        * timeout - after how many seconds should be raised exception
        * wait - if should wait until done
        * ensure_on - if vm is not up will start before lsm
    Throws:
        * DiskException if something went wrong
        * VMException if vm is not up and ensure_on=False
        * APITimeout if waiting for snapshot was longer than 20 seconds
    """
    logger.info("Start Live Migrating vm %s disks", vm_name)
    vm_obj = VM_API.find(vm_name)
    if vm_obj.get_status().get_state() == ENUMS['vm_state_down']:
        logger.warning("Storage live migrating vm %s is not in up status",
                       vm_name)
        if ensure_on:
            start_vms([vm_name], 1, wait_for_ip=False)
            waitForVMState(vm_name)
        else:
            raise exceptions.VMException("VM must be up to perform live "
                                         "storage migration")
    vm_disks = [disk.get_name() for disk in getObjDisks(vm_name,
                                                        get_href=False)]
    logger.info("Live Storage Migrating vm %s, will migrate following "
                "disks: %s", vm_name, vm_disks)
    for disk in vm_disks:
        target_sd = get_other_storage_domain(disk, vm_name)
        live_migrate_vm_disk(vm_name, disk, target_sd, timeout=timeout,
                             wait=wait)
    if wait:
        wait_for_jobs()
        waitForVMState(vm_name, timeout=timeout, sleep=5)


@is_action('removeAllVmLmSnapshots')
def remove_all_vm_lsm_snapshots(vm_name):
    """
    Description: Removes all snapshots of given VM which were created during
    live storage migration (according to snapshot description)
    Author: ratamir
    Parameters:
        * vm_name - name of the vm that should be cleaned out of snapshots
    created during live migration
    Raise: AssertionError if something went wrong
    """
    logger.info("Removing all '%s'", LIVE_SNAPSHOT_DESCRIPTION)
    stop_vms_safely([vm_name])
    snapshots = _getVmSnapshots(vm_name, False)
    results = [removeSnapshot(True, vm_name, LIVE_SNAPSHOT_DESCRIPTION,
                              SNAPSHOT_TIMEOUT)
               for snapshot in snapshots
               if snapshot.description == LIVE_SNAPSHOT_DESCRIPTION]
    assert False not in results
    wait_for_jobs()


# TODO: use 3.5 feature - ability to get device name for vm plugged devices
@is_action('getVmStorageDevices')
def get_vm_storage_devices(vm_name, username, password,
                           filter_device=FILTER_DEVICE, ensure_vm_on=False):
    """
    Function that returns vm storage devices
    Author: ratamir
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * username - username for vm
        * password - password for vm
        * filter - filter regex for device (e.g. 'vd*')
        * ensure_on - True if wish to make sure that vm is up
    Return: list of devices (e.g [vdb,vdc,...]) and boot device,
    or raise EntityNotFound if error occurs
    """
    if ensure_vm_on:
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(host=vm_ip, user=username,
                         password=password).util(LINUX)
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'
    vm_devices = vm_machine.get_storage_devices(filter=filter_device)
    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")
    vm_devices = [device for device in vm_devices if device != boot_disk]
    return vm_devices, boot_disk


@is_action('getVmStorageDevices')
def verify_vm_disk_moved(vm_name, disk_name, source_sd,
                         target_sd=None):
    """
    Function that checks if disk movement was actually succeeded
    Author: ratamir
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * disk_name - the name of the disk that moved
        * source_sd - original storage domain
        * target_sd - destination storage domain
    Return: True in case source and target sds are different or actual target
            is equal to target_sd, False otherwise
    """
    actual_sd = get_disk_storage_domain_name(disk_name, vm_name)
    if target_sd is not None:
        if source_sd != target_sd:
            if actual_sd == target_sd:
                return True
    elif source_sd != actual_sd:
        return True
    return False


def get_vm_bootable_disk(vm):
    """
    Description: get bootable disk
    Author: ratamir
    Parameters:
      * vm - vm name
    Author: ratamir
    Return: name of the bootable disk or None if no boot disk exist
    """
    vm_disks = getVmDisks(vm)
    boot_disk = [d for d in vm_disks if d.get_bootable()][0].get_alias()
    return boot_disk


def verify_write_operation_to_disk(vm_name, user_name, password,
                                   disk_number=0):
    """
    Function that perform dd command to disk
    Author: ratamir
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * user_name - user name
        * password - password
        * disk_number - disk number from devices list
    Return: ecode and output, or raise EntityNotFound if error occurs
    """
    vm_devices, boot_disk = get_vm_storage_devices(vm_name, user_name,
                                                   password,
                                                   ensure_vm_on=True)

    command = DD_COMMAND % (boot_disk, vm_devices[disk_number])

    ecode, out = run_cmd_on_vm(
        vm_name, shlex.split(command), user_name, password, DD_TIMEOUT)

    return ecode, out


def get_volume_size(hostname, user, password, disk_object, dc_obj):
    """
    Get volume size in GB
    Author: ratamir
    Parameters:
        * hostname - name of host
        * user - user name for host
        * password - password for host
        * disk_object - disk object that need checksum
        * dc_obj - data center that the disk belongs to
    Return:
        Volume size (integer), or raise exception otherwise
    """
    host_machine = Machine(host=hostname, user=user,
                           password=password).util(LINUX)

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sp_id = dc_obj.get_id()

    lv_size = host_machine.get_volume_size(sd_id, sp_id, image_id, vol_id)
    logger.info("Volume size of disk %s is %s GB",
                disk_object.get_alias(), lv_size)

    return lv_size


def get_vm_device_size(vm_name, user, password, device_name):
    """
    Get vm device size in GB
    Author: ratamir
    Parameters:
        * vm_name - name of vm
        * user - user name
        * password - password
        * device_name - name of device

    Return:
        VM device size (integer) output, or raise exception otherwise
    """
    vm_machine = get_vm_machine(vm_name, user, password)

    device_size = vm_machine.get_storage_device_size(device_name)
    logger.info("Device %s size: %s GB", device_name, device_size)

    return device_size


def get_vms_from_cluster(cluster):
    """
    Description: Gets all VM added to the given cluster

    Parameters:
        * cluster - cluster name
    """
    logging.info("Getting all vms in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    all_vms = VM_API.get(absLink=False)
    vms_in_cluster = [
        x.get_name() for x in all_vms
        if x.get_cluster().get_id() == cluster_id]
    logging.info("Vms in cluster: %s", vms_in_cluster)
    return vms_in_cluster


def does_vm_exist(vm_name):
    """
    Description: Checks if vm exists
    Parameters:
        * vm_name: name of the vm
    Retrun:
        True in case vm exists, False otherwise
    """
    try:
        VM_API.find(vm_name)
    except EntityNotFound:
        return False
    return True


def get_vms_disks_storage_domain_name(vm_name, disk_alias=None):
    """
    Desription: get the vm's disks storage domain name. if no disk alias is
                specified take the first one
    Parameters:
        * vm_name: name of the vm
        * disk_alias: alias of specific disk if needed
    Return:
        Storage Domains' name where the disk is located
    """
    disks = getVmDisks(vm_name)
    diskObj = None
    if disk_alias:
        for disk in disks:
            if disk_alias == disk.get_alias():
                diskObj = disk
                break
        if not diskObj:
            raise EntityNotFound("Disk with alias %s is not attached to vm %s"
                                 % (disk_alias, vm_name))
    else:
        diskObj = disks[0]

    sd_id = diskObj.get_storage_domains().get_storage_domain()[0].get_id()
    return STORAGE_DOMAIN_API.find(sd_id, attribute='id').get_name()


def get_vm(vm):
    """
    Description: Get vm object
    Author: ratamir
    Parameters:
        * vm: name of the vm
    Returns vm object, EntityNotFound if a vm doesn't exist
    """
    return VM_API.find(vm)


def get_vm_nics_obj(vm_name):
    """
    Description: get vm's nics objects
    Author: ratamir
    Parameters:
        * vm_name: name of the vm
    Returns: list of nics objects, or raise EntityNotFound
    """
    vm_obj = VM_API.find(vm_name)
    return VM_API.getElemFromLink(vm_obj,
                                  link_name='nics',
                                  attr='nic',
                                  get_href=False)


def get_vm_host(vm_name):
    """
    Return name of host, where vm run

    :param vm_name: name of vm.
    :type vm_name: str.
    :returns: None if function fail, otherwise name of host.
    """
    try:
        vm_obj = VM_API.find(vm_name)
        host_obj = HOST_API.find(vm_obj.host.id, 'id')
    except EntityNotFound:
        return None
    return host_obj.get_name()


def safely_remove_vms(vms):
    """
    Description: Make sure that all vms passed are removed
    Parameters:
        * vms: list of vms
    Returns: False if there's an error removing a vm or no vm were removed
    """
    logger.info("Removing vms %s", vms)
    vms_exists = filter(does_vm_exist, vms)
    if vms_exists:
        stop_vms_safely(vms_exists)
        return removeVms(True, vms_exists)
    logger.info("No vms to remove")
    return True


def get_vm_disk_logical_name(vm_name, disk_alias):
    """
    Retrieves the logical name of a disk that is attached to a VM
    **** Important note: Guest Agent must be installed in the OS for this
    function to work ****

    __author__ = "glazarov"
    :param vm_name - name of the vm which which contains the disk
    :type: str
    :param disk_alias: The alias of the disk for which the logical volume
    name should be retrieved
    :type disk_alias: str
    :returns: Disk logical name
    :rtype: str
    """
    disk_object = getVmDisk(vm_name, disk_alias)
    return disk_object.get_logical_name()
