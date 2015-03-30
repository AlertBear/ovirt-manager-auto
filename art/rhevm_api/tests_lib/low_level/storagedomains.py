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
import time
import re

from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, TimeoutingSampler
from art.core_api.validator import compareCollectionSize
from art.rhevm_api.tests_lib.low_level.disks import (
    getStorageDomainDisks,
    deleteDisk,
    waitForDisksGone,
    wait_for_disks_status,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    getHostCompatibilityVersion)
from art.rhevm_api.utils.storage_api import (
    getVmsInfo, getImagesList, getVolumeInfo, getVolumesList,
)
from art.rhevm_api.utils.test_utils import (
    validateElementStatus, get_api, searchForObj, getImageAndVolumeID,
    getAllImages)
from art.rhevm_api.utils.xpath_utils import XPathMatch
from utilities.utils import getIpAddressByHostName
from art.core_api import is_action
from art.test_handler.settings import opts
from art.test_handler import exceptions
from utilities import sshConnection, machine


ENUMS = opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']

StorageDomain = getDS('StorageDomain')
IscsiDetails = getDS('IscsiDetails')
Host = getDS('Host')
Storage = getDS('Storage')
LogicalUnit = getDS('LogicalUnit')
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

xpathMatch = is_action(
    'xpathStoragedomains', id_name='xpathMatch')(XPathMatch(util))


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
        hostObj = hostUtil.find(host)
        sd.set_host(Host(name=hostObj.get_name()))

    storage_type = kwargs.pop('storage_type', None)

    # Set storage domain metadata format - only for data domains
    if type_ and type_.lower() == ENUMS['storage_dom_type_data']:
        storage_format = kwargs.pop('storage_format', None)
        if host and storage_format is None:
            hostCompVer = getHostCompatibilityVersion(host)
            if not hostCompVer:
                util.logger.error("Can't determine storage domain version")
                return False
            if hostCompVer == '2.2':
                storage_format = ENUMS['storage_format_version_v1']
            elif hostCompVer == '3.0':
                # NFS does not support storage metadata format V2
                storage_format = (ENUMS['storage_format_version_v2'] if
                                  storage_type == ENUMS['storage_type_iscsi']
                                  else ENUMS['storage_format_version_v1'])
            else:
                storage_format = ENUMS['storage_format_version_v3']
        sd.set_storage_format(storage_format)

    if 'storage_connection' in kwargs:
        storage = Storage()
        storage.id = kwargs.pop('storage_connection')
        sd.set_storage(storage)
    elif storage_type == ENUMS['storage_type_local']:
        sd.set_storage(Storage(
            type_=storage_type, path=kwargs.pop('path', None)))
    elif storage_type == ENUMS['storage_type_nfs']:
        sd.set_format(kwargs.pop('format', None))
        sd.set_storage(
            Storage(
                type_=storage_type, path=kwargs.pop('path', None),
                address=kwargs.pop('address', None),
                nfs_version=kwargs.pop('nfs_version', None),
                nfs_retrans=kwargs.pop('nfs_retrans', None),
                nfs_timeo=kwargs.pop('nfs_timeo', None),
                mount_options=kwargs.pop('mount_options', None),
            )
        )
    elif storage_type == ENUMS['storage_type_iscsi']:
        lun = kwargs.pop('lun', None)
        lun_address = getIpAddressByHostName(kwargs.pop('lun_address', None))
        lun_target = kwargs.pop('lun_target', None)
        lun_port = kwargs.pop('lun_port', None)
        logical_unit = LogicalUnit(
            id=lun, address=lun_address, target=lun_target, port=lun_port)
        sd.set_storage(
            Storage(
                type_=storage_type,
                logical_unit=[logical_unit],
                override_luns=kwargs.pop('override_luns', None)
            )
        )
    elif storage_type == ENUMS['storage_type_fcp']:
        logical_unit = LogicalUnit(id=kwargs.pop('lun', None))
        sd.set_storage(Storage(logical_unit=logical_unit))
    elif (storage_type == ENUMS['storage_type_posixfs'] or
          storage_type == ENUMS['storage_type_gluster']):
        sd.set_storage(
            Storage(
                type_=storage_type, path=kwargs.pop('path', None),
                address=kwargs.pop('address', None),
                vfs_type=kwargs.pop('vfs_type', None),
                mount_options=kwargs.pop('mount_options', None),
            )
        )

    return sd


@is_action()
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
    try:
        sd, status = util.create(sd, positive, async=(not wait))
    except TypeError:
        util.logger.warning('Domain not created, wrong argument type passed. '
                            'Args: %s', kwargs)
        status = not positive
    return status


@is_action()
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
    storDomObj = util.find(storagedomain)
    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd, status = util.update(storDomObj, storDomNew, positive)
    return status


@is_action()
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
    storDomObj = util.find(storagedomain)

    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd, status = util.update(storDomObj, storDomNew, positive)

    return status


@is_action()
def searchForStorageDomain(positive, query_key, query_val, key_name, **kwargs):
    '''
    Description: search for storage domains by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in object equivalent to query_key
    Return: status (True if expected number is equal to found by search,
                    False otherwise)
    '''

    return searchForObj(util, query_key, query_val, key_name, **kwargs)


def getDCStorages(datacenter, get_href=True):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromLink(dcObj, get_href=get_href)


def getDCStorage(datacenter, storagedomain):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromElemColl(dcObj, storagedomain)


@is_action()
def attachStorageDomain(positive, datacenter, storagedomain, wait=True):
    '''
    Description: attach storage domain to data center
    Author: edolinin
    Parameters:
       * datacenter - name of data center to use
       * storagedomain - name of storage domain that should be attached
       * wait - if True, wait for the action to complete
    Return: status (True if storage domain was attached properly,
                    False otherwise)
    '''
    storDomObj = util.find(storagedomain)
    attachDom = StorageDomain(id=storDomObj.get_id())

    dcStorages = getDCStorages(datacenter)
    attachDom, status = util.create(
        attachDom, positive, collection=dcStorages, async=(not wait))

    dcObj = dcUtil.find(datacenter)
    if status and positive and wait:
        return dcUtil.waitForElemStatus(dcObj, "UP", 60, "datacenter")
    return status


@is_action()
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
    storDomObj = getDCStorage(datacenter, storagedomain)
    return util.delete(storDomObj, positive)


@is_action()
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
    status = util.syncAction(storDomObj, "activate", positive, async=async)
    if status and positive and wait:
        return waitForStorageDomainStatus(
            True, datacenter, storagedomain,
            ENUMS['storage_domain_state_active'],
            180,
        )
    return status


@is_action()
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

    async = 'false' if wait else 'true'
    status = util.syncAction(storDomObj, "deactivate", positive, async=async)
    if positive and status and wait:
        return waitForStorageDomainStatus(
            True, datacenter, storagedomain,
            ENUMS['storage_domain_state_maintenance'],
            180,
        )
    return status


@is_action()
def iscsiDiscover(positive, host, address):
    '''
    Description: run iscsi discovery
    Author: edolinin
    Parameters:
       * host - name of host
       * address - iscsi address
    Return: status (True if iscsi discovery succeeded, False otherwise)
    '''
    hostObj = hostUtil.find(host)

    iscsi = IscsiDetails(address=address)
    return hostUtil.syncAction(hostObj, "iscsidiscover", positive, iscsi=iscsi)


@is_action()
def iscsiLogin(positive, host, address, target, username=None, password=None):
    '''
    Description: run iscsi login
    Author: edolinin
    Parameters:
       * host - name of host
       * address - iscsi address
       * target - iscsi target name
       * username - iscsi username
       * password - iscsi password
    Return: status (True if iscsi login succeeded, False otherwise)
    '''
    hostObj = hostUtil.find(host)
    iscsi = IscsiDetails(address=address, target=target, username=username,
                         password=password)
    return hostUtil.syncAction(hostObj, "iscsilogin", positive, iscsi=iscsi)


@is_action()
def teardownStorageDomain(positive, storagedomain, host):
    '''
    Description: tear down storage domain before removing
    Author: edolinin
    Parameters:
       * storagedomain - storage domain that should be teared down
       * host - host to use
    Return: status (True if tear down succeeded, False otherwise)
    '''

    storDomObj = util.find(storagedomain)
    hostObj = hostUtil.find(host)

    sdHost = Host(id=hostObj.get_id())
    return util.syncAction(storDomObj.actions, "teardown", positive,
                           host=sdHost)


@is_action()
def removeStorageDomain(positive, storagedomain, host, format='false',
                        destroy=False):
    '''
    Description: remove storage domain
    Author: edolinin
    Parameters:
       * storagedomain - storage domain name that should be removed
       * host - host name/IP address to use
       * format - format the content of storage domain ('false' by default)
    Return: status (True if storage domain was removed properly,
                    False otherwise)
    '''
    format_bool = format.lower() == "true"

    storDomObj = util.find(storagedomain)
    hostObj = hostUtil.find(host)

    stHost = Host(id=hostObj.get_id())

    st = StorageDomain(host=stHost)
    if destroy:
        st.set_destroy(True)

    # Format domain if explicitly asked or
    # in case of data domain during a positive flow
    if format_bool or (positive and storDomObj.get_type() ==
                       ENUMS['storage_dom_type_data']):
        st.set_format('true')

    return util.delete(storDomObj, positive, st)


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


@is_action()
def importStorageDomain(positive, type, storage_type, address, path, host,
                        nfs_version=None, nfs_retrans=None, nfs_timeo=None,
                        vfs_type=None, storage_format=None,
                        clean_export_domain_metadata=False):
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

    sdStorage = Storage(type_=storage_type, address=address, path=path,
                        nfs_version=nfs_version, nfs_retrans=nfs_retrans,
                        nfs_timeo=nfs_timeo, vfs_type=vfs_type,
                        )
    h = Host(name=host)

    sd = StorageDomain(type_=type, host=h, storage=sdStorage)
    if storage_format:
        sd.set_storage_format(storage_format)
    sd, status = util.create(sd, positive)

    return status


@is_action()
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
    for dc in dcUtil.get(absLink=False):
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

    for sd_listed in util.get(absLink=False):
        if sd_listed.get_name() in storagedomains:
            removeStatus = removeStorageDomain(positive, sd_listed.get_name(),
                                               host, format)
            if not removeStatus:
                status = False

    return status


@is_action()
def waitForStorageDomainStatus(positive, dataCenterName, storageDomainName,
                               expectedStatus, timeOut=900, sleepTime=10):
    '''
     Description: Wait till the storage domain gets the desired status or till
                  timeout
     Author: egerman
     Parameters:
        * dataCenterName - name of data center
        * storageDomainName - storage domain name
        * expectedStatus - storage domain status to wait for
        * timeOut - maximum timeout [sec]
        * sleepTime - sleep time [sec]
     Return: status (True if storage domain get the desired status,
                     False otherwise)
    '''
    handleTimeout = 0
    while handleTimeout <= timeOut:
        if validateElementStatus(positive, 'storagedomain', COLLECTION,
                                 storageDomainName, expectedStatus,
                                 dataCenterName):
            return True
        time.sleep(sleepTime)
        handleTimeout += sleepTime

    return False


@is_action()
def isStorageDomainMaster(positive, dataCenterName, storageDomainName):
    '''
    The function isStorageDomainMaster checking if storage domain is a master
        dataCenterName = The name of datacenter
        storageDomainName = The name or ip address of storage domain
    return values : Boolean value (True/False ) True in case storage domain is
                    a master,otherwise False
    '''

    storDomObj = getDCStorage(dataCenterName, storageDomainName)
    attribute = 'master'
    if not hasattr(storDomObj, attribute):
        util.logger.error("Storage Domain %s doesn't have attribute %s",
                          storageDomainName, attribute)
        return False

    util.logger.info("isStorageDomainMaster - Master status of Storage Domain "
                     "%s is: %s", storageDomainName, storDomObj.master)
    isMaster = storDomObj.get_master()
    if positive:
        return isMaster
    else:
        return not isMaster


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
        floating_disks_list = [disk.get_alias() for disk in floating_disks]
        for disk in floating_disks_list:
            util.logger.info('Removing floating disk %s', disk)
            if not deleteDisk(True, alias=disk, async=False):
                return False
        util.logger.info('Ensuring all disks are removed')
        if not waitForDisksGone(
                True,
                ','.join(floating_disks_list),
                sleep=10
        ):
                return False
        util.logger.info(
            'All floating disks: %s removed successfully',
            floating_disks_list
        )


def deactivate_master_storage_domain(positive, datacenter):
    """
    Description: deactivate storage domain in a datacenter
    :param datacenter name
    :type datacenter : str
    :returns status True when successful
    :rtype: bool
    """

    status, master = findMasterStorageDomain(positive, datacenter)
    master_storage_domain = master['masterDomain']

    if master_storage_domain:
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
    :param host name
    :type host: str
    :param format_export True to format domains when removing
    :type format_export: bool
    :param format_iso True to format domains when removing
    :type format_iso: bool

    """
    for sd in sds:
        try:
            util.find(sd.get_name())
        except EntityNotFound:
            continue
        format_storage = True
        if sd.get_type() == ENUMS['storage_dom_type_iso']:
            format_storage = format_iso
        if sd.get_type() == ENUMS['storage_dom_type_export']:
            format_storage = format_export

        if not removeStorageDomain(
                True,
                sd.get_name(),
                host,
                str(format_storage)
        ):
            util.logger.error("Failed to remove %s", sd.get_name())
            return False

    return True


@is_action()
def execOnNonMasterDomains(positive, datacenter, operation, type):
    '''
    Description: Run operation on all storage domains that match type in
                 datacenter.
    Author: istein
    Parameters:
       * datacenter - datacenter name
       * operation  - 'activate' \ 'deactivate' \ 'detach'
       * type - storage domain type ('all', ENUMS[storage_dom_type_data],
                ENUMS[storage_dom_type_export], ENUMS[storage_dom_type_iso])
    Return: status (True if opearation suceeded, False otherwise)
    '''

    status = True

    sdObjList = getDCStorages(datacenter, False)

    # Find the Non-master & type storage domains.
    if type == 'all':
        sdObjects = filter(lambda sdObj: not sdObj.get_master(), sdObjList)
    else:
        sdObjects = filter(
            lambda sdObj: sdObj.get_type() == type and not sdObj.get_master(),
            sdObjList)

    dispatch_map = {
        'activate': activateStorageDomain,
        'deactivate': deactivateStorageDomain,
        'detach': detachStorageDomain,
    }

    # Get the right function to perform the operation.
    func = dispatch_map.get(operation, None)
    if not func:
        raise Exception("Unknown operation %s." % operation)

    # Do the operations.
    for sd in sdObjects:
        func_result = func(positive, datacenter, sd.name)
        if not func_result:
            status = False
            util.logger.error("Function %s failed", func)
    return status


@is_action()
def getDomainAddress(positive, storageDomain):
    '''
    Description: find the address of a storage domain
    Author: gickowic
    Parameters:
       * storageDomain - storage domain name
    return: address of the storage domain, empty string if name not found
    '''

    # Get the storage domain object
    try:
        storageDomainObject = util.find(storageDomain)

        # Check for iscsi storage domain
        if storageDomainObject.get_storage().get_type() == 'iscsi':
            # Return the address of the first LUN of the domain
            return positive, {'address': storageDomainObject.get_storage(
            ).get_volume_group().get_logical_unit()[0].get_address()}
        return positive, {
            'address': storageDomainObject.get_storage().get_address()}

    except EntityNotFound:
        return not positive, {'address': ''}


@is_action()
def findNonMasterStorageDomains(positive, datacenter):
    '''
    Description: find all non-master data storage domains
    Author: gickowic
    Parameters:
        * datacenter - datacenter name
    Return: List of non-master data storage domains, empty string if none found
    '''

    sdObjList = getDCStorages(datacenter, False)

    # Filter out master domain and ISO/Export domains
    nonMasterDomains = [sdObj.get_name() for sdObj in sdObjList if
                        sdObj.get_type() == ENUMS['storage_dom_type_data']
                        and not sdObj.get_master()]
    if nonMasterDomains:
        return positive, {'nonMasterDomains': nonMasterDomains}
    return not positive, {'nonMasterDomains': ''}


@is_action()
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
        sdObjList = util.get(absLink=False)

    isoDomains = [sdObj.get_name() for sdObj in sdObjList if
                  sdObj.get_type() == ENUMS['storage_dom_type_iso']]
    return isoDomains


@is_action()
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
        sdObjList = util.get(absLink=False)

    exportDomains = [sdObj.get_name() for sdObj in sdObjList if
                     sdObj.get_type() == ENUMS['storage_dom_type_export']]
    return exportDomains


@is_action()
def findMasterStorageDomain(positive, datacenter):
    '''
    Description: find the master storage domain.
    Author: istein
    Parameters:
       * datacenter - datacenter name
    Return: master domain storage domain if found, empty string ' ' otherwise)
    '''

    sdObjList = getDCStorages(datacenter, False)

    # Find the master DATA storage domain.
    masterResult = filter(lambda sdObj: sdObj.get_type() ==
                          ENUMS['storage_dom_type_data'] and
                          sdObj.get_master() in [True, 'true'], sdObjList)
    masterCount = len(masterResult)
    if masterCount == 1:
        return True, {'masterDomain': masterResult[0].get_name()}
    util.logger.error("Found %d master data domains, while one was expected.",
                      masterCount)
    return False, {'masterDomain': ' '}


@is_action()
def getStorageDomainFiles(positive, storagedomain, files_count):
    '''
     Description: fetch files in iso storage domain and compare to expected
     Author: edolinin
     Parameters:
        * storagedomain - name of storage domain
        * files_count - expected number of files
     Return: status (True if number of files is correct, False otherwise)
     '''

    storDomObj = util.find(storagedomain)
    storFiles = util.getElemFromLink(storDomObj, 'files', attr='file',
                                     get_href=True)
    return compareCollectionSize(storFiles, files_count, util.logger)


@is_action()
def getStorageDomainFile(positive, storagedomain, file):
    '''
     Description: fetch file in iso storage domain by name
     Author: edolinin
     Parameters:
        * storagedomain - name of storage domain
        * file - file name
     Return: status (True if file exists, False otherwise)
     '''

    storDomObj = util.find(storagedomain)

    fileObj = None
    if storDomObj:
        fileObj = fileUtil.getElemFromElemColl(storDomObj, file, 'files',
                                               'file')

    if fileObj:
        return positive
    else:
        return not positive


@is_action()
def getTemplateImageId(positive, vdsName, username, passwd, dataCenter,
                       storageDomain):
    '''
    Description: get template disk entrence, which is not exposed to REST.
    Author: istein
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
    Return: template Image Id, if found, False otherwise)
    '''

    vmIdList = []
    diskIdList = []

    # Get vms list on storageDomain
    dcObj = dcUtil.find(dataCenter)
    dcId = dcObj.get_id()
    storDomObj = util.find(storageDomain)
    storDomId = storDomObj.get_id()
    vmObjList = util.getElemFromLink(storDomObj, 'vms', attr='vm',
                                     get_href=True)
    for vmObj in vmObjList:
        vmIdList.append(vmObj.get_id())

    # Get vms info
    vmInfo = getVmsInfo(vdsName, username, passwd, dcId, storDomId)

    if vmInfo:
        # Get vms disk Id, by parsing vmInfo
        for vmId in vmIdList:
            vmInfoEntry = vmInfo[vmId]
            # Search for VM's disk ID inside VM Info
            found = re.search('<References>(.*)</References>', vmInfoEntry)
            found = found.group(1)
            found = re.match('(.*)/(.*)/(.*)', found)
            found = found.group(1)
            found = re.match('(.*)"(.*)', found)
            diskFound = found.group(2)
            diskIdList.append(diskFound)

        # Get Image Id list
        imageIdList = getImagesList(vdsName, username, passwd, storDomId)
        if imageIdList:
            # Search for the template image Id
            for imageId in imageIdList:
                found = False
                for diskId in diskIdList:
                    if imageId == diskId:
                        found = True
                if not found:
                    return imageId
    return False


@is_action()
def checkTemplateOnHost(positive, vdsName, username, passwd, dataCenter,
                        storageDomain, template, fake, noImages):
    """
    Description: Checks first volume on given storage domain of specified
                 template
    Author: istein, jlibosva
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - user password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
       * template - template name
       * fake - If template is expected to be fake set it to True, otherwise
                to False
       * noImage - set True, in case no image is expected to be in the storage
                   domain
    Return: True if volume Lagality is as expected \ No image is expected and
               it doesn't exist
            False otherwise
    """
    domain = util.find(storageDomain)
    templates = util.getElemFromLink(domain, 'templates', attr='template')
    dc = dcUtil.find(dataCenter)

    try:
        templateObj = [t for t in templates if t.get_name() == template][0]
    except IndexError:
        util.logger.error("Template %s was not found on storage domain %s",
                          template, storageDomain)
        return not positive

    template_id = templateObj.get_id()
    dc_id = dc.get_id()
    domain_id = domain.get_id()

    image_id, volume_id = getImageAndVolumeID(vdsName, username, passwd,
                                              dc_id, domain_id,
                                              template_id, 0)

    if noImages == 'true':
        if image_id is not None:
            util.logger.error("There are image(-s) on domain %s!",
                              storageDomain)
            return False
        return True
    elif image_id is None:
        util.logger.error("There are no images on domain %s", storageDomain)
        return False

    # Get volume Info
    volInfo = getVolumeInfo(vdsName, username, passwd, dc_id, domain_id,
                            image_id, volume_id)

    if not volInfo:
        msg = "failed to get volume info; DC {0}, SD{1}, Image {2}, Volume {3}"
        util.logger.error(msg.format(dc_id, domain.get_id(), image_id,
                                     volume_id))
        return False

    # Check volume info legality field
    legality = volInfo['legality']
    if ((fake == 'true' and legality != 'FAKE') or (fake == 'false' and
                                                    legality != 'LEGAL')):
        util.logger.error("Template legality is wrong: %s", legality)
        return False
    return True


@is_action()
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

    storagedomains = util.get(absLink=False)
    sdObj = filter(lambda sdObj: sdObj.get_name() == storagedomain,
                   storagedomains)
    return (len(sdObj) == 1) == positive


@is_action()
def checkStorageDomainParameters(positive, storagedomain, **kwargs):
    """
    Description: Checks whether given xpath is True
    Parameters:
        * storagedomain - domain's name
    Author: jlibosva
    Return: True if all keys and values matches given storage domain attributes
            False if any attribute is missing or if the attribute's value
            differs
    """
    domainObj = util.find(storagedomain)

    for attr in kwargs:
        if not hasattr(domainObj.storage, attr) or \
           getattr(domainObj.storage, attr) != kwargs[attr]:
            util.logger.debug("Attribute \"%s\" doesn't match with storage "
                              "domain \"%s\"", attr, storagedomain)
            return not positive

    return positive


@is_action()
def checkStorageFormatVersion(positive, storagedomain, version):
    """
    Description: Checks storage format version on given storage domain
    Parameters:
        * storagedomain - domain's name
        * version - expected version (e.g. "v2")
    Return: True if versions are the same and positive is True
            False if versions are not the same and positive is True
    """
    domainObj = util.find(storagedomain)

    return (domainObj.storage_format == version) == positive


@is_action()
def checkVmVolume(positive, vdsName, username, passwd, dataCenter,
                  storageDomain, vm, fake, noImages, exists=True):
    """
    Description: Checks first volume on given storage domain of specified
                 VM
    Author: jlibosva
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - user password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
       * vm - name of vm
       * fake - If volume is expected to be fake set it to True, otherwise
                to False
       * noImage - set True, in case no image is expected to be in the storage
                   domain
    Return: True if volume Lagality is as expected \ No image is expected and
               it doesn't exist
            False otherwise
    """
    return checkVolume(positive, vdsName, username, passwd, dataCenter,
                       storageDomain, vm, fake, noImages, exists)


@is_action()
def checkTemplateVolume(positive, vdsName, username, passwd, dataCenter,
                        storageDomain, template, fake, noImages, exists=True):
    """
    Description: Checks first volume on given storage domain of specified
                 template
    Author: jlibosva
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - user password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
       * template - name of template
       * fake - If volume is expected to be fake set it to True, otherwise
                to False
       * noImage - set True, in case no image is expected to be in the storage
                   domain
    Return: True if volume Lagality is as expected \ No image is expected and
               it doesn't exist
            False otherwise
    """
    return checkVolume(positive, vdsName, username, passwd, dataCenter,
                       storageDomain, template, fake, noImages, exists,
                       'templates')


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


def checkVolume(positive, vdsName, username, passwd, dataCenter, storageDomain,
                name, fake, noImages, exists, coll='vms'):
    """
    Description: Checks first volume on given storage domain of specified
                 name
    Author: istein, jlibosva
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - user password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
       * name - name of vm/template
       * fake - If volume is expected to be fake set it to True, otherwise
                to False
       * noImage - set True, in case no image is expected to be in the storage
                   domain
       * isVm - if True, checks for vm, False checks template
    Return: True if volume Lagality is as expected \ No image is expected and
               it doesn't exist
            False otherwise
    """
    domainObj = util.find(storageDomain)
    dcObj = dcUtil.find(dataCenter)
    objCollection = getObjList(domainObj, coll)

    try:
        Obj = [o for o in objCollection if o.name == name][0]
    except IndexError:
        if exists:
            util.logger.error("%s was not found on storage domain %s",
                              name, storageDomain)
            return not positive
        else:
            return positive

    obj_id = Obj.id
    dc_id = dcObj.id
    domain_id = domainObj.id

    images = getAllImages(vdsName, username, passwd, dc_id, domain_id, obj_id)

    if noImages:
        if images is not []:
            util.logger.error("There are image(-s) on domain %s!",
                              storageDomain)
            return not positive
        return positive
    elif images is []:
        util.logger.error("There are no images on domain %s",
                          storageDomain)
        return not positive

    image = images[0]
    try:
        volInfo = getVolumesList(vdsName, username, passwd, dc_id, domain_id,
                                 [image])[0]
    except IndexError:
        util.logger.error(
            "Can't find any volume of image DC %s, SD %s, Image %s",
            dataCenter, storageDomain, image)
        return not positive

    parentInfo = getVolumeInfo(vdsName, username, passwd, dc_id, domain_id,
                               image, volInfo['parent'])

    legality = parentInfo.get('legality', None)
    if legality is None:
        legality = volInfo['legality']

    if ((fake and legality != 'FAKE') or (not fake and legality != 'LEGAL')):
        util.logger.error("Template/Vm legality is wrong: %s", legality)
        return not positive
    return positive


@is_action("isStorageDomainActive")
def is_storage_domain_active(datacenter, domain):
    """
    Description: Checks if the storage domain is
    active in the given datacenter
    Author: gickowic
    Parameters:
        * datacenter - datacenter name
        * domain - domain name
    Returns: True if domain is active in the domain, false otherwise
    """
    sdObj = getDCStorage(datacenter, domain)
    active = sdObj.get_status().get_state()
    return active == ENUMS['storage_domain_state_active']


@is_action()
def getConnectionsForStorageDomain(storagedomain):
    """
    Description: Returns all connections added to a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
    Returns: List of Connection objects
    """
    sdObj = util.find(storagedomain)
    return connUtil.getElemFromLink(sdObj)


@is_action()
def addConnectionToStorageDomain(storagedomain, conn_id):
    """
    Description: Adds a connection to a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
        * conn_id - id of the connection
    Returns: true if operation succeeded
    """
    sdObj = util.find(storagedomain)
    connObj = connUtil.find(conn_id, attribute='id')
    conn_objs = util.getElemFromLink(
        sdObj, link_name='storageconnections', attr='storage_connection',
        get_href=True)
    _, status = connUtil.create(
        connObj, True, collection=conn_objs, async=True)
    return status


@is_action()
def detachConnectionFromStorageDomain(storagedomain, conn_id):
    """
    Description: Detach a connection from a storage domain
    Author: kjachim
    Parameters:
        * storagedomain - storage domain name
        * conn_id - id of the connection
    Returns: true if operation succeeded
    """
    sdObj = util.find(storagedomain)
    conn_objs = util.getElemFromLink(
        sdObj, link_name='storageconnections', attr='storage_connection')
    for conn in conn_objs:
        if conn.id == conn_id:
            # conn.href == "/api/storageconnections/[conn_id]" ...
            conn.href = "%s/storageconnections/%s" % (sdObj.href, conn_id)
            return util.delete(conn, True)
    return False


@is_action()
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
    sdObj = util.find(storagedomain)
    return sdObj.get_committed()


@is_action()
def get_total_size(storagedomain):
    """
    Description: Gets the total size of the storage domain (available + used)
    Author: gickowic
    Parameters:
        * storagedomain - name of the storage domain
    Returns: total size of the storage domain in bytes
    """
    sdObj = util.find(storagedomain)
    return sdObj.get_available() + sdObj.get_used()


@is_action()
def get_free_space(storagedomain):
    """
    Description: Gets the free space of the storage domain
    Author: ratamir
    Parameters:
        * storagedomain - name of the storage domain
    Returns: total size of the storage domain in bytes
    """
    sdObj = util.find(storagedomain)
    return sdObj.get_available() - sdObj.get_used()


@is_action()
def get_used_size(storagedomain):
    """
    Description: Gets the used size
    Author: cmestreg
    Parameters:
        * storagedomain - name of the storage domain
    Returns: used size of the storagedomain in bytes
    """
    sdObj = util.find(storagedomain)
    return sdObj.get_used()


@is_action()
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


@is_action()
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


@is_action()
def get_options_of_resource(host, password, address, path):
    """
    Calls mount on given host and returns options of given nfs resource

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host on which 'mount' should be called
        * *password*: root password on this host
        * *address*: address of the NFS server
        * *path*: path to the NFS resource on the NFS server

    **Returns**:  tuple (timeo, retrans, nfsvers)
                  or None if there is no such nfs mount
    """
    nfs_mounts = get_mounted_nfs_resources(host, password)
    return nfs_mounts.get((address, path), None)


@is_action()
def get_mounted_nfs_resources(host, password):
    """
    Gets info about all NFS resource mounted on specified host

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *host*: host on which 'mount' should be called
        * *password*: root password on this host

    **Returns**: dict: (address, path) ->  (timeo, retrans, nfsvers)
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


@is_action()
def _verify_one_option(real, expected):
    """ helper function for verification of one option
    """
    return expected is None or expected == real


@is_action()
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
        return ("timeo", expected_timeout, real_timeo)
    if not _verify_one_option(real_retrans, expected_retrans):
        return ("retrans", expected_retrans, real_retrans)
    if not _verify_one_option(real_nfsvers, expected_nfsvers):
        return ("nfsvers", expected_nfsvers, real_nfsvers)
    if expected_mount_options and "sync" in expected_mount_options:
        if not _verify_one_option(real_mount_options, True):
            return ("sync", True, real_mount_options)


def get_storagedomain_names():
    """
    Get list of storagedomain names

    **Returns**: List of storage domains
    """
    return [x.get_name() for x in util.get(absLink=False)]


@is_action()
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
        self.sd_type = ENUMS['storage_dom_type_data']
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


def getStorageDomainObj(storagedomain_name):
    """
    Returns storage domain object, fails with EntityNotFound
    """
    return util.find(storagedomain_name)


def wait_for_change_total_size(storagedomain_name, original_size=0,
                               sleep=5, timeout=50):
    """
    Waits until the total size changes from original_size
    Parameters:
        * storagedomain_name
        * original_size: size to compare to
    """
    for total_size in TimeoutingSampler(timeout, sleep, get_total_size,
                                        storagedomain_name):
        util.logger.info("Total size for %s is %d", storagedomain_name,
                         total_size)
        if total_size != original_size:
            return True

    util.logger.warning("Total size for %s didn't update from %d",
                        storagedomain_name, original_size)
    return False


def getStorageDomainNamesForType(datacenter_name, storage_type):
    """
    Returns a list of names of available data storage domain of storage_type
     * datacenter_name: name of datacenter
     * storage_type: type of storage (nfs, iscsi, ...)
    """
    sdObjList = getDCStorages(datacenter_name, False)

    return [sdObj.get_name() for sdObj in sdObjList if
            sdObj.get_type() == ENUMS['storage_dom_type_data']
            and sdObj.get_storage().get_type() == storage_type
            and sdObj.get_status().get_state() ==
            ENUMS['storage_domain_state_active']]


class GlanceImage(object):
    """Represents an image resides in glance like storage domain.

     Args:
      image_name (str): image name as it appears in glance
      glance_repository_name: glance attached to your engine
    """

    def __init__(self, image_name, glance_repository_name):
        self._image_name = image_name
        self._glance_repository_name = glance_repository_name
        self._imported_disk_name = None
        self._imported_template_name = None
        self._disk_status = None
        self._destination_storage_domain = None
        self._is_imported_as_template = None
        self._timeout = 600

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

    def _is_import_success(self):

        if self.imported_disk_name is not None:
            if not wait_for_disks_status(
                    disks=[self.imported_disk_name],
                    timeout=self._timeout
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
            import_as_template=False, async=False):
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
        :param async: False don't wait for response, wait otherwise
        :type async: bool
        :returns: status of creation of disk/template
        :rtype: bool
        """
        self._destination_storage_domain = destination_storage_domain
        self._is_imported_as_template = import_as_template
        self._imported_disk_name = new_disk_alias
        self._imported_template_name = new_template_name

        source_sd_obj = util.find(self._glance_repository_name)
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

        status = util.syncAction(
            source_image_obj,
            'import',
            True,
            **action_params
        )

        if not async and new_disk_alias:
            return self._is_import_success()

        util.logger.warn(
            "Note that async is %s or disk name unknown, you are responsible "
            "to check if the disk is added", async
        )

        return status
