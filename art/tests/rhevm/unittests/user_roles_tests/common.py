#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Red Hat, Inc.
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

""" Common functions and wrappers used in all other tests. """

__test__ = False

import config
import states

from time import sleep
import logging
import ovirtsdk.api
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors
from ovirtsdk.infrastructure.context import context
from ovirtsdk.infrastructure import contextmanager
from functools import wraps

MB = 1024*1024
GB = 1024*MB

logging.basicConfig(filename='messages.log',level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)
_major = int(config.OVIRT_VERSION[0])
_minor = int(config.OVIRT_VERSION[2:])
VERSION = params.Version(major=_major, minor=_minor)

users = {}
def _getApi():
    """ Return ovirtsdk api.

    Will not create another API instance when reloading this module in
    ipython (when common.API is already defined).
    Works around problem when reloading, which would
    otherwise cause the error `ImmutableError: [ERROR]::'proxy' is immutable.`.
    """
    global users
    try:
        return API
    except NameError:
        users[config.OVIRT_USERNAME] = ovirtsdk.api.API(
                    url=config.OVIRT_URL, insecure=True,
                    username=config.OVIRT_USERNAME+'@'+config.OVIRT_DOMAIN,
                    password=config.OVIRT_PASSWORD)
        return users[config.OVIRT_USERNAME]

API = _getApi()

def waitForState(obj, desiredStates, failStates=None, timeout=config.TIMEOUT,
                    sampling=1, restoreState=None):
    """ Waits for oVirt object to change state using :py:func:`time.sleep`.

    :param obj:             the oVirt object (host, VM, ...) for which to wait
    :param desiredStates:   the desired oVirt object states, accepts both a
                            list of states or a single state
    :param failStates:      fail if the object reaches one of these states
    :param timeout:         (int) time in seconds to wait for desired state
    :param sampling:        (int) how often to check state, in seconds
    :param restoreState     state, tryies to maintentce->up host, when it is non_operational

    :raises AssertionError: when timeout is exceeded and the object still isn't
        in the desired state or if failState was reached

    .. seealso:: :mod:`tests.states`
    """
    # 120 seconds is not enougn to wait for start
    if type(obj).__name__ == 'VM' and desiredStates == states.vm.up:
        timeout = 240

    global res

    if obj is None:
        return
    if type(desiredStates) is not list:
        desiredStates = [desiredStates]
    if type(failStates) is not list and failStates is not None:
        failStates = [failStates]
    elif failStates is None:
        failStates = []

    assert type(obj) is not str, "Bad use of 'waitForState()'"
    t = 0
    state = newState(obj)
    while state not in desiredStates and t <= timeout:
        sleep(sampling)
        t += sampling
        state = newState(obj)
        assert state not in failStates, \
        "Failed to get %s into state '%s' because it reached the fail \
        state '%s'" % (objectDescr(obj), desiredStates, state)

    if t > timeout:
        LOGGER.error("%s didn't reach one of states %s in timout \
                    of %i sec, current state is '%s'"
                    % (objectDescr(obj), str(desiredStates), timeout, state))
    assert state in desiredStates, \
        "Failed to get %s into desired state" % objectDescr(obj)

    if type(obj).__name__ == 'VM':
        disks = obj.get_disks().list()
        if disks is not None:
            for disk in disks:
                waitForState(disk, states.disk.ok)


def updateObject(obj):
    """ Return oVirt object with updated data.

    .. warning::
        Storage domains have unexpected behaviour (by-design in oVirt). When
        you use a SD that is unattached (by using `api.storagedomains`) and
        then attach it, it will have no status when you look at it from this
        angle (and `updateObject` will return None).  The state can be then
        found in `api.datacenters.get('dc').storagedomains`.

    :param obj:         oVirt object (host, VM, storage, ...)
    :return:            The object with updated data, for example status. None
                        if object was deleted in the meantime (or
                        attached/detached in case of storage domains).
    """

    assert type(obj) is not str, "Bad use of 'updateObject()'"
    parent = None
    t = type(obj).__name__

    # FIXME there HAS to be a nicer way to implement this
    if 'Host' == t:
        parent = API.hosts
    elif 'VM' == t:
        return getObjectByName(API.vms, obj.name)
    elif 'Disk' == t:
        return API.disks.get(id=obj.get_id())
    elif 'VMSnapshot' == t:
        vmId = obj.get_vm().get_id()
        vm = API.vms.get(id=vmId)
        return vm.snapshots.get(id=obj.get_id())
    elif 'VMDisk' == t:
        vmId = obj.get_vm().get_id()
        vm = API.vms.get(id=vmId)
        parent = vm.disks
    elif 'Template' == t:
        return getObjectByName(API.templates, obj.name)
    elif 'DataCenter' == t:
        parent = API.datacenters
    elif 'Cluster' == t:
        parent = API.clusters
    elif 'StorageDomain' == t:
        parent = API.storagedomains
    elif 'VmPool' == t:
        parent = API.vmpools
    elif 'DataCenterStorageDomain' == t:
        dcname = obj.parentclass.name
        dc = API.datacenters.get(dcname)
        parent = dc.storagedomains
    elif 'StorageDomainVM' == t:
        sdName = obj.parentclass.name
        sd = API.storagedomains.get(sdName)
        parent = sd.vms
    elif 'StorageDomainTemplate' == t:
        sdName = obj.parentclass.name
        sd = API.storagedomains.get(sdName)
        parent = sd.templates
    elif 'TemplateDisk' == t:
        tmpId = obj.get_template().get_id()
        tmp = API.templates.get(id=tmpId)
        parent = tmp.disks
    elif 'ClusterNetwork' == t:
        clId = obj.get_cluster().get_id()
        cl = API.clusters.get(id=clId)
        parent = cl.permissions
    elif 'Network' == t:
        parent = API.networks
    else:
        raise Exception("Unknown object %s, cannot update it's state"
                        % (objectDescr(obj)))

    return parent.get(id=obj.get_id())


def newState(obj):
    """ Obtain new state of an oVirt object.

    :param obj:         oVirt object (host, VM, storage, ...)
    :return:            (string) the new state of the object

    .. seealso:: :func:`updateObject`, :mod:`tests.states`
    """
    assert type(obj) is not str, "Bad use of 'newState()'"
    updatedObject = updateObject(obj)
    if updatedObject is None:
        LOGGER.warning("Object %s has no status" % (objectDescr(obj)))
        return None

    if type(updatedObject).__name__ == 'VMSnapshot':
        return updatedObject.snapshot_status

    status = updatedObject.status
    if status is None:
        LOGGER.warning("Object %s has no status" % (objectDescr(obj)))
        return None
    return status.state


def objectDescr(obj):
    """ Return oVirt object description.

    :param obj:         oVirt object (host, VM, storage, ...)
    :return:            (string) `"ObjectType 'object name'"`
    """

    typeName = type(obj).__name__
    if 'StorageDomain' in typeName:
        typeName = 'Storage Domain'

    return "%s '%s'" % (typeName, obj.name)

def createDataCenter(name, storageType=config.MAIN_STORAGE_TYPE,
                        version=VERSION):
    LOGGER.info("Creating data center '%s'" % name)
    API.datacenters.add(params.DataCenter(
                name=name,
                storage_type=storageType,
                version=version))
    dc = getObjectByName(API.datacenters, name)
    assert dc is not None

def addNetworkToDC(name, dcName):
    """ Add new network to DC 'dcName' with name 'name'. """
    dc = getObjectByName(API.datacenters, dcName)
    API.networks.add(params.Network(data_center=dc, name=name))
    LOGGER.info("Network '%s' was added to DC '%s'." % (name, dcName))

    net = getObjectByName(API.networks, name)
    assert net is not None, "Network couldn't be created."

def _getNetwork(networkName, dcName):
    """ Search network networkName by name in dc dcName """
    for network in API.networks.list():
        if dcName == API.datacenters.get(id=network.get_data_center().get_id()).get_name() and \
                network.get_name() == networkName:
                    return network

def deleteNetwork(name, dcName):
    ''' Delete network '''
    network = _getNetwork(name, dcName)
    LOGGER.info("Removing network '%s' name from dc '%s'" % (name, dcName))
    if network:
        network.delete()
        waitForRemove(network)

def removeDataCenter(name, force=False):
    """ Removes datacenter """
    dc = getObjectByName(API.datacenters, name)
    if dc is not None:
        LOGGER.info("Removing datacenter '%s'" % name)
        dc.delete(params.Action(force=force))
        assert updateObject(dc) is None, "Can't remove datacenter"

def createCluster(name, datacenterName,
                    cpu_type=config.HOST_CPU_TYPE, version=VERSION):
    """ Creates cluster """
    LOGGER.info("create_cluster")
    dc = getObjectByName(API.datacenters, datacenterName)
    API.clusters.add(params.Cluster(
                name=name,
                cpu=params.CPU(id=cpu_type),
                data_center=dc,
                version=VERSION))
    cluster = getObjectByName(API.clusters, name)
    LOGGER.info("Creating cluster '%s'" % name)
    assert cluster is not None

def removeCluster(name):
    """ Removes cluster """
    cluster = getObjectByName(API.clusters, name)
    if cluster is not None:
        cluster.delete()
        LOGGER.info("Removing cluster '%s'" % name)
        assert updateObject(cluster) is None, "Can't remove cluster"

############################# Roles/perms ##################################
def getRoles():
    """ Return list of all roles """
    return [role.get_name() for role in API.roles.list()]

def getRolePermissions(roleName):
    """ Return permissions of role """
    role = getObjectByName(API.roles, roleName)
    return [perm.get_name() for perm in role.get_permits().list()]

def getSuperUserPermissions():
    """ Return SuperUser permissions(all possible permissions) """
    return getRolePermissions('SuperUser')

######################### HOSTS ###############################################
def createHost(clusterName, hostName, hostAddress, hostPassword):
    """ create host """
    msg = "Installing host '%s' on '%s'"
    LOGGER.info(msg % (hostAddress, clusterName))

    cluster = getObjectByName(API.clusters, clusterName)
    API.hosts.add(params.Host(
            name=hostName,
            address=hostAddress,
            cluster=cluster,
            root_password=hostPassword))
    host = API.hosts.get(hostName)
    assert host is not None

    waitForState(host, states.host.up,
            failStates = states.host.install_failed,
            timeout = config.HOST_INSTALL_TIMEOUT,
            restoreState=states.host.non_operational)

def waitForTasks(host, max_times=3, sleep_time=10):
    """
    Max 3(default) times try to deactive host, if there are running tasks
    So try to wait about 30seconds, 3x10s(default)
    Parameters:
     * host - host to be deactivated
     * max_times - max times time try to deactive host
     * sleep_time - time to sleep between tryies
    """
    while max_times > 0:
        try:
            host.deactivate()
            break
        except errors.RequestError as er:
            max_times -= 1
            if max_times == 0:
                raise er
            sleep(sleep_time)
    LOGGER.info("Switching host '%s' to maintence" % host.get_name())

def removeHost(hostName):
    """ remove Host"""
    host = API.hosts.get(hostName)
    if host is not None:
        LOGGER.info("Deactivating host '%s'" % hostName)

        # Max 3 times try to deactive host, if there are running tasks
        # So try to wait about 30seconds, 3x10s
        waitForTasks(host)
        waitForState(host, states.host.maintenance)

        LOGGER.info("Deleting host")
        host.delete()
        assert updateObject(host) is None, "Failed to remove host"
    else:
        raise errors.RequestError("Unable to see any host")
    #dc = API.datacenters.get(config.MAIN_DC_NAME) ???
    #waitForState(dc, 'up')

def activeDeactiveHost(hostName):
    """ Active, deactive host """
    LOGGER.info("Activating/deactivating host '%s'" %hostName)
    host = API.hosts.get(hostName)
    waitForTasks(host)

    LOGGER.info("Waiting for maintence")
    host = API.hosts.get(hostName)
    waitForState(host, states.host.maintenance)
    host.activate()
    LOGGER.info("Waiting for 'up' state")
    waitForHostUpState(host)

    # Check DC state
    dc = getObjectByName(API.datacenters, config.MAIN_DC_NAME)
    waitForState(dc, 'up')

def checkHostStatus(hostName):
    """ Check if is status up -> do UP """
    host = API.hosts.get(hostName)
    if host is None:
        LOGGER.info("Host '%s' dont exists." % hostName)
        return
    if host.status.state != states.host.up:
        LOGGER.info("Host '%s' state is '%s'" % (hostName, host.status.state))
        if host.status.state != states.host.maintenance:
            host.deactivate()
            waitForState(host, states.host.maintenance, timeout=180)
        LOGGER.info("Activating")
        host.activate()
        #waitForState(host, states.host.up)
        waitForHostUpState(host)

def checkDataCenterStatus(dcName):
    """"
    Print dc status and attached storage domains statuses.
    Parameters:
     * dcName - name of DC to be printed
    """
    dc = getObjectByName(API.datacenters, dcName)
    if dc is None:
        LOGGER.info("DC '%s' dont exists." % dcName)
        return
    LOGGER.info("DC '%s' state is '%s'" % (dcName, dc.status.state))
    for sd in dc.storagedomains.list():
        LOGGER.info("  SD %s status is %s" % (sd.get_name(), str(sd.status.state)))

def configureHostNetwork(hostName):
    """
    Try to change network properties.
    Parameters:
     * hostName - name of host to be changed
    """
    # Deactive host - need to be before configuring network
    host = API.hosts.get(hostName)
    for nic in host.nics.list():
        if nic.status.state == 'up':
            nic.update()
            break

maxTry = 3
def waitForHostUpState(host):
    """
    Wait for host, when its state is up.
    Wait for 3x 240s. Could happend that host don't come up, so try again.
    Parameters:
     * host - host that should be wait for
    """
    try:
        waitForState(host, states.host.up, timeout=240)
    except Exception as e:
        global maxTry
        maxTry -= 1
        if maxTry == 0:
            maxTry = 3
            raise e
        if host.status.state == states.host.non_operational or\
                host.status.state == states.host.unassigned:
            host.deactivate()
            waitForState(host, states.host.maintenance)
            host.activate()
            waitForHostUpState(host)

######################### VMS #################################################
def generateTicket(vmName):
    """
    Starts vm and wait for up state.
    Generate ticket to connect to vm """
    vm = getObjectByName(API.vms, vmName)
    if vm.status.state != states.vm.up:
        vm.start()
        waitForState(vm, states.vm.up)
    LOGGER.info("Vm '%s' started." % vmName)
    vm.ticket()
    LOGGER.info("Vm '%s' ticket generated." % vmName)
    vm.stop()
    waitForState(vm, states.vm.down)

def startVm(vmName):
    ''' Starts vm '''
    vm = getObjectByName(API.vms, vmName)
    if vm.status.state == states.vm.up:
        LOGGER.info("Vm '%s' is already started" % vmName)
        return
    vm.start()
    LOGGER.info("Staritng vm '%s'" % vmName)
    waitForState(vm, states.vm.up)

def createVm(vmName, memory=1*GB, createDisk=True, diskSize=GB,
                cluster=config.MAIN_CLUSTER_NAME,
                storage=config.MAIN_STORAGE_NAME):
    """ Creates VM and adds a system disk.

    The defaultly created disk will be a bootable COW sparse system disk with
    size `diskSize` and interface virtio. If you want to add a different disk,
    set `createDisk` to False and add it manually.
    """
    cluster = getObjectByName(API.clusters, cluster)
    template = getObjectByName(API.templates, 'Blank')

    if getObjectByName(API.vms, vmName) is not None:
        LOGGER.warning("Vm '%s' with this name already exists" % vmName)
        return

    API.vms.add(params.VM(
        name=vmName, memory=memory, cluster=cluster, template=template))

    vm = getObjectByName(API.vms, vmName)

    assert vm is not None, "Failed to create vm"

    if createDisk:
        LOGGER.info('Attaching disk to VM')
        sd = getObjectByName(API.storagedomains, storage)
        param = params.StorageDomains(
                storage_domain=[sd])
        updateObject(vm).disks.add(params.Disk(
            storage_domains=param, size=diskSize, #type_='system',
        status=None, interface='virtio', format='cow',
        sparse=True, bootable=True))

    waitForState(vm, states.vm.down)
    LOGGER.info("VM '%s' was created." %(vmName))

def getMainVmDisk(vmName):
    """ Return first disk of vm """
    vm = getObjectByName(API.vms, vmName)
    disks = vm.disks.list()
    if len(disks) > 0:
        return disks[0]
    else:
        return None

def waitForAllDisks(vmName):
    """ Wait until all vm disks are ok """
    vm = getObjectByName(API.vms, vmName)
    disks = vm.disks.list()
    if len(disks) > 0:
        for disk in disks:
            waitForState(disk, states.disk.ok)

def stopVm_(vmName):
    """ Stop vm and dont wait for disks """
    vm = getObjectByName(API.vms, vmName)
    if vm.status.state != states.vm.down:
        try:
            vm.stop()
        except errors.RequestError as e:
            if 'vm is not running' in e.detail.lower():
                pass
            else:
                raise
    waitForState(vm, states.vm.down)

def stopVm(vmName):
    """ Stop vm and wait for main disk """
    stopVm_(vmName)
    disk = getMainVmDisk(vmName)
    waitForState(disk, states.disk.ok)

def removeAllVms():
    """ Remove all vms in system """
    for vm in API.vms.list():
        if vm.status.state != states.vm.down:
            vm.stop()
            waitForState(vm, states.vm.down)
        removeVmObject(vm)

def removeObject(obj):
    """ Removes object """
    if obj is None:
        return
    obj.delete()
    waitForRemove(obj)
    LOGGER.info("Object '%s' removed." % (obj.get_name()))


def removeVmObject(vm):
    """ Remove vm object """
    removeObject(vm)

def removeVm(vmName):
    """ Remove VM and wait until it really gets removed. """
    vm = getObjectByName(API.vms, vmName)
    if vm is None:
        return
    LOGGER.info("Removing vm '%s'" %vmName)
    t = 0
    while vm.status.state == states.vm.image_locked and t <= config.TIMEOUT:
        t += 1
        sleep(1)
        updateObject(vm)

    if vm.status.state != states.vm.down:
        vm.stop()
        waitForState(vm, states.vm.down)

    waitForAllDisks(vmName)
    removeVmObject(vm)

def suspendVm(vmName):
    """ Suspends VM and handles 'asynch running tasks' exception.

    While suspending, the 'asynchronous running task' RequestError often
    occurs and means you have to wait a while to suspend the VM.
    """
    vm = getObjectByName(API.vms, vmName)
    assert vm.status.state == states.vm.up, \
        "VM has to be in state 'up' before suspend"
    asyncException = True
    t = 0
    while asyncException == True and t <= config.TIMEOUT:
        try:
            vm.suspend()
            asyncException = False
        except errors.RequestError as e:
            if 'asynchronous running tasks' in e.detail.lower():
                LOGGER.info("Asynchronous running tasks in VM, \
                        cannot suspend, trying again")
                asyncException = True
                sleep(1)
                t += 1
            else:
                raise
    if t > config.TIMEOUT:
        LOGGER.error("%s didn't start to suspend within timout \
                    of '%i' sec, current state is '%s'"
                    % (objectDescr(vm), config.TIMEOUT, vm.status.state))
    assert  newState(vm) == states.vm.saving_state or \
            newState(vm) == states.vm.suspended
    waitForState(vm, states.vm.suspended)

def migrateVm(vm, host):
    """
    Migrate vm.
    Parameters:
     * vm - vm to be migrated
     * host - host where the vm should be migrated
    """
    vm.migrate(params.Action(host=host))
    waitForState(vm, states.vm.up, timeout=240)
    LOGGER.info("Migrated VM '%s' to host '%s'" % (vm.get_name(), host.get_name()))

def moveVm(vmName, storageName):
    """
    Move vm vmName to storage storageName
    Parameters:
     * vmName - vm to be moved
     * storageName - storage where the vm should be moved
    """
    vm = getObjectByName(API.vms, vmName)
    sd = getObjectByName(API.storagedomains, storageName)

    vm.move(params.Action(storage_domain=sd))
    waitForState(vm, states.vm.down, timeout=7*60)
    LOGGER.info("VM '%s' was moved to sd '%s'" % (vmName, storageName))

def createDiskObjectNoCheck(diskName, storage=config.MAIN_STORAGE_NAME, bootable=False):
    """ Create disk and return it, dont wait for ok state """
    sd = getObjectByName(API.storagedomains, storage)
    param = params.StorageDomains(storage_domain=[sd])
    disk = API.disks.add(params.Disk(alias=diskName, name=diskName, provisioned_size=GB,
            size=GB, status=None, interface='virtio',
            format='cow', sparse=True, bootable=bootable,
            storage_domains=param))
    return disk

def createDiskObject(diskName, storage=config.MAIN_STORAGE_NAME, bootable=False):
    """
    Create disk and return it.
    Parameters:
     * diskName - name of disk
     * storage  - storage, where disk should be created
    """
    disk = createDiskObjectNoCheck(diskName, storage=storage, bootable=bootable)
    waitForState(disk, states.disk.ok)
    LOGGER.info("Disk '%s' created." % (disk.get_name()))
    assert disk is not None
    return disk

def deleteDiskObject(disk):
    """
    Delete disk, and wait for remove
    Parameters:
     * disk - disk to be removed
    """
    LOGGER.info("Removing disk '%s'" % (disk.get_alias()))
    disk.delete()
    waitForRemove(disk)

def deleteDisk(diskId, alias=None):
    """
    Delete disk.
    Parameters:
     * diskId - id of disk
     * alias  - alias of disk, used if there is no id
    """
    if alias is not None:
        disk = API.disks.get(alias=alias)
    else:
        disk = API.disks.get(id=diskId)
    if disk is None:
        LOGGER.info("Trying to delete nonexisting disk")
        return

    deleteDiskObject(disk)

def attachDiskToVm(disk, vmName):
    """
    Attach disk to vm.
    Parameters:
     * disk - disk object to be attached to vm
     * vmName - vmName of vm to be attached to diskId
    """
    vm = getObjectByName(API.vms, vmName)
    if vm is None:
        LOGGER.warn("Vm '%s' is None, test will fail" % vmName)
    if disk is None:
        LOGGER.warn("Disk '%s' is None, test will fail" % disk.get_name())

    LOGGER.info("Attaching disk '" + disk.get_name() + "' to vm " + vmName)
    disk = vm.disks.add(disk) # Attach
    disk = vm.disks.get(id=disk.get_id())
    assert disk is not None
    LOGGER.info("Disk '%s' state is '%s'" % (disk.get_name(), disk.status.state))

    waitForState(disk, states.disk.ok)
    disk.delete(params.Action(detach=True)) # Detach
    disk = vm.disks.get(id=disk.get_id())
    waitForState(disk, states.disk.ok)

def editVmDiskProperties(vmName, diskId=None, description=None):
    """
    Edit vm disk properies.
    Parameters:
     * vmName - name of vm that should be changed disk
    """
    vm = getObjectByName(API.vms, vmName)
    if vm is None:
        LOGGER.warning("Vm '%s' not exists." % (vmName))
        return
    if diskId is not None:
        disk = vm.disks.get(id=diskId)
    else:
        disk = vm.disks.list()[0]
    if disk is None:
        LOGGER.warn("Disk '%s' is None, test will fail" % disk.get_alias())

    dName = disk.get_name()
    dId = disk.get_id()

    if description:
        before = disk.get_description()
        disk.set_description(description)
    else:
        before = disk.get_interface()
        disk.set_interface('ide' if before == 'virtio' else 'virtio')

    disk.update()
    disk = vm.disks.get(id=dId)
    now = disk.get_description() if description else disk.get_interface()
    assert before != now, "Failed to update disk properties"
    LOGGER.info("Disk '%s' was edited." % dName)

def startStopVm(vmName):
    """ Starts and stops VM """
    vm = getObjectByName(API.vms, vmName)
    vm.start()
    LOGGER.info("VM '%s' starting" % (vmName))
    waitForState(vm, states.vm.up)
    vm.stop()
    LOGGER.info("VM '%s' stoping" % (vmName))
    waitForState(vm, states.vm.down)

############################# TEMPLATES #######################################
def createTemplate(vmName, templateName):
    """ Create template from vmName """
    vm = getObjectByName(API.vms, vmName)
    API.templates.add(params.Template(name=templateName, vm=vm))
    LOGGER.info('Creating temaplate "' + templateName + '"')
    waitForState(vm, states.vm.down)
    assert getObjectByName(API.templates, templateName) is not None

def removeTemplate(templateName):
    """
    Remove template and wait until it really gets removed.
    Parameters:
     * templateName - name of template to be deleted
    """
    template = getObjectByName(API.templates, templateName)

    if template is None:
        LOGGER.info("Template '%s' can's be seen, or does not exist." % templateName)
        return

    template.delete()
    LOGGER.info("Removing template '" + templateName + "'")
    waitForRemove(template)

def searchByObjectName(obj, name, id, alias=None):
    """
    Return object by its name
    Parameters:
     * obj  - object, which want to search
     * name - name of object
     * id   - id of object, used if name is None
    """
    if alias is not None:
        for o in obj.list():
            if o.get_alias() == alias:
                return o
    if name is None:
        return obj.get(id=id)
    # This is used because user level API don't support searching
    for o in obj.list():
        if o.get_name() == name:
            return o

def getObjectByName(obj, name, id=None, alias=None):
    """
    Return object by its name. Valid /vmpools.
    Parameters:
     * obj  - object, which want to search
     * name - name of object
     * id   - id of object, used if name is None
    """
    return searchByObjectName(obj, name, id, alias)

#################### VM POOLS #################################################
def createVmPool(poolName, templateName, clusterName=config.MAIN_CLUSTER_NAME,
                 size=1):
    """ Create Vm pool """
    template = getObjectByName(API.templates, templateName)
    cluster = getObjectByName(API.clusters, clusterName)

    API.vmpools.add(params.VmPool(name=poolName, cluster=cluster,
                template=template, size=size))

    assert getObjectByName(API.vmpools, poolName) is not None
    LOGGER.info('Created vmpool "' + poolName + '"')

def waitForRemove(obj):
    """
    Wait config.TIMEOUT seconds until object is removed.
    Parameters:
     * obj - object for which want to wait
    """
    t = 0
    while updateObject(obj) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(obj) is None, "Could not remove object"

def detachAllVmsInPool(vmpoolName):
    """
    Removes all Vms in pool and return these vms
    Parameters:
     * vmpoolName - name of pool from which vms will be detached
    """
    vms = []
    for vm in getAllVmsInPool(vmpoolName):
        LOGGER.info("Pool '%s' vm '%s' removing" % (vmpoolName, vm.get_name()))
        vm.detach()
        waitForState(vm, states.vm.down)
        vms.append(vm)
    return vms

def removeAllVmsInPool(vmpoolName):
    """ Removes all Vms in pool """
    for vm in getAllVmsInPool(vmpoolName):
        LOGGER.info("Pool '%s' vm '%s' removing" % (vmpoolName, vm.get_name()))
        vm.detach()
        waitForState(vm, states.vm.down)
        vm.delete()
        waitForRemove(vm)

def getAllVmsInPool(vmpoolName):
    """
    Return list of vms in pool.
    Parameters:
     * vmpoolName - name of pool
    """
    vms = []
    for vm in API.vms.list():
        pool = vm.get_vmpool()
        if pool is not None:
            pool = getObjectByName(API.vmpools, None, id=pool.get_id())
            if pool.get_name() == vmpoolName:
                vms.append(vm)

    return vms

def removeVmPool(vmpool):
    """
    Removes vm pool.
    Parameters:
     * vmpool - vmpool to be deleted
    """
    if vmpool is None:
        LOGGER.warning("Trying to delete nonexisting vmpool.")
        return
    vmpool.delete()
    waitForRemove(vmpool)
    LOGGER.info("Vmpool '" + vmpool.get_name() + "' removed")

def addVmToPool(vmpool):
    """ Add one new vm to vmpool """
    LOGGER.info("Configuring VM pool '%s'" % (vmpool.get_name()))

    sizeBefore = vmpool.get_size()
    newSize = int(sizeBefore) + 1
    vmpool.set_size(newSize)
    vmpool.update()

def vmpoolBasicOperations(vmpool):
    """
    Allocate vm from pool and then stop it
    Parameters:
     * vmpool - vmpool to test
    """
    LOGGER.info("Trying basic operations on pool '%s'" % (vmpool.get_name()))

    res = vmpool.allocatevm()
    vm = API.vms.get(id=res.get_vm().get_id())
    waitForState(vm, states.vm.up)
    vm.stop()
    waitForState(vm, states.vm.down)

#################### STORAGES #################################################
def createNfsStorage(storageName, storageType='data',
                    address=config.NFS_STORAGE_ADDRESS,
                    path=config.NFS_STORAGE_PATH,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME):
    """ Creates NFS storage, but does not attach it.

    Does not test if the storage already exists, so that it can be used in
    negative tests (the error will be produced by the sdk, not by this
    function.

    :param storageName:     (string) name of the storage domain to create
    :param storageType:     (string) either 'data', 'export' or 'iso'
    :param address:         (string) IP address of the storage
    :param path:            (string) path to the storage on the server given by
                            `address`, for example `'/mnt/nfs/mystorage'`
    :param datacenter:      (string) name of the datacenter where it will
                            be created
    :param host:            (string) name of the host to use
    """

    dc = getObjectByName(API.datacenters, datacenter)
    sd = getObjectByName(API.storagedomains, storageName)

    storageParams = params.Storage(type_='nfs',
            address = address, path = path)
    sdParams = params.StorageDomain(name=storageName,
                data_center=dc, storage_format='v1', type_=storageType,
                host=API.hosts.get(host), storage = storageParams)

    LOGGER.info("Creating NFS storage with name '%s' at host '%s'" %
            (storageName, host))
    LOGGER.info("IP/Path of NFS: %s:%s" %(address, path))
    storage = API.storagedomains.add(sdParams)
    storage = getObjectByName(API.storagedomains, storage.get_name())
    assert storage is not None, "Failed to create storage"
    return storage.get_name()

def removeAllFromSD(sdName):
    """ Removes vms and temapltes from SD """
    sd = API.storagedomains.get(sdName)
    for vm in sd.vms.list():
        removeVmObject(vm)
    for tmp in sd.templates.list():
        removeTemplate(tmp.get_name())

def createIscsiStorage(storageName, storageType='data',
                    address=config.LUN_ADDRESS,
                    target=config.LUN_TARGET,
                    guid=config.LUN_GUID,
                    datacenter=config.MAIN_DC_NAME,
                    host=config.MAIN_HOST_NAME):
    """ Creates iSCSI storage, but does not attach it.

    Does not test if the storage already exists, so that it can be used in
    negative tests (the error will be produced by the sdk, not by this
    function.

    .. seealso:: :func:`createNfsStorage`
    """
    dc = API.datacenters.get(datacenter)

    logicalUnit = params.LogicalUnit(id=guid,
            address=address, port=3260, target=target)
    storageParams = params.Storage(type_='iscsi',
            volume_group=params.VolumeGroup(logical_unit=[logicalUnit]))

    sdParams = params.StorageDomain(name=storageName,
                data_center=dc, storage_format='v1', type_=storageType,
                host=API.hosts.get(host), storage = storageParams)

    LOGGER.info("Creating iSCSI storage with name '%s'" % (storageName))
    API.storagedomains.add(sdParams)
    storage = API.storagedomains.get(storageName)
    assert storage is not None, "Failed to create storage"

def deactivateActivateByStateObject(storage, storageInDc, state, jmp,
        datacenter=config.MAIN_DC_NAME):
    if  jmp or (storage.status is None and storageInDc is not None and \
        storageInDc.status is not None and \
        storageInDc.status.state != state):
            storageInDc.deactivate()
            waitForState(storageInDc, states.storage.maintenance, timeout=10*60)
            storageInDc.activate()
            waitForState(storageInDc, states.storage.active, timeout=10*60)

def deactivateActivate(storageName, datacenter=config.MAIN_DC_NAME):
    deactivateActivateByState(storageName=storageName, state=states.storage.active, jmp=False,
            datacenter=datacenter)

def deactivateActivateByState(storageName, state, jmp, datacenter=config.MAIN_DC_NAME):
    dc = API.datacenters.get(datacenter)
    storage = API.storagedomains.get(storageName)

    storageInDc = dc.storagedomains.get(storageName)

    if  jmp or (storage.status is None and storageInDc is not None and \
        storageInDc.status is not None and \
        storageInDc.status.state != state):
            storageInDc.deactivate()
            waitForState(storageInDc, states.storage.maintenance, timeout=10*60)
            storageInDc.activate()
            waitForState(storageInDc, states.storage.active, timeout=10*60)


def attachActivateStorage(storageName, isMaster=False,
                            datacenter=config.MAIN_DC_NAME):
    """ Attach and activate a storage domain.

    Will not check if the storage is already active/attached, so it can be
    used in negative tests (the error will be from the sdk, not from here)
    """

    LOGGER.info("Attaching storage '%s' to data center" % (storageName))
    dc = API.datacenters.get(datacenter)
    storage = API.storagedomains.get(storageName)
    if dc.storagedomains.get(storageName) is not None:
        return

    dc.storagedomains.add(storage)
    storage = dc.storagedomains.get(storageName)
    assert storage is not None, \
            "Failed to attach storage to datacenter"

    # the main storage gets activated on it's own, no need to call activate()
    if not isMaster:
        storage.activate()
    waitForState(storage, states.storage.active, timeout=10*60)


def removeNonMasterStorage(storageName,
                            datacenter=config.MAIN_DC_NAME,
                            host=config.MAIN_HOST_NAME,
                            destroy=False):
    """ Deactivate, detach and remove a non-master storage domain.  """
    dc = getObjectByName(API.datacenters, datacenter)
    storage = getObjectByName(API.storagedomains, storageName)
    if storage is None:
        LOGGER.warning("SD '%s' not exists." % storageName)
        return

    doFormat = False if storage.get_type() == 'iso' else True

    if isStorageAttached(storageName):
        s = getObjectByName(dc.storagedomains, storageName)
        if s.status.state != states.storage.inactive and \
            s.status.state != states.storage.maintenance:
                LOGGER.info("Deactivating storage")
                s.deactivate()
                waitForState(s, [states.storage.inactive, states.storage.maintenance])
        if not destroy:
            LOGGER.info("Detaching storage from data center")
            s.delete()
            s = getObjectByName(API.storagedomains, storageName)
            waitForState(s, states.storage.unattached)

    LOGGER.info("Deleting storage '%s'" % (storageName))
    param = params.StorageDomain(name=storageName,
            host=params.Host(name=host), format=doFormat,
            destroy=destroy)
    storage.delete(param)
    storage = getObjectByName(API.storagedomains, storageName)
    assert storage is None, "Failed to remove SD '%s'" % (storageName)

def deactivateMasterStorage(storageName=config.MAIN_STORAGE_NAME,
                        datacenter=config.MAIN_DC_NAME,
                        host=config.MAIN_HOST_NAME):
    """ Deactivates the master storage domain and its datacenter.

    Fails if the storage doesn't exist (and therefore will not remove the
    datacenter).
    """
    dc = API.datacenters.get(name=datacenter)
    assert dc is not None
    sd = dc.storagedomains

    storage = sd.get(storageName)
    assert storage is not None

    if storage.status.state == states.storage.inactive:
        LOGGER.warning("Master storage in maintenance before removal")
    else:
        LOGGER.info("Deactivating storage")
        storage.deactivate()
        waitForState(storage, states.storage.maintenance)

def removeMasterStorage(storageName=config.MAIN_STORAGE_NAME,
                        datacenter=config.MAIN_DC_NAME,
                        host=config.MAIN_HOST_NAME):
    """ Deactivates and removes the master storage domain and its datacenter.

    Fails if the storage doesn't exist (and therefore will not remove the
    datacenter).
    """
    dc = API.datacenters.get(name=datacenter)
    assert dc is not None
    sd = dc.storagedomains

    storage = sd.get(storageName)
    assert storage is not None

    LOGGER.info("Storage state: %s" %storage.status.state)
    try:
        waitForState(storage, states.storage.active)
    except:
        LOGGER.warning("Storage state: %s" %storage.status.state)
        try:
            storage.activate()
            waitForState(storage, states.storage.active)
        except:
            LOGGER.warning("Storage was not activated.")
    if storage.status.state == states.storage.inactive:
        LOGGER.warning("Master storage in maintenance before removal")
    else:
        LOGGER.info("Deactivating storage")
        storage.deactivate()
        waitForState(storage, states.storage.maintenance)

    LOGGER.info("Deleting data center")
    dc.delete()
    assert updateObject(dc) is None, "Failed to remove DC"

    storage = API.storagedomains.get(storageName)
    assert storage.status.state == states.storage.unattached, \
        "Storage '%s' was not detached from DC" % storageName
    LOGGER.info("Deleting main storage")
    storage.delete(params.StorageDomain(name=storageName,
        host=params.Host(name=host), format=True))
    assert API.storagedomains.get(storageName) is None, \
        "Cannot remove master storage"


def isStorageAttached(storageName, datacenter=config.MAIN_DC_NAME):
    """ Return True if storage domain is attached to a datacenter.

    :return:    (bool) True if it is attached (even if it is locked or
                unreachable), False if it doesn't exist or if it is unattached.
    """
    dc = getObjectByName(API.datacenters, datacenter)
    storage = getObjectByName(API.storagedomains, storageName)
    if storage is None: # storage doesn't even exist
        return False

    storageInDc = getObjectByName(dc.storagedomains, storageName)
    if  storage.status is None and storageInDc is not None and \
        storageInDc.status is not None:
            return True
    else:
            return False

def detachAttachSD(storageName=config.MAIN_STORAGE_NAME,
                   datacenter=config.MAIN_DC_NAME):
    """ Detach and attach SD from DC """
    if isStorageAttached(storageName):
        LOGGER.info("Deactivating/activating '%s'" % storageName)
        deactivateMasterStorage(storageName=storageName,
                datacenter=datacenter,
                host=config.MAIN_HOST_NAME)
        attachActivateStorage(storageName)
    else:
        LOGGER.info("Activation/deactivating '%s'" % storageName)
        attachActivateStorage(storageName)
        deactivateMasterStorage(storageName=storageName,
                datacenter=datacenter,
                host=config.MAIN_HOST_NAME)

###############################################################################
def addRole(roleName, role, description="", administrative=False):
    """ Add new role to system """
    msg = "User role '%s' has not been created"
    permits = API.roles.get(role).permits.list()
    perms = params.Permits(permit=permits)
    role = params.Role(name=roleName, permits=perms, administrative=administrative,
            description=description)
    API.roles.add(role)

    assert API.roles.get(roleName) is not None, msg
    LOGGER.info("Role '%s' was created." % roleName)

def updateRole(roleName, permits=None, description=None, administrative=None):
    """
    Update role roleName
    permits = list of permits (example: ['create_vm', 'delete_vm'])
    description = description of role
    administrative = True/False(Admin/User)
    """
    role = API.roles.get(roleName)
    if role is None:
        LOGGER.warning("Role '%s' dont exists. Unable to remove" % roleName)
        return

    if permits is not None:
        for p in permits:
            role.permits.add(p)
    if description is not None:
        role.set_description(description)
    if administrative is not None:
        role.set_administrative(administrative)

    role.update()
    LOGGER.info("Role '%s' was successfylly updated." % roleName)

def deleteRole(roleName):
    """ Delete role roleName """
    role = API.roles.get(roleName)
    if role is None:
        LOGGER.warning("Role '%s' doesnt exists. Cant remove it." % roleName)
        return

    role.delete()
    role = API.roles.get(roleName)
    assert role is None, "Unable to remove role '%s'" % roleName
    LOGGER.info("Role '%s' was removed." % roleName)

def addGroup(groupName=config.GROUP_NAME):
    """ Add group to system """
    LOGGER.info("Adding group " + groupName)
    group = params.Group(name=groupName)
    group = API.groups.add(group)
    assert API.groups.get(group.get_name()) is not None
    return group

def addRoleToGroup(roleName, group):
    """
    *RoleName* that should be added to *group* object.
    """
    LOGGER.info("Adding role to group '%s'" % group.get_name())
    group.roles.add(API.roles.get(roleName))
    assert group.roles.get(roleName) is not None

def deleteGroup(groupName=config.GROUP_NAME):
    """ Deletes group from system """
    LOGGER.info("Deleteing group '%s'" % groupName)
    group = API.groups.get(groupName)
    if group is None:
        LOGGER.warning("Group '%s' doesnt exists. Cant remove it." % groupName)
        return
    group.delete()
    group = API.groups.get(groupName)
    assert group is None

def addUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """ Add user to system """
    LOGGER.info("Adding user " + userName)
    domain = params.Domain(name=domainName)
    user = params.User(user_name=userName, domain=domain)
    user = API.users.add(user)
    assert API.users.get(user.get_name()) is not None


def removeAllUsers(domainName=config.USER_DOMAIN):
    """ Remove all users from system """
    for user in API.users.list():
        domain = API.domains.get(id=user.get_domain().get_id())
        if domain.get_name() == domainName:
            user.delete()

def removeUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """
    Removes user.
    Parameters:
     * userName - name of user
     * domainName - domain of user
    """
    LOGGER.info("Removing user '%s' " % userName)
    user = getUser(userName, domainName)
    if user is None:
        return

    global users # Remove user also from dictionary
    users.pop(userName + 'True', None)
    users.pop(userName + 'False', None)

    nameOfUser = user.get_name()
    user.delete()
    assert API.users.get(nameOfUser) is None

def getUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """ Return user object """
    try:
        return API.users.list(user_name=userName + '@' + domainName)[0]
    except Exception as err:
        LOGGER.error("User %s not found." % userName)
        return None

########################### PERMISSIONS #############################
def addRoleToUser(roleName, userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """
    Add system permissions to user.
    Parameters:
     * roleName - role permissions to add
     * userName - name of user who will be added permissions
     * domainName - domain of user
    """
    LOGGER.info("Adding role '%s' to user '%s'" % (roleName, userName))
    user = getUser(userName, domainName)
    if user is None:
        return
    user.roles.add(API.roles.get(roleName))
    assert user.roles.get(roleName) is not None

def removeAllRolesFromUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """
    Removes all permissions from user.
    Parameters:
     * userName - name of user
     * domainName - domain of user
    """
    LOGGER.info("Removing all roles from user %s" % userName)
    user = getUser(userName, domainName)
    if user is None:
        return

    for role in user.roles.list():
        LOGGER.info("Removing " + role.get_name())
        role.delete()

    assert len(user.roles.list()) == 0, "Unable to remove roles from user '%s'" % user.get_name()

def removeRoleFromUser(roleName, userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    """
    Remove role(System permissions) from user.
    Parameters:
     * roleName - name of role
     * userName - name of user
     * domainName - domain of user
    """
    LOGGER.info("Removing role %s to user %s" % (roleName, userName))
    user = getUser(userName, domainName)
    if user is None:
        return
    role = user.roles.get(roleName)
    if role:
        role.delete()

    role = user.roles.get(roleName)
    assert role is None, "Unable to remove role '%s'" % roleName

def givePermissionsToGroup(templateName, roleName='TemplateUser', group="Everyone"):
    """
    Give permission to group.
    Parameters:
     * templateName - name of template to add group perms
     * roleName     - name of role which perms to be added
     * group        - On which group should be perms added
    """
    template = getObjectByName(API.templates, templateName)
    r = API.roles.get(roleName)

    g = API.groups.get(group)
    g.permissions.add(params.Permission(role=r, template=template))
    LOGGER.info("Adding permissions on template '%s' role '%s' for group '%s'.",
            template.get_name(), roleName, group)

def givePermissionToObject(rhevm_object, roleName, userName=config.USER_NAME,
                            domainName=config.USER_DOMAIN, user_object=None,
                            role_object=None):
    """
    Add role permission to user on object.
    Parameters:
     * rhevm_object - object to add role permissions on
     * roleName     - Role permissions to be added
     * userName     - user who should be added permissions
     * domainName   - domain of user
     * user_object  - temporaly, because uf bug 869334
     * role_object  - temporaly, because uf bug 869334
    """
    # FIXME: rhevm_object can be one of:
    # [API.clusters, API.datacenters, API.disks, API.groups, API.hosts,
    #  API.storagedomains, API.templates, API.vms, API.vmpools]

    try:
        user = getUser(userName, domainName)
        if user is None:
            return
    except errors.RequestError as e:
        # User cant access /users url. Bug 869334. Workaround
        user = user_object

    try:
        role = API.roles.get(roleName)
    except errors.RequestError as e:
        # User cant access /roles url. Bug 869334. Workaround
        role = role_object

    if rhevm_object is None or user is None or role is None:
        LOGGER.warning("Unable to add permissions on 'None' object")
        return

    permissionParam = params.Permission(user=user, role=role)
    rhevm_object.permissions.add(permissionParam)

    msg = "Added permission on '%s' with role '%s' for user '%s'"
    #LOGGER.info(msg % (type(rhevm_object).__name__, roleName, user.get_name()))

def givePermissionToVm(vmName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    vm = getObjectByName(API.vms, vmName)
    givePermissionToObject(vm, roleName, userName, domainName)

def givePermissionToDc(dcName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    dc = getObjectByName(API.datacenters, dcName)
    givePermissionToObject(dc, roleName, userName, domainName)

def givePermissionToCluster(clusterName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    cl = getObjectByName(API.clusters, clusterName)
    givePermissionToObject(cl, roleName, userName, domainName)

def givePermissionToTemplate(templateName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    tmp = getObjectByName(API.templates, templateName)
    givePermissionToObject(tmp, roleName, userName, domainName)

def givePermissionToDisk(diskName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    tmp = API.disks.get(alias=diskName)
    givePermissionToObject(tmp, roleName, userName, domainName)

def givePermissionToPool(poolName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    tmp = getObjectByName(API.vmpools, poolName)
    givePermissionToObject(tmp, roleName, userName, domainName)

def givePermissionToNet(netName, dcName, roleName, userName=config.USER_NAME,
        domainName=config.USER_DOMAIN):
    for net in API.networks.list():
        if dcName == API.datacenters.get(id=net.get_data_center().get_id()).get_name():
            givePermissionToObject(net, roleName, userName, domainName)

def removeUserPermissionsFromObject(rhevm_object, user_name, role):
    """
    Remove all user permissions with specific role from object.
    Parameters:
      * rhevm_object - object from which permissions should be removed
      * user_name - name of user who should be perms deleted
      * role - role that should be deleted from user
    """
    msg = "Removing permissions from object %s with perms %s from user %s"
    permissions = rhevm_object.permissions.list()
    LOGGER.info(msg % (rhevm_object.get_name(), role, user_name))
    for p in permissions:
        u = API.users.get(id=p.get_user().get_id())
        if p.get_role().get_id() == API.roles.get(role).get_id() and \
                u.get_user_name() == user_name:
                    p.delete()

def removeAllPermissionFromObject(rhevm_object):
    """
    Removes all permissions from object
    Parameters:
     * rhevm_object - object from which permissions should be removed
    """
    LOGGER.info("Removing all permissions from object '%s'" % type(rhevm_object).__name__)
    if rhevm_object is None:
        LOGGER.info("Tying to remove perms from object that dont exists")
        return

    permissions = rhevm_object.permissions.list()
    i = 0
    for p in permissions:
        u = API.users.get(id=p.get_user().get_id())
        if u.get_name() == 'admin' and u.get_domain().get_name() == 'internal':
            i += 1
            continue
        p.delete()
    assert len(rhevm_object.permissions.list()) == i

def removeAllPermissionFromVm(vmName):
    vm = getObjectByName(API.vms, vmName)
    removeAllPermissionFromObject(vm)

def removeAllPermissionFromDc(dcName):
    dc = getObjectByName(API.datacenters, dcName)
    removeAllPermissionFromObject(dc)

def removeAllPermissionFromCluster(clusterName):
    cluster = getObjectByName(API.clusters, clusterName)
    removeAllPermissionFromObject(cluster)

############# USERS ####################
def loginAsUser(userName=config.USER_NAME,
                domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD,
                filter_=True):
    LOGGER.info("Login as %s@%s(filter=%s)" % (userName, domain, filter_))
    i = userName + str(filter_)
    try:
        global users
        global API
        API = users[i]
    except KeyError:
        users[i] = ovirtsdk.api.API(url=config.OVIRT_URL, insecure=True,
                    username=userName+'@'+domain,
                    password=password, filter=filter_)
        API = users[i]

def loginAsAdmin():
    loginAsUser(config.OVIRT_USERNAME,
                config.OVIRT_DOMAIN,
                config.OVIRT_PASSWORD,
                filter_=False)

def editObject(rhevm_object, name, newName=None, description=None, append=False):
    """
    Edit object property.
    Parameters:
     * rhevm_object - object to be edited
     * name - name of object
     * newName - new name of object
     * description - description to be updated
     * append - True if append to old description else create new
    """
    obj = getObjectByName(rhevm_object, name)

    old_name = obj.get_name()
    old_desc = obj.get_description()
    if newName is not None:
        LOGGER.info("Updating name from '%s' to '%s'" %(name, newName))
        obj.set_name(newName)
        obj.update()
        obj = getObjectByName(rhevm_object, name)
        assert old_name != obj.get_name(), "Failed to update object name"

    if description is not None:
        LOGGER.info("Updating desc from '%s' to '%s'" %(name, description))
        if old_desc is None:
            old_desc = ""
        obj.set_description(old_desc + description if append else description)
        obj.update()
        obj = getObjectByName(rhevm_object, name)
        assert old_desc != obj.get_description(), "Failed to update object description"

def copyTemplate(templateName, storageName):
    """
    Copy template disk from SD to another SD
    Parameters:
     * templateName - name of template to be copyied
     * storageName  - name of storage where tmp should be copyied
    """
    template = getObjectByName(API.templates, templateName)

    try:
        disk = template.disks.list()[0]
    except IndexError:
        LOGGER.warning("Template '%s' has no disks?! => FAIL" % templateName)
        return
    except Exception as err:
        LOGGER.warning("Unexpected error: '%s'" %str(err))
        return

    sd = getObjectByName(API.storagedomains, storageName)
    LOGGER.info("Copying '%s' disk to '%s' domain" %(templateName, storageName))

    disk.copy(action=params.Action(storage_domain=sd))
    waitForState(disk, states.disk.ok)

def changeVmCustomProperty(vmName, regexp, name, value):
    """
    Changes vm custom property
    Parameters:
     * vmName - name of vm to change
     * regexp - regexp to change
     * name - name to be changed
     * value - value to be changed
    """
    cp = params.CustomProperties([params.CustomProperty(regexp=regexp, name=name, value=value)])
    vm = getObjectByName(API.vms, vmName)
    vm.set_custom_properties(cp)
    vm.update()

def hasUserPermissions(obj, role, user=config.USER_NAME, domain=config.USER_DOMAIN):
    """
    Tests if user have role permssions on rhevm_object
    Parameters:
     * obj    - object which we wanna tests
     * role   - role we wanna test
     * user   - user we wanna test
     * domain - domain where user belongs
    """
    perms = obj.permissions.list()
    for perm in perms:
        role_name = API.roles.get(id=perm.get_role().get_id()).get_name()
        user_name = API.users.get(id=perm.get_user().get_id()).get_user_name()
        LOGGER.info("User %s has perms %s on obj %s" % (user_name, role_name, obj.get_name()))
        if user + '@' + domain == user_name and role_name == role:
            return True
    return False

def hasPermissions(role):
    """ Get a list of permissions the user role has.

    :param role:    (string) oVirt user role
    :return:        (list of strings) permissions the role should have
    """
    return getRolePermissions(role)

# If bz plugin is not enabled, use this
def bz(*ids):
    def decorator(func):
        return func
    return decorator

# If tcms plugin is not enabled, use this
def tcms(*ids):
    def decorator(func):
        return func
    return decorator
