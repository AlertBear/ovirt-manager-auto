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

from rrmngmnt.host import Host as HostResource
from rrmngmnt.user import User
from utilities import sshConnection, machine
from utilities.utils import getIpAddressByHostName
from art.core_api.apis_exceptions import APITimeout, EntityNotFound
from art.core_api.apis_utils import getDS, TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.disks import (
    getStorageDomainDisks,
    deleteDisk,
    waitForDisksGone,
    wait_for_disks_status,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    get_host_compatibility_version,
)
from art.rhevm_api.utils.test_utils import (
    validateElementStatus, get_api, )
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from art.rhevm_api.tests_lib.low_level.networks import (
    prepare_vnic_profile_mappings_object
)
from art.rhevm_api.tests_lib.low_level.general import generate_logs
ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
ACTIVE_DOMAIN = ENUMS['storage_domain_state_active']
DATA_DOMAIN_TYPE = ENUMS['storage_dom_type_data']
STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_POSIX = ENUMS['storage_type_posixfs']
STORAGE_TYPE_CEPH = ENUMS['storage_type_ceph']
POSIX_BACKENDS = [STORAGE_TYPE_CEPH, STORAGE_TYPE_NFS]
CINDER_DOMAIN_TYPE = ENUMS['storage_dom_type_cinder']
RHEVM_UTILS_ENUMS = ART_CONFIG['elements_conf']['RHEVM Utilities']

StorageDomain = getDS('StorageDomain')
IscsiDetails = getDS('IscsiDetails')
iscsi_targetsType = getDS('iscsi_targetsType')
Host = getDS('Host')
HostStorage = getDS('HostStorage')
LogicalUnit = getDS('LogicalUnit')
LogicalUnits = getDS('LogicalUnits')
DataCenter = getDS('DataCenter')
Cluster = getDS('Cluster')
Disk = getDS('Disk')
Template = getDS('Template')

ELEMENT = 'storage_domain'
COLLECTION = 'storagedomains'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')
templUtil = get_api('template', 'templates')
vmUtil = get_api('vm', 'vms')
clUtil = get_api('cluster', 'clusters')
fileUtil = get_api('file', 'files')
diskUtil = get_api('disk', 'disks')
connUtil = get_api('storage_connection', 'storageconnections')

OVF_STORE_DISK_NAME = "OVF_STORE"
HOSTED_STORAGE = "hosted_storage"
FIND_SDS_TIMEOUT = 10
SD_STATUS_OK_TIMEOUT = 120


def _prepareStorageDomainObject(positive, **kwargs):

    sd = StorageDomain()

    name = kwargs.pop('name', None)
    if name:
        sd.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        sd.set_description(description)

    type_ = kwargs.pop('type', None)
    if type_:
        sd.set_type(type_)

    host = kwargs.pop('host', None)
    if host:
        host_obj = hostUtil.find(host)
        sd.set_host(Host(name=host_obj.get_name()))

    storage_type = kwargs.pop('storage_type', None)
    if storage_type in [
        ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp']
    ]:
        discard_after_delete = kwargs.pop('discard_after_delete', None)
        if discard_after_delete is not None:
            sd.set_discard_after_delete(
                discard_after_delete=discard_after_delete
            )

    # Set storage domain metadata format - only for data domains
    if type_ and type_.lower() == DATA_DOMAIN_TYPE:
        storage_format = kwargs.pop('storage_format', None)
        if host and storage_format is None:
            host_comp_ver = get_host_compatibility_version(host)
            if not host_comp_ver:
                util.logger.error("Can't determine storage domain version")
                return False
            if host_comp_ver == '2.2':
                storage_format = ENUMS['storage_format_version_v1']
            elif host_comp_ver == '3.0':
                # NFS does not support storage metadata format V2
                storage_format = (ENUMS['storage_format_version_v2'] if
                                  storage_type == ENUMS['storage_type_iscsi']
                                  else ENUMS['storage_format_version_v1'])
            else:
                storage_format = ENUMS['storage_format_version_v3']
        sd.set_storage_format(storage_format)

    if 'storage_connection' in kwargs:
        storage = HostStorage()
        storage.id = kwargs.pop('storage_connection')
        sd.set_storage(storage)
    elif storage_type == ENUMS['storage_type_local']:
        sd.set_storage(HostStorage(
            type_=storage_type, path=kwargs.pop('path', None)))
    elif storage_type == ENUMS['storage_type_nfs']:
        sd.set_storage(
            HostStorage(
                type_=storage_type, path=kwargs.pop('path', None),
                address=kwargs.pop('address', None),
                nfs_version=kwargs.pop('nfs_version', None),
                nfs_retrans=kwargs.pop('nfs_retrans', None),
                nfs_timeo=kwargs.pop('nfs_timeo', None),
                mount_options=kwargs.pop('mount_options', None),
            )
        )
    elif storage_type == ENUMS['storage_type_iscsi']:
        logical_units = LogicalUnits()
        lun = kwargs.get('lun', None)
        lun_address = kwargs.get('lun_address', None)
        lun_target = kwargs.pop('lun_target', None)
        lun_port = kwargs.pop('lun_port', None)
        if lun and lun_address and lun_target:
            logical_units.add_logical_unit(
                LogicalUnit(
                    address=getIpAddressByHostName(lun_address),
                    target=lun_target, id=lun, port=lun_port
                )
            )
        sd.set_storage(
            HostStorage(
                type_=storage_type, logical_units=logical_units,
                override_luns=kwargs.pop('override_luns', None)
            )
        )

    elif storage_type == ENUMS['storage_type_fcp']:
        logical_units = LogicalUnits()
        lun = kwargs.get('lun', None)
        if lun:
            logical_units.add_logical_unit(LogicalUnit(id=lun))
        sd.set_storage(
            HostStorage(
                type_=storage_type,
                logical_units=logical_units,
                override_luns=kwargs.pop('override_luns', None)
            )
        )

    elif (storage_type == ENUMS['storage_type_posixfs'] or
          storage_type == ENUMS['storage_type_gluster']):
        sd.set_storage(
            HostStorage(
                type_=storage_type, path=kwargs.pop('path', None),
                address=kwargs.pop('address', None),
                vfs_type=kwargs.pop('vfs_type', None),
                mount_options=kwargs.pop('mount_options', None),
            )
        )
    return sd


def addStorageDomain(positive, wait=True, **kwargs):
    '''
    Description: add new storage domain
    Author: edolinin
    Parameters:
       * name - storage domain name
       * type - storage domain type (ENUMS['storage_dom_type_data'],
          ENUMS['storage_dom_type_export'], ENUMS['storage_dom_type_iso'])
       * storage_type - storage type (ENUMS['storage_type_nfs'],
          ENUMS['storage_type_iscsi'],
          ENUMS['storage_type_fcp'], ENUMS['storage_type_local'])
       * host - storage domain host
       * address - storage domain address (for NFS)
       * path - storage domain path (for NFS,LOCAL)
       * lun - lun id (for ISCSI)
       * lun_address - lun address (for ISCSI)
       * lun_target - lun target name (for ISCSI)
       * lun_port - lun port (for ISCSI)
       * discard_after_delete - boolean (for ISCSI and FC). Send discard
            flag to the storage server, discard will be performed after disk
            deletion if true. If it's None, the flag won't be sent.
       * nfs_version - version of NFS protocol
       * nfs_retrans - the number of times the NFS client retries a request
       * nfs_timeo - time before client retries NFS request
       * mount_options - custom mount options
       * storage_connection - id of the storage connection which should be used
            (it will override all connection params like address, lun or path)
       * wait - if True, wait for the action to complete
    Return: status (True if storage domain was added properly,
                    False otherwise)
    '''
    sd = _prepareStorageDomainObject(positive, **kwargs)
    format = kwargs.get('format', False)
    operations = ['format=true'] if format else []
    try:
        sd, status = util.create(
            sd, positive, async=(not wait), operations=operations
        )
    except TypeError:
        util.logger.warning('Domain not created, wrong argument type passed. '
                            'Args: %s', kwargs)
        status = not positive
    return status


def updateStorageDomain(positive, storagedomain, **kwargs):
    '''
    Description: update existed storage domain
    Author: edolinin
    Parameters:
       * storagedomain - name of storage domain that should be updated
       * type - storage domain type (DATA,EXPORT,etc.)
       * storage_type - storage type (NFS,ISCSI,FCP,LOCAL)
       * host - storage domain host
    Return: status (True if storage domain was updated properly,
                    False otherwise)
    '''
    storDomObj = get_storage_domain_obj(storagedomain)
    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd, status = util.update(storDomObj, storDomNew, positive)
    return status


def extendStorageDomain(positive, storagedomain, **kwargs):
    """
    Extend an existing iSCSI or FCP storage domain

    __author__ = "edolinin, glazarov"
    :param positive: True when extend storage is expected to pass,
    False otherwise
    :type positive: bool
    :param storage_domain: The storage domain which is to be extended
    :type storage_domain: str
    :param storage_type: The storage type to be used (iSCSI or FCP)
    :type storage_type: str
    :param host: The host to be used with which to extend the storage domain
    :type host: str
    :param lun: The LUN to be used when extending storage domain
    :type lun: str
    :param lun_address: The iSCSI server address which contain the LUN
    :type lun_address: str
    :param lun_target: The iSCSI target (name of the LUN in iSCSI server)
    :type lun_target: str
    :param lun_port: The iSCSI server port
    :type lun_port: int
    :param override_luns: True if the block device should be formatted
    (when not empty), False if block device should be used as is
    :type override_luns: bool
    :returns: True on success, False otherwise
    :rtype: bool
    """
    storDomObj = get_storage_domain_obj(storagedomain)

    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd, status = util.update(storDomObj, storDomNew, positive)

    return status


def getDCStorages(datacenter, get_href=True):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromLink(dcObj, get_href=get_href)


def getDCStorage(datacenter, storagedomain):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromElemColl(dcObj, storagedomain)


def attachStorageDomain(positive, datacenter, storagedomain, wait=True,
                        compare=True):
    """
    Attach storage domain to data center

    :param positive: Determines whether the call for this function is
    positive or negative
    :type positive: bool
    :param datacenter: name of data center to use
    :type datacenter: str
    :param storagedomain: name of storage domain that should be attached
    :type storagedomain: str
    :param wait: if True, wait for the action to complete
    :type wait: bool
    :param compare: When True, the validator will run when
    calling util.create
    :type compare: bool
    :returns: True if storage domain was attached properly, False otherwise
    :rtype: bool
    """
    storDomObj = get_storage_domain_obj(storagedomain)
    attachDom = StorageDomain(id=storDomObj.get_id())

    dcStorages = getDCStorages(datacenter)
    attachDom, status = util.create(
        attachDom, positive, collection=dcStorages, async=(not wait),
        compare=compare
    )

    if status and positive and wait:
        dcObj = dcUtil.find(datacenter)
        return dcUtil.waitForElemStatus(dcObj, "UP", 60, "datacenter")
    return status


def detachStorageDomain(positive, datacenter, storagedomain):
    '''
    Description: detach storage domain from data center
    Author: edolinin
    Parameters:
       * datacenter - name of data center to use
       * storagedomain - name of storage domain that should be detached
    Return: status (True if storage domain was detached properly,
                    False otherwise)
    '''
    util.logger.info(
        'Detaching domain %s from data center %s', storagedomain, datacenter
    )
    storDomObj = getDCStorage(datacenter, storagedomain)
    return util.delete(storDomObj, positive)


def wait_for_storage_domain_available_size(
    datacenter, storagedomain, timeout=60, interval=5
):
    """
    Waits until the storage domain's "available size" is set.
    These properties are not available inmediately adding the storage domain,
    and in some cases is needed for the tests.

    __author__ = "cmestreg"
    :param datacenter: Name of the data center
    :type datacenter: str
    :param storagedomain: Name of the storage domain
    :type storagedomain: str
    :param timeout: Maximum number of seconds to wait before timing out
    :type timeout: int
    :param interval: Number of seconds between polling
    :type interval: int
    :returns: True in case the available size is present, False otherwise
    :rtype: bool
    """
    def _get_size():
        if getDCStorage(datacenter, storagedomain).get_available():
            return True
        util.logger.warning('Available size still is still not set')
        return False

    util.logger.warning('Waiting for storage domain return available size')
    for size in TimeoutingSampler(timeout, interval, _get_size):
        if size:
            return True
    return False


def activateStorageDomain(positive, datacenter, storagedomain, wait=True):
    '''
    Description: activate storage domain
    Author: edolinin
    Parameters:
       * datacenter - name of data center to use
       * storagedomain - name of storage domain that should be activated
       * wait - if True, wait for the test result
    Return: status (True if storage domain was activated properly,
                    False otherwise)
    '''
    storDomObj = getDCStorage(datacenter, storagedomain)

    if positive and validateElementStatus(positive, 'storagedomain',
                                          COLLECTION, storagedomain, 'active',
                                          datacenter):
        util.logger.warning("Storage domain %s already activated",
                            storagedomain)
        return True

    async = 'false' if wait else 'true'
    status = bool(
        util.syncAction(storDomObj, "activate", positive, async=async)
    )
    if status and positive and wait:
        return wait_for_storage_domain_status(
            True, datacenter, storagedomain,
            ACTIVE_DOMAIN, 180,
        )
    return status


def deactivateStorageDomain(positive, datacenter, storagedomain, wait=True):
    '''
    Description: deactivate storage domain
    Author: cmestreg
    Parameters:
       * datacenter - name of data center to use
       * storagedomain - name of storage domain that should be deactivated
       * wait - if True, wait for the action to complete
    Return: status (True if storage domain was deactivated properly,
                    False otherwise)
    '''

    storDomObj = getDCStorage(datacenter, storagedomain)
    util.logger.info(
        'Deactivating domain %s in data center %s', storagedomain, datacenter
    )
    async = 'false' if wait else 'true'
    status = bool(
        util.syncAction(storDomObj, "deactivate", positive, async=async)
    )
    if positive and status and wait:
        return wait_for_storage_domain_status(
            True, datacenter, storagedomain,
            ENUMS['storage_domain_state_maintenance'],
            300,
        )
    return status


def iscsiDiscover(positive, host, address):
    '''
    run iscsi discovery
    __author__: edolinin, khakimi
    :param positive: True if discover succeed False otherwise
    :type positive: bool
    :param host: name of host
    :type host: str
    :param address: iscsi address
    :type address: str
    :return: list of iscsi targets if discovery succeeded, None otherwise
    :rtype: list
    '''
    hostObj = hostUtil.find(host)

    iscsi = IscsiDetails(address=address)
    response = hostUtil.syncAction(
        hostObj, "iscsidiscover", positive, iscsi=iscsi
    )
    return hostUtil.extract_attribute(response, 'iscsi_target')


def iscsiLogin(
        positive, host, addresses, targets, username=None, password=None
):
    """
    Run iscsi login

    :param positive: determines whether the call for this function is
    positive of negative
    :type positive: bool
    :param host: name of host
    :type host: str
    :param addresses: iscsi addresses
    :type addresses: list
    :param targets: iscsi target names
    :type targets: list
    :param username: iscsi username
    :type username: str
    :param password: iscsi password
    :type password: str
    :return: True if iscsi login succeeded, False otherwise
    :rtype: bool
    """
    hostObj = hostUtil.find(host)
    for address, target in zip(addresses, targets):
        iscsi = IscsiDetails(
            address=address, target=target, username=username,
            password=password
        )
        util.logger.info("Log in to address %s, target %s",
                         address, target)
        if not hostUtil.syncAction(
            hostObj, "iscsilogin", positive, iscsi=iscsi
        ):
            msg = 'Failed to login' if positive else 'Login not as expected'
            util.logger.error(
                '%s to address %s on target %s using host %s',
                msg, address, target, host
            )
            return False
    return True


def removeStorageDomain(positive, storagedomain, host, format='false',
                        destroy=False, force=False):
    """
    remove storage domain

    __author__ = 'edolinin'
    :param storagedomain: storage domain name that should be removed
    :type storagedomain: str
    :param host: host name/IP address to use
    :type host: str
    :param format: format the content of storage domain
    :type format: str - 'true' or 'false'
    :param destroy: remove the storage domain from DB without deleting it's
    content
    :type destroy: bool
    :return: True if storage domain was removed properly, False otherwise
    :rtype: bool
    """
    util.logger.info("Removing storage domain %s", storagedomain)

    storDomObj = get_storage_domain_obj(storagedomain)

    href_params = [
        "host=%s" % host,
        "format=%s" % format,
    ]

    if destroy:
        href_params.append("destroy=true")

    if force:
        href_params.append("force=true")

    return util.delete(storDomObj, positive, operations=href_params)


def cleanExportDomainMetadata(address, path):
    '''
    Fix up metadata on export storage domain to be importable.
    Parameters:
     * address - address of storage domain
     * path - path to mount directory
    Return: cmd result
    '''
    clean_cmd = ['sed', '-i', '-e', 's/^POOL_UUID=.*/POOL_UUID=/', '-e',
                 '/^_SHA_CKSUM=/ d']
    metadata_path = "$(find %s -name metadata)"
    machineObj = machine.Machine().util(machine.LINUX)
    sd = '%s:%s' % (address, path)
    with machineObj.mount(sd) as mounted_path:
        clean_cmd.append(metadata_path % mounted_path)
        util.logger.debug("Cleaning export storage domain %s. %s",
                          sd, clean_cmd)
        return machineObj.runCmd(clean_cmd)


def importStorageDomain(positive, type, storage_type, address, path, host,
                        nfs_version=None, nfs_retrans=None, nfs_timeo=None,
                        vfs_type=None, storage_format=None,
                        clean_export_domain_metadata=False,
                        mount_options=None):
    '''
    Description: import storage domain (similar to create function, but not
    providing name)
    Author: edolinin
    Parameters:
       * type - storage domain type (DATA,EXPORT, etc.)
       * storage_type - storage type (NFS,ISCSI,etc.)
       * address - storage domain address (for ISCSI)
       * path - storage domain path (for NFS)
       * host - host to use
       * clean_export_domain_metadata - if True clear export domain metadata
       * mount_options - Mount options required for posix support
    Return: status (True if storage domain was imported properly,
                    False otherwise)
    '''
    if clean_export_domain_metadata:
        ret = cleanExportDomainMetadata(address, path)
        util.logger.debug("Cleaning export storage domain: %s", ret[1])
        if not ret[0]:
            warn_msg = ("Clean of export domain metadata %s:%s failed,"
                        "may cause issues.")
            util.logger.warn(warn_msg, address, path)

    util.logger.info("Importing domain from %s:%s", address, path)
    sdStorage = HostStorage(
        type_=storage_type, address=address, path=path,
        nfs_version=nfs_version, nfs_retrans=nfs_retrans,
        nfs_timeo=nfs_timeo, vfs_type=vfs_type, mount_options=mount_options
    )
    h = Host(name=host)

    sd = StorageDomain(type_=type, host=h, storage=sdStorage)
    if storage_format:
        sd.set_storage_format(storage_format)
    sd, status = util.create(sd, positive)

    return status


def removeStorageDomains(positive, storagedomains, host, format='true'):
    '''
    Description: remove storage domains
    Author: edolinin
    Parameters:
       * storagedomains - comma-separated string or python list of storage
       domain names
       * host - host name/IP address to use
       * format - format the content of storage domain ('true' by default)
    Return: status (True if storage domains were removed properly,
    False otherwise)
    '''
    status = True
    detach_status = False
    if isinstance(storagedomains, basestring):
        storagedomains = storagedomains.split(',')
    else:
        storagedomains = storagedomains[:]
    for dc in dcUtil.get(abs_link=False):
        sds = util.getElemFromLink(dc, get_href=False)
        # detach and remove non master domains
        for sd in sds:
            if sd.get_name() in storagedomains:
                if sd.get_master():
                    continue
                else:
                    deactivate_status = deactivateStorageDomain(positive,
                                                                dc.get_name(),
                                                                sd.get_name())
                    if deactivate_status:
                        detach_status = detachStorageDomain(positive,
                                                            dc.get_name(),
                                                            sd.get_name())
                    else:
                        status = False

                    if not detach_status:
                        status = False

    for sd_listed in get_storage_domains():
        if sd_listed.get_name() in storagedomains:
            removeStatus = removeStorageDomain(positive, sd_listed.get_name(),
                                               host, format)
            if not removeStatus:
                status = False

    return status


def wait_for_storage_domain_status(
        positive, data_center_name, storage_domain_name, expected_status,
        time_out=900, sleep_time=10
):
    """
    Wait till the storage domain gets the desired status or until it times out

    __Author__ = 'ratamir'

    :param positive: Determines whether the call for this function is
    positive or negative
    :type positive: bool
    :param data_center_name: Name of data center
    :type data_center_name: str
    :param storage_domain_name: Storage domain name
    :type storage_domain_name: str
    :param expected_status: Storage domain status to wait for
    :type expected_status: str
    :param time_out: Maximum timeout [sec]
    :type time_out: int
    :param sleep_time: Sleep time [sec]
    :type sleep_time: int
    :return: True if storage domain reaches the desired status, False otherwise
    :rtype: bool
    """
    for sd_object in TimeoutingSampler(
        time_out, sleep_time, getDCStorage, data_center_name,
        storage_domain_name
    ):
        if sd_object.get_status() == expected_status:
            return positive

    return not positive


def remove_floating_disks(storage_domain):
    """
    Description: remove floating disks from storage domain
    :param storage_domain object
    :type storage_domain: object
    """

    util.logger.info(
        'Remove floating disks in storage domain %s',
        storage_domain.get_name()
    )
    floating_disks = getStorageDomainDisks(
        storage_domain.get_name(),
        False
    )
    floating_disks = filter(
        lambda w: w.get_name() != ENUMS['ovf_disk_alias'],
        floating_disks
    )

    if floating_disks:
        floating_disks_ids = [disk.get_id() for disk in floating_disks]
        floating_disks_aliases = [disk.get_alias() for disk in floating_disks]
        for disk_id, alias in zip(floating_disks_ids, floating_disks_aliases):
            util.logger.info(
                'Removing floating disk alias:%s id:%s', alias, disk_id
            )
            if not deleteDisk(True, async=False, disk_id=disk_id):
                return False
        util.logger.info('Ensuring all disks are removed')
        if not waitForDisksGone(
                True,
                ','.join(floating_disks_aliases),
                sleep=10
        ):
                return False
        util.logger.info(
            'All floating disks: %s removed successfully',
            floating_disks_aliases
        )


def deactivate_master_storage_domain(positive, datacenter):
    """
    Deactivate storage domain in a datacenter

    Args:
        positive (bool): Expected result
        datacenter (str): Datacenter name

    Returns:
        bool: True if succeeded, False otherwise
    """

    status, master = findMasterStorageDomain(positive, datacenter)
    master_storage_domain = master['masterDomain']

    if master_storage_domain:
        util.logger.info(
            "Deactivate master storage domain %s on datacenter %s",
            master_storage_domain, datacenter
        )
        if validateElementStatus(
                positive, 'storagedomain', 'storagedomains',
                master_storage_domain, 'active', datacenter
        ):
            if not deactivateStorageDomain(
                positive, datacenter, master_storage_domain
            ):
                util.logger.error(
                    "Deactivate master storage domain %s Failed",
                    master_storage_domain
                )
                status = False
    else:
        util.logger.info("Error in master storage domain search")

    return status


def remove_storage_domains(
        sds, host, format_export='false', format_iso='false'):
    """
    Description: remove given list of storage domains with host to remove with

    :param sds storage domain object list to be removed
    :type sds: list
    :param host: host name
    :type host: str
    :param format_export: True to format domains when removing
    :type format_export: bool
    :param format_iso: True to format domains when removing
    :type format_iso: bool
    :return: True if succeed to remove sds list, False otherwise
    :rtype: bool
    """
    for sd in sds:
        sd_name = sd.get_name()
        try:
            get_storage_domain_obj(sd_name)
        except EntityNotFound:
            continue
        format_storage = True
        if sd.get_type() == ENUMS['storage_dom_type_iso']:
            format_storage = format_iso
        if sd.get_type() == ENUMS['storage_dom_type_export']:
            format_storage = format_export

        if not removeStorageDomain(True, sd_name, host, str(format_storage)):
            util.logger.error("Failed to remove %s", sd_name)
            return False

    return True


def getDomainAddress(positive, storage_domain):
    """
    Find the address of a storage domain

       Args:
           positive (bool): Represents if the call for this function is
                positive or negative
           storage_domain (str): Storage domain name

       Returns:
           tuple: bool for positive or negative and dictionary with key
                'address' of storage domain and list of ip's in the value

       Raises:
           EntityNotFound: In case storage domain entity is not found

    """

    # Get the storage domain object
    try:
        # Check for iscsi storage domain
        if get_storage_domain_storage_type(storage_domain) == 'iscsi':
            # Return the address of the first LUN of the domain
            logical_units = get_storage_domain_logical_units(storage_domain)
            return positive, {
                'address': [
                    logical_units[x].get_address() for x in range(
                        len(logical_units)
                    )
                ]
            }
        return positive, {
            'address': [
                get_storage_domain_obj(
                    storage_domain
                ).get_storage().get_address()
            ]
        }

    except EntityNotFound:
        return not positive, {'address': ''}


def findNonMasterStorageDomains(positive, datacenter):
    """
    Find all non-master data storage domains

    :param positive: Represents if the call for this function is positive or
    negative
    :type positive: bool
    :param datacenter: datacenter name
    :type datacenter: str
    :returns: tuple of status, and list of non-master data storage domains,
              empty string if no non-master data domains is found
    :rtype: tuple
    """

    sd_obj_list = getDCStorages(datacenter, False)

    # Filter out master domain and ISO/Export domains
    non_master_domains = [
        sd_object.get_name() for sd_object in sd_obj_list if
        sd_object.get_type() == DATA_DOMAIN_TYPE
        and not sd_object.get_master()
    ]
    if non_master_domains and positive:
        return positive, {'nonMasterDomains': non_master_domains}
    return not positive, {'nonMasterDomains': ''}


def findIsoStorageDomains(datacenter=None):
    '''
    Description: find all iso storage domains, if datacenter is specified
                 searches only in that specific datacenter.
    Author: cmestreg
    Parameters:
        * datacenter - datacenter name
    Return: List of all iso storage domains
    '''

    if datacenter:
        sdObjList = getDCStorages(datacenter, False)
    else:
        sdObjList = get_storage_domains()

    isoDomains = [sdObj.get_name() for sdObj in sdObjList if
                  sdObj.get_type() == ENUMS['storage_dom_type_iso']]
    return isoDomains


def findExportStorageDomains(datacenter=None):
    """
    Description: find all export storage domains
    Author: cmestreg
    Parameters:
        * datacenter - datacenter name. All export domains would be returned
                       if the datacenter parameter is set to None
    Return: List of export storage domains
    """
    if datacenter:
        sdObjList = getDCStorages(datacenter, False)
    else:
        sdObjList = get_storage_domains()

    exportDomains = [sdObj.get_name() for sdObj in sdObjList if
                     sdObj.get_type() == ENUMS['storage_dom_type_export']]
    return exportDomains


def findMasterStorageDomain(positive, datacenter):
    '''
    Description: find the master storage domain.
    Author: istein
    Parameters:
       * datacenter - datacenter name
    Return: master domain storage domain if found, empty string ' ' otherwise)
    '''

    sdObjList = getDCStorages(datacenter, False)

    # Find the master DATA_DOMAIN storage domain.
    masterResult = filter(
        lambda sdObj: sdObj.get_type() == DATA_DOMAIN_TYPE and
        sdObj.get_master() in [True, 'true'], sdObjList
    )
    masterCount = len(masterResult)
    if masterCount == 1:
        return True, {'masterDomain': masterResult[0].get_name()}
    util.logger.error("Found %d master data domains, while one was expected.",
                      masterCount)
    return False, {'masterDomain': ' '}


def get_iso_domain_files(iso_domain_name):
    """
     Description: fetch files in iso storage domain

     :param iso_domain_name: name of storage domain to look for file in
     :type iso_domain_name: str
     :return: a list of files objects under given storage domain
     :rtype: list
     """
    iso_domain_object = get_storage_domain_obj(iso_domain_name)
    return util.getElemFromLink(iso_domain_object, 'files', attr='file')


def checkIfStorageDomainExist(positive, storagedomain):
    '''
    Description: Check if storagedomain exist.
    Author: istein
    Parameters:
       * storagedomain - storage domain name
    Return:
       positive == True:If storagedomain exist return True, otherwise False
       positive == False:If storagedomain exist return False, otherwise True
    '''

    storagedomains = get_storage_domains()
    sdObj = filter(lambda sdObj: sdObj.get_name() == storagedomain,
                   storagedomains)
    return (len(sdObj) == 1) == positive


def checkStorageFormatVersion(positive, storagedomain, version):
    """
    Description: Checks storage format version on given storage domain
    Parameters:
        * storagedomain - domain's name
        * version - expected version (e.g. "v2")
    Return: True if versions are the same and positive is True
            False if versions are not the same and positive is True
    """
    domainObj = get_storage_domain_obj(storagedomain)

    return (domainObj.storage_format == version) == positive


def getObjList(sd, coll):
    """
    Description: Returns list of objects specified by coll
    Author: jlibosva
    Parameters:
        * sd - storage domain we want objects from
        * coll - collection we want (vms or templates)
    Return: list of objects (vms or templates)
    """
    attr = coll[:-1]
    return util.getElemFromLink(sd, link_name=coll, attr=attr,
                                get_href=False)


def is_storage_domain_active(datacenter, domain):
    """
    Checks if the storage domain is active in the given datacenter

    __author__: gickowic

    :param datacenter: datacenter name
    :type datacenter: str
    :param domain: storage domain name
    :type domain: str
    :return: True if the storage domain state is active, otherwise False
    :rtype: bool
    """
    util.logger.info(
        'Checking if domain %s is active in dc %s', domain, datacenter
    )
    try:
        sd_object = getDCStorage(datacenter, domain)
    except EntityNotFound:
        return False
    state = sd_object.get_status()
    util.logger.info('Domain %s in dc %s is %s', domain, datacenter, state)
    return state == ACTIVE_DOMAIN


def getConnectionsForStorageDomain(storagedomain):
    """
    Description: Returns all connections added to a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
    Returns: List of Connection objects
    """
    sdObj = get_storage_domain_obj(storagedomain)
    return connUtil.getElemFromLink(sdObj)


def addConnectionToStorageDomain(storagedomain, conn_id):
    """
    Description: Adds a connection to a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
        * conn_id - id of the connection
    Returns: true if operation succeeded
    """
    sdObj = get_storage_domain_obj(storagedomain)
    connObj = connUtil.find(conn_id, attribute='id')
    conn_objs = util.getElemFromLink(
        sdObj, link_name='storageconnections', attr='storage_connection',
        get_href=True
    )
    _, status = connUtil.create(
        connObj, True, collection=conn_objs, async=True
    )
    return bool(status)


def detachConnectionFromStorageDomain(storagedomain, conn_id):
    """
    Description: Detach a connection from a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
        * conn_id - id of the connection
    Returns: true if operation succeeded
    """
    sdObj = get_storage_domain_obj(storagedomain)
    conn_objs = util.getElemFromLink(
        sdObj, link_name='storageconnections', attr='storage_connection')
    for conn in conn_objs:
        if conn.id == conn_id:
            # conn.href == "/api/storageconnections/[conn_id]" ...
            conn.href = "%s/storageconnections/%s" % (sdObj.href, conn_id)
            return util.delete(conn, True)
    return False


def get_allocated_size(storagedomain):
    """
    Description: Get the allocated space for vms in the storage domain
    Allocated space calculates size of thin provision disks according to
    their virtual size, not actual size currently on disk
    Author: gickowic
    Parameters:
        * storagedomain - name of the storage domain
    Returns: allocated space on the storagedomain in bytes
    """
    sdObj = get_storage_domain_obj(storagedomain)
    return sdObj.get_committed()


def get_total_size(storagedomain, data_center):
    """
    Gets the total size of the storage domain (available + used)

    Args:
        storagedomain (str): Name of the storage domain
        data_center (str): Name of the data center

    Returns:
        int: Total size of the storage domain in bytes, None in case of error
    """
    if data_center is not None:
        if not wait_for_storage_domain_available_size(
            data_center, storagedomain
        ):
            return None
    sdObj = get_storage_domain_obj(storagedomain)
    return sdObj.get_available() + sdObj.get_used()


def get_free_space(storagedomain):
    """
    Description: Gets the free space of the storage domain
    Author: ratamir
    Parameters:
        * storagedomain - name of the storage domain
    Returns: total size of the storage domain in bytes
    """
    sdObj = get_storage_domain_obj(storagedomain)
    return sdObj.get_available()


def get_unregistered_vms(storage_domain):
    """
    Get unregistered vms on storage domain

    __author__ = "ratamir"
    :param storage_domain: name of the storage domain on which
    to find unregistered vms
    :type storage_domain: str
    :returns: List of unregistered vm objects,
    or empty list when no unregistered vms are found
    :rtype: list
    """
    storage_domain_obj = get_storage_domain_obj(storage_domain)
    unregistered_vms = util.get(
        "%s/vms;unregistered" % storage_domain_obj.href
    )
    return unregistered_vms.get_vm()


def get_unregistered_templates(storage_domain):
    """
    Get unregistered templates on storagedomain

    __author__ = "ratamir"
    :param storage_domain: name of the storage domain on which to find
    unregistered templates
    :type storage_domain: str
    :returns: List of unregistered template objects,
    or empty list when no unregistered templates are found
    :rtype: list
    """
    storage_domain_obj = get_storage_domain_obj(storage_domain)
    unregistered_templates = util.get(
        "%s/templates;unregistered" % storage_domain_obj.href
    )
    return unregistered_templates.get_template()


def register_object(obj, cluster, **kwargs):
    """
    Register unregistered vms or templates from storage domain

    __author__ = "ratamir"

    Args:
        obj (Vm or Template): object of vm or template to register the object
            should be received from get_unregistered_vms() or
            get_unregistered_templates()
        cluster (str): Name of cluster on which the vms or templates should
            be registered

    Keyword Args:
        reassign_bad_macs (bool): Reassign MAC from pool if MAC is outside
            of MAC pool
        network_mappings (list): Map networks from the imported object to
            existing network on cluster (list of dicts)
            network_mappings = [{
            "source_network_profile_name": "src_profile_name",
            "source_network_name": "src_network_name",
            "target_network": "target_network_name",
            "target_vnic_profile": "target_profile_name",
            "cluster": "cluster_name_for_target_vnic_profile",
            "datacenter": "datacenter_name_for_target_vnic_profile"
            }]
        partial_import (bool): Determines whether the import operation allows
            to import only part of the object (e.g. VM without all it's disks)

    Returns:
        bool: True on success, False otherwise
    """
    cluster_obj = Cluster(name=cluster)
    registration_configuration = getDS("RegistrationConfiguration")()
    reassign_bad_macs = kwargs.get("reassign_bad_macs", True)
    network_mappings = kwargs.get("network_mappings")
    partial_import = kwargs.get("partial_import")
    vnic_profile_mappings = None
    if network_mappings:
        vnic_profile_mappings = prepare_vnic_profile_mappings_object(
            network_mappings=network_mappings
        )
        registration_configuration.set_vnic_profile_mappings(
            vnic_profile_mappings
        )
    return bool(
        util.syncAction(
            entity=obj, action='register', positive=True, cluster=cluster_obj,
            reassign_bad_macs=reassign_bad_macs,
            registration_configuration=registration_configuration,
            allow_partial_import=partial_import
        )
    )


def get_used_size(storagedomain):
    """
    Description: Gets the used size
    Author: cmestreg
    Parameters:
        * storagedomain - name of the storage domain
    Returns: used size of the storagedomain in bytes
    """
    sdObj = get_storage_domain_obj(storagedomain)
    return sdObj.get_used()


def get_discard_after_delete(storage_domain, attribute='name'):
    """
    Gets the discard_after_delete flag value

    Args:
        storage_domain (str): The name or id of the storage domain
        attribute (str): Key to look for the storage domain, name or id

    Returns:
        bool: true if discard_after_delete is set

    """
    return get_storage_domain_obj(
        storage_domain, attribute
    ).get_discard_after_delete()


def _parse_mount_output_line(line):
    """
    Parses one line of mount output

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *line*: one line of 'mount' output

    **Returns**:
        * (address, path, timeo, retrans, nfsvers, sync) in case it is nfs
        resource
        * None otherwise

    >>> output = "10.34.63.202:/mnt/export/nfs/lv2/kjachim/nfs01 on "
    >>> output += "/rhev/data-center/mnt/10.34.63.202:_mnt_export_nfs_lv2_kjac"
    >>> output += " type nfs (rw,soft,nosharecache,timeo=600,retrans=6"
    >>> output += ",nfsvers=3,addr=10.34.63.202)"
    >>> result = _parse_mount_output_line(output)
    >>> result[0] == '10.34.63.202' or result[0]
    True
    >>> result[1] == '/mnt/export/nfs/lv2/kjachim/nfs01' or result[1]
    True
    >>> result[2] == 600 or result[2]
    True
    >>> result[3] == 6 or result[3]
    True
    >>> result[4] == 'v3' or result[4]
    True
    >>> output = 'nfsd on /proc/fs/nfsd type nfsd (rw)'
    >>> result = _parse_mount_output_line(output)
    """
    util.logger.debug("Parsed line: %s", line)
    if 'type nfs ' not in line:
        return None
    parts = line.split(" ")
    address, path = parts[0].split(":")
    options = parts[-1][1:-1]  # skip brackets
    options = options.split(",")
    nfs_options = {}
    for option in options:
        if "=" in option:
            name, value = option.split("=")
            nfs_options[name] = value
        elif 'sync' == option:
            nfs_options[option] = True

    # support rhel6.5 & rhel7
    # mount_2.17.2 (rhel6.5)
    if nfs_options.get('nfsvers', None):
        nfsvers = nfs_options['nfsvers']
    # mount_2.23.2 (rhel7)
    elif nfs_options.get('vers', None):
        nfsvers = nfs_options['vers']
    else:
        raise Exception("Unknown NFS protocol version number")

    return (address, path, int(nfs_options['timeo']),
            int(nfs_options['retrans']), 'v' + nfsvers,
            'sync' in nfs_options.keys())


def _parse_mount_output(output):
    """
    Parses mount output

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *output*: 'mount' output

    **Returns**: list of tuples (address, path, timeo, retrans, nfsvers),
                 one tuple for each found nfs mount
    """
    result = []
    for line in output.split("\n"):
        parsed = _parse_mount_output_line(line)
        if parsed is not None:
            result.append(parsed)
    return result


def get_options_of_resource(host, password, address, path):
    """
    Calls mount on given host and returns options of given nfs resource

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host on which 'mount' should be called
        * *password*: root password on this host
        * *address*: address of the NFS server
        * *path*: path to the NFS resource on the NFS server

    **Returns**:  tuple (timeo, retrans, nfsvers, sync)
                  or None if there is no such nfs mount
    """
    nfs_mounts = get_mounted_nfs_resources(host, password)
    return nfs_mounts.get((address, path), None)


def get_mounted_nfs_resources(host, password):
    """
    Gets info about all NFS resource mounted on specified host

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host on which 'mount' should be called
        * *password*: root password on this host

    **Returns**: dict: (address, path) ->  (timeo, retrans, nfsvers, sync)
    """
    ssh_session = sshConnection.SSHSession(
        hostname=host, username='root', password=password)
    rc, out, err = ssh_session.runCmd('mount')
    if rc:
        raise exceptions.TestException(
            'mount failed with non-zero err code: %s stdout: %s stderr: %s' %
            (rc, out, err))
    mounted = _parse_mount_output(out)
    result = {}
    for (address, path, timeo, retrans, nfsvers, sync) in mounted:
        result[(address, path)] = (timeo, retrans, nfsvers, sync)
    return result


def _verify_one_option(real, expected):
    """ helper function for verification of one option
    """
    return expected is None or expected == real


def verify_nfs_options(
        expected_timeout, expected_retrans, expected_nfsvers,
        expected_mount_options, real_timeo, real_retrans, real_nfsvers,
        real_mount_options):
    """
    Verifies that the real nfs options are as expected.

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *expected_timeout*: expected NFS timeout
        * *expected_retrans*: expected # of retransmissions
        * *expected_nfsvers*: expected NFS protocol version
        * *expected_mount_options*: expected additional mount options
        * *real_timeo*: NFS timeout returned by 'mount' command
        * *real_retrans*: # of retransmissions returned by 'mount' command
        * *real_nfsvers*: NFS protocol version returned by 'mount' command
        * *real_mount_optiones*: sync value of NFS options returned by 'mount'
        command

    **Returns**: None in case of success or tuple (param_name, expected, real)
    """
    if not _verify_one_option(real_timeo, expected_timeout):
        return "timeo", expected_timeout, real_timeo
    if not _verify_one_option(real_retrans, expected_retrans):
        return "retrans", expected_retrans, real_retrans
    if not _verify_one_option(real_nfsvers, expected_nfsvers):
        return "nfsvers", expected_nfsvers, real_nfsvers
    if expected_mount_options and "sync" in expected_mount_options:
        if not _verify_one_option(real_mount_options, True):
            return "sync", True, real_mount_options


def get_storage_domains():
    """
    Get list of storage domains
    :return: List of storage domains object from the engine
    :rtype: list
    """
    return util.get(abs_link=False)


def get_storagedomain_names():
    """
    Get list of storage domain names
    :return: List of storage domains name
    :rtype: list
    """
    return [sd.get_name() for sd in get_storage_domains()]


class NFSStorage(object):
    """ Helper class - one object represents one NFS storage domain.

    **Attributes**:
        * *name*: name of the storage domain in RHEV-M
        * *address*: address of the NFS server
        * *path*: path to the NFS resource on the NFS server
        * *timeout_to_set*: value of the NFS timeout which should be passed to
                        RHEV-M when storage domain is created
        * *retrans_to_set*: # of retransmissions as above
        * *mount_options_to_set*: # of mount_options_to_set as above
        * *vers_to_set*: NFS protocol version as above
        * *expected_timeout*: value of the NFS timeout which should be used by
                          RHEV-M when NFS resource is mounted on the host
        * *expected_retrans*: # of retransmissions as above
        * *expected_vers*: NFS protocol version as above
        * *sd_type*: one of ENUMS['storage_dom_type_data'],
             ENUMS['storage_dom_type_iso'], ENUMS['storage_dom_type_export']

        Actually, the X_to_set and expected_X values are different only when
        X_to_set is None, which means that the default value should be used.
    """
    __allowed = ("name", "address", "path", "sd_type",
                 "timeout_to_set", "retrans_to_set", "vers_to_set",
                 "mount_options_to_set", "expected_timeout",
                 "expected_retrans", "expected_vers", "expected_mount_options")

    def __init__(self, **kwargs):
        self.sd_type = DATA_DOMAIN_TYPE
        for k, v in kwargs.iteritems():
            assert (k in self.__allowed)
            setattr(self, k, v)


def get_master_storage_domain_name(datacenter_name):
    """
    Get master storage domain

    Return: master domain name, or raise exception otherwise
    """
    rc, masterSD = findMasterStorageDomain(True, datacenter_name)
    if not rc:
        raise exceptions.StorageDomainException("Could not find master "
                                                "storage domain for dc %s"
                                                % datacenter_name)
    masterSD = masterSD['masterDomain']
    return masterSD


def get_storage_domain_obj(storage_domain, key='name'):
    """
    Get storage domain object from engine by name

    :param storage_domain: the storage domain name/id
    :type storage_domain: str
    :param key: key to look for storage domain, it can be name or id
    Important: If key='id', storage domain should be the storage domain's id
    :type key: str
    :return: the storage domain object
    :rtype: Storage Domain Object
    :raise: EntityNotFound
    """
    return util.find(storage_domain, attribute=key)


def wait_for_change_total_size(
    storage_domain, data_center, original_size=0, sleep=5, timeout=50,
):
    """
    Wait until the total size changes from original_size

    Args:
        storage_domain (str): The name of the storage domain
        data_center (str): The data_center name which storage_domain is
            attached to
        original_size (int): The size to compare to
        sleep (int): The sampler interval in seconds
        timeout (int): The time to wait for the storage domain size to change
            in seconds

    Returns:
        bool: True in case the size has changed, False otherwise
    """
    for total_size in TimeoutingSampler(
        timeout, sleep, get_total_size, storage_domain, data_center
    ):
        util.logger.info(
            "Total size for %s is %d", storage_domain, total_size
        )
        if total_size != original_size:
            return True

    util.logger.warning(
        "Total size for %s didn't update from %d", storage_domain,
        original_size
    )
    return False


def get_posix_backend_type(storagedomain_name):
    """
    Returns the vfs type of the given storage-domain

    :param storagedomain_name: Storage domain name
    :type storagedomain_name: str
    :return: vfs type of the storage doamin
    :rtype: str
    """
    storage_domain_object = get_storage_domain_obj(storagedomain_name)
    storage_connections = connUtil.getElemFromLink(
        storage_domain_object, link_name='storageconnections', get_href=False
    )
    for storage_connection in storage_connections:
        if storage_connection.get_type() == STORAGE_TYPE_POSIX:
            return storage_connection.get_vfs_type()


def getStorageDomainNamesForType(datacenter_name, storage_type):
    """
    Returns a list of data domain names of a certain storage_type
    Note: Only the active data domains are returned
     * datacenter_name: name of datacenter
     * storage_type: type of storage (nfs, iscsi, ...)
    """
    def validate_domain_storage_type(storage_domain_object, storage_type):
        """
        A validator for storage objects that checks whether a storage is a data
        domain of a certain type

        __author__ = "ogofen"
        :param storage_domain_object: Storage domain object
        :type storage_domain_object: Storage Object
        :param storage_type: The type of storage to use (NFS,
        iSCSI, GlusterFS, Volume, POSIX etc.)
        :type storage_type: str
        :returns: True if a data domain is active and is of a chosen type,
        False otherwise
        :rtype: bool
        """
        state = storage_domain_object.get_status()
        sd_type = storage_domain_object.get_type()
        _storage_type = storage_domain_object.get_storage().get_type()

        if sd_type == DATA_DOMAIN_TYPE or sd_type == CINDER_DOMAIN_TYPE:
            if _storage_type == storage_type:
                # TODO: W/A for bug:
                # https://bugzilla.redhat.com/show_bug.cgi?id=1354200
                if storage_domain_object.get_name() != HOSTED_STORAGE:
                    return True

            elif (_storage_type == STORAGE_TYPE_POSIX and
                    state == ACTIVE_DOMAIN and
                    storage_type in POSIX_BACKENDS
                  ):
                sd_name = storage_domain_object.get_name()
                if storage_type == get_posix_backend_type(sd_name):
                    return True
        return False

    sd_obj_list = []
    for sd in getDCStorages(datacenter_name, False):
        if validate_domain_storage_type(sd, storage_type):
            if sd.get_status() == ACTIVE_DOMAIN:
                sd_obj_list.append(sd.get_name())
            elif sd.get_status() == ENUMS['storage_domain_state_maintenance']:
                continue
            else:
                util.logger.info(
                    "Waiting up to %s seconds for sd %s to be active",
                    SD_STATUS_OK_TIMEOUT, sd.get_name()
                )
                try:
                    wait_for_storage_domain_status(
                        True, datacenter_name, sd.get_name(),
                        ACTIVE_DOMAIN, SD_STATUS_OK_TIMEOUT, 1
                    )
                    sd_obj_list.append(sd.get_name())
                except APITimeout:
                    util.logger.error(
                        "Domain '%s' has not reached %s state after %s secs" %
                        (
                            sd.get_name(), ACTIVE_DOMAIN, SD_STATUS_OK_TIMEOUT
                        )
                    )
    return sd_obj_list


def get_storage_domain_images(storage_domain_name):
    """
    Get all images in storage domain

    :param storage_domain_name: Storage domain to use in finding disk images
    :type storage_domain_name: str
    :return: List of disk image objects
    :rtype: list
    """
    storage_domain_obj = get_storage_domain_obj(storage_domain_name)
    return util.getElemFromLink(
        storage_domain_obj,
        link_name='images',
        attr='image',
        get_href=False,
    )


def verify_image_exists_in_storage_domain(storage_domain_name, image_name):
    """
    Verifies whether specified image exists in storage domain

    :param storage_domain_name: Storage domain name
    :type storage_domain_name: str
    :param image_name: Image name to look for
    :type image_name: str
    :return: True if image exists in storage domain, False otherwise
    :rtype: bool
    """
    return image_name in [
        image.get_name() for image in
        get_storage_domain_images(storage_domain_name)
    ]


class GlanceImage(object):
    """Represents an image resides in glance like storage domain.

     Args:
      image_name (str): image name as it appears in glance
      glance_repository_name: glance attached to your engine
    """

    def __init__(self, image_name, glance_repository_name, timeout=600):
        self._image_name = image_name
        self._glance_repository_name = glance_repository_name
        self._imported_disk_name = None
        self._imported_template_name = None
        self._disk_status = None
        self._destination_storage_domain = None
        self._is_imported_as_template = None
        self._timeout = timeout

    @property
    def image_name(self):
        return self._image_name

    @property
    def glance_repository_name(self):
        return self._glance_repository_name

    @property
    def imported_disk_name(self):
        return self._imported_disk_name

    @property
    def imported_template_name(self):
        return self._imported_template_name

    @property
    def disk_status(self):
        return self._disk_status

    @property
    def destination_storage_domain(self):
        return self._destination_storage_domain

    @property
    def is_imported_as_template(self):
        return self._is_imported_as_template

    def _is_import_success(self, timeout=None):

        if self.imported_disk_name is not None:
            if not wait_for_disks_status(
                    disks=[self.imported_disk_name],
                    timeout=timeout if timeout else self._timeout,
            ):
                return False

            self._disk_status = ENUMS['disk_state_ok']

            util.logger.info(
                "Disk %s have been imported successfully",
                self.imported_disk_name
            )

            return True

        return False

    def import_image(
            self, destination_storage_domain, cluster_name,
            new_disk_alias=None, new_template_name=None,
            import_as_template=False, async=False, return_response_body=False):
        """
        Description: Import images from glance type storage domain
        :param destination_storage_domain: Name of storage domain to import to
        :type destination_storage_domain: str
        :param cluster_name: Name of cluster to import to.
        :type cluster_name: str
        :param new_disk_alias: Name of imported disk
        :type new_disk_alias: str
        :param new_template_name: Name of imported template
        :type new_template_name: str
        :param import_as_template: True for template, False otherwise
        :type import_as_template: bool.
        :param async: True when not waiting for response, False otherwise
        :type async: bool
        :param return_response_body: False in case return type is bool, True
        to return to response body of import request
        :type return_response_body: bool
        :returns: status of creation of disk/template in
        case return_response_body=True, Response body (str) of import
        request in case return_response_body=False
        :rtype: bool or str
        """
        self._destination_storage_domain = destination_storage_domain
        self._is_imported_as_template = import_as_template
        self._imported_disk_name = new_disk_alias
        self._imported_template_name = new_template_name

        source_sd_obj = get_storage_domain_obj(self._glance_repository_name)
        destination_sd_obj = StorageDomain(name=destination_storage_domain)
        disk_obj = None
        template_obj = None

        all_images = util.getElemFromLink(
            source_sd_obj,
            link_name='images',
            attr='image',
            get_href=False
        )

        source_image_obj = filter(
            lambda x: x.get_name() == self.image_name, all_images
        )[0]

        cluster_obj = Cluster(name=cluster_name)

        if new_disk_alias:
            disk_obj = Disk(name=new_disk_alias)
        if new_template_name:
            template_obj = Template(name=new_template_name)

        action_params = dict(
            storage_domain=destination_sd_obj,
            cluster=cluster_obj, async=async,
            import_as_template=import_as_template,
            template=template_obj,
            disk=disk_obj,
            )
        status = (
            util.syncAction(source_image_obj, 'import', True, **action_params)
        )
        if not async and new_disk_alias and not return_response_body:
            return self._is_import_success()

        if async or new_disk_alias is None:
            util.logger.warn(
                "Note that if async is True or disk name unknown, you are "
                "responsible to check if the disk is added"
            )
        # TODO syncAction returns only the response body (not a boolean
        # code with the operation).
        # This should be change in the future when the syncAction
        # changes are in place (RHEVM-2549) to return a list of bool, response
        if not return_response_body:
            return bool(status)
        return status


def import_glance_image(
        glance_repository, glance_image, target_storage_domain,
        target_cluster, new_disk_alias=None, new_template_name=None,
        import_as_template=False, async=False, return_response_body=False
):
    """
    Import images from glance type storage domain

    :param glance_repository: Name of glance repository
    :type glance_repository: str
    :param glance_image: Name of glance image to import
    :type glance_image: str
    :param target_storage_domain: Name of the storage domain into which
    the glance image will be imported
    :type target_storage_domain: str
    :param target_cluster: Name of the cluster into which the glance
    image will be imported
    :type target_cluster: str
    :param new_disk_alias: New name for the imported disk
    :type new_disk_alias: str
    :param new_template_name: New name for the imported template
    :type new_template_name: str
    :param import_as_template: True for template, False otherwise
    :type import_as_template: bool
    :param async: False don't wait for response, wait otherwise
    :type async: bool
    :param return_response_body: False in case return type is bool, True to
    return to response body of import request
    :type return_response_body: bool
    :returns: status of creation of disk/template
    :rtype: bool
    """
    # Create a class instance for GlanceImage
    glance = GlanceImage(
        glance_image, glance_repository
    )
    util.logger.info("Importing glance image from %s", glance_repository)
    status = glance.import_image(
        destination_storage_domain=target_storage_domain,
        cluster_name=target_cluster,
        new_disk_alias=new_disk_alias, new_template_name=new_template_name,
        import_as_template=import_as_template, async=async,
        return_response_body=return_response_body
    )
    if not status:
        util.logger.error(
            "Failed to import image %s from glance repository %s",
            glance_image, glance_repository
        )
    return status


def get_number_of_ovf_store_disks(storage_domain):
    """
    Return the total number of OVF stores in the requested storage domain
    """
    all_disks = getStorageDomainDisks(storage_domain, False)
    return len(
        [disk for disk in all_disks if disk.get_alias() == OVF_STORE_DISK_NAME]
    )


def get_storagedomain_objects():
    """
    Get list of storage domain objects

    :return: List of storage domain objects
    :rtype: list
    """
    return util.get(abs_link=False)


def wait_storage_domain_status_is_unchanged(
        data_center_name, storage_domain_name, status,
        timeout=30, sleep=5
):
    """
    Waits for timeout amount of time and checks that the storage domain
    status doesn't change

    :param data_center_name: Name of data center
    :type data_center_name: str
    :param storage_domain_name: Name of the storage domain
    :type storage_domain_name: str
    :param status: Storage domain status to check
    :type status: str
    :param timeout: Maximum timeout [sec]
    :type timeout: int
    :param sleep: Sleep time [sec]
    :type sleep: int
    :return: True if storage domain status doesn't change, False otherwise
    :rtype: bool
    """
    try:
        for sd_object in TimeoutingSampler(
            timeout, sleep, getDCStorage, data_center_name, storage_domain_name
        ):
            current_status = sd_object.get_status()
            if current_status != status:
                util.logger.error(
                    "Storage domain %s changed to status %s",
                    storage_domain_name, current_status
                )
                return False
    except APITimeout:
        return True


# This is a W/A since ovirt doesn't support removal of glance images
# RFE for ovirt: https://bugzilla.redhat.com/show_bug.cgi?id=1317833
def remove_glance_image(image_id, glance_hostname, username, password):
    """
    Remove glance image

    TODO: There's not support to remove a glance image from ovirt,
    so it needs to connect to the server and remove it via glance cli

    :param image_id: ID of the image to be removed
    :type image_id: str
    :param glane_hostanme: Hostname of the glance server
    :type glance_hostname: str
    :param username: Username to connect to the glance server
    :type username: str
    :param password: Password to connect to the glance server
    :type password: str
    :return: True if the image was removed properly, False otherwise
    :rtype: bool
    """
    host = HostResource(ip=glance_hostname)
    user = User(username, password)
    host.users.append(user)
    host_executor = host.executor(user)
    cmd = "source keystonerc_admin && glance image-delete %s" % image_id
    rc, out, error = host_executor.run_cmd(cmd.split())
    if rc:
        util.logger.error(
            "Unable to remove image %s, error: %s", image_id, error
        )
    return not rc


def get_storage_domain_storage_type(storage_domain):
    """
    Gets the storage domain type e.g. iscsi, nfs...

    :param storage_domain: name of storage domain
    :type storage_domain: str
    :return: the name of the storage domain type
    :type: str
    """
    return get_storage_domain_obj(storage_domain).get_storage().get_type()


def get_storage_domains_by_type(storage_domain_type=DATA_DOMAIN_TYPE):
    """
    Get all storage domains of the specific type

    Args:
        storage_domain_type (srt): Storage domain type

    Returns:
        list: Storage domains objects
    """
    storage_domains = get_storage_domains()
    return [
        storage_domain for storage_domain in storage_domains
        if storage_domain.get_type() == storage_domain_type
    ]


def get_storage_domain_logical_units(storage_domain, attribute='name'):
    """
    Get the block storage domain logical units

    Args:
        storage_domain(str): The name or ID of the storage domain
        attribute(str): The method to get the domain: name or ID

    Returns:
        list: The storage domain's logical units
    """
    assert get_storage_domain_storage_type(storage_domain) in [
        ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp']
    ], "Storage domain is not from block type"

    return get_storage_domain_obj(
        storage_domain, attribute).get_storage().get_volume_group(
    ).get_logical_units().get_logical_unit()


def get_storage_domain_luns_ids(storage_domain, attribute='name'):
    """
    Get the block storage domain's LUNs IDs

    Args:
        storage_domain (str): The name or ID of the storage domain
        attribute (str): The method to get the domain: name or ID

    Returns:
        list: The LUNs IDs of the storage domain
    """
    sd_logical_units = get_storage_domain_logical_units(
        storage_domain, attribute
    )

    return [
        sd_logical_units[x].get_id() for x in range(len(sd_logical_units))
    ]


@generate_logs()
def get_storage_domain_luns_serials(storage_domain, attribute='name'):
    """
    Get the storage domain LUNs serial numbers

    Args:
        storage_domain (str): Name of storage domain
        attribute (str): The method to get the domain: name or ID
    Returns:
        list: The serial numbers of storage domain's LUNs
    """
    sd_logical_units = get_storage_domain_logical_units(
        storage_domain, attribute
    )

    return [
        sd_logical_units[x].get_serial() for x in range(len(sd_logical_units))
    ]


@generate_logs()
def get_logical_units_obj(logical_unit_ids):
    """
    Get logical units according to given logical units ids

    Args:
        logical_unit_ids (list): Logical units IDs

    Returns:
        LogicalUnits: Object of LogicalUnits
    """
    lu = LogicalUnits()
    for lu_id in logical_unit_ids:
        lu.add_logical_unit(LogicalUnit(id=lu_id))
    return lu


@generate_logs()
def reduce_storage_domain_luns(storage_domain, logical_unit_ids):
    """
    Reduce LUNs from given block based storage domain

    Args:
        storage_domain (str): Storage domain name
        logical_unit_ids (list): Logical units IDs to reduce from the storage
            domain

    Returns:
        bool: True in case of success, False otherwise
    """
    sd_obj = get_storage_domain_obj(storage_domain)

    lu = get_logical_units_obj(logical_unit_ids)
    return bool(
        util.syncAction(
            sd_obj, "reduceluns", positive=True, logical_units=lu
        )
    )


def get_iscsi_storage_domin_addresses(storage_domain):
    """
    Get all the addresses of all iscsi storage domain's logical units

    Args:
        storage_domain (Str): Storage domain name

    Returns:
         list: list of all storage domain's logical units addresses
    """
    try:
        storage_domain_object = get_storage_domain_obj(storage_domain)
        if storage_domain_object.get_storage().get_type() == 'iscsi':
            return [
                logical_unit.get_address() for logical_unit in
                get_storage_domain_logical_units(storage_domain=storage_domain)
            ]
        else:
            util.logger.error(
                "Storage domain: %s is not an iscsi storage domain"
            )
    except EntityNotFound:
        return []


@generate_logs()
def get_nfs_version(storage_domain):
    """
    Get nfs version for storage domain if storage domain is of type nfs

    Args:
        storage_domain (str): Name of storage domain

    Returns:
        str: nfs protocol version ('3.0', '4.0', '4.1', '4.2')
    """
    if not get_storage_domain_storage_type(storage_domain) == STORAGE_TYPE_NFS:
        return ''
    return get_storage_domain_obj(
        storage_domain).get_storage().get_nfs_version()


@generate_logs()
def refresh_storage_domain_luns(storage_domain, logical_unit_ids):
    """
    Refresh LUNs list on a given block based storage domain

    Args:
        storage_domain (str): Storage domain name
        logical_unit_ids (list): Logical units IDs to refresh their size on the
            storage domain

    Returns:
        bool: True in case of success, False otherwise
    """
    sd_obj = get_storage_domain_obj(storage_domain)
    lu = get_logical_units_obj(logical_unit_ids)
    return bool(
        util.syncAction(
            sd_obj, "refreshluns", positive=True, logical_units=lu
        )
    )


@generate_logs()
def update_ovf_store(storage_domain):
    """
    Initiate force update for the storage domain's OVF_STORE disks

    Args:
        storage_domain (str): Storage domain name

    Returns:
        bool: True if update succeded, False otherwise
    """
    sd_obj = get_storage_domain_obj(storage_domain)
    return bool(
        util.syncAction(sd_obj, "updateovfstore", positive=True)
    )


@generate_logs()
def get_storage_domain_ovf_store_disks(storage_domain):
    """
    Receive all OVF store disks from a storage domain

    Args:
        storage_domain (str): Name of the storage domain

    Returns:
        list: List of OVF store disk IDs
    """
    ovf_disks = []
    all_disks = getStorageDomainDisks(storage_domain, False)
    for disk in all_disks:
        if disk.get_name() == OVF_STORE_DISK_NAME:
            ovf_disks.append(disk.get_id())

    return ovf_disks
