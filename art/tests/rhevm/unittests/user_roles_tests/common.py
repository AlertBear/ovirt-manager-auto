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
from ovirtsdk.infrastructure import contextmanager
from functools import wraps

MB = 1024*1024
GB = 1024*MB

logging.basicConfig(filename='messages.log',level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)
_major = int(config.OVIRT_VERSION[0])
_minor = int(config.OVIRT_VERSION[2:])
VERSION = params.Version(major=_major, minor=_minor)

def disconnect():
    proxy = contextmanager.get('proxy')
    persistent_auth = contextmanager.get('persistent_auth')
    filter_header = contextmanager.get('filter')

    if proxy and persistent_auth:
        try:
            proxy.request(method='GET',
                        url='/api',
                        headers={'Filter': filter_header},
                        last=True)
        except Exception:
            pass
    contextmanager._clear(force=True)

def _getApi():
    """ Return ovirtsdk api.

    Will not create another API instance when reloading this module in
    ipython (when common.API is already defined).
    Works around problem when reloading, which would
    otherwise cause the error `ImmutableError: [ERROR]::'proxy' is immutable.`.
    """
    try:
        return API
    except NameError:
        disconnect()
        return ovirtsdk.api.API(
                    url=config.OVIRT_URL, insecure=True,
                    username=config.OVIRT_USERNAME+'@'+config.OVIRT_DOMAIN,
                    password=config.OVIRT_PASSWORD)

API = _getApi()


def waitForState(obj, desiredStates, failStates=None, timeout=config.TIMEOUT,
                    sampling=1):
    """ Waits for oVirt object to change state using :py:func:`time.sleep`.

    :param obj:             the oVirt object (host, VM, ...) for which to wait
    :param desiredStates:   the desired oVirt object states, accepts both a
                            list of states or a single state
    :param failStates:      fail if the object reaches one of these states
    :param timeout:         (int) time in seconds to wait for desired state
    :param sampling:        (int) how often to check state, in seconds

    :raises AssertionError: when timeout is exceeded and the object still isn't
        in the desired state or if failState was reached

    .. seealso:: :mod:`tests.states`
    """

    if obj is None:
        return
    if type(desiredStates) is not list:
        desiredStates = [desiredStates]
    if type(failStates) is not list and failStates is not None:
        failStates = [failStates]
    elif failStates is None:
        failStates = []

    assert type(obj) is not str, "Bad use of 'waitForState()'"
    #LOGGER.info("Waiting for %s to reach one of states %s"
    #            % (objectDescr(obj), str(desiredStates)))
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
        parent = API.vms
    elif 'VMDisk' == t:
        vmId = obj.get_vm().get_id()
        vm = API.vms.get(id=vmId)
        parent = vm.disks
    elif 'Template' == t:
        parent = API.templates
    elif 'DataCenter' == t:
        parent = API.datacenters
    elif 'Cluster' == t:
        parent = API.clusters
    elif 'StorageDomain' == t:
        parent = API.storagedomains
    elif 'VmPool' == t:
        parent = API.vmpools
    elif 'DataCenterStorageDomain' == t:
        # it is attached
        dcname = obj.parentclass.name
        dc = API.datacenters.get(dcname)
        parent = dc.storagedomains
    else:
        raise Exception("Unknown object %s, cannot update it's state"
                        % (objectDescr(obj)))

    return parent.get(obj.name)


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
    dc = API.datacenters.get(name)
    assert dc is not None

def removeDataCenter(name):
    dc = API.datacenters.get(name)
    if dc is not None:
        LOGGER.info("Removing datacenter '%s'" % name)
        dc.delete()
        assert updateObject(dc) is None, "Can't remove datacenter"

def createCluster(name, datacenterName,
                    cpu_type=config.HOST_CPU_TYPE, version=VERSION):
    LOGGER.info("create_cluster")
    dc = API.datacenters.get(datacenterName)
    API.clusters.add(params.Cluster(
                name=name,
                cpu=params.CPU(id=cpu_type),
                data_center=dc,
                version=VERSION))
    cluster = API.clusters.get(name)
    LOGGER.info("Creating cluster '%s'" % name)
    assert cluster is not None

def removeCluster(name):
    cluster = API.clusters.get(name)
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
    role = API.roles.get(roleName)
    return [perm.get_name() for perm in role.get_permits().list()]

def getSuperUserPermissions():
    """ Return SuperUser permissions(all possible permissions) """
    return getRolePermissions('SuperUser')

######################### HOSTS ###############################################
def createHost(clusterName, hostName=config.ALT_HOST_ADDRESS, hostAddress=config.ALT_HOST_ADDRESS,
                hostPassword=config.ALT_HOST_ROOT_PASSWORD):
    """ create host """
    msg = "Installing host '%s' on '%s'"
    LOGGER.info(msg % (hostAddress, clusterName))

    cluster = API.clusters.get(clusterName)
    API.hosts.add(params.Host(
            name=hostName,
            address=hostAddress,
            cluster=cluster,
            root_password=hostPassword))
    host = API.hosts.get(hostName)
    assert host is not None

    waitForState(host, states.host.up,
            failStates = states.host.install_failed,
            timeout = config.HOST_INSTALL_TIMEOUT)

def removeHost(hostName=config.ALT_HOST_ADDRESS):
    """ remove Host"""
    host = API.hosts.get(hostName)
    if host is not None:
        LOGGER.info("Deactivating host '%s'" % hostName)
        host.deactivate()
        waitForState(host, states.host.maintenance)

        LOGGER.info("Deleting host")
        host.delete()
        assert updateObject(host) is None, "Failed to remove host"
    else:
        raise errors.RequestError("Unable to see any host")

def activeDeactiveHost(hostName):
    """ Active, deactive host """
    LOGGER.info("Activating/deactivating host")
    host = API.hosts.get(hostName)
    host.deactivate()
    waitForState(host, states.host.maintenance)
    host.activate()
    waitForState(host, states.host.up)

def checkHostStatus(hostName):
    """ Check if is status up -> do UP """
    host = API.hosts.get(hostName)
    if host is None:
        LOGGER.info("Host '%s' dont exists." % hostName)
        return
    LOGGER.info("Host '%s' state is '%s'" % (hostName, host.status.state))
    if host.status.state != states.host.up:
        LOGGER.info("Activating")
        host.activate()

def checkDataCenterStatus(dcName):
    """" Print dc status and sds """
    dc = API.datacenters.get(dcName)
    if dc is None:
        LOGGER.info("DC '%s' dont exists." % dcName)
        return
    LOGGER.info("DC '%s' state is '%s'" % (dcName, dc.status.state))
    for sd in dc.storagedomains.list():
        LOGGER.info("  SD %s status is %s" % (sd.get_name(), str(sd.status.state)))

######################### VMS #################################################
def createVm(vmName, memory=1*GB, createDisk=True, diskSize=512*MB,
                cluster=config.MAIN_CLUSTER_NAME,
                storage=config.MAIN_STORAGE_NAME):
    """ Creates VM and adds a system disk.

    The defaultly created disk will be a bootable COW sparse system disk with
    size `diskSize` and interface virtio. If you want to add a different disk,
    set `createDisk` to False and add it manually.
    """
    cluster = API.clusters.get(cluster)
    template = API.templates.get('Blank')

    API.vms.add(params.VM(
        name=vmName, memory=memory, cluster=cluster, template=template))
    vm = API.vms.get(vmName)
    assert vm is not None, "Failed to create vm"

    if createDisk:
        LOGGER.info('Attaching disk to VM')
        param = params.StorageDomains(
                storage_domain=[API.storagedomains.get(storage)])
        updateObject(vm).disks.add(params.Disk(
            storage_domains=param, size=diskSize, #type_='system',
        status=None, interface='virtio', format='cow',
        sparse=True, bootable=True))

    waitForState(vm, states.vm.down)
    LOGGER.info("VM '%s' was created." %(vmName))

def getMainVmDisk(vmName):
    vm = API.vms.get(vmName)
    disks = vm.disks.list()
    if len(disks) > 0:
        return disks[0]
    else:
        return None

def waitForAllDisks(vmName):
    vm = API.vms.get(vmName)
    disks = vm.disks.list()
    if len(disks) > 0:
        for disk in disks:
            waitForState(disk, states.disk.ok)

def stopVm_(vmName):
    vm = API.vms.get(vmName)
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
    stopVm_(vmName)
    disk = getMainVmDisk(vmName)
    waitForState(disk, states.disk.ok)

def removeVm(vmName):
    """ Remove VM and wait until it really gets removed. """
    vm = API.vms.get(vmName)
    if vm is None:
        return

    t = 0
    while vm.status.state == states.vm.image_locked and t <= config.TIMEOUT:
        t += 1
        sleep(1)
        updateObject(vm)

    if vm.status.state != states.vm.down:
        vm.stop()
        waitForState(vm, states.vm.down)

    waitForAllDisks(vmName)

    vm.delete()

    t = 0
    while updateObject(vm) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(vm) is None, "Could not remove VM"
    LOGGER.info("VM '%s' removed." % (vmName))


def suspendVm(vmName):
    """ Suspends VM and handles 'asynch running tasks' exception.

    While suspending, the 'asynchronous running task' RequestError often
    occurs and means you have to wait a while to suspend the VM.
    """
    vm = API.vms.get(vmName)
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


def changeVmCd(vmName, isoName):
    vm = API.vms.get(vmName)

    if vm.status.state != states.vm.down:
        vm.stop()
    sDomain = API.storagedomains.get(isoName)
    newFile = sDomain.files.get(name=config.ISO_FILE)
    if newFile is None:
        LOGGER.warn("File '%s' doesnt exist." % config.ISO_FILE)
    param = params.CdRom(file=newFile)
    vm.cdroms.add(param)
    LOGGER.info("VM's '%s' CD changed" %(vmName))


def migrateVm(vmName, hostAddress=config.ALT_HOST_ADDRESS):
    """ """
    vm = API.vms.get(vmName)
    host = API.hosts.get(hostAddress)
    action = params.Action(host=host)
    if vm.status.state != states.vm.up:
        vm.start()
    waitForState(vm, states.vm.up)
    vm.migrate(action)
    LOGGER.info("Migratng VM " + vmName + " to host " + hostAddress)
    # TODO: Check if migrate action was OK

def moveVm(vmName, storageName=config.ALT_STORAGE_NAME):
    """ moveVm """
    vm = API.vms.get(vmName)
    sd = API.storagedomains.get(storageName)
    action = params.Action(storage_domain=sd)

    vm.move(action)

    LOGGER.info("Vm " + vmName + " was moved")
    # TODO: Check if move action was OK


def createDisk(diskName, storage=config.MAIN_STORAGE_NAME):
    """ createDisk """
    if getDisksByName(diskName) is not None:
        LOGGER.warn("Disk '%s' already exists" % diskName)
        return
    param = params.StorageDomains(storage_domain=[API.storagedomains.get(storage)])
    disk = API.disks.add(params.Disk(name=diskName, provisioned_size=10,
            size=10, status=None, interface='virtio',
            format='cow', sparse=True, bootable=False,
            storage_domains=param))

    LOGGER.info('Creating disk "' + diskName + '"')
    assert disk is not None

# workaround because of BZ 859897
def getDisksByName(diskName):
    """ get disk by name """
    for disk in API.disks.list():
        if disk.get_name() == diskName:
            return disk

def deleteDisk(diskName):
    """ deleteDisk """
    #disk = API.disks.get(name=diskName)
    disk = getDisksByName(diskName)
    if disk is None:
        LOGGER.info("Trying to delete nonexisting disk '%s'" % (diskName))
        return

    disk.delete()
    LOGGER.info("Removing disk '" + diskName + "'")

    t = 0
    while updateObject(disk) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(disk) is None, "Could not remove disk"


def attachDiskToVm(diskName, vmName):
    """ attachDisk """
    vm = API.vms.get(vmName)
    if vm is None:
        LOGGER.warn("Vm '%s' is None, test will fail" % vmName)
    disk = getDisksByName(diskName)
    #disk = API.disks.get(diskName)
    if disk is None:
        LOGGER.warn("Disk '%s' is None, test will fail" % diskName)

    LOGGER.info("Attaching disk '" + diskName + "' to vm " + vmName)
    vm.disks.add(disk)
    disk = vm.disks.get(diskName)
    assert disk is not None
    LOGGER.info("Disk '%s' state is '%s'" % (diskName, disk.status.state))
    if disk.status.state != states.disk.ok:
        disk.activate()
    waitForState(disk, states.disk.ok)

def editDiskProperties(diskName):
    """ edit disk properies """
    #disk = API.disks.get(diskName)
    disk = getDisksByName(diskName)
    if disk is None:
        LOGGER.warn("Disk '%s' is None, test will fail" % diskName)

    before = disk.get_shareable()
    if before is None or before == False:
        after = True
    else:
        after = False

    disk.set_shareable(after)
    disk.update()

    disk = getDisksByName(diskName)
    #disk = API.disks.get(diskName)
    now = disk.get_shareable()
    assert before != now, "Failed to update disk shareable properties"
    LOGGER.info("Editting disk '" + diskName + "'")

def startStopVm(vmName):
    """ Starts and stops VM """
    vm = API.vms.get(vmName)
    vm.start()
    LOGGER.info("VM '%s' starting" % (vmName))
    waitForState(vm, states.vm.up)
    vm.stop()
    LOGGER.info("VM '%s' stoping" % (vmName))
    waitForState(vm, states.vm.down)

############################# TEMPLATES #######################################
def createTemplate(vmName, templateName):
    """ """
    #assert API.templates.get(templateName) is None, \
    #    "Template with the name '" + templateName + "' already exists"
    if API.templates.get(templateName) is not None:
        LOGGER.warning("Template '%s' already exists" % templateName)
        return
    vm = API.vms.get(vmName)
    API.templates.add(params.Template(name=templateName, vm=vm))
    LOGGER.info('Creating temaplate "' + templateName + '"')
    waitForState(vm, states.vm.down)
    assert API.templates.get(templateName) is not None

def removeTemplate(templateName):
    """ Remove template and wait until it really gets removed. """
    template = API.templates.get(templateName)
    if template is None:
        return

    template.delete()
    LOGGER.info("Removing template '" + templateName + "'")

    t = 0
    while updateObject(template) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(template) is None, "Could not remove template"

#################### VM POOLS #################################################
def createVmPool(poolName, templateName, clusterName=config.MAIN_CLUSTER_NAME,
                 size=1):
    """ Create Vm pool """
    assert API.vmpools.get(poolName) is None, \
        "Vmpool with the name '" + poolName + "' already exists"

    template = API.templates.get(templateName)
    cluster = API.clusters.get(clusterName)

    API.vmpools.add(params.VmPool(name=poolName, cluster=cluster, 
                template=template, size=size))
    assert API.vmpools.get(poolName) is not None
    LOGGER.info('Creating vmpool "' + poolName + '"')

def removeAllVmsInPool(vmpoolName):
    """ Removes all Vms in pool """
    for vm in getAllVmsInPool(vmpoolName):
        vm.detach()
        waitForState(vm, states.vm.down)
        vm.delete()
        t = 0
        while updateObject(vm) is not None and t <= config.TIMEOUT:
            t += 1
            sleep(1)
        assert updateObject(vm) is None, "Could not remove Vm"

def getAllVmsInPool(vmpoolName):
    """ Return all vms in pool """
    vms = []
    for vm in API.vms.list():
        pool = vm.get_vmpool()
        if pool is not None:  # and pool.get_name() == vmpoolName:
            vms.append(vm)

    return vms

def removeVmPool(vmpoolName):
    """ Removes vm pool """
    vmpool = API.vmpools.get(vmpoolName)
    if vmpool is None:
        return

    removeAllVmsInPool(vmpoolName)
    vmpool.delete()

    t = 0
    while updateObject(vmpool) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(vmpool) is None, "Could not remove vm pool"
    LOGGER.info("Vmpool '" + vmpoolName + "' removed")

def addVmToPool(vmpoolName):
    """ Add one new vm to vmpool """
    LOGGER.info("Configuring VM pool '%s'" % (vmpoolName))
    vmpool = API.vmpools.get(vmpoolName)
    sizeBefore = vmpool.get_size()
    newSize = int(sizeBefore) + 1
    vmpool.set_size(newSize)
    vmpool.update()

    vmpool = API.vmpools.get(vmpoolName)
    now = vmpool.get_size()
    assert sizeBefore != now, "Failed to update vmpools configuration"

def vmpoolBasicOperations(vmpoolName):
    """ Start, stop, detach vm from pool """
    LOGGER.info("Trying basic operations on pool '%s'" % (vmpoolName))
    vm = getAllVmsInPool(vmpoolName)[0]
    LOGGER.info("VM state is '%s'" % vm.status.state)
    if vm.status.state == states.vm.image_locked:
        waitForState(vm, states.vm.down)
    vm.start()
    waitForState(vm, states.vm.up)
    vm.stop()
    waitForState(vm, states.vm.down)
    vm.detach()
    waitForState(vm, states.vm.down)
    vm.delete()

    t = 0
    while updateObject(vm) is not None and t <= config.TIMEOUT:
        t += 1
        sleep(1)
    assert updateObject(vm) is None, "Could not remove Vm"


#################### QUOTAS ###################################################
def configureQuota(vmName, dcName=config.MAIN_DC_NAME, user=config.USER_NAME):
    """ Configure quota for DC - dcName """
    dc = API.datacenters.get(dcName)
    vm = API.vms.get(vmName)
    users = API.users.get(user)
    quota = params.Quota(data_center=dc, vms=vm,
                    disks=vm.disks, users=users)
    dc.quotas.add(quota)

################### GLUSTER ###################################################
def createGlusterVolume():
    """ Create gluster volume """
    pass

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

    dc = API.datacenters.get(datacenter)
    sd = API.storagedomains.get(storageName)
    if sd is not None:
        LOGGER.warn("SD '%s' already exists" % storageName)
        return

    storageParams = params.Storage(type_='nfs',
            address = address, path = path)
    sdParams = params.StorageDomain(name=storageName,
                data_center=dc, storage_format='v1', type_=storageType,
                host=API.hosts.get(host), storage = storageParams)

    LOGGER.info("Creating NFS storage with name '%s' at host '%s'" %
            (storageName, host))
    API.storagedomains.add(sdParams)
    storage = API.storagedomains.get(storageName)
    assert storage is not None, "Failed to create storage"


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
    waitForState(storage, states.storage.active)


def removeNonMasterStorage(storageName,
                            datacenter=config.MAIN_DC_NAME,
                            host=config.MAIN_HOST_NAME):
    """ Deactivate, detach and remove a non-master storage domain.  """
    dc = API.datacenters.get(name=datacenter)
    storage = API.storagedomains.get(storageName)
    assert storage is not None

    doFormat = False if storage.get_type() == 'iso' else True

    if isStorageAttached(storageName):
        storage = dc.storagedomains.get(storageName)
        if storage.status.state != states.storage.inactive and \
            storage.status.state != states.storage.maintenance:
                LOGGER.info("Deactivating storage")
                storage.deactivate()
                waitForState(storage,
                    [states.storage.inactive, states.storage.maintenance])
        LOGGER.info("Detaching storage from data center")
        storage.delete()
        storage = API.storagedomains.get(storageName)
        waitForState(storage, states.storage.unattached)

    LOGGER.info("Deleting storage '%s'" % (storageName))
    param = params.StorageDomain(name=storageName,
            host=params.Host(name=host), format=doFormat)
    storage.delete(param)
    storage = API.storagedomains.get(storageName)
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
    dc = API.datacenters.get(name=datacenter)
    storage = API.storagedomains.get(storageName)
    if storage is None: # storage doesn't even exist
        return False

    storageInDc = dc.storagedomains.get(storageName)
    if  storage.status is None and storageInDc is not None and \
        storageInDc.status is not None:
            return True
    else:
            return False

def detachAttachSD(storageName=config.MAIN_STORAGE_NAME,
                   datacenter=config.MAIN_DC_NAME):
    """ Detach and attach SD from DC """

    if isStorageAttached(storageName):
        deactivateMasterStorage()
        attachActivateStorage(storageName)
    else:
        attachActivateStorage(storageName)
        deactivateMasterStorage()

###############################################################################
def addRole(roleName, permits, description="", administrative=False):
    """ Add new role to system """
    msg = "User role '%s' has not been created"

    perms = params.Permits(permits)
    role = params.Role(name=roleName, permits=perms, description=description,
            administrative=administrative)

    API.roles.add(role)

    role = API.roles.get(name=roleName)
    assert role is not None, msg % roleName

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
        role.set_permits(permits)
    if description is not None:
        role.set_description(description)
    if administrative is not None:
        role.set_administrative(administrative)

    role.update()

def deleteRole(roleName):
    """ Delete role roleName """
    role = API.roles.get(roleName)
    if role is None:
        LOGGER.warning("Role '%s' doesnt exists. Cant remove it." % roleName)
        return
    role.delete()

    role = API.roles.get(roleName)
    assert role is None, "Unable to remove role '%s'" % roleName

def addUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    LOGGER.info("Adding user " + userName)
    domain = params.Domain(name=domainName)
    user = params.User(user_name=userName, domain=domain)
    API.users.add(user)
    assert API.users.get(userName) is not None

def addRoleToUser(roleName, userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    LOGGER.info("Adding role to user")
    user = API.users.get(userName)
    user.roles.add(API.roles.get(roleName))
    assert user.roles.get(roleName) is not None

def removeAllRolesFromUser(userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    LOGGER.info("Removing all roles from user %s" % userName)
    user = API.users.get(userName)
    for role in user.roles.list():
        role.delete()

    assert len(user.roles.list() == 0), "Unable to remove roles from user '%s'" % userName

def removeRoleFromUser(roleName, userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    LOGGER.info("Removing role %s to user %s" % (roleName, userName))
    user = API.users.get(userName)
    role = user.roles.get(roleName)
    role.delete()

    role = user.roles.get(roleName)
    assert role is None, "Unable to remove role '%s'" % roleName

def addPermissionsToUser(roleName, dcName=config.MAIN_DC_NAME,
                userName=config.USER_NAME, domainName=config.USER_DOMAIN):
    user = API.users.get(userName)
    role = API.roles.get(roleName)
    dc = API.datacenters.get(dcName)
    param = params.Permission(role=role, data_center=dc)
    user.permissions.add(param)
    LOGGER.info("Manipulating permissions success")
    # TODO: check if action was OK.

def removeUser(userName=config.USER_NAME):
    user = API.users.get(userName)
    user.delete()
    assert API.users.get(userName) is None

def givePermissionToVm(vmName, roleName, userName=config.USER_NAME):
    msg = "Adding permission on vm '%s' with role '%s' for user '%s'"
    LOGGER.info(msg % (vmName, roleName, userName))
    vm = API.vms.get(vmName)
    user = API.users.get(userName)
    role = API.roles.get(roleName)
    assert vm is not None
    assert user is not None
    assert role is not None

    permissionParam = params.Permission(user=user, role=role)
    vm.permissions.add(permissionParam)

def givePermissionToDc(dcName, roleName, userName=config.USER_NAME):
    """ """
    msg = "Adding permission on DC '%s' with role '%s' for user '%s'"
    LOGGER.info(msg % (dcName, roleName, userName))
    dc = API.datacenters.get(dcName)
    user = API.users.get(userName)
    role = API.roles.get(roleName)
    assert dc is not None
    assert user is not None
    assert role is not None

    permissionParam = params.Permission(user=user, role=role)
    dc.permissions.add(permissionParam)

def givePermissionToCluster(clusterName, roleName, userName=config.USER_NAME):
    """ """
    msg = "Adding permission on cluster '%s' with role '%s' for user '%s'"
    LOGGER.info(msg % (clusterName, roleName, userName))
    cl = API.clusters.get(clusterName)
    user = API.users.get(userName)
    role = API.roles.get(roleName)
    assert cl is not None
    assert user is not None
    assert role is not None

    permissionParam = params.Permission(user=user, role=role)
    cl.permissions.add(permissionParam)

def givePermissionToTemplate(templateName, roleName, userName=config.USER_NAME):
    """ """
    msg = "Adding permission on template '%s' with role '%s' for user '%s'"
    LOGGER.info(msg % (templateName, roleName, userName))
    tmp = API.templates.get(templateName)
    user = API.users.get(userName)
    role = API.roles.get(roleName)
    assert tmp is not None
    assert user is not None
    assert role is not None

    permissionParam = params.Permission(user=user, role=role)
    tmp.permissions.add(permissionParam)

def removeAllPermissionFromVm(vmName):
    LOGGER.info("Removing all permissions from VM '%s'" % vmName)
    vm = API.vms.get(vmName)
    if vm is None:
        LOGGER.info("Tying to remove permiison from VM '%s' that don't exists" % vmName)
        return

    permissions = vm.permissions.list()
    for perm in permissions:
        perm.delete()
    assert len(vm.permissions.list()) == 0

def removeAllPermissionFromDc(dcName):
    LOGGER.info("Removing all permissions from DC '%s'" % dcName)
    dc = API.datacenters.get(dcName)
    if dc is None:
        LOGGER.info("Tying to remove permiisions from DC '%s' that don't exists" %
                dcName)
        return

    permissions = dc.permissions.list()
    for perm in permissions:
        perm.delete()
    assert len(dc.permissions.list()) == 0

def removeAllPermissionFromCluster(clusterName):
    LOGGER.info("Removing all permissions from cluster '%s'" % clusterName)
    cl = API.clusters.get(clusterName)
    if cl is None:
        LOGGER.info("Tying to remove permiisions from cluster '%s' that don't exists" %
                clusterName)
        return

    permissions = cl.permissions.list()
    for perm in permissions:
        perm.delete()
    assert len(cl.permissions.list()) == 0

def getFilterHeader():
    """ Has user admin role or user role? """
    return contextmanager.get('filter')

def loginAsUser(userName=config.USER_NAME,
                domain=config.USER_DOMAIN,
                password=config.USER_PASSWORD,
                filter_=True):
    LOGGER.info("Login as %s" % userName)
    global API
    API.disconnect()
    API = ovirtsdk.api.API(url=config.OVIRT_URL, insecure=True,
                    username=userName+'@'+domain,
                    password=password, filter=filter_)


def loginAsAdmin():

    loginAsUser(config.OVIRT_USERNAME,
                config.OVIRT_DOMAIN,
                config.OVIRT_PASSWORD,
                filter_=False)

def asUser(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loginAsUser()
            result = f(*args, **kwargs)
        finally:
            loginAsAdmin()
        return result
    return wrapper


