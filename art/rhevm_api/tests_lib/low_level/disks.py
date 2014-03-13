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
import types
from utilities.machine import Machine

from art.core_api.apis_exceptions import EntityNotFound, APITimeout
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.data_struct.data_structures import Fault
from art.rhevm_api.utils.test_utils import get_api, split, waitUntilGone
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.core_api import is_action
from art.test_handler.exceptions import DiskException, CanNotResolveActionPath
from art.test_handler.settings import opts

GBYTE = 1024 ** 3
ENUMS = opts['elements_conf']['RHEVM Enums']
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEFAULT_DISK_TIMEOUT = 180

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
CONN_API = get_api('storage_connection', 'storageconnections')

logger = logging.getLogger(__name__)
xpathMatch = is_action('xpathMatch')(XPathMatch(VM_API))
BLOCK_DEVICES = [ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp']]


def getStorageDomainDisks(storagedomain, get_href):
    '''
    Descrpition: Returns all disks in the given storage domain
    Parameters:
        * storagedomain - name of the storage domain
        * get_href - Returns link for rest if True or sdk object if false
    Author: gickowic
    '''
    sdObj = STORAGE_DOMAIN_API.find(storagedomain)
    return DISKS_API.getElemFromLink(sdObj, get_href=get_href)


def getObjDisks(name, get_href=True, is_template=False):
    """
    Description: Returns given vm's disks collection
    Parameters:
        * vmName - name of VM
        * get_href - True means to return href link for rest or object for sdk
                    (VmDisks)
                    False means to return the list of objects -
                    [VmDisk, VmDisk, ...]
    Author: jlibosva
    Return: href link to disks or list of disks
    """
    api = TEMPLATE_API if is_template else VM_API
    obj = api.find(name)
    return DISKS_API.getElemFromLink(obj, get_href=get_href)


def getVmDisk(vmName, alias):
    """
    Description: Returns disk from VM's collection
    Parameters:
        * vmName - name of VM
        * alias - name of disk
    Author: jlibosva
    Return: Disk from VM's collection
    """
    vmObj = VM_API.find(vmName)
    return DISKS_API.getElemFromElemColl(vmObj, alias)


def _prepareDiskObject(**kwargs):
    """
    Description: Prepare disk object according kwargs
    Parameters:
        * alias - name of the disk
        * provisioned_size - size of the disk
        * interface - IDE or virtio
        * format - raw or cow
        * size - size of the disk
        * sparse - True or False whether disk should be sparse
        * bootable - True or False whether disk should be bootable
        * shareable - True or False whether disk should be sharable
        * allow_snapshot - True or False whether disk should allow snapshots
        * propagate_errors - True or False whether disk should propagate errors
        * wipe_after_delete - True or False whether disk should wiped after
                              deletion
        * storagedomain - name of storage domain where disk will reside
        * quota - disk quota
        * storage_connection - in case of direct LUN - existing storage
                               connection to use instead of creating a new one
        You cannot set both storage_connection and lun_* in one call!

        * id - disk id
        * active - True or False whether disk should activate after creation
        * snapshot - snapshot object of the disk


    Author: jlibosva
    Return: Disk object
    """
    storage_domain_name = kwargs.pop('storagedomain', None)

    # Tuple (lun_address, lun_target, lun_id, lun_port)
    lun = (kwargs.pop('lun_address', None), kwargs.pop('lun_target', None),
           kwargs.pop('lun_id', None), kwargs.pop('lun_port', 3260))
    # Tuple (username, password)
    lun_creds = (kwargs.pop('lun_username', None),
                 kwargs.pop('lun_password', None))
    type_ = kwargs.pop('type_', None)

    storage_connection = kwargs.pop('storage_connection', None)

    if lun != (None, None, None, 3260) and storage_connection:
        logger.error(
            "You cannot set storage connection id and LUN params in one call!")
        return None

    disk = data_st.Disk(**kwargs)

    if storage_connection is not None:
        storage = data_st.Storage()
        storage.id = storage_connection
        disk.set_lun_storage(storage)

    if storage_domain_name is not None:
        storage_domain = STORAGE_DOMAIN_API.find(storage_domain_name,
                                                 NAME_ATTR)
        storage_domains = data_st.StorageDomains()
        storage_domains.add_storage_domain(storage_domain)
        disk.storage_domains = storage_domains

    # quota
    quota_id = kwargs.pop('quota', None)
    if quota_id == '':
        disk.set_quota(data_st.Quota())
    elif quota_id:
        disk.set_quota(data_st.Quota(id=quota_id))

    if lun != (None, None, None, 3260):
        direct_lun = data_st.LogicalUnit(address=lun[0], target=lun[1],
                                         id=lun[2], port=lun[3])
        if lun_creds != (None, None):
            direct_lun.set_username(lun_creds[0])
            direct_lun.set_password(lun_creds[1])

        disk.set_lun_storage(data_st.Storage(logical_unit=[direct_lun],
                                             type_=type_))

    # id
    disk_id = kwargs.pop('id', None)
    if disk_id:
        disk.set_id(disk_id)

    # active
    active = kwargs.pop('active', None)
    if active:
        disk.set_active(active)

    # snapshot
    snapshot = kwargs.pop('snapshot', None)
    if snapshot:
        disk.set_snapshot(snapshot)

    return disk


@is_action()
def addDisk(positive, **kwargs):
    """
    Description: Adds disk to setup
    Parameters:
        * alias - name of the disk
        * provisioned_size - size of the disk
        * interface - IDE or virtio
        * format - raw or cow
        * size - size of the disk
        * sparse - True or False whether disk should be sparse
        * bootable - True or False whether disk should be bootable
        * shareable - True or False whether disk should be sharable
        * allow_snapshot - True or False whether disk should allow snapshots
        * propagate_errors - True or False whether disk should propagate errors
        * wipe_after_delete - True or False whether disk should wiped after
                              deletion
        * storagedomain - name of storage domain where disk will reside
        * lun_address - iscsi server address for direct lun
        * lun_target - iscsi target for direct lun
        * lun_id - direct lun's id
        * quota - disk quota
        * storage_connection - in case of direct LUN - existing storage
                               connection to use instead of creating a new one
        You cannot set both storage_connection and lun_* in one call!
    Author: jlibosva
    Return: True - if positive and successfully added or not positive and not
                   added successfully
            False - if positive but failed to add or not positive but added
    """
#    kwargs.update(add=True)
    disk = _prepareDiskObject(**kwargs)
    disk, status = DISKS_API.create(disk, positive)
    return status, {'diskId': disk.get_id()
                    if disk and not isinstance(disk, Fault) else None}


@is_action()
def updateDisk(positive, **kwargs):
    """
    Description: Update already existing disk
    Parameters:
        * alias - name of current disk
        * name - new name of the disk
        * provisioned_size - size of the disk
        * interface - IDE or virtio
        * format - raw or cow
        * size - size of the disk
        * sparse - True or False whether disk should be sparse
        * bootable - True or False whether disk should be bootable
        * shareable - True or False whether disk should be sharable
        * allow_snapshot - True or False whether disk should allow snapshots
        * propagate_errors - True or False whether disk should propagate errors
        * wipe_after_delete - True or False whether disk should wiped after
                              deletion
        * storagedomain - name of storage domain where disk will reside
        * quota - disk quota
        * storage_connection - in case of direct LUN - existing storage
                               connection to use instead of creating a new one
        You cannot set both storage_connection and lun_* in one call!
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    diskObj = DISKS_API.find(kwargs.pop('alias'))
    newDisk = _prepareDiskObject(**kwargs)
    newDisk, status = DISKS_API.update(diskObj, newDisk, positive)
    return status


@is_action()
def deleteDisk(positive, alias, async=True):
    """
    Description: Removes disk from system
    Parameters:
        * alias - name of disk
        * async - whether the task should be asynchronous
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    diskObj = DISKS_API.find(alias)

    # TODO: add async parameter to delete method once it's supported
    status = DISKS_API.delete(diskObj, positive)
    return status


@is_action('attachDiskToVm')
def attachDisk(positive, alias, vmName, active=True):
    """
    Description: Attach disk to VM
    Parameters:
        * alias - disk to attach
        * vmName - vm attaching disk to
        * active - if disk should be activated after attaching
    Author: jlibosva
    Return: Status of the operation dependent on positive value
    """
    diskObj = DISKS_API.find(alias)
    diskObj.active = active
    vmDisks = getObjDisks(vmName)
    diskObj, status = DISKS_API.create(diskObj, positive, collection=vmDisks)
    return status


@is_action('detachDiskFromVm')
def detachDisk(positive, alias, vmName, detach=True):
    """
    Description: Detach disk from VM
    Parameters:
        * alias - disk to detach
        * vmName - vm from which disk will be detached
    Author: jlibosva
    Return: Status of the operation dependent on positive value
    Exceptions: EntityNotFound when disk is not found
    """
    diskObj = getVmDisk(vmName, alias)
    body = data_st.Action(detach=detach)

    return DISKS_API.delete(
        diskObj, positive, body=body, element_name='action')


@is_action()
def waitForDisksState(disksNames, status=ENUMS['disk_state_ok'],
                      timeout=DEFAULT_DISK_TIMEOUT, sleep=10):
    """
    Description: Waits till all disks are in the given state
    Parameters:
        * disksNames - string containing disks' names separated by comma
        * status - desired state
        * timeout - timeout how long should we wait
        * sleep - polling interval
    Author: jlibosva
    Return: True if state was reached on all disks, False otherwise
    """
    if isinstance(disksNames, types.StringTypes):
        disksNames = split(disksNames)

    [DISKS_API.find(disk) for disk in disksNames]

    sampler = TimeoutingSampler(timeout, sleep, DISKS_API.get, absLink=False)

    try:
        for sample in sampler:
            disks_in_wrong_state = [
                x for x in sample
                if x.name in disksNames and x.status.state != status]
            if not disks_in_wrong_state:
                return True
    except APITimeout:
        logger.error(
            "Timeout when waiting for all the disks %s in %s state" % (
                disksNames, status))
        return False


@is_action()
def waitForDisksGone(positive, disksNames, timeout=DEFAULT_DISK_TIMEOUT,
                     sleep=10):
    """
    Description: Waits until disks are still in system
    Author: jlibosva
    Parameters:
        * disksNames - comma separated list of disks
        * timeout - how long it should wait
        * sleep - how often it should poll the state
    Return: True if disks are gone before timeout runs out, False otherwise
    """
    return waitUntilGone(positive, disksNames, DISKS_API, timeout, sleep)


@is_action()
def compareDisksCount(name, expected_count, is_template=False):
    """
    Description: Compares counts of disks attached to given VM/template
    Author: jlibosva
    Parameters:
        * name - name of object you want disks from
        * expected_count - expected count of attached disks
    Return: expected_count == count_of_disks(name)
    """
    disks = getObjDisks(name, is_template=is_template, get_href=False)
    return len(disks) == expected_count


@is_action()
def checkDiskExists(positive, name):
    """
    Description: Checks that disk is in system
    Author: jlibosva
    Parameters:
        * positive - whether disk should exist or not
        * name - name of the disk
    Return: True if disk is found, False otherwise
    """
    try:
        DISKS_API.find(name)
    except EntityNotFound:
        return not positive
    return positive


@is_action()
def move_disk(disk_name, source_domain, target_domain, wait=True,
              timeout=DEFAULT_DISK_TIMEOUT, sleep=10):
    """
    Description: Moves disk from source_domain to target_domain
    WARNING: does not work at the moment - remove this comment once it works
    Author: gickowic
    Parameters:
        * disk_name - name of disk to move
        * source domain - name of the domain disk is currently on
        * target_domain - name of the domain to move the disk to
        * wait - wait for disk to be status 'ok' before returning
        * timeout - how long to wait for disk status (if wait=True)
        * sleep - how long to wait between checks when waiting for disk status
    """
    #TODO: This feature does not work, being implemented, BZ#911348
    sd = STORAGE_DOMAIN_API.find(target_domain)
    disk = DISKS_API.find(disk_name)
    DISKS_API.logger.info('Disk found: %s', disk)

    if not DISKS_API.syncAction(disk, 'move', storage_domain=sd,
                                positive=True):
        raise DiskException(
            "Failed to move disk %s from domain %s to storage domain %s" %
            (source_domain, disk_name, target_domain))
    if wait:
        for disk in TimeoutingSampler(timeout, sleep, getStorageDomainDisks,
                                      target_domain):
            if disk.name == disk_name and \
                    disk.status.state == ENUMS['disk_state_ok']:
                return


def checksum_disk(hostname, user, password, disk_object, dc_obj):
    """
    Checksum disk
    Author: ratamir
    Parameters:
        * hostname - name of host
        * user - user name for host
        * password - password for host
        * disk_object - disk object that need checksum
        * dc_obj - data center that the disk belongs to
    Return:
        Checksum output, or raise exception otherwise
    """
    host_machine = Machine(host=hostname, user=user,
                           password=password).util('linux')

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sd = STORAGE_DOMAIN_API.find(sd_id, attribute='id')
    sp_id = dc_obj.get_id()
    block = sd.get_type() in BLOCK_DEVICES

    if block:
        host_machine.lv_change(sd_id, vol_id, activate=True)

    vol_path = host_machine.get_volume_path(sd_id, sp_id, image_id, vol_id)
    checksum = host_machine.checksum(vol_path)

    if block:
        host_machine.lv_change(sd_id, vol_id, activate=False)

    return checksum
