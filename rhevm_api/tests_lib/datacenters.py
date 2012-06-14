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

from core_api.apis_utils import getDS
from rhevm_api.utils.test_utils import get_api, split
import re
from core_api.validator import compareCollectionSize
import threading
import Queue
from core_api.apis_exceptions import EntityNotFound
import time

ELEMENT = 'data_center'
COLLECTION = 'datacenters'
util = get_api(ELEMENT, COLLECTION)

DataCenter = getDS('DataCenter')
Version = getDS('Version')


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
    dcVersion = Version(major=majorV, minor = minorV)

    dc = DataCenter(version = dcVersion, **kwargs)

    dc, status = util.create(dc, positive)
  
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

    if 'version' in kwargs:
        majorV, minorV = kwargs.pop('version').split(".")
        dcVersion = Version(major=majorV, minor = minorV)
        dcUpd.set_verion(dcVersion)

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


def searchForDataCenter(positive, query_key, query_val, key_name):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    expected_count = 0
    datacenters = util.get(absLink=False)

    for dc in datacenters:
        dcProperty = getattr(dc, key_name)
        if re.match(r'(.*)\*$',query_val):
            if re.match(r'^' + query_val, dcProperty):
                expected_count = expected_count + 1
        else:
            if dcProperty == query_val:
                expected_count = expected_count + 1

    contsraint = "{0}={1}".format(query_key, query_val)
    query_dcs = util.query(contsraint)
    status = compareCollectionSize(query_dcs, expected_count, util.logger)

    return status


def removeDataCenterAsynch(positive, datacenter, queue):
    '''
     Description: Remove existed data center, using threading for removing of multiple objects
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

    status = util.delete(dc,positive)
    time.sleep(30)

    queue.put(status)
    

def removeDataCenters(positive, datacenters):
    '''
     Description: Remove several data centers, using threading
     Parameters:
        * datacenters - name of data centers that should removed separated by comma
     Return: status (True if all data centers were removed properly, False otherwise)
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



