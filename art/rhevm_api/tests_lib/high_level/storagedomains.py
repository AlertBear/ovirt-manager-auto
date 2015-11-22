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
from pprint import pformat
import shlex
from art.rhevm_api import resources

from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.high_level import datastructures
from art.core_api import is_action
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__name__)


def _ISCSIdiscoverAndLogin(host, lun_address, lun_target, login_all=False):
    '''
    performs iscsi discovery and login
    __author__: kjachim, khakimi
    :param host: name of host on which iscsi commands should be performed
    :type host: str
    :param lun_address: iscsi server address
    :type lun_address:str
    :param lun_target: iscsi target (name of lun on iscsi address)
    :type lun_target: str
    :param login_all: When True login to all lun addresses and targets
    :type login_all: bool
    :return: True if both operations succeeded, False otherwise
    :rtype: bool
    '''
    # TODO fix the ll_sd.iscsiDiscover to return tuple of addresses and targets
    # when the RFE https://bugzilla.redhat.com/show_bug.cgi?id=1264777
    # will resolve then remove discover_addresses_and_targets method
    addresses = []
    targets = []
    if login_all:
        addresses, targets = discover_addresses_and_targets(host, lun_address)
    else:
        targets = ll_sd.iscsiDiscover('True', host, lun_address)
        if not targets:
            logger.error(
                'Failed to discover lun address %s from %s', lun_address, host
            )
            return False

    lun_address = addresses if login_all else [lun_address]
    lun_target = targets if login_all else [lun_target]

    if not ll_sd.iscsiLogin(True, host, lun_address, lun_target):
        return False

    return True


def discover_addresses_and_targets(host, server_address):
    """
    discover the addresses and corresponding targets that host could login
    :param host: name of host on which iscsiadm commands should be performed
    :type host: str
    :param server_address: iscsi server address
    :type server_address: str
    :return: tuple of corresponding lists ([addresses], [targets])
    :rtype: tuple
    """
    cmd = "iscsiadm -m discovery -t st -p %s" % server_address

    host_obj = ll_sd.hostUtil.find(host)

    vds_host = resources.Host.get(host_obj.address)
    rc, out, err = vds_host.executor().run_cmd(cmd=shlex.split(cmd))
    if rc:
        logger.error(
            "Failed to run command %s on host %s; out: %s; err: %s",
            cmd, vds_host.ip, out, err
        )
        return None, None
    # each line in out looks like the following:
    # "10.35.160.107:3260,4 iqn.1992-04.com.emc:cx.ckm00121000438.b7"
    addresses, targets = zip(
        *[(line.split()[0].split(":")[0], line.split()[1])
          for line in out.splitlines() if line]
    )
    return list(addresses), list(targets)


@is_action()
def importBlockStorageDomain(host, lun_address, lun_target):
    """
    Import an iscsi storage domain

    __author__ = "ratamir"
    :param host: host name to use for import
    :type host: str
    :param lun_address: lun address
    :type lun_address: str
    :param lun_target: lun target
    :type lun_target: str
    :return: True if the import succeeded or False otherwise
    """
    if not _ISCSIdiscoverAndLogin(host, lun_address, lun_target):
        return False
    host_obj = ll_sd.hostUtil.find(host)
    host_obj_id = ll_sd.Host(id=host_obj.get_id())
    iscsi = ll_sd.IscsiDetails(address=lun_address)
    # TODO: This call for asyc is not working until
    # JIRA ticket https://projects.engineering.redhat.com/browse/RHEVM-2141
    # will be resolved
    response = ll_sd.hostUtil.syncAction(
        host_obj, "unregisteredstoragedomainsdiscover", True, iscsi=iscsi,
        iscsi_target=[lun_target]
    )
    if not response:
        ll_sd.util.logger.error('Failed to find storage domains to import')
        return False
    sd_object = response.get_storage_domains().get_storage_domain()[0]

    storage_object = ll_sd.Storage()
    storage_object.set_type(ENUMS['storage_type_iscsi'])

    sd = ll_sd.StorageDomain(id=sd_object.get_id())
    sd.set_type(ENUMS['storage_dom_type_data'])
    sd.set_host(host_obj_id)
    sd.set_storage(storage_object)
    sd.set_import('true')

    return ll_sd.util.create(sd, True, compare=False)[1]


@is_action()
def addISCSIDataDomain(host, storage, data_center, lun, lun_address,
                       lun_target, lun_port=3260, storage_format=None,
                       override_luns=None, login_all=False):
    '''
    positive flow for adding ISCSI Storage including all the necessary steps
    __author__: atal
    :param host: name of host
    :type host: str
    :param storage: name of storage domain that will be created in rhevm
    :type storage: str
    :param data_center: name of DC which will contain this SD
    :type data_center: str
    :param lun: lun number
    :type lun: str
    :param lun_address: iscsi server address
    :type lun_address:str
    :param lun_target: iscsi target (name of lun on iscsi address)
    :type lun_target: str
    :param lun_port: lun port
    :type lun_port: int
    :param storage_format: storage format version (v1/v2/v3)
    :type storage_format: str
    :param override_luns: when True it will format/wipe out the block device
    :type override_luns: bool
    :param login_all: when True login to all lun addresses and targets
    :type login_all: bool
    :return: True if succeeded, False otherwise
    :rtype: bool
    '''

    if not _ISCSIdiscoverAndLogin(host, lun_address, lun_target, login_all):
        return False

    if not ll_sd.addStorageDomain(
            True, host=host, name=storage, type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_iscsi'], lun=lun,
            lun_address=lun_address, lun_target=lun_target, lun_port=lun_port,
            storage_format=storage_format, override_luns=override_luns):
        logger.error('Failed to add (%s, %s, %s) to %s' % (
            lun_address, lun_target, lun, host))
        return False

    status = ll_sd.attachStorageDomain(True, data_center, storage, True)

    return status and ll_sd.activateStorageDomain(True, data_center, storage)


@is_action()
def extendISCSIDomain(
        storage_domain, host, extend_lun, extend_lun_address,
        extend_lun_target, extend_lun_port=3260, override_luns=None):
    """
    Extends iSCSI storage domain using the requested LUN parameters

    __author__ = "kjachim, glazarov"
    :param storage_domain: The storage domain which is to be extended
    :type storage_domain: str
    :param host: The host to be used with which to extend the storage domain
    :type host: str
    :param extend_lun: The LUN to be used when extending storage domain
    :type extend_lun: str
    :param extend_lun_address: The iSCSI server address which contains the LUN
    :type extend_lun_address: str
    :param extend_lun_target: The iSCSI target (name of the LUN in iSCSI
    server)
    :type extend_lun_target: str
    :param extend_lun_port: The iSCSI server port (default is 3260)
    :type extend_lun_port: int
    :param override_luns: True if the block device should be formatted
    (when not empty), False if block device should be used as is
    :type override_luns: bool
    :returns: True when storage domain is successfully extended,
    False otherwise
    :rtype: bool
    """
    if not _ISCSIdiscoverAndLogin(host, extend_lun_address, extend_lun_target):
        return False

    return ll_sd.extendStorageDomain(
        True, storagedomain=storage_domain, host=host, lun=extend_lun,
        lun_address=extend_lun_address, lun_target=extend_lun_target,
        lun_port=extend_lun_port, storage_type=ENUMS['storage_type_iscsi'],
        override_luns=override_luns)


@is_action()
def extendFCPDomain(storage_domain, host, lun):
    """
    Description: extends fcp storage domain with given lun
    Author: kjachim
    Parameters:
        * host - host on which storage domain is created
        * lun - lun which we want to extend storage domain with
        * storage_domain - storage domain to extend
    returns True in case of success, False otherwise
    """
    return ll_sd.extendStorageDomain(
        True, storagedomain=storage_domain, lun=lun, host=host,
        storage_type=ENUMS['storage_type_fcp'])


@is_action()
def addGlusterDomain(host, name, data_center, address, path, vfs_type,
                     sd_type=ENUMS['storage_dom_type_data'],
                     storage_format=None):
    """
    Description: Adds a glusterFS storage domain, attaches it to the given DC
    and activates it
    Author: gickowic
    Parameters:
        * host - host used to add the domain
        * name - name of the storage domain
        * data_center - datacenter to create the domain in
        * address - address of one of the gluster nodes
        * path - path of gluster volume
        * vfs_type - vfs_type parameter used by rhevm api like posix domain
    Return: True if domain was successfully added, attached to DC and activated
    """
    if not ll_sd.addStorageDomain(
            True, host=host, name=name, type=sd_type,
            storage_type=ENUMS['storage_type_gluster'], address=address,
            path=path, storage_format=storage_format, vfs_type=vfs_type):
        logger.error('Failed to add %s:%s using host %s', address, path, host)
        return False

    status = ll_sd.attachStorageDomain(True, data_center, name, True)

    return status and ll_sd.activateStorageDomain(True, data_center, name)


@is_action()
def addNFSDomain(host, storage, data_center, address, path,
                 sd_type=ENUMS['storage_dom_type_data'], storage_format=None,
                 format=None, activate=True):
    '''
    positive flow for adding NFS Storage including all the necessary steps
    Author: atal
    Parameters:
        * host - name of host
        * storage - name of storage domain that will be created in rhevm
        * data_center - name of DC which will contain this SD
        * address - nfs server address
        * path - path for nfs mount
        * sd_type - type of storage domain: data, iso or export
        * storage_format - storage format version (v1/v2/v3)
        * format - when True it will remove the previous data
        * activate - when True it will attach & activate domain
    return True if succeeded, False otherwise
    '''
    if not ll_sd.addStorageDomain(
            True, host=host, name=storage, type=sd_type,
            storage_type=ENUMS['storage_type_nfs'], address=address, path=path,
            storage_format=storage_format, format=format):
        logger.error('Failed to add %s:%s to %s' % (address, path, host))
        return False

    if activate:
        status = ll_sd.attachStorageDomain(True, data_center, storage, True)
        return status and ll_sd.activateStorageDomain(
            True, data_center, storage,
        )
    return True


@is_action()
def addLocalDataDomain(host, storage, data_center, path):
    """
    positive flow for adding local storage including all the necessary steps
    Author: kjachim
    Parameters:
        * host - name of host
        * storage - name of storage domain that will be created in rhevm
        * data_center - name of DC which will contain this SD
        * path - path on the local machine
    return True if succeeded, False otherwise
    """
    if not ll_sd.addStorageDomain(
            True, host=host, name=storage, type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_local'], path=path):
        logger.error('Failed to add local storage %s to %s' % (path, host))
        return False

    if not ll_sd.activateStorageDomain(True, data_center, storage):
        logger.error("Cannot activate storage domain %s" % storage)
        return False

    return True


@is_action()
def addPosixfsDataDomain(
        host, storage, data_center, address, path,
        sd_type=ENUMS['storage_dom_type_data'],
        vfs_type=ENUMS['storage_type_nfs'], nfs_version=None):
    """
    positive flow for adding posixfs storage including all the necessary steps

    :param host: Name of the host to be used for adding the posix domain
    :type host: str
    :param storage: Name of storage domain that will be created in rhevm
    :type storage: str
    :param data_center: Name of DC which will contain this SD
    :type data_center: str
    :param address: NFS server address
    :type address: str
    :param path: Path for nfs mount
    :type path: str
    :param sd_type: Type of storage domain: data, iso or export
    :type sd_type: str
    :param vfs_type: VFS type to use for the new POSIX domains
    :type vfs_type: str
    :param nfs_version: NFS version to use for mounting posix domain
    :type nfs_version: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    if not ll_sd.addStorageDomain(
            True, host=host, name=storage, type=sd_type,
            address=address, storage_type=ENUMS['storage_type_posixfs'],
            path=path, vfs_type=vfs_type, nfs_version=nfs_version):
        logger.error('Failed to add posixfs storage %s to %s' % (path, host))
        return False

    if not ll_sd.attachStorageDomain(True, data_center, storage, True):
        logger.error("Cannot attach posixfs domain %s" % storage)
        return False

    if not ll_sd.activateStorageDomain(True, data_center, storage):
        logger.error("Cannot activate posixfs domain %s" % storage)
        return False

    return True


@is_action()
def addFCPDataDomain(host, storage, data_center, lun):
    """
    positive flow for adding FCP storage including all the necessary steps
    Author: kjachim
    Parameters:
        * host - name of host
        * storage - name of storage domain that will be created in rhevm
        * data_center - name of DC which will contain this SD
        * lun - lun
    return True if succeeded, False otherwise
    """
    if not ll_sd.addStorageDomain(
            True, host=host, name=storage, type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_fcp'], lun=lun):
        logger.error('Failed to add fcp storage %s to %s' % (lun, storage))
        return False

    if not ll_sd.activateStorageDomain(True, data_center, storage):
        logger.error("Cannot activate storage domain %s" % storage)
        return False

    return True


def extend_storage_domain(storage_domain, type_, host, **kwargs):
    """
    Description: Extends given storage domain with luns defined
        with extend_lun* params
    Author: kjachim
    Parameters:
        * storage_domain - name of storage domain which should be extended
        * storage - dictionary ([storage_type] section)
        * type_ - type of storage (iscsi, nfs, fcp, localfs)
        * host - name of the host to use
    """
    logger.info("extending storage domain %s" % storage_domain)
    if type_ == ENUMS['storage_type_iscsi']:
        __extend_iscsi_domain(storage_domain, host, **kwargs)
    elif type_ == ENUMS['storage_type_fcp']:
        __extend_fcp_domain(storage_domain, host, **kwargs)
    else:
        raise errors.UnkownConfigurationException(
            "Extending storage domain is supported for iscsi/fcp data centers")


def __extend_iscsi_domain(storage_domain, host, **kwargs):
    """
    Extends iSCSI storage domain using the requested LUN parameters

    __author__ = "glazarov"
    :param storage_domain: The storage domain which is to be extended
    :type storage_domain: str
    :param host: The host to be used with which to extend the storage domain
    :type host: str
    :param lun_list: The LUNs to be used when extending storage domain
    :type lun_list: list of str

    :param lun_addresses: The iSCSI server addresses which contain the LUNs
    :type lun_addresses: list of str
    :param lun_targets: The iSCSI targets (names of the LUN in iSCSI server)
    :type lun_targets: list of str
    :param override_luns: True if the block device should be formatted
    (when not empty), False if block device should be used as is
    :type override_luns: bool
    :returns: Null on success, raises StorageDomainException on failure
    :rtype: null
    """
    lun_targets_list = kwargs.pop('lun_targets')
    lun_addresses_list = kwargs.pop('lun_addresses')
    lun_list = kwargs.pop('lun_list')
    override_luns = kwargs.pop('override_luns', None)
    for (lun, lun_address, lun_target) in zip(
            lun_list, lun_addresses_list, lun_targets_list):
        if not extendISCSIDomain(
                storage_domain, host, lun, lun_address, lun_target,
                override_luns=override_luns):
            raise errors.StorageDomainException(
                "extendISCSIDomain(%s, %s, %s, %s, %s) failed." % (
                    storage_domain, host, lun, lun_address, lun_target))


def __extend_fcp_domain(storage_domain, host, **kwargs):
    """
    Description: Extends fcp domain with luns defined with extend_lun parameter
    Parameters:
        * storage_domain - storage domain to extend
        * host - host on which storage domain is created
        * lun_targets - list of lun targets
        * lun_addresses - list of lun addresses
        * lun_list - list of lun ids
    """
    lun_list = kwargs.pop('lun_list')
    for lun in lun_list:
        if not extendFCPDomain(storage_domain, host, lun):
            raise errors.StorageDomainException(
                "extendFCPDomain(%s, %s, %s) failed." %
                (storage_domain, host, lun))


class StorageAdder(object):
    """ Adds all storages defined in config file to given datacenter.
        This is a base class, use one of the specific implementations!
        Each implementation should define its own add_storage for adding
        one data storage domain.
    """
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        """
            Parameters:
              * datacenter - data center name
              * host - name of the host to use
              * storage - storage configuration (config file section)
              * export_name - name of export domain
              * iso_name - name of iso domain
        """
        self.datacenter = datacenter
        self.host = host
        self.storage = storage
        self.no_of_data_storages = 0
        self.export_name = export_name
        self.iso_name = iso_name

    def _add_storage(self, add_func, *args):
        if not add_func(*args):
            raise errors.StorageDomainException(
                "%s domain adding function with arguments %s failed" % (
                    add_func.__name__, args))
        logging.info(
            "%s function added storage with args %s", add_func.__name__, args)

    def add_storage(self, i):
        """ adds one data domain
            parameters:
             * index of the data domain in the config file
        """
        raise NotImplementedError("Should be implemented in subclass!")

    def add_storages(self):
        """ Adds all storages from config file.
        """
        if not self.no_of_data_storages:
            return []
        created_storages = []
        created_storages.append(self.add_storage(0))
        hosts.waitForSPM(self.datacenter, 600, 10)
        for i in range(1, self.no_of_data_storages):
            created_storages.append(self.add_storage(i))
        self.add_export_domains()
        self.add_iso_domains()
        return created_storages

    def _add_nfs_domain(self, address, path, sd_type, name, activate=True):
        if address is not None and path is not None:
            if not addNFSDomain(
                self.host, name, self.datacenter, address, path, sd_type,
                activate,
            ):
                raise errors.StorageDomainException(
                    "addNFSDomain %s (%s, %s, %s) to DC %s failed." %
                    (sd_type, address, path, self.host, self.datacenter))
            logging.info(
                "%s domain %s was created successfully", sd_type, name)
        else:
            logging.info(
                "There is no %s domain defined in config file", sd_type)

    def add_export_domains(self):
        """ Adds export domain
        """
        try:
            export_addresses = self.storage.as_list('export_domain_address')
            export_paths = self.storage.as_list('export_domain_path')
        except KeyError:
            export_addresses = []
            export_paths = []

        activate = True
        for address, path in zip(export_addresses, export_paths):
            self._add_nfs_domain(
                address, path, ENUMS['storage_dom_type_export'],
                self.export_name, activate,
            )
            activate = False

    def add_iso_domains(self):
        """ Adds iso domain
        """
        iso_address = self.storage.get('iso_domain_address', None)
        iso_path = self.storage.get('iso_domain_path', None)
        self._add_nfs_domain(
            iso_address, iso_path, ENUMS['storage_dom_type_iso'],
            self.iso_name)


class NFSStorageAdder(StorageAdder):
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        super(NFSStorageAdder, self).__init__(
            datacenter, host, storage, export_name, iso_name)
        self.addresses = self.storage.as_list('data_domain_address')
        self.paths = self.storage.as_list('data_domain_path')
        self.no_of_data_storages = len(self.paths)

    def add_storage(self, i):
        """ Adds one NFS data domain
        """

        name = "nfs_%s" % i
        self._add_storage(
            addNFSDomain, self.host, name, self.datacenter, self.addresses[i],
            self.paths[i], ENUMS['storage_dom_type_data'])
        return name


class ISCSIStorageAdder(StorageAdder):
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        super(ISCSIStorageAdder, self).__init__(
            datacenter, host, storage, export_name, iso_name)
        self.lun_targets = self.storage.as_list('lun_target')
        self.lun_addresses = self.storage.as_list('lun_address')
        self.luns = self.storage.as_list('lun')
        self.no_of_data_storages = len(self.luns)

    def add_storage(self, i):
        """ Adds one iSCSI data domain
        """
        name = "iscsi_%d" % i
        self._add_storage(
            addISCSIDataDomain, self.host, name, self.datacenter, self.luns[i],
            self.lun_addresses[i], self.lun_targets[i])
        return name


class FCPStorageAdder(StorageAdder):
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        super(FCPStorageAdder, self).__init__(
            datacenter, host, storage, export_name, iso_name)
        self.luns = self.storage.as_list('lun')
        self.no_of_data_storages = len(self.luns)

    def add_storage(self, i):
        """ Adds one FCP data domain
        """
        name = "iscsi_%d" % i
        self._add_storage(
            addFCPDataDomain, self.host, name, self.datacenter, self.luns[i])
        return name


class LocalFSStorageAdder(StorageAdder):
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        super(LocalFSStorageAdder, self).__init__(
            datacenter, host, storage, export_name, iso_name)
        self.local_domain_paths = self.storage.as_list("local_domain_path")
        self.no_of_data_storages = len(self.local_domain_paths)

    def add_storage(self, i):
        """ Adds one localfs data domain
        """
        name = "local_%s" % i
        self._add_storage(
            addLocalDataDomain, self.host, name, self.datacenter,
            self.local_domain_paths[i])
        return name


class PosixFSStorageAdder(StorageAdder):
    def __init__(self, datacenter, host, storage, export_name, iso_name):
        super(PosixFSStorageAdder, self).__init__(
            datacenter, host, storage, export_name, iso_name)
        self.vfs_type = self.storage["vfs_type"]
        self.domain_paths = self.storage.as_list("data_domain_path")
        self.domain_addresses = self.storage.as_list("data_domain_address")
        self.no_of_data_storages = len(self.domain_paths)
        self.mount_options = self.storage.get(
            "data_domain_mount_options", None)

    def add_storage(self, i):
        """ Adds one posixfs data domain
        """
        name = "posixfs_%s" % i
        self._add_storage(
            addPosixfsDataDomain, self.host, name, self.datacenter,
            self.domain_addresses[i], self.domain_paths[i], self.vfs_type,
            self.mount_options)
        return name


class GlusterStorageAdder(PosixFSStorageAdder):
    def add_storage(self, i):
        name = 'gluster_%s' % i
        self.domain_addresses = self.storage.as_list(
            "gluster_data_domain_address"
        )
        self.domain_paths = self.storage.as_list("gluster_data_domain_path")
        self._add_storage(addGlusterDomain, self.host, name, self.datacenter,
                          self.domain_addresses[i], self.domain_paths[i],
                          self.vfs_type, ENUMS['storage_dom_type_data'])
        return name


def create_storages(storage, type_, host, datacenter,
                    export_name="export_domain", iso_name="iso_domain"):
    """
    Description: Creates storages accordign storage dictionary
    Parameters:
        * storage - dictionary ([storage_type] section)
        * type_ - type of storage (iscsi, nfs, fcp, localfs)
        * host - name of the host to use
        * export_name - name of export domain, if any
        * iso_name - name of iso domain, if any
    """
    storage_types = {
        ENUMS['storage_type_nfs']: NFSStorageAdder,
        ENUMS['storage_type_iscsi']: ISCSIStorageAdder,
        ENUMS['storage_type_fcp']: FCPStorageAdder,
        ENUMS['storage_type_local']: LocalFSStorageAdder,
        ENUMS['storage_type_posixfs']: PosixFSStorageAdder,
        ENUMS['storage_type_gluster']: GlusterStorageAdder}

    logger.debug('Creating storages: %s', pformat(storage))

    if type_ in storage_types:
        storage_adder = storage_types[type_](
            datacenter, host, storage, export_name, iso_name)
    else:
        raise errors.UnkownConfigurationException(
            "unknown storage type: %s" % type_)

    return storage_adder.add_storages()


@is_action()
def remove_storage_domain(name, datacenter, host, format_disk=False, vdc=None,
                          vdc_password=None):
    """ Deactivates, detaches and removes storage domain.
    """

    dc_storages = []
    if datacenter is not None:
        dc_storages = [x.name for x in ll_sd.getDCStorages(datacenter, False)]

    if name in dc_storages:
        if ll_sd.is_storage_domain_active(datacenter, name):
            logging.info("Deactivating storage domain")
            if not ll_sd.deactivateStorageDomain(True, datacenter, name):
                raise errors.StorageDomainException(
                    "Cannot deactivate storage domain %s in datacenter %s!" % (
                        name, datacenter))

        logging.info("Detaching storage domain")
        if not ll_sd.detachStorageDomain(True, datacenter, name):
            raise errors.StorageDomainException(
                "Cannot detach storage domain %s from datacenter %s!" % (
                    name, datacenter))

    logging.info("Removing storage domain")
    if not ll_sd.removeStorageDomain(True, name, host, str(format_disk)):
        raise errors.StorageDomainException(
            "Cannot remove storage domain %s!" % name)
    logging.info("Storage domain %s removed" % name)


@is_action()
def create_nfs_domain_with_options(
        name, sd_type, host, address, path, version=None, retrans=None,
        timeo=None, mount_options=None, datacenter=None, positive=True):
    """
    Creates NFS storage domain with specified options. If datacenter is not
    None, also attaches to the specified datacenter.

    **Author**: Katarzyna Jachim

    **Parameters**:
        * *name* - name of created storage domain
        * *sd_type* - one of ENUMS['storage_dom_type_export'],
             ENUMS['storage_dom_type_iso'] or ENUMS['storage_dom_type_data']
        * *host* - host on which NFS resource should be mounted
        * *address* - address of NFS server
        * *path* - path of the NFS resource on the server
        * *version* - NFS protocol version which should be used
        * *retrans* - Retransmissions (NFS option)
        * *mount_options* - # custom mount options (NFS option)
        * *timeo* - NFS timeout
        * *datacenter* - if not None: datacenter to which sd should be attached

    **Returns**: nothing, raise an exception in case of an error
    """
    logging.info("Adding storage domain")
    old_storage = ll_sd.Storage
    if not positive:  # in positive tests we won't pass incorrect values
        ll_sd.Storage = datastructures.Storage
    if not ll_sd.addStorageDomain(
            positive, name=name, type=sd_type, host=host, address=address,
            storage_type=ENUMS['storage_type_nfs'], path=path,
            nfs_version=version, nfs_retrans=retrans, nfs_timeo=timeo,
            mount_options=mount_options):
        ll_sd.Storage = old_storage  # just in case...
        raise errors.StorageDomainException(
            "Cannot add storage domain %s" % name)
    ll_sd.Storage = old_storage

    if datacenter is not None and positive:
        logging.info("Attaching storage domain")
        if not ll_sd.attachStorageDomain(True, datacenter, name):
            raise errors.StorageDomainException(
                "Cannot attach %s to %s" % (name, datacenter))


@is_action('attachAndActivateDomain')
def attach_and_activate_domain(datacenter, domain):
    """
    Description: Attaches (if necessary) and activates a domain
    Author: gickowic
    Parameters:
        * datacenter - datacenter name
        * domain - domain name
    Returns true if successful
    """
    logger.info('Checking if domain %s is attached to dc %s'
                % (domain, datacenter))

    dc_storage_objects = ll_sd.getDCStorages(datacenter, False)

    if not [sd for sd in dc_storage_objects if sd.get_name() == domain]:
        logger.info('Attaching domain %s to dc %s' % (domain, datacenter))
        if not ll_sd.attachStorageDomain(True, datacenter, domain):
            raise errors.StorageDomainException(
                'Unable to attach domain %s to dc %s'
                % (domain, datacenter))
    logger.info('Domain %s attached to dc %s' % (domain, datacenter))

    logger.info('Activating domain %s on dc %s' % (domain, datacenter))

    if not ll_sd.activateStorageDomain(True, datacenter, domain):
        raise errors.StorageDomainException(
            'Unable to activate domain %s on dc %s'
            % (domain, datacenter))
    logger.info('Domain %s was activated', domain)

    return True


@is_action('createNfsDomainAndVerifyOptions')
def create_nfs_domain_and_verify_options(domain_list, host=None,
                                         password=None, datacenter=None):
    """
    Creates NFS domains with specified options, if datacenter is not
    None - attaches them to this datacenter, then check that the specified
    NFS resources are mounted on given host with required options.

    **Author**: Katarzyna Jachim

    **Parameters**:
     * *domain_list*: list of objects of class NFSStorage, each of them
                      describes one storage domain
     * *host*: name of host on which storage domain should be mounted
     * *password*: root password on the host
     * *datacenter*: if not None - datacenter to which NFS storage domain
                     should be attached

    **Returns**: nothing, raise StorageDomainException exception if the
                 verification phase of this function fails
    """

    for domain in domain_list:
        logger.info("Creating nfs domain %s" % domain.name)
        create_nfs_domain_with_options(
            domain.name, domain.sd_type, host, domain.address,
            domain.path, retrans=domain.retrans_to_set,
            version=domain.vers_to_set, timeo=domain.timeout_to_set,
            mount_options=domain.mount_options_to_set,
            datacenter=datacenter)

    logger.info("Getting info about mounted resources")
    host_ip = hosts.getHostIP(host)
    mounted_resources = ll_sd.get_mounted_nfs_resources(host_ip, password)

    logger.info("verifying nfs options")
    for domain in domain_list:
        nfs_timeo, nfs_retrans, nfs_vers, nfs_sync = mounted_resources[
            (domain.address, domain.path)]
        result = ll_sd.verify_nfs_options(
            domain.expected_timeout, domain.expected_retrans,
            domain.expected_vers, domain.expected_mount_options, nfs_timeo,
            nfs_retrans, nfs_vers, nfs_sync)
        if result:
            raise errors.StorageDomainException(
                "Wrong NFS options! Expected %s: %s, real: %s" % result)


@is_action('detachAndDeactivateDomain')
def detach_and_deactivate_domain(datacenter, domain):
    """
    Description: deactivates a domain (if necessary) and detaches it
    Author: gickowic
    Parameters:
        * datacenter - datacenter name
        * domain - domain name
    Returns true if successful
    """
    logger.info('Checking if domain %s active in dc %s'
                % (domain, datacenter))
    if ll_sd.is_storage_domain_active(datacenter, domain):
        logger.info('Domain %s is active in dc %s' % (domain, datacenter))

        logger.info('Deactivating domain  %s in dc %s' % (domain, datacenter))
        if not ll_sd.deactivateStorageDomain(True, datacenter, domain):
            raise errors.StorageDomainException(
                'Unable to deactivate domain %s on dc %s'
                % (domain, datacenter))

    logger.info('Domain %s is inactive in datacenter %s'
                % (domain, datacenter))

    logger.info('Detaching domain %s from dc %s' % (domain, datacenter))
    if not ll_sd.detachStorageDomain(True, datacenter, domain):
        raise errors.StorageDomainException(
            'Unable to detach domain %s from dc %s'
            % (domain, datacenter))
    logger.info('Domain %s detached to dc %s' % (domain, datacenter))

    return True


def get_master_storage_domain_ip(datacenter):
    found, master_domain = ll_sd.findMasterStorageDomain(True, datacenter)
    assert found
    master_domain = master_domain['masterDomain']
    found, master_domain_ip = ll_sd.getDomainAddress(True, master_domain)
    assert found
    return master_domain_ip['address']
