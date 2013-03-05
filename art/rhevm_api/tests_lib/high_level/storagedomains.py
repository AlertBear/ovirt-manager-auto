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
from art.core_api import is_action
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__name__)

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

    if not storagedomains.iscsiDiscover(True, host, lun_address):
        logger.error('Failed to discover lun address %s from %s' %
                     (lun_address, host))
        return False

    if not storagedomains.iscsiLogin(True, host, lun_address, lun_target):
        logger.error('Failed to login %s on target %s from %s' %
                     (lun_address, lun_target, host))
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
        __create_nfs_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_iscsi']:
        __create_iscsi_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_fcp']:
        __create_fcp_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_posixfs']:
        __create_localfs_storages(datacenter, host, storage)
    elif type_ == ENUMS['storage_type_local']:
        __create_posixfs_storages(datacenter, host, storage)
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


def __create_nfs_storages(datacenter, host, storage_conf):
    """
    Description: Creates nfs storages
    Parameters:
        * datacenter - name of datacenter
        * host - host that will create storage domains
        * storage_conf - storage configuration section
    """
    data_domain_paths = storage_conf.as_list('data_domain_path')
    for index, address in enumerate(
                          storage_conf.as_list('data_domain_address')):
        path = data_domain_paths[index]
        if not addNFSDomain(host, "nfs_%d" % index, datacenter,
                            address, path, ENUMS['storage_dom_type_data']):
            raise errors.StorageDomainException(
                    "addNFSDomain (%s, %s) to DC %s failed." %
                    (address, path, datacenter))
        logging.info("NFS data domain %s was created successfully",
                     "nfs_%d" % index)


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
    for index, lun in enumerate(storage_conf.as_list('lun')):
        lun_target = lun_targets_list[index]
        lun_address = lun_addresses_list[index]
        if not addISCSIDataDomain(host, "iscsi_%d" % index,
                                  datacenter, lun, lun_address,
                                  lun_target):
            raise errors.StorageDomainException(
                    "addISCSIDomain (%s, %s, %s) to DC %s failed." %
                    (lun_address, lun_target, lun, datacenter))
        logging.info("iSCSI data domain %s was created successfully",
                     "iscsi_%d" % index)


def __create_fcp_storages(datacenter, host, storage_conf):
    """
    TODO: Future Kuba will do it
    """
    raise NotImplementedError("Not implemented yet!")


def __create_localfs_storages(datacenter, host, storage_conf):
    """
    TODO
    """
    raise NotImplementedError("Not implemented yet!")

def __create_posixfs_storages(datacenter, host, storage_conf):
    """
    TODO
    """
    raise NotImplementedError("Not implemented yet!")

