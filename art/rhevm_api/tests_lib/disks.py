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
import time

from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api, split
from art.rhevm_api.utils.xpath_utils import XPathMatch
from utilities.utils import readConfFile

GBYTE = 1024**3
ELEMENTS = os.path.join(os.path.dirname(__file__), '../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEFAULT_DISK_TIMEOUT=180

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
xpathMatch = XPathMatch(VM_API)


def getVmDisks(vmName, get_href=True):
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
    vmObj = VM_API.find(vmName)
    return DISKS_API.getElemFromLink(vmObj, get_href=get_href)


def getVmDisk(vmName, diskName):
    """
    Description: Returns disk from VM's collection
    Parameters:
        * vmName - name of VM
        * diskName - name of disk
    Author: jlibosva
    Return: Disk from VM's collection
    """
    vmObj = VM_API.find(vmName)
    return DISKS_API.getElemFromElemColl(vmObj, diskName)


def _prepareDiskObject(**kwargs):
    """
    Description: Prepare disk object according kwargs
    Parameters:
        * diskName - name of the disk
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
    Author: jlibosva
    Return: Disk object
    """
    # Change size to provisioned_size
    disk = data_st.Disk(name=kwargs.pop('name', None),
                        size=kwargs.pop('size', None),
                        interface=kwargs.pop('interface', None),
                        format=kwargs.pop('format', None),
                        provisioned_size=kwargs.pop('provisioned_size', None),
                        sparse=kwargs.pop('sparse', None),
                        bootable=kwargs.pop('bootable', None),
                        shareable=kwargs.pop('shareable', None),
                        allow_snapshot=kwargs.pop('allow_snapshot', None),
                        propagate_errors=kwargs.pop('propagate_errors', None),
                        wipe_after_delete=kwargs.pop('wipe_after_delete', None),
           )

    storage_domain_name = kwargs.pop('storagedomain', None)

    if storage_domain_name is not None:
        storage_domain =  STORAGE_DOMAIN_API.find(storage_domain_name,
                                                  NAME_ATTR)
        storage_domains = data_st.StorageDomains()
        storage_domains.add_storage_domain(storage_domain)
        disk.storage_domains = storage_domains

    return disk


def addDisk(positive, **kwargs):
    """
    Description: Adds disk to setup
    Parameters:
        * diskName - name of the disk
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
    Author: jlibosva
    Return: True - if positive and successfully added or not positive and not
                   added successfully
            False - if positive but failed to add or not positive but added
    """
    kwargs.update(add=True)
    kwargs.update(name=kwargs.get('diskName', None))
    disk = _prepareDiskObject(**kwargs)
    disk, status = DISKS_API.create(disk, positive)
    return status, { 'diskId' : disk.get_id() }


def updateDisk(positive, diskName, **kwargs):
    """
    Description: Update already existing disk
    Parameters:
        * diskName - name of current disk
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
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    diskObj = DISKS_API.find(diskName)
    newDisk = _prepareDiskObject(**kwargs)
    newDisk, status = DISKS_API.update(diskObj, newDisk, positive)
    return status


def deleteDisk(positive, diskName, async=True):
    """
    Description: Removes disk from system
    Parameters:
        * diskName - name of disk
        * async - whether the task should be asynchronous
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    diskObj = DISKS_API.find(diskName)

    # TODO: add async parameter to delete method once it's supported
    status = DISKS_API.delete(diskObj, positive)
    return status


def attachDisk(positive, diskName, vmName, active=True):
    """
    Description: Attach disk to VM
    Parameters:
        * diskName - disk to attach
        * vmName - vm attaching disk to
        * active - if disk should be activated after attaching
    Author: jlibosva
    Return: Status of the operation dependent on positive value
    """
    diskObj = DISKS_API.find(diskName)
    diskObj.active = active

    vmDisks = getVmDisks(vmName)
    diskObj, status = DISKS_API.create(diskObj, positive, collection=vmDisks)

    return status


def detachDisk(positive, diskName, vmName, detach=True):
    """
    Description: Detach disk from VM
    Parameters:
        * diskName - disk to detach
        * vmName - vm from which disk will be detached
    Author: jlibosva
    Return: Status of the operation dependent on positive value
    """
    diskObj = getVmDisk(vmName, diskName)
    body = data_st.Action(detach=detach)

    return DISKS_API.delete(diskObj, positive, body=body, element_name='action')


def waitForDisksState(disksNames, status=ENUMS['disk_state_ok'], timeout=DEFAULT_DISK_TIMEOUT, sleep=10):
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
    names = split(disksNames)
    [DISKS_API.find(disk) for disk in names]

    query = ' and '.join(['alias="%s" and status=%s' % (name, status) for name in
                          names])
    return DISKS_API.waitForQuery(query, timeout=timeout, sleep=sleep)


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
    disks = split(disksNames)
    start = time.time()
    query = ' or '.join(["name=%s" % disk for disk in disks])
    while timeout > time.time() - start and timeout > 0:
        time.sleep(sleep) # Sleep first due to rhevm slowness
        found = DISKS_API.query(query)
        if not found:
            return positive

    logger.error("Remaining disks: %s" % [disk.name for disk in found])
    return not positive


