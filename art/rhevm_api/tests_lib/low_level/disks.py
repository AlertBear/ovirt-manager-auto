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
from utilities.machine import Machine
import random
from art.core_api.apis_exceptions import EntityNotFound, APITimeout
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.data_struct.data_structures import Disk, Fault
from art.rhevm_api.tests_lib.low_level.datacenters import get_sd_datacenter
from art.rhevm_api.tests_lib.low_level.general import prepare_ds_object
from art.rhevm_api.utils.test_utils import get_api, waitUntilGone, split
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEFAULT_DISK_TIMEOUT = 180
DEFAULT_SLEEP = 5

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

logger = logging.getLogger("art.ll_lib.disks")
BLOCK_DEVICES = [ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp']]

FORMAT_COW = ENUMS['format_cow']
FORMAT_RAW = ENUMS['format_raw']
VIRTIO = ENUMS['interface_virtio']
VIRTIO_SCSI = ENUMS['interface_virtio_scsi']


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


def getVmDisk(vmName, alias=None, disk_id=None):
    """
    Description: Returns disk from VM's collection
    Parameters:
        * vmName - name of VM
        * alias - name of disk
    Author: jlibosva
    Return: Disk from VM's collection
    """
    value = None
    vmObj = VM_API.find(vmName)
    if disk_id:
        prop = "id"
        value = disk_id
    elif alias:
        prop = "name"
        value = alias
    else:
        raise EntityNotFound("No disk identifier or name was provided")
    return DISKS_API.getElemFromElemColl(vmObj, value, prop=prop)


def getTemplateDisk(template_name, alias):
    """
    Description: Returns disk from template collection
    Parameters:
        *  template_name - name of template
        * alias - name of disk
    Return: Disk from template collection
    """
    template_obj = TEMPLATE_API.find(template_name)
    return DISKS_API.getElemFromElemColl(template_obj, alias)


def get_disk_obj(disk_alias, attribute='name'):
    """
    Returns disk object from disks' collection

    __author__ = "ratamir"
    :param disk_alias: Name of disk
    :type disk_alias: str
    :param attribute: The key to use for finding disk object ('id', 'name')
    :type attribute:str
    :return: Disk from disks collection
    :rtype: Disk object
    """
    return DISKS_API.find(disk_alias, attribute=attribute)


def _prepareDiskObject(**kwargs):
    """
    Prepare or update disk object according to its kwargs

    __author__ = jlibosva
    :param alias: Name of the disk
    :type alias: str
    :param description: Description of the disk
    :type description: str
    :param provisioned_size: Size of the disk
    :type provisioned_size: int
    :param interface: IDE or virtio or virtio-scsi
    :type interface: str
    :param format: raw or cow
    :type format: str
    :param sparse: True if disk should be sparse, False otherwise
    :type sparse: bool
    :param bootable: True if disk should be marked as bootable, False otherwise
    :type bootable: bool
    :param shareable: True if disk should be marked as shareable,
        False otherwise
    :type shareable: bool
    :param allow_snapshot: True if disk should allow snapshots, False otherwise
    :type allow_snapshot: bool
    :param propagate_errors: True if disk should allow errors to propagate,
        False otherwise
    :type propagate_errors: bool
    :param wipe_after_delete: True if disk should be wiped after deletion,
        False otherwise
    :type wipe_after_delete: bool
    :param storagedomain: Name of storage domain where disk will reside
    :type storagedomain: str
    :param quota: Disk quota
    :type quota: str
    :param storage_connection: In the case of a direct LUN, the existing
        storage connection will be used (instead of creating a new one).
        Note that you cannot set both this parameter and lun_* in the same call
    :type storage_connection: str
    :param active: True if the disk should be activated after being attached to
        VM, False otherwise
    :type active: bool
    :param id: The ID of a disk that will be updated
    :type id: str
    :param read_only: True if disk should be marked as read-only,
        False otherwise
    :type read_only: bool
    :param snapshot: Snapshot object of the disk
    :type snapshot: snapshot object
    :param update: Disk object to update with the kwargs
    :type update: disk object
    :return: Disk object with the updated kwargs
    :rtype: Disk object
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

    disk = kwargs.pop('update', None)
    if disk is None:
        disk = data_st.Disk(**kwargs)

    if storage_connection is not None:
        storage = data_st.HostStorage()
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

        logical_units = data_st.LogicalUnits(logical_unit=[direct_lun])
        disk.set_lun_storage(
            data_st.HostStorage(logical_units=logical_units, type_=type_)
        )

    # id
    disk_id = kwargs.pop('id', None)
    if disk_id:
        disk.set_id(disk_id)

    # read_only
    read_only = kwargs.pop('read_only', None)
    if read_only is not None:
        disk.set_read_only(read_only)

    # active
    active = kwargs.pop('active', None)
    if active is not None:
        disk.set_active(active)

    # snapshot
    snapshot = kwargs.pop('snapshot', None)
    if snapshot:
        disk.set_snapshot(snapshot)

    # description
    description = kwargs.pop('description', None)
    if description is not None:
        disk.set_description(description)

    return disk


def addDisk(positive, **kwargs):
    """
    Description: Adds disk to setup
    Parameters:
        * alias - name of the disk
        * description - description of the disk
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
        * active - True or False whether disk should be automatically activated
        * sgio - 'unfiltered' in case a direct LUN should be with pass-through
        capabilities or 'filtered' or None if not
        You cannot set both storage_connection and lun_* in one call!
    Author: jlibosva
    Return: True - if positive and successfully added or not positive and not
                   added successfully
            False - if positive but failed to add or not positive but added
    """
    disk = _prepareDiskObject(**kwargs)
    logger.info("Adding disk %s", disk.get_alias())
    disk, status = DISKS_API.create(disk, positive)
    return status, {'diskId': disk.get_id() if (disk and not isinstance(
        disk, Fault)) else None}


def updateDisk(positive, **kwargs):
    """
    Description: Update already existing disk
    Parameters:
        * vmName - mandatory, will find the disk from the VM name
        * alias - name of current disk or new alias if id is provided
        * id - id of the current disk
        * description - description for the current disk
        * provisioned_size - size of the disk
        * interface - IDE or virtio
        * format - raw or cow
        * sparse - True or False whether disk should be sparse
        * bootable - True or False whether disk should be bootable
        * shareable - True or False whether disk should be sharable
        * allow_snapshot - True or False whether disk should allow snapshots
        * propagate_errors - True or False whether disk should propagate errors
        * wipe_after_delete - True or False whether disk should wiped after
                              deletion
        * read_only - True if disk should be read only, False otherwise
        * storagedomain - name of storage domain where disk will reside
        * quota - disk quota
        * storage_connection - in case of direct LUN - existing storage
                               connection to use instead of creating a new one
        * active - True or False whether disk should be automatically activated
        You cannot set both storage_connection and lun_* in one call!
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    vm_name = kwargs.pop('vmName', None)
    if not vm_name:
        raise TypeError("Parameter vmName is needed to update the disk")
    disk_id = kwargs.pop('id', None)
    alias = kwargs.get('alias', None)
    if disk_id:
        disk_object = getVmDisk(vmName=vm_name, disk_id=disk_id)
    elif alias:
        disk_object = getVmDisk(vmName=vm_name, alias=alias)

    new_disk_object = _prepareDiskObject(**kwargs)
    new_disk_object, status = DISKS_API.update(disk_object, new_disk_object,
                                               positive)
    return status


def deleteDisk(positive, alias=None, async=True, disk_id=None):
    """
    Removes disk from system

    :param positive: Specifies whether the delete disk call should succeed
    :type positive: bool
    :param alias: Name of disk
    :type alias: str
    :param async: True if operation should be asynchronous - NOT SUPPORTED
    :type async: bool
    :param disk_id: The Disk ID to be used for deletion
    :type disk_id: str
    :return: Status of the operation's result dependent on positive value
    :rtype: bool
    """
    disk_obj = DISKS_API.find(disk_id, attribute='id') if disk_id else (
        DISKS_API.find(alias)
    )
    # TODO: add async parameter to delete method once it's supported
    status = DISKS_API.delete(disk_obj, positive)
    return status


def attachDisk(
        positive, alias, vm_name, active=True, read_only=False, disk_id=None
):
    """
    Attach disk to VM

    :param positive: Specifies whether the attach disk call should succeed
    (positive=True) or fail (positive=False)
    :type positive: bool
    :param alias: The name of the disk to attach
    :type alias: str
    :param vmName: VM name to attach the disk to
    :type vmName: str
    :param active: Specifies whether disk should be activated after being
    attached to VM
    :type active: bool
    :param read_only: Specifies whether disk should be marked as read-only
    :type read_only: bool
    :return: Status of the operation based on the input positive value
    on positive value
    :rtype: bool
    """
    disk_object = DISKS_API.find(disk_id, attribute='id') if disk_id else (
        DISKS_API.find(alias)
    )
    updated_disk = _prepareDiskObject(
        update=disk_object, active=active, read_only=read_only
    )

    vm_disks = getObjDisks(vm_name)
    logger.info("Attaching disk %s to vm %s", alias, vm_name)
    return DISKS_API.create(updated_disk, positive, collection=vm_disks)[1]


def detachDisk(positive, alias, vmName):
    """
    Detach disk from VM

    :param positive: Specifies whether the detach disk call should succeed
    (positive=True) or fail (positive=False)
    :type positive: bool
    :param alias: Disk to detach
    :type alias: str
    :param vmName: VM from which disk will be detached
    :type vmName: str
    :returns: True/False of the operation dependent on positive value
    """
    disk_object = getVmDisk(vmName, alias)
    logger.info("Detaching disk %s from vm %s", alias, vmName)
    return DISKS_API.delete(disk_object, positive)


def wait_for_disks_status(disks, key='name', status=ENUMS['disk_state_ok'],
                          timeout=DEFAULT_DISK_TIMEOUT, sleep=DEFAULT_SLEEP):
    """ Description: Waits until all disks reached the requested status
    :param disks: list of disk names/ids to poll on their status
    :type disks: list
    :param key: key to look for disks by, it can be name or id
    :type key: str
    :param status: state of disks disk_state_{ok, locked, illegal, invalid}
    :type status: str
    :param timeout: Maximum time to poll for disks to reach the requested state
    :type timeout: int
    :param sleep: polling interval
    :type sleep: int
    :return: True if disks reach the requested status, False otherwise
    :rtype: bool
    """
    if isinstance(disks, basestring):
        # 'vm1, vm2' -> [vm1, vm2]
        disks_list = split(disks)
    else:
        disks_list = disks

    logger.info("Waiting for status %s on disks %s", status, disks_list)
    sampler = TimeoutingSampler(timeout, sleep, DISKS_API.get, absLink=False)
    is_incorrect_state = lambda d, s: (d.get_status() != s)  # flake8: noqa
    try:
        for sample in sampler:
            disks_in_wrong_status = []
            for disk_obj in sample:
                if key == 'name':
                    disk_to_poll = disk_obj.get_name()
                elif key == 'id':
                    disk_to_poll = disk_obj.get_id()
                else:
                    logger.error("Can't poll with key: {0}".format(key))
                    break

                if disk_to_poll not in disks_list:
                    continue

                logger.debug(
                    "polling on disk: {0} for state: {1}".format(
                        disk_to_poll, status
                    )
                )
                if is_incorrect_state(disk_obj, status):
                    disks_in_wrong_status.append(disk_obj)

            if not disks_in_wrong_status:
                return True

    except APITimeout:
        logger.error(
            "Timeout when waiting for all the disks {0} in {1} state".format(
                disks, status
            )
        )
        return False

    return False


def waitForDisksGone(positive, disksNames, timeout=DEFAULT_DISK_TIMEOUT,
                     sleep=DEFAULT_SLEEP):
    """
    Description: Waits until disks are still in system
    Author: jlibosva
    Parameters:
        * disksNames - comma separated list of disks
        * timeout - how long it should wait
        * sleep - how often it should poll the state
    Return: True if disks are gone before timeout runs out, False otherwise
    """
    return waitUntilGone(
        positive, disksNames, DISKS_API, timeout, sleep, search_by='alias'
    )


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


def checkDiskExists(positive, disk, attr='name'):
    """
    Checks that disk is in system

    __author__ = 'jlibosva'
    :param positive: Determines whether the disk should exist
    :type positive: bool
    :param disk: Name or ID of the disk
    :type disk: str
    :param attr: The attribute to use for finding disk object ('id', 'name')
    :type attr: str
    :return: True if the disk is found, False otherwise
    :rtype: bool
    """
    try:
        DISKS_API.find(disk, attr)
    except EntityNotFound:
        return not positive
    return positive


def copy_disk(**kwargs):
    """
    Description: Copy a disk to a target_domain
    """
    return do_disk_action('copy', **kwargs)


def move_disk(**kwargs):
    """
    Description: Moves a disk to a target_domain
    """
    return do_disk_action('move', **kwargs)


def do_disk_action(
        action, disk_name=None, target_domain=None, disk_id=None, wait=True,
        timeout=DEFAULT_DISK_TIMEOUT, sleep=10, positive=True,
        new_disk_alias=None
):
    """
    Executes an action (copy/move) on the disk
    __author__ = 'cmestreg'

    :param disk_name: name of disk
    :type disk_name: str
    :param disk_id: id of the disk
    :type disk_id: str
    :param target_domain: name of the domain
    :type target_domain: str
    :param wait: wait for disk to be status 'ok' before returning
    :type wait: bool
    :param timeout: how long to wait for disk status (if wait=True)
    :type timeout: int
    :param sleep: how long to wait between checks when waiting for disk status
    :type sleep: int
    :return: True on success/False on failure
    :rtype: bool
    """
    sd = STORAGE_DOMAIN_API.find(target_domain)
    if disk_id:
        disk = DISKS_API.find(disk_id, attribute='id')
    elif disk_name:
        disk = DISKS_API.find(disk_name)
    else:
        raise ValueError("Either specify disk_id or disk_name")

    DISKS_API.logger.info(
        "Disk found. name: %s id: %s", disk.get_alias(), disk.get_id()
    )
    updated_disk_alias = None
    if new_disk_alias and action == 'copy':
        logger.info(
            "Disk with current alias %s will be copied into a disk with "
            "alias %s", disk.get_alias(), new_disk_alias
        )
        updated_disk_alias = Disk(alias=new_disk_alias)

    if not DISKS_API.syncAction(
            disk, action, storage_domain=sd, positive=positive,
            disk=updated_disk_alias

    ):
        return False

    if wait and positive:
        # TODO: shouldn't it be possible to use a query here?
        for sample in TimeoutingSampler(
                timeout, sleep, getStorageDomainDisks, target_domain, False
        ):
            for target_disk in sample:
                if disk.get_id() == target_disk.get_id() and (
                        disk.get_status() == ENUMS['disk_state_ok']
                ):
                    return True
    return True


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


def get_all_disk_permutation(block=True, shared=False,
                             interfaces=(VIRTIO, VIRTIO_SCSI)):
    """
    Description: Get all disks interfaces/formats/allocation policies
    permutations possible
    Author: ratamir, glazarov
    Parameters:
        * block - True if storage type is block, False otherwise
        * shared - True if disk is shared, False otherwise
        * interfaces - The list of interfaces to use in generating the disk
        permutations, default is (VIRTIO, VIRTIO_SCSI)
    Return: list of permutations stored in dictionary
    """
    permutations = []
    for disk_format in [FORMAT_COW, FORMAT_RAW]:
        for interface in interfaces:
            for sparse in [True, False]:
                if disk_format is FORMAT_RAW and sparse and block:
                    continue
                if disk_format is FORMAT_COW and not sparse:
                    continue
                if shared and disk_format is FORMAT_COW:
                    continue
                if not sparse and not block:
                    continue
                permutation = {'format': disk_format,
                               'interface': interface,
                               'sparse': sparse,
                               }
                permutations.append(permutation)
    return permutations


def check_disk_visibility(disk, disks_list):
    """
    Check if disk is in vm disks collection
    Author: ratamir
    Parameters:
        * disk - alias of disk that need to checked
        * disks_list - collection of disks objects
    Return: True if ok, or False otherwise
    """
    is_visible = disk in [disk_obj.get_alias() for disk_obj in
                          disks_list if disk_obj.get_active()]
    return is_visible


def get_other_storage_domain(
    disk, vm_name=None, storage_type=None, force_type=True,
    ignore_type=[], key='name'
):
    """
    Choose a random, active data storage domain from the available list of
    storage domains (ignoring the storage domain on which the disk is found)

    __author__ = "ratamir"

    :param disk: Disk name/ID
    :type disk: str
    :param vm_name: In case of a non-floating disk, name of vm that contains
                    the disk
    :type vm_name: str
    :param storage_type: If provided, only return the storage domain of the
                         specified type
    :type storage_type: str
    :param force_type: Return only the storage domain of the same device type
                       (file or block)
    :type force_type: bool
    :param ignore_type: List of storage types to ignore (e.g. ignore
                        GlusterFS for shared disks)
    :type ignore_type: list
    :param key: Key to look for disks by, it can be name or ID
    :type key: str
    :returns: Name of a storage domain that doesn't contain the disk or empty
    string
    :rtype: str
    """
    logger.info(
        "Find the storage domain type that the disk %s is found on", disk
    )
    if vm_name:
        if key == 'id':
            disk = getVmDisk(vm_name, disk_id=disk)
        else:
            disk = getVmDisk(vm_name, disk)
    else:
        disk = DISKS_API.find(disk, key)

    disk_sd_id = disk.get_storage_domains().get_storage_domain()[0].get_id()
    disk_sd = STORAGE_DOMAIN_API.find(disk_sd_id, 'id')

    disk_sd_type = disk_sd.get_storage().get_type()
    logger.info(
        "Disk '%s' is using storage domain of type '%s'",
        disk.get_name(), disk_sd_type
    )
    dc = get_sd_datacenter(disk_sd.get_name())
    sd_list = []

    logger.info(
        "Searching for storage domain with %s type",
        "the same" if force_type else "a different"
    )
    for sd in STORAGE_DOMAIN_API.getElemFromLink(dc, get_href=False):
        if sd.get_id() != disk_sd_id and (
            sd.get_status() == ENUMS['storage_domain_state_active']) and (
            sd.get_type() == ENUMS['storage_dom_type_data']
        ):
            sd_type = sd.get_storage().get_type()
            if storage_type and storage_type != sd_type:
                continue
            if force_type and (disk_sd_type != sd_type):
                continue
            if not force_type and (disk_sd_type == sd_type):
                continue
            if sd_type in ignore_type:
                continue
            sd_list.append(sd.get_name())
    if sd_list:
        random_sd = random.choice(sd_list)
        logger.info(
            "Disk %s improper storage domain is: %s",
            disk.get_name(), random_sd,
        )
        return random_sd
    return None


def get_disk_storage_domain_name(disk_name, vm_name=None, template_name=None):
    """
    Gets the disk storage domain name

    __author__ = "ratamir"
    :param disk_name: Name of the disk
    :type disk_name: str
    :param vm_name: Name of the vm that contains disk.
    None if the disk is floating disk (will be searched in disks
    collection)
    :type vm_name: str
    :param template_name: Name of the template that contains disk
    None if the disk is floating disk (will be searched in disks
    collection)
    :type template_name: str
    :returns: Storage domain that contains the requested disk
    :rtype: str
    """
    if vm_name and template_name:
        logger.error(
            "Only one of the parameters vm_name or template_name "
            "should be provided"
        )
        return None

    logger.info("Get disk %s storage domain", disk_name)
    if vm_name is None and template_name is None:
        disk = DISKS_API.find(disk_name)
    elif vm_name is not None:
        disk = getVmDisk(vm_name, disk_name)
    else:
        disk = getTemplateDisk(template_name, disk_name)

    sd_id = disk.get_storage_domains().get_storage_domain()[0].get_id()
    disk_sd_name = STORAGE_DOMAIN_API.find(sd_id, 'id').get_name()
    logger.info("Disk %s storage domain is: %s", disk_name, disk_sd_name)
    return disk_sd_name


def get_disk_ids(disk_names):
    """
    gets the disks' storage domain ids

    :param disk_names: List of disks aliases
    :type disk_names: list
    :return: List of disks' id
    :rtype: list
    """
    return [get_disk_obj(disk_name).get_id() for disk_name in disk_names]


def export_disk_to_glance(
        positive, disk, target_domain, async=False, attr='id'
):
    """
    Export a disk to glance repository

    :param positive: Specifies whether the export image call should succeed
    :type positive: bool
    :param disk: Disk identifier according to attr parameter (id, name)
    :type disk: str
    :param target_domain: Name of the domain where to export the image to
    :type target_domain: str
    :param async: True if operation should be asynchronous
    :type async: bool
    :param attr: The key to use for finding disk object ('id', 'name')
    :type attr: str
    :return: Status of the operation's result dependent on positive value
    :rtype: bool
    """
    storage_domain = STORAGE_DOMAIN_API.find(target_domain)
    disk = DISKS_API.find(disk, attribute=attr)
    if not DISKS_API.syncAction(
        disk, 'export', storage_domain=storage_domain, positive=positive,
        async=async
    ):
        return False
    return True


def get_all_disks():
    """
    Get list of disk objects from API

    Returns:
        list: List objects
    """
    return DISKS_API.get(absLink=False)


def prepare_disk_attachment_object(disk_id, **kwargs):
    """
    Creates a disk attachment object

    :param disk_id: ID of the disk
    :type disk_id: str
    :param interface: Interface of the disk
    :type interface: str
    :param bootable: True if disk should be marked as bootable, False otherwise
    :type bootable: bool
    :return: DiskAttahcment object
    :rtype: data_st.DiskAtachment
    """
    disk_obj = prepare_ds_object("Disk", id=disk_id)
    return prepare_ds_object("DiskAttachment", disk=disk_obj, **kwargs)


def wait_for_disk_storage_domain(
    disk, storage_domain, key='id', timeout=600, interval=5
):
    """
    Samples a disk and waits until disk is found in the specific storage
    domain or until timeout is reached

    :param disk: name or id of the disk to be checked
    :type disk: str
    :param storage_domain: name of the storage domain in which we expect the
    disk to exist
    :type storage_domain: str
    :param key: Determines whether disk should be a name or an id of a disk
    :type key: str
    :param timeout: time to wait until stopping to sample SD
    :type timeout: int
    :param interval: inter between each sample of SD
    :type interval: int
    """
    disk_name = get_disk_obj(disk, key).get_name() if key == 'id' else disk
    for sample in TimeoutingSampler(
        timeout, interval, get_disk_storage_domain_name, disk_name
    ):
        if sample == storage_domain:
            return
