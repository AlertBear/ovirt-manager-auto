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

from art.rhevm_api.utils import test_utils
from art.core_api import apis_utils
from utilities import utils
from art.test_handler.settings import opts
from art.core_api import is_action

StorageConnection = apis_utils.getDS('StorageConnection')
Host = apis_utils.getDS('Host')

ENUMS = opts['elements_conf']['RHEVM Enums']
api = test_utils.get_api('storage_connection', 'storageconnections')
hostApi = test_utils.get_api('host', 'hosts')

LOGGER = logging.getLogger(__name__)


def _prepare_connection_object(**kwargs):
    conn = StorageConnection()

    type_ = kwargs.pop('type')
    conn.set_type(type_)

    if type_ == ENUMS['storage_type_iscsi']:
        address = kwargs.pop('lun_address', None)
        if address:
            address = utils.getIpAddressByHostName(address)
        conn.set_address(address)
        conn.set_target(kwargs.pop('lun_target', None))
        conn.set_port(kwargs.pop('lun_port', None))
        conn.set_portal(kwargs.pop('lun_portal', None))
        conn.set_username(kwargs.pop('username', None))
        conn.set_password(kwargs.pop('password', None))
    elif type_ == ENUMS['storage_type_nfs']:
        conn.set_address(kwargs.pop('address', None))
        conn.set_path(kwargs.pop('path', None))
        conn.set_nfs_timeo(kwargs.pop('nfs_timeo', None))
        conn.set_nfs_version(kwargs.pop('nfs_version', None))
        conn.set_nfs_retrans(kwargs.pop('nfs_retrans', None))
    elif type_ == ENUMS['storage_type_posixfs']:
        conn.set_address(kwargs.pop('address', None))
        conn.set_path(kwargs.pop('path', None))
        conn.set_mount_options(kwargs.pop('mount_options', None))
        conn.set_vfs_type(kwargs.pop('vfs_type', None))
    elif type_ == ENUMS['storage_type_local']:
        conn.set_path(kwargs.pop('path', None))
    else:
        raise Exception("Unknown storage type: %s" % type_)

    return conn


@is_action('addConnection')
def add_connection(wait=True, **kwargs):
    """
    Description: add new storage connection
    Author: kjachim
    Parameters:
       * type - storage type (ENUMS['storage_type_nfs'],
          ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp'],
          ENUMS['storage_type_local'])
       * address - storage domain address (for NFS)
       * path - storage domain path (for NFS,LOCAL)
       * lun_address - lun address (for iSCSI)
       * lun_target - lun target name (for iSCSI)
       * lun_port - lun port (for iSCSI)
       * nfs_version - version of NFS protocol
       * nfs_retrans - the number of times the NFS client retries a request
       * nfs_timeo - time before client retries NFS request
       * mount_options - custom mount options
       * wait - if True, wait for the action to complete
       * password - password for iSCSI
       * username - username for iSCSI
    Return: status of the operation
    """
    conn = _prepare_connection_object(**kwargs)
    return api.create(conn, True, async=(not wait))


@is_action('updateConnection')
def update_connection(conn_id, **kwargs):
    """
    Description: update a storage connection
    Author: kjachim
    Parameters:
       * conn_id - id of the changed connection
       * type - storage type (ENUMS['storage_type_nfs'],
          ENUMS['storage_type_iscsi'], ENUMS['storage_type_fcp'],
          ENUMS['storage_type_local'])
       * address - storage domain address (for NFS)
       * path - storage domain path (for NFS,LOCAL)
       * lun_address - lun address (for iSCSI)
       * lun_target - lun target name (for iSCSI)
       * lun_port - lun port (for iSCSI)
       * nfs_version - version of NFS protocol
       * nfs_retrans - the number of times the NFS client retries a request
       * nfs_timeo - time before client retries NFS request
       * mount_options - custom mount options
       * password - password for iSCSI
       * username - username for iSCSI
    Return: status of the operation
    """
    LOGGER.info("Changing connection %s" % conn_id)
    old_conn = api.find(conn_id, attribute='id')
    new_conn = _prepare_connection_object(**kwargs)
    result = api.update(old_conn, new_conn, True)
    return result


@is_action('removeStorageConnection')
def remove_storage_connection(conn_id, host=None):
    """
    Description: remove a storage connection
    Author: kjachim
    Parameters:
        * conn_id - id of the changed connection
        * host - host where connection should be removed
    Return: status of the operation
    """
    conn_obj = api.find(conn_id, attribute='id')
    LOGGER.info("Removing connection %s" % conn_id)
    if host is None:
        host_id = "00000000-0000-0000-0000-000000000000"
    else:
        host = hostApi.find(host)
        host_id = host.id
    host = Host(id=host_id)
    return api.delete(conn_obj, True, body=host, element_name='host')


@is_action('removeAllStorageConnections')
def remove_all_storage_connections():
    """
    Description: removes all storage connections
    Author: kjachim
    Return: status of the operation
    """
    connections = api.get(absLink=False)
    result = True
    for connection in connections:
        result = remove_storage_connection(connection.id) and result
    return result
