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
import os
from utilities.utils import readConfFile
from core_api.apis_exceptions import EntityNotFound
from core_api.validator import compareCollectionSize
import time
import re
import utilities.machine as hostUtil
from rhevm_api.tests_lib.datacenters import addDataCenter,removeDataCenter
from rhevm_api.tests_lib.hosts import deactivateHost, removeHost, getHostCompatibilityVersion
from rhevm_api.tests_lib.clusters import addCluster, removeCluster
from rhevm_api.tests_lib.hosts import addHost,waitForHostsStates,getHost
from rhevm_api.tests_lib.clusters import isHostAttachedToCluster,attachHostToCluster,connectClusterToDataCenter
#from rhevm_api.storage_api import getVmsInfo,getImagesList,getVolumeInfo
from rhevm_api.tests_lib.vms import removeVms, stopVms
from rhevm_api.tests_lib.templates import removeTemplates
from rhevm_api.utils.test_utils import validateElementStatus, get_api
from utilities.utils import getIpAddressByHostName
from core_api.apis_utils import getDS
from rhevm_api.utils.xpath_utils import XPathMatch
from rhevm_api.utils.test_utils import searchForObj

ELEMENTS = os.path.join(os.path.dirname(__file__), '../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')

StorageDomain = getDS('StorageDomain')
IscsiDetails = getDS('IscsiDetails')
Host = getDS('Host')
Storage = getDS('Storage')
LogicalUnit = getDS('LogicalUnit')

ELEMENT = 'storage_domain'
COLLECTION = 'storagedomains'
util = get_api(ELEMENT, COLLECTION)
dcUtil = get_api('data_center', 'datacenters')
hostUtil = get_api('host', 'hosts')
templUtil = get_api('template', 'templates')
vmUtil = get_api('vm', 'vms')
clUtil = get_api('cluster', 'clusters')
fileUtil = get_api('file', 'files')

xpathMatch = XPathMatch(util)


def _prepareStorageDomainObject(positive, **kwargs):

    sd = StorageDomain()

    name = kwargs.pop('name', None)
    if name:
        sd.set_name(name)

    type = kwargs.pop('type', None)
    if type:
        sd.set_type(type)

    host = kwargs.pop('host', None)
    if host:
        hostObj = hostUtil.find(host)
        sd.set_host(Host(name=hostObj.get_name()))

    storage_type = kwargs.pop('storage_type', None)

    if storage_type == ENUMS['storage_type_local']:
        sd.set_storage(Storage(type_=storage_type, path=kwargs.pop('path', None)))
    elif storage_type == ENUMS['storage_type_nfs']:
        sd.set_storage(Storage(type_=storage_type, path=kwargs.pop('path', None),
                            address=kwargs.pop('address', None),
                            nfs_version=kwargs.pop('nfs_version', None),
                            nfs_retrans=kwargs.pop('nfs_retrans', None),
                            nfs_timeo=kwargs.pop('nfs_timeo', None),
                            mount_options=kwargs.pop('mount_options', None)))
    elif storage_type == ENUMS['storage_type_iscsi']:
        lun = kwargs.pop('lun', None)
        lun_address = getIpAddressByHostName(kwargs.pop('lun_address', None))
        lun_target = kwargs.pop('lun_target', None)
        lun_port = kwargs.pop('lun_port', None)
        logical_unit = LogicalUnit(id=lun, address=lun_address,
                        target=lun_target, port=lun_port)
        sd.set_storage(Storage(type_=storage_type, logical_unit=[logical_unit]))
        
        if type and type.lower() == 'data':
            if 'iscsi_storage_format' in kwargs:
                sd.set_storage_format(kwargs.pop('iscsi_storage_format'))
            elif host:
                status, hostCompVer = getHostCompatibilityVersion(positive, host)
                if not status:
                    util.logger.error("Can't determine storage domain version")
                    return False
                if hostCompVer['hostCompatibilityVersion'] == '2.2':
                    sd.set_storage_format(ENUMS['storage_format_version_v1'])
                else:
                    sd.set_storage_format(ENUMS['storage_format_version_v2'])
    elif storage_type == ENUMS['storage_type_fcp']:
        logical_unit = LogicalUnit(id=kwargs.pop('lun', None))
        sd.set_storage(Storage(logical_unit=logical_unit))
  
    return sd


def addStorageDomain(positive, iscsi_storage_format=None, wait=True, **kwargs):
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
       * wait - if True, wait for the action to complete
    Return: status (True if storage domain was added properly,
                    False otherwise)
    '''
    sd = _prepareStorageDomainObject(positive, **kwargs)
    sd, status = util.create(sd, positive, async=(not wait))
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
    storDomObj = util.find(storagedomain)
    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd,status = util.update(storDomObj, storDomNew, positive)
    return status


def extendStorageDomain(positive, storagedomain, host, **kwargs):
    '''
    Description: extend existing iscsi/fcp storage domain
    Author: edolinin
    Parameters:
       * storagedomain - storage domain name
       * storage_type - storage type (ENUMS['storage_type_iscsi'],
        ENUMS['storage_type_fcp'])
       * lun - lun id
       * host - storage domain host
       * lun_address - iscsi lun address
       * lun_target - iscsi lun target name
       * lun_port - iscsi lun port
    Return: status (True if storage domain was extended properly,
                    False otherwise)
    '''
    storDomObj = util.find(storagedomain)
    # just check for host existence
    hostUtil.find(host)
    
    storDomNew = _prepareStorageDomainObject(positive, **kwargs)
    sd,status = util.update(storDomObj, storDomNew, positive)

    return status


def searchForStorageDomain(positive, query_key, query_val, key_name, **kwargs):
    '''
    Description: search for storage domains by desired property
    Author: edolinin
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - name of the property in object equivalent to query_key
    Return: status (True if expected number is equal to found by search, False otherwise)
    '''

    return searchForObj(util, query_key, query_val, key_name, **kwargs)


def getDCStorages(datacenter, get_href=True):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromLink(dcObj, get_href=get_href)


def getDCStorage(datacenter, storagedomain):

    dcObj = dcUtil.find(datacenter)
    return util.getElemFromElemColl(dcObj, storagedomain)


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
    attachDom, status = util.create(attachDom, positive, collection=dcStorages,
                                                            async=(not wait))

    dcObj = dcUtil.find(datacenter)
    if status and positive and wait:
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
    storDomObj = getDCStorage(datacenter, storagedomain)
    return util.delete(storDomObj, positive)


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

    if positive and validateElementStatus(positive, 'storagedomain', COLLECTION,
                                    storagedomain, 'active', datacenter):
        util.logger.warning("Storage domain %s already activated" % (storagedomain))
        return True

    async = 'false' if wait else 'true'
    status = util.syncAction(storDomObj, "activate", positive, async=async)
    if status and positive and wait:
        return util.waitForElemStatus(storDomObj, "active", 180,
                            collection=getDCStorages(datacenter, False))
    return status


def deactivateStorageDomain(positive, datacenter, storagedomain, wait=True):
    '''
    Description: deactivate storage domain
    Author: edolinin
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
        return util.waitForElemStatus(storDomObj, "inactive maintenance", 180,
                                    collection=getDCStorages(datacenter, False))
    return status


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
    return util.syncAction(storDomObj.actions, "teardown", positive, host=sdHost)


def removeStorageDomain(positive, storagedomain, host, format='false'):
    '''
    Description: remove storage domain
    Author: edolinin
    Parameters:
       * storagedomain - storage domain name that should be removed
       * host - host name/IP address to use
       * format - format the content of storage domain ('false' by default)
    Return: status (True if storage domain was removed properly, False otherwise)
    '''
    format_bool = format.lower() == "true"
    
    storDomObj = util.find(storagedomain)
    hostObj = hostUtil.find(host)

    stHost = Host(id=hostObj.get_id())

    st = StorageDomain(host=stHost)

    # Format domain if explicitly asked or
    # in case of data domain during a positive flow
    if format_bool or (positive and \
                       storDomObj.get_type() == ENUMS['storage_dom_type_data']):
        st.set_format('true')

    return util.delete(storDomObj, positive, st)


def importStorageDomain(positive, type, storage_type, address, path, host):
    '''
    Description: import storage domain (similar to create function, but not providing name)
    Author: edolinin
    Parameters:
       * type - storage domain type (DATA,EXPORT, etc.)
       * storage_type - storage type (NFS,ISCSI,etc.)
       * address - storage domain address (for ISCSI)
       * path - storage domain path (for NFS)
       * host - host to use
    Return: status (True if storage domain was imported properly, False otherwise)
    '''
   
    sdStorage = Storage(type_=storage_type, address=address, path=path)
    h = Host(name=host)

    sd = StorageDomain(type_=type, host=h, storage=sdStorage)
    sd, status = util.create(sd, positive)

    return status


def removeStorageDomains(positive, storagedomains, host, format='true'):
    '''
    Description: remove storage domains
    Author: edolinin
    Parameters:
       * storagedomains - comma-separated list of storage domain names
       * host - host name/IP address to use
       * format - format the content of storage domain ('true' by default)
    Return: status (True if storage domains were removed properly, False otherwise)
    '''
    status = True
    sdList = storagedomains.split(',')
    for dc in dcUtil.get(absLink=False):
        sds = util.getElemFromLink(dc, get_href=True)
        # detach and remove non master domains
        for sd in sds:
            if sd.get_name() in sdList:
                #   if hasattr(sd, "master"):
                if sd.get_master() == 'true':
                        continue
                else:
                    deactivateStatus = deactivateStorageDomain(positive,
                                            dc.get_name(),sd.get_name())
                    detachStatus = detachStorageDomain(positive, 
                                    dc.get_name(),sd.get_name())
                    if not detachStatus:
                        status = False

    for sdlisted in util.get(absLink=False):
        if sdlisted.name in sdList:
            removeStatus = removeStorageDomain(positive, sdlisted.get_name(), host, format)
            if not removeStatus:
                status = False

    return status


def waitForStorageDomainStatus(positive, dataCenterName, storageDomainName, 
                               expectedStatus, timeOut=900, sleepTime=10):
    '''
     Description: Wait till the storage domain gets the desired status or till timeout
     Author: egerman
     Parameters:
        * dataCenterName - name of data center
        * storageDomainName - storage domain name
        * expectedStatus - storage domain status to wait for
        * timeOut - maximum timeout [sec]
        * sleepTime - sleep time [sec]
     Return: status (True if storage domain get the desired status, False otherwise)
    '''
    handleTimeout = 0
    while handleTimeout <= timeOut:
        if validateElementStatus(positive, 'storagedomain', COLLECTION, storageDomainName,
                                 expectedStatus, dataCenterName):
            return True
        time.sleep(sleepTime)
        handleTimeout += sleepTime

    return False


def isStorageDomainMaster(positive, dataCenterName, storageDomainName):
    '''
    The function isStorageDomainMaster checking if storage domain is a master
        dataCenterName = The name of datacenter
        storageDomainName = The name or ip address of storage domain
    return values : Boolean value (True/False ) True in case storage domain is a master,otherwise False
    '''
    
    storDomObj = getDCStorage(dataCenterName, storageDomainName)
    attribute='master'
    if not hasattr(storDomObj, attribute):
        util.logger.error("Storage Domain " + storageDomainName + \
                            " doesn't have attribute " + attribute)
        return False

    util.logger.info("isStorageDomainMaster - Master status of Storage Domain " + \
                    storageDomainName  + " is: " + storDomObj.master.upper())
    isMaster = storDomObj.get_master().lower() == 'true'
    if positive:
        return isMaster
    else:
        return not isMaster
    

def createDatacenter(positive, hosts, cpuName, username, password, datacenter, 
                     storage_type, cluster, version, dataStorageDomains='', address='',
                     lun_address='', lun_target='', luns='', lun_port='',
                     sdNameSuffix='_data_domain'):
    """
    Function creates data center.
        positive           = positive
        hosts              = host\s name\s or ip\s. A single host, or a list of hosts separated by comma.
        username           = user name
        password           = password
        datacenter         = data center name
        storage_type       = 'NFS'\'iSCSI'\'FCP'
        cluster            = cluster name
        dataStorageDomains = NFS data storage domain path list
        address            = NFS storage domain address
        lun_address        = address of iSCSI machine
        lun_target         = LUN target
        luns               = lun\s id. A single lun id, or a list of luns, separeted by comma.
        lun_port           = lun port
        sdNameSuffix    = suffix for storage domain name (default is '_data_domain')
        version            = data center supported version (2.2 or 3.0)
    """

    storageDomainList = []
    if dataStorageDomains:
        storageArr = dataStorageDomains.split(',')
    if luns:
        storageArr = luns.split(',')
    if hosts:
        hostArr = hosts.split(',')
        host = hostArr[0]
    if password:
        passwordArr = password.split(',')
        password = passwordArr[0]
    if lun_address:
        lunAddrArr = lun_address.split(',')
    if lun_target:
        lunTgtArr = lun_target.split(',')
    
    #Add dataCenter
    try:
        dcUtil.find(datacenter)
    except EntityNotFound:
        util.logger.info("Create an empty %s Storage Pool %s" %  (storage_type, datacenter))
        if not addDataCenter(positive, datacenter, storage_type, version, datacenter):
            util.logger.error('Creating an empty Storage Pool %s failed' % datacenter)
            return False

    #Add cluster
    try:
        clUtil.find(cluster)
    except EntityNotFound:
        util.logger.info("Create cluster %s" % cluster)
        if not addCluster(positive=positive, name=cluster, cpu=cpuName,
                            data_center=datacenter, version=version):
            util.logger.error("Creating cluster %s failed" % cluster)
            return False

    #Add Host\s
    for index, host in enumerate(hostArr):
        try:
            hostUtil.find(host)
        except EntityNotFound:
            util.logger.info("Add host %s" % host)
            ipAddress = getIpAddressByHostName(host)
            if not addHost(positive=positive, name=host, address=ipAddress,
            root_password=passwordArr[index], port='54321', cluster=cluster, wait=False):
                util.logger.error("Add host %s failed" % host)
                return False

    if not waitForHostsStates(positive=positive, names=hosts, states='up'):
        util.logger.error("wait For hosts State UP failed")
        return False

    #Check if host\s attached to cluster
    for host in hostArr:
        util.logger.info("Check if host %s attached to cluster %s" % (host, cluster))
        if not isHostAttachedToCluster(positive, host, cluster) and not attachHostToCluster(positive, host, cluster):
            util.logger.error("Attach host %s to cluster %s failed" % (host, cluster))
            return False

    #Connect cluster to dataCenter
    util.logger.info('Connect cluster to dataCenter')
    if not connectClusterToDataCenter(positive, cluster, datacenter):
        util.logger.error("Connect cluster %s to dataCenter %s failed" % (cluster, datacenter))
        return False

    #iSCSI discover and login
    if storage_type == ENUMS['storage_type_iscsi']:
        for index, lunAddr in enumerate(lunAddrArr):
            util.logger.info('Run ISCSI discovery and login')
            if not iscsiDiscover(positive, host, lunAddr):
                util.logger.error("iscsiDiscover failed for storage %s" % lunAddr)
                return False
            if not iscsiLogin(positive, host, lunAddr, lunTgtArr[index]):
                util.logger.error("iscsiLogin failed for storage %s and target %s" % (lunAddr, lunTgtArr[index]))
                return False

    #create data storage domains
    util.logger.info('Create data storage domains')
    sdNamePref = datacenter + sdNameSuffix
    domainType = ENUMS['storage_dom_type_data']
    
    for index, storagePath in enumerate(storageArr):
        sdName = sdNamePref + str(index)
        addStorageDomainLogMassageTemplate = "Add {0} storage domain parameters: positive=%s, name=%s, type=%s, storage_type=%s, host=%s {1}.." % (positive, sdName, domainType, storage_type, host)
        logger.info("Create storage domain %s from storage %s" % (sdName, storagePath))
        if storage_type == ENUMS['storage_type_nfs']:
            util.logger.info(addStorageDomainLogMassageTemplate.format(ENUMS['storage_type_nfs'], "path=%s, address=%s" % (storagePath, address)))
            status = addStorageDomain(positive=positive, name=sdName, type=domainType, storage_type=storage_type, path=storagePath, address=address, host=host)
        elif storage_type == ENUMS['storage_type_iscsi']:
            util.logger.info(addStorageDomainLogMassageTemplate.format(ENUMS['storage_type_iscsi'], "lun=%s, lun_address=%s, lun_target=%s, lun_port=%s" % (storagePath, lunAddrArr[index], lunTgtArr[index], lun_port)))
            status = addStorageDomain(positive=positive, name=sdName, type=domainType, storage_type=storage_type, host=host, lun=storagePath, lun_address=lunAddrArr[index], lun_target=lunTgtArr[index], lun_port=lun_port)
        elif storage_type == ENUMS['storage_type_fcp']:
            util.logger.info(addStorageDomainLogMassageTemplate.format(ENUMS['storage_type_fcp'], "lun=%s" % (storagePath)))
            status = addStorageDomain(positive=positive, name=sdName, type=domainType, storage_type=storage_type, host=host, lun=storagePath)

        if not status:
            util.logger.error("Add Storage domain %s failed" % sdName)
            return False
        storageDomainList.append(sdName)

    #attach storage domains
    for sd in storageDomainList:
        util.logger.info("Attach storage domain %s to data center %s" % (sd, datacenter))
        if not attachStorageDomain(positive=positive, datacenter=datacenter, storagedomain=sd):
            logger.error("Attach storage domain %s to data center %s failed" % (sd, datacenter))
            return False
        storDomObj = util.find(links['storagedomains'],sd)
        # Non master storage domains, require activation
        if storDomObj.master == 'false':
            if not activateStorageDomain(positive=positive, datacenter=datacenter, storagedomain=sd):
                util.logger.error("Activate storage domain %s failed", sd)
                return False
    return True


def cleanDataCenter(positive,datacenter,formatIsoStorage='false'):
    '''
    Description: Remove all elements in data center: dataCenter, storage domains, hosts & cluster.
    Author: istein
    Parameters:
       * datacenter - data center name
       * formatIsoStorage - Determine if ISO storage domain will be formatted or not (true/false).
    '''
    
    status = True
    vmList = []
    templList = []
    sd_attached = False

    spmExist,spmHostName = getHost(positive, datacenter, True)

    if not spmExist:
        util.logger.error("No SPM host found in data center %s, storage domains can't be removed, exit cleanDataCenter" % datacenter)
        return False
    spmHostName = spmHostName['hostName']

    spmHostObject = hostUtil.find(spmHostName)
    clId = spmHostObject.get_cluster().get_id()

    util.logger.info('Remove VMs, if any, connected to cluster')
    vmObjList = vmUtil.get(absLink=False)
    vmsConnectedToCluster = filter(lambda vmObj: vmObj.get_cluster().get_id() == clId, vmObjList)
    if vmsConnectedToCluster:
        [vmList.append(vmObj.get_name()) for vmObj in vmsConnectedToCluster]
        if not stopVms(','.join(vmList)):
            return False

        if not removeVms(positive, ','.join(vmList)):
            return False

    util.logger.info('Remove Templates, if any, connected to cluster')
    templObjList = templUtil.get(absLink=False)
    templConnectedToCluster = filter(lambda templObj: templObj.get_cluster().get_id() == clId, templObjList)
    if templConnectedToCluster:
        [templList.append(templObj.name) for templObj in templConnectedToCluster]
        rmTemplStatus = removeTemplates(positive, ','.join(templList))
        if not rmTemplStatus:
            return False

    util.logger.info("Find all non master storage domains")
    sdObjList = getDCStorages(datacenter)
    
    nonMasterSdObjects = filter(lambda sdObj: sdObj.get_master() == 'false', sdObjList)

    util.logger.info("Find Master Domain")
    st, masterDomain = findMasterStorageDomain(positive, datacenter)
    masterSd = masterDomain['masterDomain']

    util.logger.info("Deactivate & detach non master storage domains")
    if nonMasterSdObjects:
        for sd in nonMasterSdObjects:
            if validateElementStatus(positive, 'storagedomain', sd.get_name(), 'active', datacenter):
                deactivateStatus = deactivateStorageDomain(positive,datacenter, sd.get_name())
                if not deactivateStatus:
                    util.logger.error("Deactivate storage domain %s Failed" % sd.get_name())
                    status = False
            detachStatus = detachStorageDomain(positive,datacenter,sd.get_name())
            if not detachStatus:
                util.logger.error("Detach storage domain %s Failed" % sd.get_name())
                status = False
    else:
        util.logger.info("No non master storage domains found")

    util.logger.info("Deactivate master storage domain")
    if masterSd:
        if validateElementStatus(positive, 'storagedomain', masterSd, 'active', datacenter):
            deactivateStatus = deactivateStorageDomain(positive, datacenter, masterSd)
            if not deactivateStatus:
                util.logger.error("Deactivate master storage domain %s Failed" % masterSd)
                status = False
    else:
        util.logger.info("Error in master storage domain search")
                
    util.logger.info("Remove data center")
    if not removeDataCenter(positive, datacenter):
        util.logger.error("Remove data center %s failed" % datacenter)
        status = False

    util.logger.info("Remove storage domains")
    for sd in sdObjList:
        # If storage domain do not exist skip to the next one.
        try:
            sdObj = util.find(sd.get_name())
        except EntityNotFound:
            continue
        sd_attached = False
        # If storage domain is still attached to any dataCenter skip to next one
        for dc in dcUtil.get(absLink=False):
            sdObjList = util.getElemFromLink(dc, get_href=True)
            for storageDomain in sdObjList:
                if storageDomain.get_name() == sd.get_name():
                    sd_attached = True

        if not sd_attached:
            if sd.get_type() == ENUMS['storage_dom_type_iso']:
                removeStatus = removeStorageDomain(positive, sd.get_name(), spmHostName, formatIsoStorage)
            else:
                removeStatus = removeStorageDomain(positive, sd.get_name(), spmHostName, 'true')
            if not removeStatus:
                util.logger.error("Remove storage domain %s Failed" % sd.get_name())
                status = False

    util.logger.info("Deactivate all non maintenance hosts, connected to SPM host's cluster")
    hostObjList = hostUtil.get(absLink=False)
    hostsConnectedToCluster = filter(lambda hostObj: hostObj.get_cluster().get_id() == clId, hostObjList)
    if hostsConnectedToCluster:
        nonMaintHosts = filter(lambda hostObj: hostObj.get_status().get_state() != "MAINTENANCE", hostsConnectedToCluster)
        if nonMaintHosts:
            for hostObj in nonMaintHosts:
                if not deactivateHost(positive, hostObj.get_name()):
                    util.logger.error("Deactivate Host %s Failed" % hostObj.get_name())
                    status = False
        for hostObj in hostsConnectedToCluster:
            if not removeHost(positive, hostObj.name):
                util.logger.error("Remove Host %s Failed" % hostObj.get_name())
                return False

    util.logger.info("Remove cluster")
    clObj = clUtil.find(clId, 'id')
    cluster = clObj.get_name()
    if not removeCluster(positive, cluster):
        util.logger.error("Remove cluster %s Failed" % cluster)
        status = False
    return status


def execOnNonMasterDomains(positive, datacenter, operation, type):
    '''
    Description: Run operation on all storage domains that match type in datacenter.
    Author: istein
    Parameters:
       * datacenter - datacenter name
       * operation  - 'activate' \ 'deactivate' \ 'detach' \ 'attach'
       * type - storage domain type ('all', ENUMS[storage_dom_type_data], ENUMS[storage_dom_type_export], ENUMS[storage_dom_type_iso])
    Return: status (True if opearation suceeded, False otherwise)
    '''

    status = True
    
    sdObjList = getDCStorages(datacenter)
    
    # Find the Non-master & type storage domains.
    if type == 'all':
        sdObjects = filter(lambda sdObj: sdObj.get_master() == 'false', sdObjList)
    else:
        sdObjects = filter(lambda sdObj: sdObj.get_type() == type and \
                                sdObj.get_master() == 'false', sdObjList)

    dispatch_map = {
        'activate' : activateStorageDomain,
        'deactivate' : deactivateStorageDomain,
        'detach' : detachStorageDomain,
        'attach' : attachStorageDomain
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
            util.logger.error("Function %s failed" % func)
    return status


def findMasterStorageDomain(positive,datacenter):
    '''
    Description: find the master storage domain.
    Author: istein
    Parameters:
       * datacenter - datacenter name
    Return: master domain storage domain if found, empty string ' ' otherwise)
    '''
    
    sdObjList = getDCStorages(datacenter)

    # Find the master DATA storage domain.
    masterResult = filter(lambda sdObj: sdObj.get_type() == \
        ENUMS['storage_dom_type_data'] and sdObj.get_master() == 'true', sdObjList)
    masterCount = len(masterResult)
    if masterCount == 1:
        return True, {'masterDomain' : masterResult[0].get_name()}
    util.logger.error("Found %d master data domains, while one was expected." % masterCount)
    return False, {'masterDomain' : ' '}


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
    storFiles = util.getElemFromLink(storDomObj, 'files', attr='file', get_href=True)
    return compareCollectionSize(storFiles, files_count, util.logger)


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
    fileObj = fileUtil.getElemFromElemColl(storDomObj, file, 'files', 'file')
    
    if fileObj:
        return positive
    else:
        return not positive


def getTemplateImageId(positive, vdsName, username, passwd, dataCenter, storageDomain):
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
    vmObjList = util.getElemFromLink(storDomObj, 'vms', attr='vm', get_href=True)
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


def checkTemplateOnHost(positive, vdsName, username, passwd, dataCenter, storageDomain, template, fake, noImages):
    '''
    Description: check template on host get template disk entrence, which is not exposed to REST.
    Author: istein
    Parameters:
       * vdsName - host name
       * username - user name
       * passwd - user password
       * dataCenter - data center name
       * storageDomain - name of the storage domain
       * template - template name
       * fake - If template is expected to be fake set it to True, otherwise to False
       * noImage - set True, in case no image is expected to be in the storage domain
    Return: True if volume Lagality is as expected \ No image is expected, and it is not exist,
            False otherwise)
    '''

    # Get template's volume Id
    templObj = templUtil.find(template)
    volumeObj = util.getElemFromLink(templObj, 'disks', attr='disk', get_href=True)
    numOfDisks = len(volumeObj)
    if numOfDisks != 1:
        util.logger.error("Template %s is expected to have a single disk %s" % template)
	return False
    volumeId = volumeObj[0].get_id()

    # Get Image Id
    imageId = getTemplateImageId(positive, vdsName, username, passwd, dataCenter, storageDomain)
    if noImages == 'true':
        if imageId != False:
            util.logger.error("There are image(-s) on domain %s!" % storageDomain)
            return False
        return True
    else:
        if imageId == False:
            util.logger.error("There are no images on domain %s" % storageDomain)
            return False

    # Get volume Info
    dcObj = dcUtil.find(dataCenter)
    dcId = dcObj.get_id()
    storDomObj = util.find(storageDomain)
    storDomId = storDomObj.get_id()
    volInfo = getVolumeInfo(vdsName, username, passwd, dcId, storDomId, imageId, volumeId)

    if not volInfo:
        msg = "failed to get volume info; DC {0}, SD{1}, Image {2}, Volume {3}"
        util.logger.error(msg.format(dcId, storDomId, imageId, volumeId))
        return False

    # Check volume info legality field
    legality = volInfo['legality']
    if (fake == 'true' and legality != 'FAKE') or (fake == 'false' and legality != 'LEGAL'):
        util.logger.error("Template legality is wrong: %s" % legality)
	return False
    return True


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
    sdObj = filter(lambda sdObj: sdObj.get_name() == storagedomain, storagedomains)
    return (len(sdObj) == 1) == positive


def checkStorageDomainParameters(positive, storagedomain, **kwargs):
    """
    Description: Checks whether given xpath is True
    Parameters:
        * storagedomain - domain's name
    Author: jlibosva
    Return: True if all keys and values matches given storage domain attributes
            False if any attribute is missing or if the attribute's value differs
    """
    domainObj = util.find(storagedomain)

    for attr in kwargs:
        if not hasattr(domainObj.storage, attr) or \
           getattr(domainObj.storage, attr) != kwargs[attr]:
            util.logger.debug("Attribute \"%s\" doesn't match with storage domain \
\"%s\"", attr, storagedomain)
            return not positive

    return positive


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


