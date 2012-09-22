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
import logging

from art.rhevm_api.tests_lib.low_level import storagedomains
from utilities.utils import readConfFile
from art.core_api import is_action

ELEMENTS = os.path.join(os.path.dirname(__file__), '../../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')

logger = logging.getLogger(__package__ + __name__)

@is_action()
def addISCSIDataDomain(host, storage, data_center, lun, lun_address, lun_target, lun_port=3260):
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
    return True if succeeded, False otherwise
    '''

    if not storagedomains.iscsiDiscover('True', host, lun_address):
        logger.error('Failed to discover lun address %s from %s' % (lun_address, host))
        return False

    if not storagedomains.iscsiLogin('True', host, lun_address, lun_target):
        logger.error('Failed to login %s on target %s from %s' % (lun_address, lun_target, host))
        return False

    if not storagedomains.addStorageDomain('True', host=host, name=storage,
                                    type=ENUMS['storage_dom_type_data'],
                                    storage_type=ENUMS['storage_type_iscsi'],
                                    lun=lun, lun_address=lun_address,
                                    lun_target=lun_target, lun_port=lun_port):
        logger.error('Failed to add %s to %s' % (lun_address, host))
        return False

    return storagedomains.attachStorageDomain('True', data_center, storage, 'True')


@is_action()
def addNFSDomain(host, storage, data_center, address, path, sd_type=ENUMS['storage_dom_type_data']):
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
    return True if succeeded, False otherwise
    '''
    if not storagedomains.addStorageDomain('True', host=host, name=storage,
                                    type=sd_type, storage_type=ENUMS['storage_type_nfs'],
                                    address=address, path=path):
        logger.error('Failed to add %s to %s' % (address, host))
        return False

    return storagedomains.attachStorageDomain('True', data_center, storage, 'True')
