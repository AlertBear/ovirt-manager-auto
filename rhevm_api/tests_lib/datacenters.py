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
import Queue
import threading
import time
from core_api.apis_exceptions import EntityNotFound
from core_api.apis_utils import getDS
from rhevm_api.utils.test_utils import get_api, split
from utilities.utils import readConfFile
from rhevm_api.utils.test_utils import searchForObj


ELEMENT = 'data_center'
COLLECTION = 'datacenters'
util = get_api(ELEMENT, COLLECTION)

DataCenter = getDS('DataCenter')
Version = getDS('Version')

ELEMENTS = os.path.join(os.path.dirname(__file__), '../../conf/elements.conf')
ENUMS = readConfFile(ELEMENTS, 'RHEVM Enums')

DATA_CENTER_INIT_TIMEOUT = 180


def addDataCenter(positive, **kwargs):
    '''
     Description: Add new data center
     Parameters:
        * name - name of a new data center
        * storage_type - storage type data center will support
        * version - data center supported version (2.2 or 3.0)
     Return: status (True if data center was added properly, False otherwise)
     '''

    majorV, minorV = kwargs.pop('version').split(".")
    dcVersion = Version(major=majorV, minor=minorV)

    dc = DataCenter(version=dcVersion, **kwargs)

    dc, status = util.create(dc, positive)
    if positive:
        supported_versions_valid = checkSupportedVersions(kwargs.pop('name'))
        status = status and supported_versions_valid

    return status


def updateDataCenter(positive, datacenter, **kwargs):
    '''
     Description: Update existed data center
     Parameters:
        * datacenter - name of a data center that should updated
        * name - new name of a data center (if relevant)
        * description - new data center description (if relevant)
        * storage_type - new data center storage type (if relevant)
     Return: status (True if data center was updated properly, False otherwise)
     '''

    dc = util.find(datacenter)
    dcUpd = DataCenter()

    if 'name' in kwargs:
        dcUpd.set_name(kwargs.pop('name'))

    if 'description' in kwargs:
        dcUpd.set_description(kwargs.pop('description'))

    if 'storage_type' in kwargs:
        dcUpd.set_storage_type(kwargs.pop('storage_type'))

    if 'version' in kwargs:
        majorV, minorV = kwargs.pop('version').split(".")
        dcVersion = Version(major=majorV, minor=minorV)
        dcUpd.set_version(dcVersion)

    dcUpd, status = util.update(dc, dcUpd, positive)

    return status


def removeDataCenter(positive, datacenter):
    '''
     Description: Remove existed data center
     Author: edolinin
     Parameters:
        * datacenter - name of a data center that should removed
     Return: status (True if data center was removed properly, False otherwise)
     '''

    dc = util.find(datacenter)
    return util.delete(dc, positive)


def searchForDataCenter(positive, query_key, query_val, key_name, **kwargs):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    return searchForObj(util, query_key, query_val, key_name, **kwargs)


def removeDataCenterAsynch(positive, datacenter, queue):
    '''
     Description: Remove existed data center, using threading for removing
     of multiple objects
     Parameters:
        * datacenter - name of a data center that should removed
        * queue - queue of threads
     Return: status (True if data center was removed properly, False otherwise)
     '''

    try:
        dc = util.find(datacenter)
    except EntityNotFound:
        queue.put(False)
        return False

    status = util.delete(dc, positive)
    time.sleep(30)

    queue.put(status)


def removeDataCenters(positive, datacenters):
    '''
     Description: Remove several data centers, using threading
     Parameters:
        * datacenters - name of data centers that should removed
                        separated by comma
     Return: status:
          True if all data centers were removed properly
          False otherwise
     '''

    datacentersList = split(datacenters)

    status = True

    threadQueue = Queue.Queue()
    for dc in datacentersList:
        thread = threading.Thread(target=removeDataCenterAsynch,
            name="Remove DC " + dc, args=(positive, dc, threadQueue))
        thread.start()
        thread.join()

    while not threadQueue.empty():
        dcStatus = threadQueue.get()
        if not dcStatus:
            status = status and False

    return status


def waitForDataCenterState(name, state=ENUMS['data_center_state_up'],
                           timeout=DATA_CENTER_INIT_TIMEOUT, sleep=10):
    """
    Wait until given datacenter is in desired state
    Parameters:
        * name - Data center's name
        * state - Desired state for given data centers
    Author: jlibosva
    """
    util.find(name)
    query = 'name=%s and status=%s' % (name, state)

    return util.waitForQuery(query, timeout=timeout, sleep=sleep)


def checkSupportedVersions(name):
    """
    Checks if the data center's supported versions are valid.
    Parameters:
        *name - Data Center's name to check

    Return: status: (True if the supported versions are valid, False otherwise)
    """
    datacenter = util.find(name)
    dcVersion = datacenter.get_version()
    dcSupportedVersions = datacenter.get_supported_versions().get_version()
    for version in dcSupportedVersions:
        if dcVersion.get_major() > version.get_major() or (
                dcVersion.get_major() == version.get_major() and
                dcVersion.get_minor() > version.get_minor()):
            util.logger.error('Invalid supported versions in ' \
                              'data center {0}'.format(name))
            return False
    util.logger.info('Validated supported versions of' \
                     ' data center {0}'.format(name))
    return True