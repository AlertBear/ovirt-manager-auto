#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Red Hat, Inc.
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
import traceback
import re
from functools import wraps

import storageapi.storageManagerWrapper as smngr
from storageapi.storageErrors import StorageManagerObjectCreationError
import storageapi.snmp as snmp
from storageapi.storageUtils import timeStamp
from utilities.utils import getIpAddressByHostName, getHostName
from utilities.machine import Machine
from utilities.errors import FileAlreadyExistsError, GeneralException

FAIL_REMOVE_MSG = 'Failed to remove device of type {0}: {1}\n{2}'
PASS_REMOVE_MSG = 'Successfully removed device of type {0}: {1}'
FAIL_CREATE_MSG = 'Failed to create device of type {0}: {1}\n{2}'
PASS_CREATE_MSG = 'Successfully created device of type {0}: {1}'

MAIN_SECTION = 'PARAMETERS'
DEVICES_TARGET_PATHS = {
                        'gluster': '%s.%s' % (MAIN_SECTION, 'gluster_domain'),
                        'nfs': '%s.%s' % (MAIN_SECTION, 'data_domain'),
                        'export': '%s.%s' % (MAIN_SECTION, 'export_domain'),
                        'iso': '%s.%s' % (MAIN_SECTION, 'tests_iso_domain'),
                        'iscsi': '%s.%s' % (MAIN_SECTION, 'lun'),
                        'local': '%s.%s' % (MAIN_SECTION, 'local_domain'),
                        }
POSIXFS_TYPE = 'gluster'
ISO_EXPORT_TYPE = 'iso_export_domain_nas'
LOAD_BALANCING_CAPACITY = 'capacity'
LOAD_BALANCING_RANDOM = 'random'

logger = logging.getLogger(__name__)


def createStorageManager(ips, type, conf):
    for i in range(0, len(ips)):
        try:
            return smngr.StorageManagerWrapper(ips.pop(i), type.upper(),
                                               conf).manager
        except StorageManagerObjectCreationError as ex:
            logger.warning(ex)
    raise


def getStorageServers(storageType='none'):
    """
    Description: This closure will be used as decorator for getting storage
                 server information that will be used by decorated function
    Author: lustalov
    Parameters:
        *  storageType - storage type, in case of none passed, storageType
                         will be selected between nfs and gluster according to
                         data_center_type that passed to decorated function
    It is:
        - adding corresponding storage api object to self.storages[storageType]
        - adding corresponding storage provider ip to corresponding data type.
    """
    def outwrap(f):
        setattr(f, 'storageType', storageType)

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if self.load_balancing:
                storageType = f.storageType
                stype = storageType
                dtypes = [stype]
                if storageType == ISO_EXPORT_TYPE:
                    stype = self.config[MAIN_SECTION][ISO_EXPORT_TYPE]
                    dtypes = ['iso', 'export']
                elif storageType == 'none':
                    stype = args[0] if args[0] != 'posixfs' \
                                       else POSIXFS_TYPE
                    dtypes = [stype]
                targetDevPath = self.getDeviceTargetPath(None, stype)
                if self.storages[stype] and \
                    self.storages[stype][targetDevPath]['total'] > 0:
                    if stype not in self.storageServers:
                        servers = getStorageServer(stype, self.load_balancing,
                                                   self.storageConfigFile,
                                                   self.serverPool)
                        smng = createStorageManager(servers, stype,
                                                     self.storageConfigFile)
                        self.storageServers[stype] = smng
                    for t in dtypes:
                        for section, params in self.storages[t].items():
                            self.storages[t][section]['ip'] = \
                                self.storageServers[stype].host
            return f(self, *args, **kwargs)
        return wrapper
    return outwrap


def processConfList(confList):
    '''
    Description: check list value in configuration file
    Author: edolinin
    Parameters: configuration value in list format
    Return: list if its length more than 1, otherwise - first element
    '''

    return confList[0] if len(confList) == 1 else confList


def getFromMainConfSection(config, key, mainSection=MAIN_SECTION, asList=True):
    '''
    Description: get value by key from parameters section
    Author: edolinin
    Parameters:
           * config - ConfigObj
           * key - parameter key
           * mainSection - name of parameters section
           * asList - to return values in a list  or not
    Return: list asList is True, otherwise - single element
    '''

    if asList:
        return config[mainSection].as_list(key)
    else:
        return config[mainSection].get(key)


def setConfValueByKeyPath(config, targetPath, keyValue, keyExtension=''):
    '''
    Description: set value in configuration file by given key path
    Author: edolinin
    Parameters:
           * config - ConfigObj
           * targetPath - path to conf key
           * keyValue - key value
           * kyeExtension - extension to add to key name
    Return: None
    '''

    targetConfSection, targetConfKey = targetPath.split('.')
    cfg = config.get(targetConfSection, {})
    stKey = targetConfKey + keyExtension
    cfg[stKey] = keyValue
    logger.debug("dynamic storage: filling variable: %s.%s = %s" % (\
                                    targetConfSection, stKey, keyValue))
    config[targetConfSection] = cfg


def filterNonEmptyDicts(originalDict):
    '''
    Description: remove empty dictionaries from a parent dictionary
    Author: edolinin
    Parameters:
           * originalDict - original dictionary
    Return: result dictionary
    '''

    return filter(lambda x: originalDict[x], originalDict)


class CreateHostGroupNameException(GeneralException):
    message = "Host group is missing. Failed to create it from vdc hostname."


class GetServerForDynamicStorageAllocationException(GeneralException):
    message = "Failed to get server for dynamic storage allocation"


def createHostGroupName(vdc):
    '''
    Create host group name from vdc hostname/IP
    '''
    try:
        if re.search('^\d+\.\d+\.\d+\.\d+$|localhost', vdc):
            vdc = getHostName(vdc)
        return vdc.split('.')[0]
    except Exception as e:
        raise CreateHostGroupNameException(e)


def getStorageServer(type, load_balancing, conf=None, servers=None):
    '''
    Get less used storage server(less used disk space + cpu load)
    Parameters:
        * storageType - storage type(NFS/iSCSI)
        * servers - list of storage server IPs to choose from, if not defined -
                    configuration file used
    '''
    try:
        if load_balancing == LOAD_BALANCING_CAPACITY:
            monitor = snmp.SNMPMonitor(type, conf, servers=servers)
            return monitor.getServersByDiskSpaceToCpuRatio()
        elif load_balancing == LOAD_BALANCING_RANDOM:
            return smngr.getRandomServers(type, conf, servers)
        else:
            raise GetServerForDynamicStorageAllocationException(
                "Unsupported load-balancing type: %s" % load_balancing)
    except Exception as e:
        raise GetServerForDynamicStorageAllocationException(e)


class StorageUtils:
    '''
    Implements storage management methods
    '''
    def __init__(self, config, storageConfig=None):

        self.nfs_devices = {}
        self.gluster_devices = {}
        self.iscsi_devices = {}
        self.local_devices = {}
        self.iso_devices = {}
        self.export_devices = {}
        self.vdsData = {}
        self.storageServers = {}

        self.config = config
        self.storageConf = config['STORAGE']
        self.logger = logging.getLogger('storage')
        self.host_group = self.storageConf.get('host_group')
        self.data_center_type = str(getFromMainConfSection(config,
                                'data_center_type', asList=False))
        self.load_balancing = False
        self.serverPool = None
        self.storageConfigFile = storageConfig
        self.vfs_type = config['PARAMETERS']['vfs_type']
        self.storages = {'gluster': {},
                         'nfs':     {},
                         'iscsi':   {},
                         'local':   {},
                         'iso':     {},
                         'export':  {},
                         }

        vdsServers = map(lambda x: getIpAddressByHostName(x),
                        getFromMainConfSection(config, 'vds', MAIN_SECTION))
        vdsPasswords = getFromMainConfSection(config, 'vds_password',
                                              MAIN_SECTION)

        numOfVds = len(vdsServers)
        numOfPassw = len(vdsPasswords)
        if numOfPassw < numOfVds:
            addPasswords = [vdsPasswords[0]] * (numOfVds - numOfPassw)
            vdsPasswords.extend(addPasswords)

        if self.data_center_type == 'iscsi' or self.data_center_type == 'none':
            for vds, password in zip(vdsServers, vdsPasswords):
                try:
                    machine = Machine(vds, 'root', password).util('linux')
                    self.vdsData[vds] = machine.getIscsiInitiatorName()
                except:
                    self.logger.error("Failed to get iqn for host " + vds)
                    raise

        # new style - no sub-sections, default paths are set
        self.getStorageConfData(self.storageConf, vdsServers[0],
                                vdsPasswords[0])
        # keeping this loop for backward compatibility, devices still
        # can be configured with sub-sections
        for subSection in self.storageConf.sections:
            confSubSection = self.storageConf[subSection]
            self.getStorageConfData(confSubSection, vdsServers[0],
                                    vdsPasswords[0], subSection)

        if not self.host_group:
            self.host_group = createHostGroupName(getFromMainConfSection(\
              config, 'host', mainSection='REST_CONNECTION', asList=False))

    def getDeviceTargetPath(self, targetPath, type_):
        '''
        Description: decide the path in conf file where to put the device,
            target path has the following format: section_name.param_name
        Author: edolinin
        Parameters:
           * targetPath - pre-defined path or None
           * type - device type, possible values: nfs, gluster, iscsi, local,
            export, iso
        Return: target path of a device in conf file
        '''
        if targetPath:
            return targetPath

        return DEVICES_TARGET_PATHS[type_]

    def getStorageConfData(self, confStorageSection, vds, vdsPassw,
                           targetPath=None):
        '''
        Description: retrieve configuration data for allocation of
                     storage devices
        Author: edolinin
        Parameters:
            * confStorageSection - config section or sub-section
            where to fetch the data
            * vds - server ip for local devices creation
            * vdsPassw - server password for local devices creation
            * targetPath - pre-defined path where to put the device
        Return: None
        '''

        for dev_type in ('gluster', 'nfs', 'iso', 'export', 'iscsi'):
            storageServer = confStorageSection.get(
                            '{0}_server'.format(dev_type), None)
            targetDevPath = self.getDeviceTargetPath(targetPath, dev_type)
            self.storages[dev_type][targetDevPath] = {
                'ip': getIpAddressByHostName(storageServer) if storageServer \
                      else None,
                'total': int(confStorageSection.get(
                             '{0}_devices'.format(dev_type), '0')),
            }
            if dev_type == 'iscsi':
                self.storages[dev_type][targetDevPath]['capacity'] = \
                    confStorageSection.get('devices_capacity', '0')
                self.storages[dev_type][targetDevPath]['is_specific'] = False

        localDevices = confStorageSection.get('local_devices', None)
        if localDevices:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'local')

            self.storages['local'][targetDevPath] = {
                'ip': confStorageSection.get('local_server', vds),
                'password': confStorageSection.get('password', vdsPassw),
                'paths': confStorageSection.as_list('local_devices'),
        }

    @getStorageServers()
    def _storageSetupNAS(self, data_center_type):
        """
        Description: creation of NAS devices
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        if data_center_type == 'posixfs':
            for storageSection, sectionParams in\
                self.storages[POSIXFS_TYPE].items():
                    self.gluster_devices[storageSection] = [
                    self.__create_nas_device(sectionParams['ip'],
                                                 self.host_group,
                                                 POSIXFS_TYPE)
                            for i in range(0, sectionParams['total'])
                    ]

        elif data_center_type == 'nfs':
            for storageSection, sectionParams in\
                self.storages[data_center_type].items():
                    self.nfs_devices[storageSection] = [
                    self.__create_nas_device(sectionParams['ip'],
                                             self.host_group,
                                             data_center_type)
                            for i in range(0, sectionParams['total'])
                    ]

    @getStorageServers('iscsi')
    def _storageSetupSAN(self):
        """
        Description: creation of SAN devices
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        for storageSection, sectionParams in self.storages['iscsi'].items():
                self.iscsi_devices[storageSection] = [
                    self.__create_iscsi_device(sectionParams, self.host_group,
                                    sectionParams['capacity'], **self.vdsData)
                        for i in range(0, sectionParams['total'])
                    ]

    def _storageSetupDAS(self):
        """
        Description: creation of local fs devices
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        for storageSection, sectionParams in self.storages['local'].items():
                self.local_devices[storageSection] = [
                    self.__create_local_device(sectionParams['ip'],
                                    sectionParams['password'], path)
                        for path in sectionParams['paths']
                    ]

    @getStorageServers(ISO_EXPORT_TYPE)
    def _storageSetupISOandExportDomains(self):
        """
        Description: creation of iso and export domains
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        fsType = self.config[MAIN_SECTION][ISO_EXPORT_TYPE]

        for storageSection, sectionParams in self.storages['iso'].items():
            self.iso_devices[storageSection] = [
                self.__create_nas_device(sectionParams['ip'], self.host_group,
                            fsType)
                    for i in range(0, sectionParams['total'])
            ]

        for storageSection, sectionParams in self.storages['export'].items():
            self.export_devices[storageSection] = [
                self.__create_nas_device(sectionParams['ip'], self.host_group,
                                             fsType)
                    for i in range(0, sectionParams['total'])
            ]

    def storageSetup(self):
        '''
        Description: create NAS and ISCSI devices defined in settings
        Author: edolinin
        Parameters: None
        '''
        if self.data_center_type == 'none':
            self._storageSetupNAS('nfs')
            self._storageSetupNAS('posixfs')
            self._storageSetupSAN()
            self._storageSetupDAS()

        elif self.data_center_type == 'nfs':
            self._storageSetupNAS(self.data_center_type)

        elif self.data_center_type == 'posixfs' and self.vfs_type == 'nfs':
            self._storageSetupNAS('posixfs')
            self._storageSetupNAS('nfs')

        elif self.data_center_type == 'posixfs' and \
                self.vfs_type == 'glusterfs':
            self._storageSetupNAS('posixfs')

        elif self.data_center_type == 'iscsi':
            self._storageSetupSAN()

        elif self.data_center_type == 'localfs':
            self._storageSetupDAS()

        create_iso_exp = False
        for stype in ('iso', 'export'):
            for targ in self.storages[stype]:
                if self.storages[stype][targ]['total'] > 0:
                    create_iso_exp = True
                    break
        if create_iso_exp:
            self._storageSetupISOandExportDomains()

        self.logger.info("Finished successfully creation of storage devices")

    def updateConfFile(self):
        '''
        Description: update settings.conf with created devices data
        Author: edolinin
        Parameters: None
        Return: None
        '''
        for type, devices in dict(gluster=self.gluster_devices,
                                  nfs=self.nfs_devices,
                                  iso=self.iso_devices,
                                  export=self.export_devices,
                                  iscsi=self.iscsi_devices).iteritems():
            for target in filterNonEmptyDicts(devices):
                targetData = self.storages[type][target]
                address = processConfList(
                                    [targetData['ip']] * targetData['total'])
                setConfValueByKeyPath(self.config, target, address, '_address')
                if type is not 'iscsi':
                    path = processConfList(devices[target])
                    setConfValueByKeyPath(self.config, target, path, '_path')
                else:
                    iscsiTarget = processConfList(
                        map(lambda x: x['target'], devices[target]))
                    setConfValueByKeyPath(self.config, target, iscsiTarget,
                                          '_target')
                    iscsiLun = processConfList(
                        map(lambda x: x['uuid'], devices[target]))
                    setConfValueByKeyPath(self.config, target, iscsiLun)

        # Local domain
        for target in filterNonEmptyDicts(self.local_devices):
            path = processConfList(self.local_devices[target])
            setConfValueByKeyPath(self.config, target, path, '_path')

        self.config.write()

    def storageCleanup(self):
        '''
        Description: remove NFS and ISCSI devices defined in settings
        Author: edolinin
        Parameters: None
        Return: None
        '''
        for storageSection in self.storages['gluster']:
            if storageSection in self.gluster_devices.keys():
                for device in self.gluster_devices[storageSection]:
                    self.__remove_nas_device(\
                     self.storages['gluster'][storageSection]['ip'], device,
                     'gluster')

        for storageSection in self.storages['nfs']:
            if storageSection in self.nfs_devices.keys():
                for device in self.nfs_devices[storageSection]:
                    self.__remove_nas_device(\
                     self.storages['nfs'][storageSection]['ip'], device, 'nfs')

        for storageSection in self.storages['iscsi']:
            lunId = 'serial' if self.storages['iscsi'][\
                             storageSection]['is_specific'] else 'uuid'
            if storageSection in self.iscsi_devices.keys():
                for device in self.iscsi_devices[storageSection]:
                    self.__remove_iscsi_device(self.storages['iscsi'][\
                            storageSection]['ip'], device[lunId])
                if self.iscsi_devices[storageSection]:
                    self.__unmap_iscsi_initiators(
                            self.storages['iscsi'][storageSection]['ip'])

        for storageSection in self.storages['local']:
            if storageSection in self.local_devices.keys():
                for device in self.local_devices[storageSection]:
                    self.__remove_local_device(self.storages['local'][\
                            storageSection]['ip'],
                            self.storages['local'][storageSection]['password'],
                            device)

        # choosing nas type for iso and export domain removal
        fsType = self.config[MAIN_SECTION][ISO_EXPORT_TYPE]

        for storageSection in self.storages['iso']:
            if storageSection in self.iso_devices.keys():
                for device in self.iso_devices[storageSection]:
                    self.__remove_nas_device(self.storages['iso'][\
                        storageSection]['ip'], device, fsType)

        for storageSection in self.storages['export']:
            if storageSection in self.export_devices.keys():
                for device in self.export_devices[storageSection]:
                    self.__remove_nas_device(self.storages['export'][\
                        storageSection]['ip'], device, fsType)

    def getStorageManager(self, type, serverIp):
        return self.storageServers[type] if type in self.storageServers else \
            createStorageManager([serverIp], type.upper(),
                                 self.storageConfigFile)

    def __create_nas_device(self, storageServerIp, deviceName, fsType):
        '''
        Description: create NFS device with given name
        Author: edolinin
        Parameters:
           * deviceName - device name
        Return: path of a new device
        '''
        storageMngr = self.getStorageManager(fsType, storageServerIp)

        path = storageMngr.createDevice(deviceName)

        self.logger.info(PASS_CREATE_MSG.format(fsType, path))

        return path

    def __create_iscsi_device(self, storageServer, lunName, capacity,
                               **serversData):
        '''
        Description: create ISCSI device with given name
        Author: edolinin
        Parameters:
           * storageServerIp - IP of storage server
           * lunName - LUN name
           * capacity - LUN capacity
           * servers - list of lun initiators
        Return: dictionary of lunInfo and type of storage server
        '''
        storageMngr = self.getStorageManager('iscsi', storageServer['ip'])

        lunId, targetName = storageMngr.createLun(lunName, capacity)

        storageServer['is_specific'] = re.match('netapp|xtreamio',
                                        storageMngr.__class__.__name__, re.I)
        # linux TGT requires host IP instead of iqn for mapping
        initiators = serversData.values() if 'tgt' not in \
            storageMngr.__class__.__name__.lower() else serversData.keys()

        for initiator in initiators:
            hostGroups = storageMngr.getInitiatorHostGroups(initiator)
            for hg in hostGroups:
                if hg != lunName:
                    self.logger.info('Unmap initiator %s from host group %s' %
                                     (initiator, hg))
                    storageMngr.unmapInitiator(hg, initiator)
        self.logger.info('Map lun %s to host group %s, initiators: %s',
                         lunId, lunName, initiators)
        storageMngr.mapLun(lunId, lunName, *initiators)

        if storageServer['is_specific']:
            lunInfo = storageMngr.getLun(lunId, serversData.iterkeys().next())
        else:
            lunInfo = storageMngr.getLun(lunId)

        self.logger.info(PASS_CREATE_MSG.format('iscsi', lunId))

        return lunInfo

    def __create_local_device(self, server, password, path, username='root'):
        '''
        Description: create local device with given path
        Author: edolinin
        Parameters:
           * server - dictionary of server ip and password
           * path - path of local device
           * username - server username
        Return: path of a new local device
        '''
        path = '{0}_{1}'.format(path, timeStamp())
        try:
            machineObj = Machine(server, username, password).util('linux')
            rc, out = machineObj.createLocalStorage(path)
            if not rc:
                raise Exception("Failed to create local storage device with"
                                "path %s. Error message is %s" %
                                (path, out))
        except FileAlreadyExistsError:
            pass

        self.logger.info(PASS_CREATE_MSG.format('local', path))

        return path

    def __remove_nas_device(self, storageServerIp, path, fsType):
        '''
        Description: remove NFS device with given name
        Author: edolinin
        Parameters:
           * storageServerIp - IP of storage server
           * path - path to NFS device
        Return: None
        '''
        try:
            storageMngr = self.getStorageManager(fsType, storageServerIp)
            storageMngr.removeDevice(path)
            self.logger.info(PASS_REMOVE_MSG.format(fsType, path))
        except:
            self.logger.info(FAIL_REMOVE_MSG.format(fsType, path,
                                                    traceback.format_exc()))

    def __remove_iscsi_device(self, storageServerIp, deviceId):
        '''
        Description: remove ISCSI device with given id
        Author: edolinin
        Parameters:
           * storageServerIp -  IP of storage server
           * deviceId - device lun id or serial number
        Return: None
        '''

        try:
            storageMngr = self.getStorageManager('iscsi', storageServerIp)
            storageMngr.removeLun(deviceId)
            self.logger.info(PASS_REMOVE_MSG.format('iscsi', deviceId))
        except:
            self.logger.info(FAIL_REMOVE_MSG.format('iscsi', deviceId,
                                                    traceback.format_exc()))

    def __unmap_iscsi_initiators(self, storageServerIp):
        '''
        Description: cleanup iscsi initiator group -
                     remove all the initiators from the group
        Parameters:
            * storageServerIp - IP of storage server
        '''
        storageMngr = self.getStorageManager('iscsi', storageServerIp)
        initiators = self.vdsData.values() if 'tgt' not in \
            storageMngr.__class__.__name__.lower() else self.vdsData.keys()
        hostGroup = self.host_group
        if initiators:
            self.logger.info('Unmap initiators %s from host group %s',
                         initiators, self.host_group)
            if 'solaris' in storageMngr.__class__.__name__.lower():
                # real host group name has suffix added to distinguish it
                # from target group
                hostGroups = storageMngr.getInitiatorHostGroups(initiators[0])
                hostGroup = hostGroups[0]

        for initiator in initiators:
            try:
                storageMngr.unmapInitiator(hostGroup, initiator)
            except Exception as ex:
                self.logger.error('Unmap initiator %s from host group %s: %s',
                    initiator, self.host_group, ex)

    def __remove_local_device(self, server, password, path, username='root'):
        '''
        Description: remove local device with given path
        Author: edolinin
        Parameters:
           * server - server name/ip
           * password - server root password
           * path - path of a local device
           * username - server username
        Return: None
        '''

        try:
            machineObj = Machine(server, username, password).util('linux')
            rc, out = machineObj.removeLocalStorage(path, force=True)
            if not rc:
                raise Exception("Failed to remove local storage device with"
                                "path %s. Error message is %s" %
                                (path, out))
            self.logger.info(PASS_REMOVE_MSG.format('local', path))
        except:
            self.logger.info(FAIL_REMOVE_MSG.format('local', path,
                                                 traceback.format_exc()))
