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
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, data_st
from art.rhevm_api.utils.test_utils import get_api, split
from art.rhevm_api.utils.test_utils import searchForObj
from art.core_api import is_action
from art.test_handler.settings import opts
import art.test_handler.exceptions as exceptions


ELEMENT = 'data_center'
COLLECTION = 'datacenters'
util = get_api(ELEMENT, COLLECTION)
STORAGE_API = get_api('storage_domain', 'storagedomains')
QOS_API = get_api("qos", "datacenters")
QOSS_API = get_api("qoss", "datacenters")
DataCenter = getDS('DataCenter')
Version = getDS('Version')

ELEMENTS = os.path.join(
    os.path.dirname(__file__), '../../../conf/elements.conf')
ENUMS = opts['elements_conf']['RHEVM Enums']

DATA_CENTER_INIT_TIMEOUT = 180


@is_action()
def addDataCenter(positive, **kwargs):
    """
     Description: Add new data center
     Parameters:
        *  *name - name of a new data center
        *  *storage_type - storage type data center will support
        *  *version - data center supported version (2.2 or 3.0)
        *  *local - True for localFS DC type, False for shared DC type
     Return: status (True if data center was added properly, False otherwise)
     """

    majorV, minorV = kwargs.pop('version').split(".")
    dcVersion = Version(major=majorV, minor=minorV)

    dc = DataCenter(version=dcVersion, **kwargs)

    dc, status = util.create(dc, positive)
    if positive:
        supported_versions_valid = checkSupportedVersions(kwargs.pop('name'))
        status = status and supported_versions_valid

    return status


@is_action()
def updateDataCenter(positive, datacenter, **kwargs):
    """
    Update Data Center parameters

    :param positive: Expected result
    :type positive: bool
    :param datacenter: DataCenter name
    :type datacenter: str
    :param kwargs:
            name: new DC name
            description: new DC description
            storage_type: new storage type
            version: new DC version
            mac_pool: new MAC pool for the DC
    :return: True if update succeeded, False otherwise
    """

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

    if "mac_pool" in kwargs:
        dcUpd.set_mac_pool(kwargs.pop("mac_pool"))

    dcUpd, status = util.update(dc, dcUpd, positive)

    return status


@is_action()
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


@is_action()
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
        util.logger.error('Failed to find DC %s', datacenter)
        queue.put(False)
        return False

    status = util.delete(dc, positive)
    time.sleep(30)

    queue.put(status)


@is_action()
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
        thread = threading.Thread(
            target=removeDataCenterAsynch, name="Remove DC " + dc,
            args=(positive, dc, threadQueue))
        thread.start()
        thread.join()

    while not threadQueue.empty():
        dcStatus = threadQueue.get()
        if not dcStatus:
            status = status and False

    return status


@is_action()
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


@is_action("waitForDataCenterStateApi")
def wait_for_datacenter_state_api(name, state=ENUMS['data_center_state_up'],
                                  timeout=DATA_CENTER_INIT_TIMEOUT, sleep=10):
    """
    Description: Waits for state of datacenter using API polling. It's similar
                 to function waitForDataCenterState. which uses search engine
    Parameters:
        * name - Name of datacenter
        * state - Desired state of given datacenter
        * timeout - How long should it wait
        * sleep - How often should it poll
    """
    dc_obj = util.find(name)
    start_t = time.time()
    while dc_obj.status.state != state and time.time() - start_t < timeout:
        time.sleep(sleep)
        dc_obj = util.find(name)
        util.logger.debug(
            "State of %s datacenter is %s", name, dc_obj.status.state)
    if dc_obj.status.state != state:
        raise exceptions.DataCenterException(
            "Waiting for %s dc's state timed out. Final state is still %s, "
            "but expected was %s" % (name, dc_obj.status.state, state))


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
            util.logger.error('Invalid supported versions in '
                              'data center {0}'.format(name))
            return False
    util.logger.info('Validated supported versions of'
                     ' data center {0}'.format(name))
    return True


def get_data_center(dc_name):
    """
    Get data center object by name
    Author: ratamir
    Parameters:
        *dc_name - Data Center's name to get

    Return: dc object, or raise EntityNotFound
    """
    dc_obj = util.find(dc_name)
    return dc_obj


def get_sd_datacenter(storage_domain_name):
    """
    Description: Returns data-center object that storage is connected to
    Author: ratamir
    Parameters:
        * storage_domain_name - Name of the storage domain
    Returns: DC name which storage_domain_name belongs to, False otherwise
    """
    storage_domain_id = STORAGE_API.find(storage_domain_name).get_id()
    all_dcs = util.get(absLink=False)
    for dc in all_dcs:
        dc_sds = STORAGE_API.getElemFromLink(dc, get_href=False)
        for sd in dc_sds:
            if sd.get_id() == storage_domain_id:
                return dc
    util.logger.info("Storage domain %s is not attached to any data-center",
                     storage_domain_name)
    return False


def _prepare_qos_obj(**kwargs):
    """
    Prepare Qos object to add to datacenter
    :param kwargs: qos_name: QoS name
                   qos type: (all, storage, cpu, network)
                   description: type=string
                Type Storage:
                    max_throughput: type=int
                    max_read_throughput: type=int
                    max_write_throughput: type=int
                    max_iops: type=int
                    max_read_iops: type=int
                    max_write_iops: type=int

                Type CPU:
                    cpu_limit: type=int

                Type Network:
                    inbound_average: type=int
                    inbound_peak: type=int
                    inbound_burst: type=int
                    outbound_average: type=int
                    outbound_peak: type=int
                    outbound_burst: type=int
    :return: QoS object or raise exceptions
    """
    exclude_kwargs = ["new_name"]
    qos_obj = data_st.QoS()
    for key, val in kwargs.iteritems():
        if hasattr(qos_obj, key):
            setattr(qos_obj, key, val)
        else:
            if key not in exclude_kwargs:
                raise exceptions.DataCenterException(
                    "QoS object has no attribute: %s" % key
                )
    return qos_obj


def add_qos_to_datacenter(datacenter, qos_name, qos_type, **kwargs):
    """
    Add QoS object to datacenter
    :param datacenter: Datacenter name
    :param qos_name: QoS name
    :param qos_type: QoS type (all, storage, cpu, network)
    :param kwargs: description: type=string
                Type Storage:
                    max_throughput: type=int
                    max_read_throughput: type=int
                    max_write_throughput: type=int
                    max_iops: type=int
                    max_read_iops: type=int
                    max_write_iops: type=int

                Type CPU:
                    cpu_limit: type=int

                Type Network:
                    inbound_average: type=int
                    inbound_peak: type=int
                    inbound_burst: type=int
                    outbound_average: type=int
                    outbound_peak: type=int
                    outbound_burst: type=int
    :return: True/False
    """
    kwargs["name"] = qos_name
    kwargs["type_"] = qos_type
    qos_obj = _prepare_qos_obj(**kwargs)
    dc = get_data_center(datacenter)
    qoss_coll = data_st.QoSs()
    qoss_coll.set_qos(qos_obj)

    qoss_dc_coll_href = util.getElemFromLink(
        dc, link_name="qoss", attr="qos", get_href=True
    )

    return QOS_API.create(
        qos_obj, collection=qoss_dc_coll_href, coll_elm_name="qos",
        positive=True
    )


def get_qoss_from_datacenter(datacenter):
    """
    Get all QoSs in datacenter
    :param datacenter: Datacenter name
    :return: List of QoSs
    """
    dc = get_data_center(datacenter)
    return util.getElemFromLink(
        dc, link_name="qoss", attr="qos", get_href=False
    )


def get_qos_from_datacenter(datacenter, qos_name):
    """
    Get QoS from datacenter
    :param datacenter: Datacenter name
    :param qos_name: Qos name
    :return: QoS object or False
    """
    qoss = get_qoss_from_datacenter(datacenter)
    for qos in qoss:
        if qos.get_name() == qos_name:
            return qos
    return False


def delete_qos_from_datacenter(datacenter, qos_name):
    """
    Get QoS from datacenter
    :param datacenter: Datacenter name
    :param qos_name: Qos name
    :return: True/False
    """
    qos = get_qos_from_datacenter(datacenter, qos_name)
    return util.delete(qos, True)


def update_qos_in_datacenter(datacenter, qos_name, **kwargs):
    """
    Update QoS in datacenter
    :param datacenter: Datacenter name
    :param qos_name: QoS name
    :param kwargs: description: type=string
                For Storage QoS type:
                    max_throughput: type=int
                    max_read_throughput: type=int
                    max_write_throughput: type=int
                    max_iops: type=int
                    max_read_iops: type=int
                    max_write_iops: type=int

                For CPU QoS type:
                    cpu_limit: type=int

                For Network QoS type:
                    inbound_average: type=int
                    inbound_peak: type=int
                    inbound_burst: type=int
                    outbound_average: type=int
                    outbound_peak: type=int
                    outbound_burst: type=int
    :return: True/False
    """
    qos_obj = get_qos_from_datacenter(datacenter, qos_name)
    if not qos_obj:
        return False

    if kwargs.get("new_name"):
        kwargs["name"] = kwargs.get("new_name")

    try:
        new_qos_obj = _prepare_qos_obj(**kwargs)
    except exceptions.DataCenterException:
        return False

    return QOS_API.update(qos_obj, new_qos_obj, True)
