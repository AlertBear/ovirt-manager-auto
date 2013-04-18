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

from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.high_level import datastructures
from art.core_api import is_action
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__name__)


def _ISCSIdiscoverAndLogin(host, lun_address, lun_target):
    """
        Description: performs iscsi discovery and login
        Author: kjachim
        Parameters:
            * host - host on which iscsi commands should be performed
            * lun_address - iscsi server address
            * lun_target - iscsi target (name of lun on iscsi address)
        returns True of both operations succeeded, False otherwise
    """
    if not storagedomains.iscsiDiscover('True', host, lun_address):
        logger.error('Failed to discover lun address %s from %s' %
                     (lun_address, host))
        return False

    if not storagedomains.iscsiLogin('True', host, lun_address, lun_target):
        logger.error('Failed to login %s on target %s from %s' %
                     (lun_address, lun_target, host))
        return False

    return True


@is_action()
def addISCSIDataDomain(host, storage, data_center, lun, lun_address,
                       lun_target, lun_port=3260, storage_format=None):
    '''
    positive flow for adding ISCSI Storage including all the necessary steps
    Author: atal
    Parameters:
        * host - name of host
        * storage - name of storage domain that will be created in rhevm
        * data_center - name of DC which will contain this SD
        * lun - lun number
        * lun_address - iscsi server address
        * lun_target - name of lun target in iscsi server
        * lun_port - lun port
        * storage_format - storage format version (v1/v2/v3)
    return True if succeeded, False otherwise
    '''

    if not _ISCSIdiscoverAndLogin(host, lun_address, lun_target):
        return False

    if not storagedomains.addStorageDomain(True, host=host, name=storage,
                                    type=ENUMS['storage_dom_type_data'],
                                    storage_type=ENUMS['storage_type_iscsi'],
                                    lun=lun, lun_address=lun_address,
                                    lun_target=lun_target, lun_port=lun_port,
                                    storage_format=storage_format):
        logger.error('Failed to add (%s, %s, %s) to %s' % (lun_address,
                     lun_target, lun, host))
        return False

    status = storagedomains.attachStorageDomain(True, data_center, storage,
                                                True)

    return status and storagedomains.activateStorageDomain(True, data_center,
                                 storage)


@is_action()
def extendISCSIDomain(storage_domain, host, extend_lun, extend_lun_address,
                     extend_lun_target, extend_lun_port=3260):
    """
    Description:
        Extends iscsi storage domain with given lun,
        performs all needed operation (discover & login)
    Author: kjachim
    Parameters:
        * host - host on which storage domain is created
        * storage_domain - storage domain to extend
        * extend_lun - lun which we want to extend storage domain with
        * extend_lun_address - iscsi server address
        * extend_lun_target - iscsi target (name of lun on iscsi address)
        * extend_lun_port - (optional) iscsi server port (default 3260)
    returns True in case of success, False otherwise
    """
    if not _ISCSIdiscoverAndLogin(host, extend_lun_address, extend_lun_target):
        return False

    return storagedomains.extendStorageDomain(
                True,
                storagedomain=storage_domain,
                lun=extend_lun,
                lun_address=extend_lun_address,
                lun_target=extend_lun_target,
                lun_port=extend_lun_port,
                host=host,
                storage_type=ENUMS['storage_type_iscsi'])


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
    return storagedomains.extendStorageDomain(
                True,
                storagedomain=storage_domain,
                lun=lun,
                host=host,
                storage_type=ENUMS['storage_type_fcp'])


@is_action()
def addNFSDomain(host, storage, data_center, address, path,
                 sd_type=ENUMS['storage_dom_type_data'], storage_format=None):
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
    return True if succeeded, False otherwise
    '''
    if not storagedomains.addStorageDomain(True, host=host, name=storage,
                                    type=sd_type,
                                    storage_type=ENUMS['storage_type_nfs'],
                                    address=address, path=path,
                                    storage_format=storage_format):
        logger.error('Failed to add %s:%s to %s' % (address, path, host))
        return False

    status = storagedomains.attachStorageDomain(True, data_center, storage,
                                                True)
    return status and storagedomains.activateStorageDomain(True, data_center,
                                 storage)


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
    if not storagedomains.addStorageDomain(True, host=host, name=storage,
            type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_local'], path=path):
        logger.error('Failed to add local storage %s to %s' % (path, host))
        return False

    if not storagedomains.activateStorageDomain(True, data_center, storage):
        logger.error("Cannot activate storage domain %s" % storage)
        return False

    return True


@is_action()
def addPosixfsDataDomain(host, storage, data_center, address, path, vfs_type):
    """
    positive flow for adding posixfs storage including all the necessary steps
    Author: kjachim
    Parameters:
        * host - name of host
        * storage - name of storage domain that will be created in rhevm
        * data_center - name of DC which will contain this SD
        * storage_format - storage format version (v1/v2/v3)
        * address - nfs server address
        * path - path for nfs mount
        * sd_type - type of storage domain: data, iso or export
        * vfs_type - ...
    return True if succeeded, False otherwise
    """
    if not storagedomains.addStorageDomain(True, host=host, name=storage,
            type=ENUMS['storage_dom_type_data'], address=address,
            storage_type=ENUMS['storage_type_posixfs'], path=path,
            vfs_type=vfs_type):
        logger.error('Failed to add posixfs storage %s to %s' % (path, host))
        return False

    if not storagedomains.attachStorageDomain(
                                    True, data_center, storage, True):
        logger.error("Cannot attach posixfs domain %s" % storage)
        return False

    if not storagedomains.activateStorageDomain(True, data_center, storage):
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
    if not storagedomains.addStorageDomain(True, host=host, name=storage,
            type=ENUMS['storage_dom_type_data'],
            storage_type=ENUMS['storage_type_fcp'], lun=lun):
        logger.error('Failed to add fcp storage %s to %s' % (lun, storage))
        return False

    if not storagedomains.activateStorageDomain(True, data_center, storage):
        logger.error("Cannot activate storage domain %s" % storage)
        return False

    return True


def extend_storage_domain(storage_domain, type_, host, storage):
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
        __extend_iscsi_domain(storage_domain, host, storage)
    elif type_ == ENUMS['storage_type_fcp']:
        __extend_fcp_domain(storage_domain, host, storage)
    else:
        raise errors.UnkownConfigurationException(
            "Extending storage domain is supported for iscsi/fcp data centers")


def __extend_iscsi_domain(storage_domain, host, storage_conf):
    """
    Description: Extends iscsi domain with luns defined with extend_lun* params
    Parameters:
        * storage_domain - storage domain to extend
        * host - host on which storage domain is created
        * storage_conf - dictionary ([storage_type] section)
    """
    lun_targets_list = storage_conf.as_list('extend_lun_target')
    lun_addresses_list = storage_conf.as_list('extend_lun_address')
    lun_list = storage_conf.as_list('extend_lun')
    for (lun, lun_address, lun_target) in zip(
                lun_list, lun_addresses_list, lun_targets_list):
        if not extendISCSIDomain(
                    storage_domain, host, lun, lun_address, lun_target):
            raise errors.StorageDomainException(
                    "extendISCSIDomain(%s, %s, %s, %s, %s) failed.",
                    storage_domain, host, lun, lun_address, lun_target)


def __extend_fcp_domain(storage_domain, host, storage_conf):
    """
    Description: Extends fcp domain with luns defined with extend_lun parameter
    Parameters:
        * storage_domain - storage domain to extend
        * host - host on which storage domain is created
        * storage_conf - dictionary ([storage_type] section)
    """
    lun_list = storage_conf.as_list('extend_lun')
    for lun in lun_list:
        if not extendFCPDomain(storage_domain, host, lun):
            raise errors.StorageDomainException(
                    "extendFCPDomain(%s, %s, %s) failed.",
                    storage_domain, host, lun)


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

    if type_ == ENUMS['storage_type_nfs']:
        names = __create_nfs_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_iscsi']:
        names = __create_iscsi_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_fcp']:
        names = __create_fcp_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_local']:
        names = __create_localfs_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_posixfs']:
        names = __create_posixfs_storages(datacenter, host, storage)
    else:
        raise errors.UnkownConfigurationException("unknown storage type: %s" %
                                                  type_)

    export_address = storage.get('export_domain_address', None)
    if export_address is not None:
        export_path = storage['export_domain_path']

        if not addNFSDomain(host, export_name, datacenter, export_address,
                            export_path, ENUMS['storage_dom_type_export']):
            raise errors.StorageDomainException(
                "addNFSDomain export (%s, %s) to DC %s failed." %
                (export_address, export_path, datacenter))
        logging.info("Export domain %s was created successfully", export_name)

    iso_address = storage.get('tests_iso_domain_address', None)
    if iso_address is not None:
        iso_path = storage['tests_iso_domain_path']
        if not addNFSDomain(host, iso_name, datacenter,

                            iso_address, iso_path,
                            ENUMS['storage_dom_type_iso']):
            raise errors.StorageDomainException(
                    "addNFSDomain iso (%s, %s) to DC %s failed." %
                    (iso_address, iso_path, datacenter))
        logging.info("ISO domain %s was created successfully", iso_name)
    return names


def __create_nfs_storages(datacenter, host, storage_conf):
    """
    Description: Creates nfs storages
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    data_domain_paths = storage_conf.as_list('data_domain_path')
    names = []
    for index, address in enumerate(
                          storage_conf.as_list('data_domain_address')):
        name = "nfs_%d" % index
        path = data_domain_paths[index]
        if not addNFSDomain(host, name, datacenter, address, path,
                            ENUMS['storage_dom_type_data']):
            raise errors.StorageDomainException(
                    "addNFSDomain (%s, %s) to DC %s failed." %
                    (address, path, datacenter))
        logging.info("NFS data domain %s was created successfully", name)
        names.append(name)
    return names


def __create_iscsi_storages(datacenter, host, storage_conf):
    """
    Description: Creates iscsi storages
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    lun_targets_list = storage_conf.as_list('lun_target')
    lun_addresses_list = storage_conf.as_list('lun_address')
    names = []
    for index, lun in enumerate(storage_conf.as_list('lun')):
        lun_target = lun_targets_list[index]
        lun_address = lun_addresses_list[index]
        name = "iscsi_%d" % index
        if not addISCSIDataDomain(host, name, datacenter,
                                  lun, lun_address, lun_target):
            raise errors.StorageDomainException(
                    "addISCSIDomain (%s, %s, %s) to DC %s failed." %
                    (lun_address, lun_target, lun, datacenter))
        logging.info("iSCSI data domain %s was created successfully", name)
        names.append(name)
    return names


def __create_fcp_storages(datacenter, host, storage_conf):
    """
    Description: Creates fcp storages
    Author: kjachim
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    for index, lun in enumerate(storage_conf.as_list('lun')):
        name = "fcp_%d" % index
        if not addFCPDataDomain(host, name, datacenter, lun):
            raise errors.StorageDomainException(
                "addFCPDataDomain (%s) to DC %s failed." % (lun, datacenter))
        logging.info("FCP data domain %s was created successfully", name)


def __create_localfs_storages(datacenter, host, storage_conf):
    """
    Description: Creates local storages
    Author: kjachim
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    local_domain_paths = storage_conf.as_list("local_domain_path")
    for index, path in enumerate(local_domain_paths):
        name = "local_%s" % index
        if not addLocalDataDomain(host, name, datacenter, path):
            raise errors.StorageDomainException(
                "addLocalDataDomain(%s, %s, %s, %s) failed!" % (
                                    host, name, datacenter, path))
        logging.info("local data domain %s created successfully", name)


def __create_posixfs_storages(datacenter, host, storage_conf):
    """
    Description: Creates posixfs storages
    Author: kjachim
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    gluster_domain_paths = storage_conf.as_list("gluster_domain_path")
    gluster_domain_addresses = storage_conf.as_list("gluster_domain_address")
    vfs_type = storage_conf["vfs_type"]
    for index, (path, address) in enumerate(
                        zip(gluster_domain_paths, gluster_domain_addresses)):
        name = "posixfs_%s" % index
        if not addPosixfsDataDomain(
                        host, name, datacenter, address, path, vfs_type):
            raise errors.StorageDomainException(
                "addPosixfsDataDomain(%s, %s, %s, %s, %s, %s) failed!" % (
                            host, name, datacenter, address, path, vfs_type))
        logging.info("posixfs data domain %s created successfully", name)


@is_action()
def remove_storage_domain(name, datacenter, host, format_disk=False, vdc=None,
                          vdc_password=None):
    """ Deactivates, detaches and removes storage domain.
    """

    dc_storages = []
    if datacenter is not None:
        dc_storages = [
            x.name for x in storagedomains.getDCStorages(datacenter, False)]

    if name in dc_storages:
        if storagedomains.is_storage_domain_active(datacenter, name):
            logging.info("Deactivating storage domain")
            if not storagedomains.deactivateStorageDomain(
                    True, datacenter, name):
                raise errors.StorageDomainException(
                    "Cannot deactivate storage domain %s in datacenter %s!" % (
                        name, datacenter))

        logging.info("Detaching storage domain")
        if not storagedomains.detachStorageDomain(True, datacenter, name):
            raise errors.StorageDomainException(
                "Cannot detach storage domain %s from datacenter %s!" % (
                    name, datacenter))

    logging.info("Removing storage domain")
    if not storagedomains.removeStorageDomain(
            True, name, host, str(format_disk)):
        raise errors.StorageDomainException(
            "Cannot remove storage domain %s!" % name)
    logging.info("Storage domain %s removed" % name)


@is_action()
def create_nfs_domain_with_options(
        name, sd_type, host, address, path, version=None, retrans=None,
        timeo=None, datacenter=None, positive=True):
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
        * *retrans* - # retransmissions (NFS option)
        * *timeo* - NFS timeout
        * *datacenter* - if not None: datacenter to which sd should be attached

    **Returns**: nothing, raise an exception in case of an error
    """
    logging.info("Adding storage domain")
    old_storage = storagedomains.Storage
    if not positive:  # in positive tests we won't pass incorrect values
        storagedomains.Storage = datastructures.Storage
    if not storagedomains.addStorageDomain(
            positive, name=name, type=sd_type, host=host, address=address,
            storage_type=ENUMS['storage_type_nfs'], path=path,
            nfs_version=version, nfs_retrans=retrans, nfs_timeo=timeo):
        storagedomains.Storage = old_storage  # just in case...
        raise errors.StorageDomainException(
            "Cannot add storage domain %s" % name)
    storagedomains.Storage = old_storage

    if datacenter is not None:
        logging.info("Attaching storage domain")
        if not storagedomains.attachStorageDomain(True, datacenter, name):
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

    dc_storage_objects = storagedomains.getDCStorages(datacenter, False)

    if not [sd for sd in dc_storage_objects if sd.get_name() == domain]:
        logger.info('Attaching domain %s to dc %s' % (domain, datacenter))
        if not storagedomains.attachStorageDomain(True, datacenter, domain):
            raise errors.StorageDomainException(
                'Unable to attach domain %s to dc %s'
                % (domain, datacenter))
    logger.info('Domain %s attached to dc %s' % (domain, datacenter))

    logger.info('Activating domain %s on dc %s' % (domain, datacenter))

    if not storagedomains.activateStorageDomain(True, datacenter, domain):
        raise errors.StorageDomainException(
            'Unable to activate domain %s on dc %s'
            % (domain, datacenter))
    logger.info('Domain %s actived' % domain)

    return True


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
    if storagedomains.is_storage_domain_active(datacenter, domain):
        logger.info('Domain %s is active in dc %s' % (domain, datacenter))

        logger.info('Deactivating domain  %s in dc %s' % (domain, datacenter))
        if not storagedomains.deactivateStorageDomain(True, datacenter,
                                                      domain):
            raise errors.StorageDomainException(
                'Unable to deactivate domain %s on dc %s'
                % (domain, datacenter))

    logger.info('Domain %s is inactive in datacenter %s'
                % (domain, datacenter))

    logger.info('Detaching domain %s from dc %s' % (domain, datacenter))
    if not storagedomains.detachStorageDomain(True, datacenter, domain):
        raise errors.StorageDomainException(
            'Unable to detach domain %s from dc %s'
            % (domain, datacenter))
    logger.info('Domain %s detached to dc %s' % (domain, datacenter))

    return True
