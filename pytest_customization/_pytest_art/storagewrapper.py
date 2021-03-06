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
"""
This module wraps stroage-api library and sets relevant variables in
art-config.

TODO: We need to get rid of this module and stop inject variables to config.
"""

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
DEV_TYPES = (
    'gluster',
    'nfs',
    'iso',
    'export',
    'iscsi',
    'fcp',
    'pnfs',
)
DEVICES_TARGET_PATHS = {
    'gluster': '%s.%s' % (MAIN_SECTION, 'data_domain'),
    'nfs': '%s.%s' % (MAIN_SECTION, 'data_domain'),
    'pnfs': '%s.%s' % (MAIN_SECTION, 'data_domain'),
    'export': '%s.%s' % (MAIN_SECTION, 'export_domain'),
    'iso': '%s.%s' % (MAIN_SECTION, 'tests_iso_domain'),
    'iscsi': '%s.%s' % (MAIN_SECTION, 'lun'),
    'fcp': '%s.%s' % (MAIN_SECTION, 'lun'),
    'local': '%s.%s' % (MAIN_SECTION, 'local_domain'),
}
POSIXFS_COMPLIANT_TYPES = [
    'gluster',
    'nfs',
    'pnfs',
]
NAS_STORAGE_TYPES = [
    'gluster',
    'nfs',
    'pnfs',
]
SAN_STORAGE_TYPES = [
    'iscsi',
    'fcp',
]
ISO_EXPORT_TYPE = 'iso_export_domain_nas'
LOAD_BALANCING_CAPACITY = 'capacity'
LOAD_BALANCING_RANDOM = 'random'
STORAGE_ROLE = 'storage_role'
LOAD_BALANCING = 'devices_load_balancing'

logger = logging.getLogger(__name__)


def createStorageManager(ips, type, conf):
    for i in xrange(len(ips)):
        try:
            return smngr.StorageManagerWrapper(
                ips.pop(i), type.upper(), conf).manager
        except StorageManagerObjectCreationError as ex:
            logger.warning(ex)
            raise


def getStorageServers(storageType='none'):
    """
    This closure will be used as decorator for getting storage
    server information that will be used by decorated function

    :author: lustalov
    :param storageType: storage type, in case of none passed, storageType
                        will be selected between nfs and gluster according to
                        storage type that passed to decorated function
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
                    stype = args[0]
                    dtypes = [stype]
                targetDevPath = self.getDeviceTargetPath(None, stype)
                if (
                    self.storages[stype]
                    and self.storages[stype][targetDevPath]['total'] > 0
                ):
                    if stype not in self.storageServers:
                        servers = getStorageServer(
                            stype,
                            self.load_balancing,
                            self.storageConfigFile,
                            self.storage_pool,
                        )
                        smng = createStorageManager(
                            servers, stype, self.storageConfigFile,
                        )
                        self.storageServers[stype] = smng
                    for t in dtypes:
                        for section, params in self.storages[t].items():
                            self.storages[t][section]['ip'] = (
                                self.storageServers[stype].host
                            )
                if stype in self.storageServers:
                    return f(self, *args, **kwargs)
                logger.debug(
                    "\n{2}\nSkipping storage creation for '{1}'\n"
                    "Reason: you are running with "
                    "PARAMETERS.storage_type={0}\n"
                    "STORAGE.{1}_devices=0 or {1}_devices missing in "
                    "[STORAGE] section in conf file\n{2}".format(
                        storageType, stype, "#" * 50
                    )
                )
            else:
                try:
                    return f(self, *args, **kwargs)
                except Exception:
                    logger.error(
                        "\n{2}\n{0}{1} run failed\n"
                        "Reason: you are running without "
                        "load balancing. It means that you need to "
                        "provide storage servers for all your "
                        "storages\n.You didn't provide a storage "
                        "server\n{2}".format(
                            f.__name__, args, "#" * 50
                        )
                    )
                    raise
        return wrapper
    return outwrap


def processConfList(confList):
    '''
    Description: check list value in configuration file
    :author: edolinin
    :return: list if its length more than 1, otherwise - first element
    '''

    return confList[0] if len(confList) == 1 else confList


def getFromMainConfSection(config, key, mainSection=MAIN_SECTION, asList=True):
    '''
    get value by key from parameters section

    :author: edolinin
    :param config: ConfigObj
    :param key: parameter key
    :param mainSection: name of parameters section
    :param asList: to return values in a list  or not
    :return: list asList is True, otherwise - single element
    '''

    if asList:
        return config[mainSection].as_list(key)
    else:
        return config[mainSection].get(key)


def setConfValueByKeyPath(config, targetPath, keyValue, keyExtension='',
                          backwardCompatibilityCheck=False, cleanUpConf=False):
    '''
    set value in configuration file by given key path

    :author: edolinin
    :param config: ConfigObj
    :param targetPath: path to conf key
    :param keyValue: key value
    :param kyeExtension: extension to add to key name
    :param backwardCompatibilityCheck: checks and converts list with one
        parameter to string and updates conf file
    :param cleanUpConf: erases existing conf data with empty list
    :return: None
    '''
    targetConfSection, targetConfKey = targetPath.split('.')
    cfg = config.get(targetConfSection, {})
    stKey = targetConfKey + keyExtension

    if backwardCompatibilityCheck:
        data = cfg[stKey]
        if len(data) == 1:
            cfg[stKey] = data[0]
    else:
        # if key doesn't exists or None create list value for it
        if cfg.get(stKey, None) is None:
            cfg[stKey] = []
        # cleanup existing data
        if cleanUpConf:
            cfg[stKey] = []
        else:
            cfg[stKey].extend(keyValue)
        logger.debug("dynamic storage: filling variable: %s.%s = %s",
                     targetConfSection, stKey, keyValue)
    config[targetConfSection] = cfg


def filterNonEmptyDicts(originalDict):
    '''
    remove empty dictionaries from a parent dictionary

    :author: edolinin
    :param originalDict: original dictionary
    :return: result dictionary
    '''
    return filter(lambda x: originalDict[x], originalDict)


def createHostGroupName(vdc):
    '''
    Create host group name from vdc hostname/IP
    '''
    try:
        if re.search(r'^\d+\.\d+\.\d+\.\d+$|localhost', vdc):
            vdc = getHostName(vdc)
        return vdc.split('.')[0]
    except Exception as e:
        raise CreateHostGroupNameException(e)


def getStorageServer(type_, load_balancing, conf=None, servers=None):
    '''
    Get less used storage server(less used disk space + cpu load)
    :param storageType: storage type(NFS/iSCSI/FCP)
    :param servers: list of storage server IPs to choose from, if not defined -
                    configuration file used
    '''
    try:
        if load_balancing == LOAD_BALANCING_CAPACITY:
            monitor = snmp.SNMPMonitor(type_, conf, servers=servers)
            return monitor.getServersByDiskSpaceToCpuRatio()
        elif load_balancing == LOAD_BALANCING_RANDOM:
            return smngr.get_random_servers(type_, conf, servers)
        else:
            raise GetServerForDynamicStorageAllocationException(
                "Unsupported load-balancing type: %s" % load_balancing)
    except Exception as e:
        raise GetServerForDynamicStorageAllocationException(e)


class CreateHostGroupNameException(GeneralException):
    message = "Host group is missing. Failed to create it from vdc hostname."


class GetServerForDynamicStorageAllocationException(GeneralException):
    message = "Failed to get server for dynamic storage allocation"


class StorageUtils:
    '''
    Implements storage management methods
    '''
    def __init__(self, config, storageConfig=None):

        self.nfs_devices = {}
        self.pnfs_devices = {}
        self.gluster_devices = {}
        self.iscsi_devices = {}
        self.fcp_devices = {}
        self.local_devices = {}
        self.iso_devices = {}
        self.export_devices = {}
        self.vdsData = {}
        self.storageServers = {}

        self.config = config
        self.storageConf = config['STORAGE']
        self.logger = logging.getLogger('storage')
        self.host_group = self.storageConf.get('host_group')
        # the storage roles is a dictionary which easily resolve params
        # related to each storage_role
        self.storage_roles = {}
        self.storage_type = str(getFromMainConfSection(config, 'storage_type',
                                                       asList=False))
        # alligning with gluster name in rhevm
        self.storage_type = 'gluster' if self.storage_type == 'glusterfs' \
            else self.storage_type
        self.real_storage_type = 'mixed'
        if 'posixfs_' in self.storage_type:
            self.storage_type, self.real_storage_type = \
                self.storage_type.split('_')
        load_balancing = self.storageConf.get(LOAD_BALANCING, False)
        self.load_balancing = (False if load_balancing in ('no', 'false')
                               else load_balancing)
        self.storage_pool = self.storageConf.get('storage_pool', None)
        self.storageConfigFile = storageConfig
        self.storages = {
            'gluster': {},
            'nfs':     {},
            'iscsi':   {},
            'fcp':     {},
            'local':   {},
            'iso':     {},
            'export':  {},
            'pnfs':    {},
        }

        vdsServers = map(
            lambda x:
                getIpAddressByHostName(x),
                getFromMainConfSection(config, 'vds', MAIN_SECTION)
        )
        vdsPasswords = getFromMainConfSection(
            config, 'vds_password', MAIN_SECTION
        )

        numOfVds = len(vdsServers)
        numOfPassw = len(vdsPasswords)
        if numOfPassw < numOfVds:
            addPasswords = [vdsPasswords[0]] * (numOfVds - numOfPassw)
            vdsPasswords.extend(addPasswords)

        # fixme: exclude fcp
        if self.storage_type in SAN_STORAGE_TYPES or \
                self.storage_type == 'none':
            for vds, password in zip(vdsServers, vdsPasswords):
                try:
                    machine = Machine(vds, 'root', password).util('linux')
                    self.vdsData[vds] = machine.getIscsiInitiatorName()
                except Exception:
                    self.logger.error("Failed to get iqn for host %s", vds)
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
            self.host_group = createHostGroupName(getFromMainConfSection(
                config, 'host', mainSection='REST_CONNECTION', asList=False))

    def update_storage_roles(self, section):
        '''
        Update storage_roles dictionary with storage_role details
        from conf file if the storage_role exist in this section

        :author: 'khakimi'
        :param section: from self.config STORAGE section or subsection of it.
        :type section: dict
        '''
        storage_role = section.get(STORAGE_ROLE, None)
        if storage_role:
            config_default = self.config['DEFAULT']
            storage_api_conf = config_default.get('STORAGE_API_CONF', None)
            server_dict = smngr.get_server_dict_by_role(
                storage_api_conf, self.storage_pool, storage_role)
            if server_dict:
                self.storage_roles.update(server_dict)

    def getDeviceTargetPath(self, targetPath, type_):
        '''
        decide the path in conf file where to put the device,
        target path has the following format: section_name.param_name

        :author: edolinin
        :param targetPath: pre-defined path or None
        :param type: device type, possible values: nfs, gluster, iscsi, fcp,
                     local, export, iso
        :return: target path of a device in conf file
        '''
        if targetPath:
            return targetPath

        return DEVICES_TARGET_PATHS[type_]

    def getStorageConfData(self, confStorageSection, vds, vdsPassw,
                           targetPath=None):
        '''
        retrieve configuration data for allocation of storage devices

        :author: edolinin
        :param confStorageSection: config section or sub-section
            where to fetch the data
        :param vds: server ip for local devices creation
        :param vdsPassw: server password for local devices creation
        :param targetPath: pre-defined path where to put the device
        :return: None
        '''

        self.update_storage_roles(confStorageSection)
        storage_role = confStorageSection.get(STORAGE_ROLE, None)
        for dev_type in DEV_TYPES:
            storageServer = confStorageSection.get(
                '{0}_server'.format(dev_type), None)
            if storageServer is None and storage_role:
                storage_type = confStorageSection.get('storage_type', None)
                if storage_type == dev_type:
                    storageServer = self.storage_roles[storage_role]['ip']
            targetDevPath = self.getDeviceTargetPath(targetPath, dev_type)
            storage_ip = getIpAddressByHostName(storageServer) if \
                storageServer else None
            total_devices = int(confStorageSection.get(
                '{0}_devices'.format(dev_type), '0'))
            if ((storage_ip or self.load_balancing in ('capacity', 'random'))
                    and total_devices > 0):
                self.storages[dev_type][targetDevPath] = {
                    'ip': storage_ip,
                    'total': total_devices
                }
                if dev_type in SAN_STORAGE_TYPES:
                    self.storages[dev_type][targetDevPath]['capacity'] = \
                        confStorageSection.get('devices_capacity', '0')
                    self.storages[dev_type][targetDevPath]['is_specific'] = \
                        False

        localDevices = confStorageSection.get('local_devices', None)
        if localDevices:
            targetDevPath = self.getDeviceTargetPath(targetPath, 'local')

            self.storages['local'][targetDevPath] = {
                'ip': confStorageSection.get('local_server', vds),
                'password': confStorageSection.get('password', vdsPassw),
                'paths': confStorageSection.as_list('local_devices'),
            }

    def log_storage_server(self, server_name, storageSection, storage_type):
        logger.info("Server: {0} Type: {1} from section :{2}".format(
            server_name, storage_type, storageSection))

    @getStorageServers()
    def _storageSetupNAS(self, storage_type):
        """
        creation of NAS devices

        :author: imeerovi
        :param storage_type: storage type, in all cases except posixfs it
                             is exactly storage type from conf file
        :return: None
        """
        for storageSection, sectionParams in\
                self.storages[storage_type].items():
            self.log_storage_server(sectionParams['ip'], storageSection,
                                    storage_type)
            if storage_type == 'gluster':
                self.gluster_devices[storageSection] = [
                    self.__create_nas_device(
                        sectionParams['ip'],
                        self.host_group,
                        storage_type,
                    )
                    for i in xrange(sectionParams['total'])
                ]
            elif storage_type == 'nfs':
                self.nfs_devices[storageSection] = [
                    self.__create_nas_device(
                        sectionParams['ip'],
                        self.host_group,
                        storage_type,
                    )
                    for i in xrange(sectionParams['total'])
                ]

            elif storage_type == 'pnfs':
                self.pnfs_devices[storageSection] = [
                    self.__create_nas_device(
                        sectionParams['ip'],
                        self.host_group,
                        storage_type,
                    )
                    for i in xrange(sectionParams['total'])
                ]

    @getStorageServers()
    def _storageSetupSAN(self, storage_type):
        """
        Description: creation of SAN devices

        :author: imeerovi
        :param storage_type: storage type type from conf file
        :return: None
        """
        block_devices = self.iscsi_devices if storage_type == 'iscsi' \
            else self.fcp_devices
        for storageSection, sectionParams in \
                self.storages[storage_type].items():
            self.log_storage_server(sectionParams['ip'], storageSection,
                                    storage_type)
            block_devices[storageSection] = [
                self.__create_block_device(
                    storage_type, sectionParams, self.host_group,
                    sectionParams['capacity'], **self.vdsData)
                for i in range(0, sectionParams['total'])
            ]

    def _storageSetupDAS(self):
        """
        creation of local fs devices

        :author: imeerovi
        :return: None
        """
        for storageSection, sectionParams in self.storages['local'].items():
            self.log_storage_server(sectionParams['ip'], storageSection,
                                    'local')
            self.local_devices[storageSection] = [
                self.__create_local_device(sectionParams['ip'],
                                           sectionParams['password'], path)
                for path in sectionParams['paths']
            ]

    @getStorageServers(ISO_EXPORT_TYPE)
    def _storageSetupISOandExportDomains(self):
        """
        creation of iso and export domains

        :author: imeerovi
        :return: None
        """
        fsType = self.config[MAIN_SECTION][ISO_EXPORT_TYPE]

        for storageSection, sectionParams in self.storages['iso'].items():
            self.log_storage_server(sectionParams['ip'], storageSection,
                                    'iso')
            self.iso_devices[storageSection] = [
                self.__create_nas_device(sectionParams['ip'], self.host_group,
                                         fsType)
                for i in range(0, sectionParams['total'])
            ]

        for storageSection, sectionParams in self.storages['export'].items():
            self.log_storage_server(sectionParams['ip'], storageSection,
                                    'export')
            self.export_devices[storageSection] = [
                self.__create_nas_device(sectionParams['ip'], self.host_group,
                                         fsType)
                for i in range(0, sectionParams['total'])
            ]

    def storageSetup(self):
        '''
        create NAS and block devices defined in settings

        :author: edolinin
        '''
        if self.storage_type == 'none':
            for st_type in NAS_STORAGE_TYPES:
                self._storageSetupNAS(st_type)
            for st_type in SAN_STORAGE_TYPES:
                self._storageSetupSAN(st_type)
            self._storageSetupDAS()
            # only storages from (POSIXFS_COMPLIANT_TYPES -
            # (already created POSIXFS_COMPLIANT_TYPES)) will be created
            # it means that 'nfs' and 'gluster' storages will not be created
            # since they were created before
            only_posixfs_supported_storage_types = \
                set(POSIXFS_COMPLIANT_TYPES) - set(NAS_STORAGE_TYPES)
            for st_type in only_posixfs_supported_storage_types:
                self._storageSetupNAS(st_type)

        elif self.storage_type in NAS_STORAGE_TYPES:
            self._storageSetupNAS(self.storage_type)

        elif self.storage_type == 'posixfs':
            if self.real_storage_type == 'mixed':
                for st_type in POSIXFS_COMPLIANT_TYPES:
                    self._storageSetupNAS(st_type)

            elif self.real_storage_type in POSIXFS_COMPLIANT_TYPES:
                self._storageSetupNAS(self.real_storage_type)

        elif self.storage_type in SAN_STORAGE_TYPES:
            self._storageSetupSAN(self.storage_type)

        elif self.storage_type == 'localfs':
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
        Wrapper that checks backward compatibility and updates conf file

        :author: imeerovi
        :return: None
        '''
        self._updateConfFile(cleanUpConf=True)
        self._updateConfFile()
        self._updateConfFile(backwardCompatibilityCheck=True)

    def _updateConfFile(self, backwardCompatibilityCheck=False,
                        cleanUpConf=False):
        '''
        update settings.conf with created devices data

        :author: edolinin
        :param backwardCompatibilityCheck: checks and converts list with one
            parameter to string and updates conf file
        :param cleanUpConf: if set, all existing storage data in conf file will
                            replaced with empty lists
        :return: None
        '''
        for type_, devices in dict(gluster=self.gluster_devices,
                                   nfs=self.nfs_devices,
                                   iso=self.iso_devices,
                                   export=self.export_devices,
                                   iscsi=self.iscsi_devices,
                                   fcp=self.fcp_devices,
                                   pnfs=self.pnfs_devices).iteritems():
            for target in filterNonEmptyDicts(devices):
                targetData = self.storages[type_][target]
                address = [targetData['ip']] * targetData['total']
                setConfValueByKeyPath(self.config, target, address, '_address',
                                      backwardCompatibilityCheck, cleanUpConf)
                if type_ not in SAN_STORAGE_TYPES:
                    path = devices[target]
                    setConfValueByKeyPath(self.config, target, path, '_path',
                                          backwardCompatibilityCheck,
                                          cleanUpConf)
                    if type_ not in ['iso', 'export']:
                        storage_types = [type_] * targetData['total']
                        setConfValueByKeyPath(self.config, target,
                                              storage_types,
                                              '_real_storage_type',
                                              backwardCompatibilityCheck,
                                              cleanUpConf)
                else:
                    scsiTarget = map(lambda x: x['target'], devices[target])
                    setConfValueByKeyPath(self.config, target, scsiTarget,
                                          '_target',
                                          backwardCompatibilityCheck,
                                          cleanUpConf)
                    scsiLun = map(lambda x: x['uuid'], devices[target])
                    setConfValueByKeyPath(self.config, target, scsiLun, '',
                                          backwardCompatibilityCheck,
                                          cleanUpConf)

        # Local domain
        for target in filterNonEmptyDicts(self.local_devices):
            path = self.local_devices[target]
            setConfValueByKeyPath(self.config, target, path, '_path',
                                  backwardCompatibilityCheck, cleanUpConf)

        self.config.write()

    def storageCleanup(self):
        '''
        remove NFS and block devices defined in settings

        :author: edolinin
        :return: None
        '''
        for storageSection in self.storages['gluster']:
            if storageSection in self.gluster_devices.keys():
                for device in self.gluster_devices[storageSection]:
                    self.__remove_nas_device(
                        self.storages['gluster'][storageSection]['ip'], device,
                        'gluster')

        for storageSection in self.storages['nfs']:
            if storageSection in self.nfs_devices.keys():
                for device in self.nfs_devices[storageSection]:
                    self.__remove_nas_device(
                        self.storages['nfs'][storageSection]['ip'], device,
                        'nfs')

        for storageSection in self.storages['pnfs']:
            if storageSection in self.pnfs_devices.keys():
                for device in self.pnfs_devices[storageSection]:
                    self.__remove_nas_device(
                        self.storages['pnfs'][storageSection]['ip'], device,
                        'pnfs')

        for stype in SAN_STORAGE_TYPES:
            for storageSection in self.storages[stype]:
                if self.storages[stype][storageSection]['total'] > 0:
                    lunId = 'serial' if self.storages[stype][
                        storageSection]['is_specific'] else 'uuid'
                    block_devices = self.iscsi_devices if \
                        stype == 'iscsi' else self.fcp_devices
                    if storageSection in block_devices.keys():
                        for device in block_devices[storageSection]:
                            self.__remove_block_device(
                                stype,
                                self.storages[stype][storageSection]['ip'],
                                device[lunId])
                        if block_devices[storageSection]:
                            self.__unmap_initiators(
                                stype,
                                self.storages[stype][storageSection]['ip'],
                            )

        for storageSection in self.storages['local']:
            if storageSection in self.local_devices.keys():
                for device in self.local_devices[storageSection]:
                    self.__remove_local_device(
                        self.storages['local'][storageSection]['ip'],
                        self.storages['local'][storageSection]['password'],
                        device,
                    )

        # choosing nas type for iso and export domain removal
        fsType = self.config[MAIN_SECTION][ISO_EXPORT_TYPE]

        for storageSection in self.storages['iso']:
            if storageSection in self.iso_devices.keys():
                for device in self.iso_devices[storageSection]:
                    self.__remove_nas_device(self.storages['iso'][
                        storageSection]['ip'], device, fsType)

        for storageSection in self.storages['export']:
            if storageSection in self.export_devices.keys():
                for device in self.export_devices[storageSection]:
                    self.__remove_nas_device(self.storages['export'][
                        storageSection]['ip'], device, fsType)

    def getStorageManager(self, storage_type, serverIp):
        if storage_type not in self.storageServers:
            self.storageServers[storage_type] = createStorageManager(
                [serverIp], storage_type.upper(), self.storageConfigFile)
        return self.storageServers[storage_type]

    def __create_nas_device(self, storageServerIp, deviceName, fsType):
        '''
        create NFS device with given name

        :author: edolinin
        :param deviceName: device name
        :return: path of a new device
        '''
        storageMngr = self.getStorageManager(fsType, storageServerIp)

        path = storageMngr.createDevice(deviceName)

        self.logger.info(PASS_CREATE_MSG.format(fsType, path))

        return path

    def __create_block_device(self, stype, storageServer, lunName, capacity,
                              **serversData):
        '''
        create block device with given name

        :author: edolinin
        :param stype: block device type: iSCSI or FCP
        :param storageServerIp: IP of storage server
        :param lunName: LUN name
        :param capacity: LUN capacity
        :param servers: list of lun initiators
        :return: dictionary of lunInfo and type of storage server
        '''
        storageMngr = self.getStorageManager(stype, storageServer['ip'])

        lunId, targetName = storageMngr.createLun(lunName, capacity)

        storageServer['is_specific'] = re.match('netapp|xtreamio',
                                                storageMngr.__class__.__name__,
                                                re.I)
        # linux TGT requires host IP instead of iqn for mapping
        if not re.search('(tgt|fcp)', storageMngr.__class__.__name__, re.I):
            initiators = serversData.values()
        else:
            initiators = serversData.keys()

        for initiator in initiators:
            hostGroups = storageMngr.getInitiatorHostGroups(initiator)
            for hg in hostGroups:
                if hg != lunName:
                    self.logger.info(
                        'Unmap initiator %s from host group %s',
                        initiator, hg,
                    )
                    storageMngr.unmapInitiator(hg, initiator)
        self.logger.info(
            'Map lun %s to host group %s, initiators: %s',
            lunId, lunName, initiators,
        )
        storageMngr.mapLun(lunId, lunName, *initiators)

        if storageServer['is_specific']:
            lunInfo = storageMngr.getLun(lunId, serversData.iterkeys().next())
        else:
            lunInfo = storageMngr.getLun(lunId)

        self.logger.info(PASS_CREATE_MSG.format(stype, lunId))

        return lunInfo

    def __create_local_device(self, server, password, path, username='root'):
        '''
        create local device with given path

        :author: edolinin
        :param server: dictionary of server ip and password
        :param path: path of local device
        :param username: server username
        :return: path of a new local device
        '''
        path = '{0}_{1}'.format(path, timeStamp())
        try:
            machineObj = Machine(server, username, password).util('linux')
            rc, out = machineObj.createLocalStorage(path)
            if not rc:
                raise Exception(
                    "Failed to create local storage device with path %s. "
                    "Error message is %s" % (path, out)
                )
        except FileAlreadyExistsError:
            pass

        self.logger.info(PASS_CREATE_MSG.format('local', path))

        return path

    def __remove_nas_device(self, storageServerIp, path, fsType):
        '''
        remove NFS device with given name

        :author: edolinin
        :param storageServerIp: IP of storage server
        :param path: path to NFS device
        :return: None
        '''
        try:
            storageMngr = self.getStorageManager(fsType, storageServerIp)
            storageMngr.removeDevice(path)
            self.logger.info(PASS_REMOVE_MSG.format(fsType, path))
        except Exception:
            self.logger.info(FAIL_REMOVE_MSG.format(fsType, path,
                                                    traceback.format_exc()))

    def __remove_block_device(self, stype, storageServerIp, deviceId):
        '''
        remove block device with given id

        :author: edolinin
        :param stype: block device type: iSCSI or FCP
        :param storageServerIp:  IP of storage server
        :param deviceId: device lun id or serial number
        :return: None
        '''

        try:
            storageMngr = self.getStorageManager(stype, storageServerIp)
            storageMngr.removeLun(deviceId)
            self.logger.info(PASS_REMOVE_MSG.format(stype, deviceId))
        except Exception:
            self.logger.info(FAIL_REMOVE_MSG.format(stype, deviceId,
                                                    traceback.format_exc()))

    def __unmap_initiators(self, stype, storageServerIp):
        '''
        cleanup initiator group - remove all the initiators from the group

        :param stype: block device type: iSCSI or FCP
        :param storageServerIp: IP of storage server
        '''
        storageMngr = self.getStorageManager(stype, storageServerIp)
        storageMngr_name = storageMngr.__class__.__name__.lower()
        initiators = (
            self.vdsData.values()
            if 'tgt' not in storageMngr_name and 'fcp' not in storageMngr_name
            else self.vdsData.keys()
        )
        hostGroup = self.host_group
        if initiators:
            self.logger.info('Unmap initiators %s from host group %s',
                             initiators, self.host_group)
            if (
                'solaris' in storageMngr_name or
                storageMngr_name == "newnetappstoragemanageriscsi"
            ):
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
        remove local device with given path

        :author: edolinin
        :param server: server name/ip
        :param password: server root password
        :param path: path of a local device
        :param username: server username
        :return: None
        '''

        try:
            machineObj = Machine(server, username, password).util('linux')
            rc, out = machineObj.removeLocalStorage(path, force=True)
            if not rc:
                raise Exception("Failed to remove local storage device with"
                                "path %s. Error message is %s" %
                                (path, out))
            self.logger.info(PASS_REMOVE_MSG.format('local', path))
        except Exception:
            self.logger.info(FAIL_REMOVE_MSG.format('local', path,
                                                    traceback.format_exc()))
