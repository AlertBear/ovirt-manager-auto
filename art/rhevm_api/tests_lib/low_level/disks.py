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
import random
import shlex
from art.core_api.apis_exceptions import EntityNotFound, APITimeout
from art.core_api.apis_utils import data_st, TimeoutingSampler
from art.rhevm_api.data_struct.data_structures import Disk, Fault
from art.rhevm_api.tests_lib.low_level.datacenters import get_sd_datacenter
from art.rhevm_api.tests_lib.low_level.general import (
    prepare_ds_object, generate_logs
)
from art.rhevm_api.utils.test_utils import get_api, waitUntilGone
from art.test_handler.settings import ART_CONFIG
from rrmngmnt.host import Host as HostResource
from rrmngmnt.user import User


ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEFAULT_DISK_TIMEOUT = 180
COPY_MOVE_DISK_TIMEOUT = 300
DEFAULT_SLEEP = 5

VM_API = get_api('vm', 'vms')
CLUSTER_API = get_api('cluster', 'clusters')
TEMPLATE_API = get_api('template', 'templates')
HOST_API = get_api('host', 'hosts')
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')
DISKS_API = get_api('disk', 'disks')
DISK_ATTACHMENTS_API = get_api('disk_attachment', 'diskattachments')
NIC_API = get_api('nic', 'nics')
SNAPSHOT_API = get_api('snapshot', 'snapshots')
TAG_API = get_api('tag', 'tags')
CDROM_API = get_api('cdrom', 'cdroms')
CONN_API = get_api('storage_connection', 'storageconnections')
DISK_SNAPSHOT_API = get_api('disk_snapshot', 'disk_snapshots')

logger = logging.getLogger("art.ll_lib.disks")
BLOCK_DEVICES = [ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp']]
FILE_DEVICES = [
    ENUMS['storage_type_gluster'], ENUMS['storage_type_nfs'],
    ENUMS['storage_type_ceph'], ENUMS['storage_type_posixfs']
]
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
    Returns given vm's/templates's disks collection href or list of disk
    objects

    :param name: Name of VM/Template
    :type name: str
    :param get_href: True means to return href link for rest or object for sdk
                     (DiskAttachments)
                     False means to return the list of objects -
                     [VmDisk, VmDisk, ...]
    :type get_href: bool
    :param is_template: True in case the provided name is from a template
    :type is_template: bool
    :returns: href link to diskattachments or list of disks
    """
    response = get_disk_attachments(
        name, 'template' if is_template else 'vm', get_href
    )
    if get_href:
        return response
    return get_disk_list_from_disk_attachments(response)


def getVmDisk(vmName, alias=None, disk_id=None):
    """
    Returns a Disk object from a disk attached to a vm
    Parameters:
        * vmName - name of VM
        * alias - name of disk
    Author: jlibosva
    Return: Disk from VM's collection
    """
    value = None
    if disk_id:
        prop = "id"
        value = disk_id
    elif alias:
        prop = "name"
        value = alias
    else:
        logger.error("No disk identifier or name was provided")
        return None
    return get_disk_obj_from_disk_attachment(
        get_disk_attachment(vmName, value, prop)
    )


def getTemplateDisk(template_name, alias):
    """
    Returns disk from template collection

    :param template_name: Name of the template
    :type template_name: str
    :param alias: Name of the disk
    :type alias: str
    :raises: EntityNotFound
    :returns: Disk obj
    """
    template_disks = getObjDisks(
        template_name, get_href=False, is_template=True
    )
    for template_disk in template_disks:
        if alias == template_disk.get_alias():
            return template_disk
    raise EntityNotFound(
        "Didn't find disk %s for template %s" % (alias, template_name)
    )


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
    :param qcow_version: Qcow disk version 'qcow2_v2' or 'qcow2_v3'
    :type qcow_version: str
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
    kwargs.pop('active', None)

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

    # snapshot
    snapshot = kwargs.pop('snapshot', None)
    if snapshot:
        disk.set_snapshot(snapshot)

    # description
    description = kwargs.pop('description', None)
    if description is not None:
        disk.set_description(description)

    # qcow_version
    qcow_version = kwargs.pop('qcow_version', None)
    if qcow_version:
        disk.set_qcow_version(qcow_version)

    return disk


@generate_logs()
def addDisk(positive, **kwargs):
    """
    Description: Adds disk to setup
    Parameters:
        * alias - name of the disk
        * description - description of the disk
        * provisioned_size - size of the disk
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
        * qcow_version - 'qcow2_v3' or 'qcow2_v2' whether disk version v2 or v3
    Author: jlibosva
    Return: Status of the operation's result dependent on positive value
    """
    vm_name = kwargs.pop('vmName', None)
    if not vm_name:
        raise TypeError("Parameter vmName is needed to update the disk")
    disk_id = kwargs.pop('id', None)
    alias = kwargs.get('alias', None)

    # Get the disk parameters and construct the disk object
    if disk_id:
        disk_object = getVmDisk(vmName=vm_name, disk_id=disk_id)
    elif alias:
        disk_object = getVmDisk(vmName=vm_name, alias=alias)

    # Disk Attachment properties
    interface = kwargs.pop('interface', None)
    bootable = kwargs.pop('bootable', None)
    active = kwargs.pop('active', None)
    disk_attachment_object = get_disk_attachment(
        vm_name, disk_object.get_id()
    )
    # Create the new disk object to be updated
    new_disk_object = _prepareDiskObject(**kwargs)
    new_disk_attachment_object = prepare_disk_attachment_object(
        disk_object.get_id(), interface=interface, bootable=bootable,
        disk=new_disk_object, active=active,
    )
    response, status = DISK_ATTACHMENTS_API.update(
        disk_attachment_object, new_disk_attachment_object, positive,
    )
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
    if not status and positive:
        logger.error("Failed to delete disk %s", alias)
    return status


def attachDisk(
    positive, alias, vm_name, active=True, read_only=False, disk_id=None,
    interface='virtio', bootable=None,
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
    :param interface: Interface of the disk (default virtio)
    :type interface: str
    :param bootable: True if disk should be marked as bootable, False otherwise
    :type bootable: bool
    :return: Status of the operation based on the input positive value
    on positive value
    :rtype: bool
    """
    if disk_id:
        name = disk_id
        attribute = 'id'
    else:
        name = alias
        attribute = 'name'
    disk_object = get_disk_obj(name, attribute)
    # This is only needed because for legacy reason we also want to modify
    # the read_only property when we attach a disk
    # Also for attaching a disk the active parameter is pass inside the disk
    # object
    updated_disk = _prepareDiskObject(
        id=disk_object.get_id(), read_only=read_only
    )
    vm_disks = getObjDisks(vm_name)
    logger.info("Attaching disk %s to vm %s", alias, vm_name)
    disk_attachment = prepare_disk_attachment_object(
        updated_disk.get_id(), interface=interface, bootable=bootable,
        disk=updated_disk, active=active
    )
    return DISK_ATTACHMENTS_API.create(
        disk_attachment, positive, collection=vm_disks
    )[1]


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
    logger.info("Detaching disk %s from vm %s", alias, vmName)
    disk_attachment = get_disk_attachment(vmName, alias, attr='name')
    return DISK_ATTACHMENTS_API.delete(disk_attachment, positive)


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
        disks_list = disks.replace(',', ' ').split()
    else:
        disks_list = disks

    logger.info("Waiting for status %s on disks %s", status, disks_list)
    sampler = TimeoutingSampler(timeout, sleep, DISKS_API.get, abs_link=False)
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
        timeout=COPY_MOVE_DISK_TIMEOUT, sleep=10, positive=True,
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
                        target_disk.get_status() == ENUMS['disk_state_ok']
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
    host_resource = HostResource(hostname)
    host_resource.users.append(User(user, password))

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sd = STORAGE_DOMAIN_API.find(sd_id, attribute='id')
    sp_id = dc_obj.get_id()
    block = sd.get_type() in BLOCK_DEVICES

    if block:
        host_resource.lvm.lvchange(sd_id, vol_id, activate=True)

    vol_path = host_resource.executor().run_cmd(
        shlex.split("lvs -o path | grep %s" % vol_id)
    )[1]
    checksum = host_resource.executor().run_cmd(
        shlex.split("md5sum %s" % vol_path)
    )[1]

    if block:
        host_resource.lvm.lvchange(sd_id, vol_id, activate=False)

    return checksum


def get_all_disk_permutation(
    block=True, shared=False, interfaces=(VIRTIO, VIRTIO_SCSI)
):
    """
    Get all disks interfaces/formats/allocation policies permutations possible

    Args:
        block (bool): True if storage type is block, False otherwise
        shared (bool): True if disk is shared, False otherwise
        interfaces (list): The disks interfaces for permutations.

    Returns:
        list: Each permutation is stored in a dictionary which is one element
            in the list
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
    is_visible = disk in [disk_obj.get_alias() for disk_obj in disks_list]
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

    # Make sure that the func return sd from different kind file <-> block
    device_type = (
        FILE_DEVICES if disk_sd_type in FILE_DEVICES else BLOCK_DEVICES
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
            if not force_type and (sd_type in device_type):
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
    return DISKS_API.get(abs_link=False)


def prepare_disk_attachment_object(disk_id=None, **kwargs):
    """
    Creates a disk attachment object

    :param disk_id: ID of the disk
    :type disk_id: str
    :param active: True if disk should be activate, False otherwise
    :type active: bool
    :param bootable: True if disk should be marked as bootable, False otherwise
    :type bootable: bool
    :param disk: A Disk object to update
    :type disk: Disk object
    :param interface: Interface of the disk
    :type interface: str
    :return: DiskAttahcment object
    :rtype: data_st.DiskAtachment
    """
    disk = kwargs.pop("disk", None)
    disk_obj = disk if disk else prepare_ds_object("Disk", id=disk_id)
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


def get_disk_obj_from_disk_attachment(disk_attachment):
    """
    Return disk obj from disk attachment obj

    :param disk_attachment: disk attachment obj
    :type disk_attachment: DiskAttachment
    :returns: Disk object
    :rtype: Disk object
    """
    return get_disk_obj(disk_attachment.get_id(), 'id')


def get_disk_list_from_disk_attachments(disk_attachments):
    """
    Return disk obj list from disk attachments list

    :param disk_attachments: disk attachment objs
    :type disk_attachments: list
    :returns: list of Disk objects
    :rtype: list
    """
    return [
        get_disk_obj_from_disk_attachment(disk_attachment) for
        disk_attachment in disk_attachments
    ]


def get_disk_attachments(name, object_type='vm', get_href=False):
    """
    Get disk attachments objects or hrefs from a vm or template

    :param name: Name of the vm or template
    :type name: str
    :param object_type: If the object is a vm or a template
    :type object_type: str
    :param get_href: True if function should return the href to the objects,
    False if it should return list of DiskAttachment objects
    :type get_href: bool
    :returns: List of disk attachment objects or href
    :rtype: list
    """
    api = get_api(object_type, "%ss" % object_type)
    obj = api.find(name)
    return DISK_ATTACHMENTS_API.getElemFromLink(obj, get_href=get_href)


def get_disk_attachment(name, disk, attr='id', object_type='vm'):
    """
    Returns a disk attachment object

    :param name: Name of the vm or template
    :type name: str
    :param disk: Disk name or ID
    :type disk: str
    :param attr: Attribute to identify the disk, 'id' or 'name'
    :type attr: str
    :param object_type: If parameter name is a vm or a template
    :type object_type: str
    :returns: Disk attachment object
    :rtype: Disk attachment object
    """
    disk_list = get_disk_attachments(name, object_type=object_type)
    disk_id = None
    if attr == 'name' or attr == 'alias':
        for disk_obj in disk_list:
            disk_obj_alias = get_disk_obj(
                disk_obj.get_id(), attribute='id'
            ).get_alias()
            if disk_obj_alias == disk:
                disk_id = disk_obj.get_id()
                break
    elif attr == 'id':
        disk_id = disk

    for disk in disk_list:
        if disk.get_id() == disk_id:
            return disk
    return None


def get_non_ovf_disks():
    """
    Get all disks in the system except the OVF store disks
    Returns:
        list: List of disks that are not OVF_STORE
    """
    return [
        d.get_id() for d in get_all_disks() if (
            d.get_alias() != ENUMS['ovf_disk_alias']
        )
    ]


def get_qcow_version_disk(disk_name, attribute='name'):
    """
    Get the qcow_version info from disk name or id

    Arguments:
        disk_name (str): The name of the disk
        attribute (str): The key to use for finding disk object ('id', 'name')

    Returns:
        str: Qcow value - 'qcow2_v2' or 'qcow2_v3'
    """
    return get_disk_obj(disk_name, attribute).get_qcow_version()


def get_snapshot_disks_by_snapshot_obj(snapshot):
    """
    Return the disks contained in a snapshot

    Args:
        snapshot (Snapshot Object): Object of the snapshot to extract the
            disks from
    Returns:
        List: List of disks, or raise EntityNotFound exception
    """
    return DISKS_API.getElemFromLink(snapshot)


def get_storage_domain_diskssnapshots_objects(storagedomain, get_href=False):
    """
    Returns all disksnapshots objects list in the given storage domain

    Arguments:
        storagedomain (str): Name of the storage domain
        get_href (bool): True if function should return href to objects,
            False if it should return list of snapshot disks objects

    Returns:
        list: Snapshot disks objects list
    """
    from art.rhevm_api.tests_lib.low_level.storagedomains import (
        get_storage_domain_obj
    )
    storage_domain_object = get_storage_domain_obj(storagedomain)
    return DISK_SNAPSHOT_API.getElemFromLink(
        storage_domain_object,
        link_name='disksnapshots',
        attr='disk_snapshot',
        get_href=get_href,
    )


@generate_logs()
def get_read_only(vm_name, disk_id):
    """
    Check if certain disk is attached to VM as Read Only

    Args:
        vm_name (str): Name of the VM the disk is attached to
        disk_id (str): ID of the disk

    Returns:
        bool: True if the disk is Read Only, False otherwise
    """
    return get_disk_attachment(vm_name, disk_id).get_read_only()


def wait_for_sparsify_event(disk_id, success=True):
    """
    Wait for an event of successful/failed sparsify event starting from the
    last start sparsify event in the system.

    Args:
        disk_id (str): Disk id

    Returns:
         bool: True if an event of sparsify action completion was issued after
            The event of the action's start was issued and within event
            timeout, False otherwise.
    """
    import art.rhevm_api.tests_lib.low_level.events as ll_events
    disk_name = get_disk_obj(disk_alias=disk_id, attribute='id').get_name()
    start_sparsify_query = "\"Started to sparsify %s\"" % disk_name
    finished_sparsify_query = (
        "%s sparsified successfully" % disk_name if success else
        "Failed to sparsify %s" % disk_name
    )
    last_event_id = ll_events.get_max_event_id(start_sparsify_query)
    return ll_events.wait_for_event(
        query=finished_sparsify_query, start_id=last_event_id
    )


@generate_logs()
def sparsify_disk(disk_id, storage_domain_name, wait=True):
    """
    Invoke sparsify action on disk.

    Args:
        disk_id (str): Name of the disk we want to sparsify
        storage_domain_name (str): Name of the storage domain where the disk
            exist
        wait (bool): Determines whether to wait for action to finish or not

    Returns:
        bool: True if an event of sparsify action completion was issued after
            The event of the action's start was issued and within event
            timeout, False otherwise.
    """
    if not do_disk_action(
        'sparsify', disk_id=disk_id, target_domain=storage_domain_name,
        wait=wait
    ):
        return False
    return wait_for_sparsify_event(disk_id) if wait else True
