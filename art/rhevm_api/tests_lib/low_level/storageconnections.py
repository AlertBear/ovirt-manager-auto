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
from art.test_handler.settings import ART_CONFIG

StorageConnection = apis_utils.getDS('StorageConnection')
Host = apis_utils.getDS('Host')

ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
api = test_utils.get_api('storage_connection', 'storageconnections')
hostApi = test_utils.get_api('host', 'hosts')

logger = logging.getLogger("art.ll_lib.storageconnections")


def _prepare_connection_object(**kwargs):
    conn = StorageConnection()

    type_ = kwargs.pop('type', None)
    conn.set_type(type_)
    host = kwargs.pop('host', None)
    if host:
        hostObj = hostApi.find(host)
        conn.set_host(Host(name=hostObj.get_name()))

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
    elif type_ == ENUMS['storage_type_gluster']:
        conn.set_address(kwargs.pop('address', None))
        conn.set_path(kwargs.pop('path', None))
        conn.set_vfs_type(kwargs.pop('vfs_type', None))
    elif type_ == ENUMS['storage_type_local']:
        conn.set_path(kwargs.pop('path', None))
    else:
        raise Exception("Unknown storage type: %s" % type_)

    return conn


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
       * host - "Passing host id/name is optional. Providing it will lead to
                 attempt to connect to the storage via the host. Not providing
                 host will lead to just persisting storage details in db."
    Return: status of the operation
    """
    conn = _prepare_connection_object(**kwargs)
    return api.create(conn, True, async=(not wait))


def update_connection(positive, conn_id, **kwargs):
    """
    Description: update a storage connection
    Author: kjachim
    Parameters:
       * positive - if positive or negative verification should be done
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
       * host - "Specifying host (vdsm) will lead the host to attempt to
                 connect to the newly specified storage details. Not specifying
                 host will lead to just update the details in engine db."
    Return: status of the operation
    """
    logger.debug("Changing connection %s", conn_id)
    old_conn = api.find(conn_id, attribute='id')
    new_conn = _prepare_connection_object(**kwargs)
    result = api.update(old_conn, new_conn, positive)
    return result


def remove_storage_connection(conn_id, host=None):
    """
    Remove a storage connection

    __author__ = "cmestreg"
    :param conn_id: id of the changed connection
    :type conn_id: str
    :param host: host name from which connection should be removed
    :type host: str
    :returns: status of the operation
    :rtype: bool
    """
    conn_obj = api.find(conn_id, attribute='id')
    logger.debug("Removing connection %s", conn_id)
    if host:
        conn_obj.href += ";host=%s" % host
    return api.delete(conn_obj, True)


def get_all_storage_connections():
    """
    Return all storage connections

    __author__ = "glazarov"
    :return: List of all storage connections
    :rtype: list
    """
    return api.get(abs_link=False)


def get_storage_connection_object(connection, attribute):
    """
    Retrieve the storage connectionReturn all storage connections

    __author__ = "glazarov"
    :param connection: The ID or name of the connection to retrieve
    :type connection: ID or Name
    :param attribute: The connection type to query ('id' or 'name')
    :type attribute: str
    :return: List of all storage connections
    :rtype: list
    """
    return api.find(connection, attribute)
