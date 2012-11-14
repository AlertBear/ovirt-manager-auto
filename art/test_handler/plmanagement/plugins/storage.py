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

import storageapi.storageManagerWrapper as smngr
from utilities.utils import getIpAddressByHostName, getHostName
from utilities.machine import Machine, runLocalCmd
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
POSIXFS_TYPES = ['gluster']


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


def setConfValueByKeyPath(config, targetPath, keyValue, kyeExtension=''):
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
    cfg[targetConfKey + kyeExtension] = keyValue
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


def createHostGroupName(vdc):
    '''
    Create host group name from vdc hostname/IP
    '''
    try:
        return getHostName(vdc) if re.search('^\d+\.\d+\.\d+\.\d+$', vdc) \
                else vdc.split('.')[0]
    except Exception as e:
        raise CreateHostGroupNameException(e)


class StorageUtils:
    '''
    Implements storage management methods
    '''
    def __init__(self, config):

        self.nfs_devices = {}
        self.gluster_devices = {}
        self.iscsi_devices = {}
        self.local_devices = {}
        self.iso_devices = {}
        self.export_devices = {}
        self.vdsData = {}

        self.config = config
        self.storageConf = config['STORAGE']
        self.logger = logging.getLogger('storage')
        self.host_group = self.storageConf.get('host_group')
        self.data_center_type = str(getFromMainConfSection(config,
                                'data_center_type', asList=False))

        self.storages = {'gluster': {},
                         'nfs':     {},
                         'iscsi':   {},
                         'local':   {},
                         'iso':     {},
                         'export':  {},
                         }

        vdsSection = MAIN_SECTION
        if self.data_center_type == 'iscsi' or \
           self.data_center_type == 'localfs':
            vdsSection = self.data_center_type.upper()

        vdsServers = map(lambda x: getIpAddressByHostName(x),
                        getFromMainConfSection(config, 'vds', vdsSection))
        vdsPasswords = getFromMainConfSection(config, 'vds_password',
                                              vdsSection)

        if self.data_center_type == 'iscsi' or self.data_center_type == 'none':
            for vds, password in zip(vdsServers, vdsPasswords):
                try:
                    machine = Machine(vds, 'root', password).util('linux')
                    self.vdsData[vds] = machine.getIscsiInitiatorName()
                except:
                    self.logger.error("Failed to get iqn for host " + vds)

        # keeping this loop for backward compatibility, devices still
        # can be configured with sub-sections
        for subSection in self.storageConf.sections:
            confSubSection = self.storageConf[subSection]
            self.getStorageConfData(confSubSection, vdsServers[0],
                                    vdsPasswords[0], subSection)

        # new style - no sub-sections, default paths are set
        self.getStorageConfData(self.storageConf, vdsServers[0],
                                vdsPasswords[0])

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

        glusterStorage = confStorageSection.get('gluster_server', None)
        if glusterStorage:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'gluster')

            self.storages['gluster'][targetDevPath] = {
                'ip': getIpAddressByHostName(glusterStorage),
                'total': int(confStorageSection.get('gluster_devices', '0')),
            }

        nfsStorage = confStorageSection.get('nfs_server', None)
        if nfsStorage:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'nfs')

            self.storages['nfs'][targetDevPath] = {
                'ip': getIpAddressByHostName(nfsStorage),
                'total': int(confStorageSection.get('nfs_devices', '0')),
            }

        isoStorage = confStorageSection.get('iso_server', None)
        if isoStorage:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'iso')

            self.storages['iso'][targetDevPath] = {
                'ip': getIpAddressByHostName(isoStorage),
                'total': int(confStorageSection.get('iso_devices', '0')),
            }

        exportStorage = confStorageSection.get('export_server', None)
        if exportStorage:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'export')

            self.storages['export'][targetDevPath] = {
                'ip': getIpAddressByHostName(exportStorage),
                'total': int(confStorageSection.get('export_devices', '0')),
            }

        iscsiStorage = confStorageSection.get('iscsi_server', None)
        if iscsiStorage:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'iscsi')

            self.storages['iscsi'][targetDevPath] = {
                'ip': getIpAddressByHostName(iscsiStorage),
                'total': int(confStorageSection.get('iscsi_devices', '0')),
                'capacity': confStorageSection.get('devices_capacity', '0'),
                'is_specific': False,
            }

        localDevices = confStorageSection.get('local_devices', None)
        if localDevices:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'local')

            self.storages['local'][targetDevPath] = {
                'ip': confStorageSection.get('local_server', vds),
                'password': confStorageSection.get('password', vdsPassw),
                'paths': confStorageSection.as_list('local_devices'),
        }

    def _storageSetupNAS(self, data_center_type):
        """
        Description: creation of NAS devices
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        if data_center_type == 'posixfs':
            for fsType in POSIXFS_TYPES:
                for storageSection, sectionParams in\
                    self.storages[fsType].items():
                        self.gluster_devices[storageSection] = [
                        self.__create_nas_device(sectionParams['ip'],
                                                     self.host_group,
                                                     fsType)
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

    def _storageSetupISOandExportDomains(self):
        """
        Description: creation of iso and export domains
        Author: imeerovi
        Parameters:
            * data_center_type - data center type from conf file
        Return: None
        """
        fsType = self.config[MAIN_SECTION]['iso_export_domain_nas']

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

        elif self.data_center_type == 'nfs' or\
           self.data_center_type == 'posixfs':
            self._storageSetupNAS(self.data_center_type)

        elif self.data_center_type == 'iscsi':
            self._storageSetupSAN()

        elif self.data_center_type == 'localfs':
            self._storageSetupDAS()

        self._storageSetupISOandExportDomains()

        self.logger.info("Finished successfully creation of storage devices")

    def updateConfFile(self):
        '''
        Description: update settings.conf with created devices data
        Author: edolinin
        Parameters: None
        Return: None
        '''
        # GLUSTER domain
        for target in filterNonEmptyDicts(self.gluster_devices):
            targetData = self.storages['gluster'][target]

            glusterAddress = processConfList(\
                                    [targetData['ip']] * targetData['total'])
            setConfValueByKeyPath(self.config, target, glusterAddress,
                                  '_address')

            glusterPath = processConfList(self.gluster_devices[target])
            setConfValueByKeyPath(self.config, target, glusterPath, '_path')
        # NFS domain
        for target in filterNonEmptyDicts(self.nfs_devices):
            targetData = self.storages['nfs'][target]

            nfsAddress = processConfList(\
                                    [targetData['ip']] * targetData['total'])
            setConfValueByKeyPath(self.config, target, nfsAddress, '_address')

            nfsPath = processConfList(self.nfs_devices[target])
            setConfValueByKeyPath(self.config, target, nfsPath, '_path')

        # ISO domain
        for target in filterNonEmptyDicts(self.iso_devices):
            targetData = self.storages['iso'][target]

            nfsAddress = processConfList(\
                                    [targetData['ip']] * targetData['total'])
            setConfValueByKeyPath(self.config, target, nfsAddress, '_address')

            nfsPath = processConfList(self.iso_devices[target])
            setConfValueByKeyPath(self.config, target, nfsPath, '_path')

        # Export domain
        for target in filterNonEmptyDicts(self.export_devices):
            targetData = self.storages['export'][target]

            nfsAddress = processConfList(\
                                    [targetData['ip']] * targetData['total'])
            setConfValueByKeyPath(self.config, target, nfsAddress, '_address')

            nfsPath = processConfList(self.export_devices[target])
            setConfValueByKeyPath(self.config, target, nfsPath, '_path')

        # ISCSI domain
        for target in filterNonEmptyDicts(self.iscsi_devices):
            targetData = self.storages['iscsi'][target]

            iscsiAddress = processConfList(\
                                    [targetData['ip']] * targetData['total'])
            setConfValueByKeyPath(self.config, target, iscsiAddress,
                                  '_address')

            iscsiTarget = processConfList(\
                        map(lambda x: x['target'], self.iscsi_devices[target]))
            setConfValueByKeyPath(self.config, target, iscsiTarget, '_target')

            iscsiLun = processConfList(\
                        map(lambda x: x['uuid'], self.iscsi_devices[target]))
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

        for storageSection in self.storages['local']:
            if storageSection in self.local_devices.keys():
                for device in self.local_devices[storageSection]:
                    self.__remove_local_device(self.storages['local'][\
                            storageSection]['ip'],
                            self.storages['local'][storageSection]['password'],
                            device)

        # choosing nas type for iso and export domain removal
        fsType = self.config[MAIN_SECTION]['iso_export_domain_nas']

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

    def __create_nas_device(self, storageServerIp, deviceName, fsType):
        '''
        Description: create NFS device with given name
        Author: edolinin
        Parameters:
           * deviceName - device name
        Return: path of a new device
        '''

        storageMngr = smngr.StorageManagerWrapper(storageServerIp,
                                                  fsType.upper()).manager
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

        storageServerIp = storageServer['ip']
        storageMngr = smngr.StorageManagerWrapper(storageServerIp,
                                                  'ISCSI').manager
        lunId, targetName = storageMngr.createLun(lunName, capacity)

        storageServer['is_specific'] = re.match('netapp|xtreamio',
                                        storageMngr.__class__.__name__, re.I)
        # linux TGT requires host IP instead of iqn for mapping
        isTGT = re.match('TGT', storageMngr.__class__.__name__, re.I)
        initiators = serversData.values() if not isTGT else serversData.keys()

        for initiator in initiators:
            hostGroups = storageMngr.getInitiatorHostGroups(initiator)
            for hg in hostGroups:
                if hg != lunName:
                    storageMngr.unmapInitiator(hg, initiator)
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

        try:
            machineObj = Machine(server, username, password).util('linux')
            if not machineObj.isAlive():
                raise Exception("Machine is not reachable: " + server)
            if not machineObj.createLocalStorage(path):
                raise Exception("Failed to create local storage device:"\
                                + path)
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
            storageMngr = smngr.StorageManagerWrapper(storageServerIp,
                                            fsType.upper()).manager
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
            storageMngr = smngr.StorageManagerWrapper(storageServerIp,
                                                      'ISCSI').manager
            storageMngr.removeLun(deviceId)
            self.logger.info(PASS_REMOVE_MSG.format('iscsi', deviceId))
        except:
            self.logger.info(FAIL_REMOVE_MSG.format('iscsi', deviceId,
                                                    traceback.format_exc()))

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
            if not machineObj.isAlive():
                raise Exception("Machine is not reachable: " + server)
            if not machineObj.removeLocalStorage(path, force=True):
                raise Exception("Failed to remove local storage device: "\
                                + path)
            self.logger.info(PASS_REMOVE_MSG.format('local', path))
        except:
            self.logger.info(FAIL_REMOVE_MSG.format('local', path,
                                                 traceback.format_exc()))
