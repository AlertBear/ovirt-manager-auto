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
import time
import Queue
import logging
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, data_st
from art.rhevm_api.utils.test_utils import get_api, split
from art.rhevm_api.utils.test_utils import searchForObj
from art.core_api import is_action
from art.test_handler.settings import opts
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.rhevm_api.tests_lib.low_level.general import prepare_ds_object


ELEMENT = 'data_center'
COLLECTION = 'datacenters'
util = get_api(ELEMENT, COLLECTION)
STORAGE_API = get_api('storage_domain', 'storagedomains')
QOS_API = get_api("qos", "datacenters")
QOSS_API = get_api("qoss", "datacenters")
CLUSTER_API = get_api("cluster", "clusters")
DataCenter = getDS('DataCenter')
Version = getDS('Version')

ELEMENTS = os.path.join(
    os.path.dirname(__file__), '../../../conf/elements.conf')
ENUMS = opts['elements_conf']['RHEVM Enums']

DATA_CENTER_INIT_TIMEOUT = 180

# Quota api constants
QUOTA_COL = "quotas"
QUOTA_ELM = "quota"
QUOTA_API = get_api(QUOTA_ELM, QUOTA_COL)
QUOTA_CLUSTER_LIMIT_ELM = "cluster_quota_limit"
QUOTA_CLUSTER_LIMIT_API = get_api(
    QUOTA_CLUSTER_LIMIT_ELM, "cluster_quota_limits"
)
QUOTA_STORAGE_DOMAIN_LIMIT_ELM = "storage_quota_limit"
QUOTA_STORAGE_DOMAIN_LIMIT_API = get_api(
    QUOTA_STORAGE_DOMAIN_LIMIT_ELM, "storage_quota_limits"
)
API = "api"
ATTR = "attr"
OBJ_API = "obj_api"
LINK_NAME = "link_name"
CLASS_NAME = "class_name"
QUOTA_LIMITS = {
    "cluster": {
        CLASS_NAME: "QuotaClusterLimit",
        API: QUOTA_CLUSTER_LIMIT_API,
        OBJ_API: CLUSTER_API,
        LINK_NAME: "quotaclusterlimits",
        ATTR: QUOTA_CLUSTER_LIMIT_ELM
    },
    "storage_domain": {
        CLASS_NAME: "QuotaStorageLimit",
        API: QUOTA_STORAGE_DOMAIN_LIMIT_API,
        OBJ_API: STORAGE_API,
        LINK_NAME: "quotastoragelimits",
        ATTR: QUOTA_STORAGE_DOMAIN_LIMIT_ELM
    }
}

logger = logging.getLogger(__name__)


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
            quota_mode: datacenter quota mode(disabled, audit, enabled)
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
    if "quota_mode" in kwargs:
        dcUpd.set_quota_mode(kwargs.pop("quota_mode"))

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
    resultsQ = Queue.Queue()
    datacentersList = split(datacenters)
    for dc in datacentersList:
        resultsQ.put(removeDataCenter(positive, dc))
    status = True

    while not resultsQ.empty():
        dcStatus = resultsQ.get()
        if not dcStatus:
            status = False

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


def prepare_qos_obj(**kwargs):
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

                Type hostnetwork:
                    outbound_average_linkshare: type=int
                    outbound_average_realtime: type=int
                    outbound_average_upperlimit: type=int
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

                Type hostnetwork:
                    outbound_average_linkshare: type=int
                    outbound_average_realtime: type=int
                    outbound_average_upperlimit: type=int

    :return: True/False
    """
    kwargs["name"] = qos_name
    kwargs["type_"] = qos_type
    log_info, log_error = ll_general.get_log_msg(
        action="Add", obj_name=qos_name, obj_type="QoS"
    )
    qos_obj = prepare_qos_obj(**kwargs)
    dc = get_data_center(datacenter)
    qoss_coll = data_st.QoSs()
    qoss_coll.set_qos(qos_obj)

    qoss_dc_coll_href = util.getElemFromLink(
        dc, link_name="qoss", attr="qos", get_href=True
    )

    logger.info(log_info)
    res = QOS_API.create(
        qos_obj, collection=qoss_dc_coll_href, coll_elm_name="qos",
        positive=True
    )[1]
    if not res:
        logger.error(log_error)
    return res


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
    log_info, log_error = ll_general.get_log_msg(
        action="Get", obj_name=qos_name, obj_type="QoS"
    )
    logger.info(log_info)
    for qos in qoss:
        if qos.get_name() == qos_name:
            return qos

    logger.error(log_error)
    return False


def delete_qos_from_datacenter(datacenter, qos_name):
    """
    Get QoS from datacenter
    :param datacenter: Datacenter name
    :param qos_name: Qos name
    :return: True/False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="delete", obj_name=qos_name, obj_type="QoS"
    )
    qos = get_qos_from_datacenter(datacenter, qos_name)
    logger.info(log_info)
    res = util.delete(qos, True)
    if not res:
        logger.error(log_error)
    return res


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

                For Host Network QoS type:
                    Type hostnetwork:
                    outbound_average_linkshare: type=int
                    outbound_average_realtime: type=int
                    outbound_average_upperlimit: type=int

    :return: True/False
    """
    qos_obj = get_qos_from_datacenter(datacenter, qos_name)
    if not qos_obj:
        return False

    if kwargs.get("new_name"):
        kwargs["name"] = kwargs.get("new_name")

    try:
        new_qos_obj = prepare_qos_obj(**kwargs)
    except exceptions.DataCenterException:
        return False

    return QOS_API.update(qos_obj, new_qos_obj, True)[1]


def __prepare_quota_obj(**kwargs):
    """
    Prepare quota object

    :param kwargs: name: type=str
                   description: type=str
                   cluster_soft_limit_pct: type=int
                   cluster_hard_limit_pct: type=int
                   storage_soft_limit_pct: type=int
                   storage_hard_limit_pct: type=int
    :return: Quota object or None
    :rtype: Quota
    """
    try:
        quota_obj = prepare_ds_object("Quota", **kwargs)
    except exceptions.RHEVMEntityException as e:
        util.logger.error("Failed to prepare quota object: %s", e)
        return None
    return quota_obj


def get_quotas_obj_from_dc(dc_name):
    """
    Get quotas object from datacenter

    :param dc_name: name of datacenter
    :type dc_name: str
    :return: Quotas object or None
    :rtype: Quotas
    """
    dc_obj = get_data_center(dc_name)
    try:
        quotas_obj = util.getElemFromLink(
            elm=dc_obj, link_name=QUOTA_COL, attr=QUOTA_ELM
        )
    except EntityNotFound as e:
        util.logger.error(
            "Failed to get quotas object from datacenter %s: %s", dc_name, e
        )
        return None
    return quotas_obj


def get_quotas_href(dc_name):
    """
    Get quotas href under datacenter

    :param dc_name: name of datacenter
    :type dc_name: str
    :return: href on quotas under datacenter
    :rtype: str
    """
    dc_obj = get_data_center(dc_name)
    return util.getElemFromLink(
        elm=dc_obj, link_name=QUOTA_COL, get_href=True
    )


def get_quota_obj_from_dc(dc_name, quota_name):
    """
    Get quota object from datacenter

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :return: Quota object or None
    :rtype: Quota
    """
    quotas_obj = get_quotas_obj_from_dc(dc_name)
    if not quotas_obj:
        return None
    for quota_obj in quotas_obj:
        if quota_obj.name == quota_name:
            return quota_obj


def get_quota_id_by_name(dc_name, quota_name):
    """
    Get quota id by name

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :return: quota id
    :rtype: str
    """
    quota_obj = get_quota_obj_from_dc(dc_name=dc_name, quota_name=quota_name)
    if not quota_obj:
        return ''
    return quota_obj.get_id()


def create_dc_quota(dc_name, quota_name, **kwargs):
    """
    Create datacenter quota

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: create quota with name
    :type quota_name: str
    :param kwargs: description: type=str
                   cluster_soft_limit_pct: type=int
                   cluster_hard_limit_pct: type=int
                   storage_soft_limit_pct: type=int
                   storage_hard_limit_pct: type=int
    :return: True, if creation succeed, otherwise False
    :rtype: bool
    """
    quotas_href = get_quotas_href(dc_name)
    quota_obj = __prepare_quota_obj(name=quota_name, **kwargs)
    if not quota_obj:
        return False
    logger.info("Create quota %s under datacenter %s", quota_name, dc_name)
    if not QUOTA_API.create(
        entity=quota_obj, positive=True, collection=quotas_href
    )[1]:
        logger.error(
            "Failed to create quota %s under datacenter %s",
            quota_name, dc_name
        )
        return False
    return True


def update_dc_quota(dc_name, quota_name, **kwargs):
    """
    Update datacenter quota

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param kwargs: name: type=str
                   description: type=str
                   cluster_soft_limit_pct: type=int
                   cluster_hard_limit_pct: type=int
                   storage_soft_limit_pct: type=int
                   storage_hard_limit_pct: type=int
    :return: True, if update succeed, otherwise False
    :rtype: bool
    """
    old_quota_obj = get_quota_obj_from_dc(dc_name, quota_name)
    new_quota_obj = __prepare_quota_obj(**kwargs)
    if not(old_quota_obj and new_quota_obj):
        return False
    return QUOTA_API.update(old_quota_obj, new_quota_obj, True)[1]


def delete_dc_quota(dc_name, quota_name):
    """
    Delete datacenter quota

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :return: True, if delete succeed, otherwise False
    :rtype: bool
    """
    quota_obj = get_quota_obj_from_dc(dc_name, quota_name)
    if not quota_obj:
        return False
    logger.info("Delete quota %s from datacenter %s", quota_name, dc_name)
    if not QUOTA_API.delete(quota_obj, True):
        logger.error(
            "Failed to delete quota %s from datacenter %s", quota_name, dc_name
        )
        return False
    return True


def __prepare_quota_limit_object(limit_type, **kwargs):
    """
    Prepare quota limit object

    :param limit_type: limit type(storage_domain, cluster)
    :type limit_type: str
    :param kwargs: limit: type=int(-1 for unlimited)
                   vcpu_limit: type=int(-1 for unlimited)
                   memory_limit: type=int(-1 for unlimited)
                   obj_name: type=str(storage_domain or cluster name)
    :return: QuotaStorageLimit object or QuotaClusterLimit object or None
    :rtype: QuotaStorageLimit or QuotaClusterLimit
    """
    object_name = kwargs.pop("obj_name", None)
    obj = None
    if object_name:
        obj = QUOTA_LIMITS[limit_type][OBJ_API].find(
            object_name
        )
    try:
        quota_limit_obj = prepare_ds_object(
            QUOTA_LIMITS[limit_type][CLASS_NAME], **kwargs
        )
    except exceptions.RHEVMEntityException as e:
        util.logger.error(
            "Failed to prepare quota %s limit object: %s", limit_type, e
        )
        return None
    if hasattr(quota_limit_obj, limit_type):
        setattr(quota_limit_obj, limit_type, obj)
    return quota_limit_obj


def get_quota_limits_object(dc_name, quota_name, limit_type):
    """
    Get quota limits object from specific quota

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param limit_type: limit type(storage_domain or cluster)
    :return: QuotaStorageLimits object or QuotaClusterLimits object or None
    :rtype: QuotaStorageLimits or QuotaClusterLimits
    """
    quota_obj = get_quota_obj_from_dc(dc_name, quota_name)
    if not quota_obj:
        return None
    try:
        quota_limits_obj = QUOTA_API.getElemFromLink(
            elm=quota_obj,
            link_name=QUOTA_LIMITS[limit_type][LINK_NAME],
            attr=QUOTA_LIMITS[limit_type][ATTR]
        )
    except EntityNotFound as e:
        util.logger.error(
            "Failed to get quota %s limits object from quota %s: %s",
            limit_type, quota_name, e
        )
        return None
    return quota_limits_obj


def get_quota_limits_href(dc_name, quota_name, limit_type):
    """
    Get quota limits object href

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param limit_type: limit type(storage_domain or cluster)
    :return: href o quotas limit of specific type
    :rtype: str
    """
    quota_obj = get_quota_obj_from_dc(dc_name, quota_name)
    if not quota_obj:
        return ''
    return QUOTA_API.getElemFromLink(
        elm=quota_obj,
        link_name=QUOTA_LIMITS[limit_type][LINK_NAME],
        get_href=True
    )


def get_quota_limit(dc_name, quota_name, limit_type, obj_name=None):
    """
    Get specific quota limit

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param limit_type: limit type(storage_domain or cluster)
    :type limit_type: str
    :param obj_name: name of cluster or storage domain object
    :type obj_name: str
    :return: QuotaStorageLimit object or QuotaClusterLimit object or None
    :rtype: QuotaStorageLimits or QuotaClusterLimits
    """
    obj = None
    quota_limits_obj = get_quota_limits_object(dc_name, quota_name, limit_type)
    if not quota_limits_obj:
        return None
    if obj_name:
        obj = QUOTA_LIMITS[limit_type][OBJ_API].find(obj_name)
    for quota_limit_obj in quota_limits_obj:
        obj_t = getattr(quota_limit_obj, limit_type)
        if obj_t and obj and obj.get_id() == obj_t.get_id():
            return quota_limit_obj
        elif obj_t is None and obj_name is None:
            return quota_limit_obj
    return None


def create_quota_limits(dc_name, quota_name, limit_type, limits_d):
    """
    Create storage limits under specific quota
    (you can send {None: limit_value} to set
    limit for all storages or clusters in datacenter)

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param limit_type: limit name(storage_domain or cluster)
    :type limit_type: str
    :param limits_d: quota limits dictionary
    ({storage_domain or cluster name: limit value})
    :type limits_d: dict
    :return: True, if creation succeed, False otherwise
    :rtype: bool
    """
    quota_limits_href = get_quota_limits_href(dc_name, quota_name, limit_type)
    if not quota_limits_href:
        return False
    for obj_name, limits in limits_d.iteritems():
        quota_limit_obj = __prepare_quota_limit_object(
            limit_type=limit_type, obj_name=obj_name, **limits
        )
        if not quota_limit_obj:
            return False
        status = QUOTA_LIMITS[limit_type][API].create(
            entity=quota_limit_obj,
            positive=True,
            collection=quota_limits_href
        )[1]
        if not status:
            return False
    return True


def delete_quota_limits(dc_name, quota_name, limit_type, objects_names_l):
    """
    Delete quota limits

    :param dc_name: datacenter name
    :type dc_name: str
    :param quota_name: quota name
    :type quota_name: str
    :param limit_type: limit name(storage_domain or cluster)
    :type limit_type: str
    :param objects_names_l: list of objects names
    :type objects_names_l: list
    :return: True, if deletion succeed, False otherwise
    :rtype: bool
    """
    quota_limits_obj = get_quota_limits_object(dc_name, quota_name, limit_type)
    if not quota_limits_obj:
        return False
    for obj_name in objects_names_l:
        quota_limit_obj = get_quota_limit(
            dc_name=dc_name,
            quota_name=quota_name,
            limit_type=limit_type,
            obj_name=obj_name
        )
        if not quota_limit_obj:
            return False
        status = QUOTA_LIMITS[limit_type][API].delete(
            quota_limit_obj, True
        )
        if not status:
            return False
    return True


def get_quota_limit_usage(
    dc_name, quota_name, limit_type, usage, obj_name=None
):
    """
    Get quota limit usage

    :param dc_name: datacenter name
    :param quota_name: quota name
    :param limit_type: limit type(storage or cluster)
    :param usage: usage type(storage: usage; cluster: vcpu_usage, memory_usage)
    :param obj_name: name of cluster or storage domain,
    if not specify search for general quota
    :return: limit usage
    :rtype: float
    """
    quota_limit_obj = get_quota_limit(
        dc_name=dc_name,
        quota_name=quota_name,
        limit_type=limit_type,
        obj_name=obj_name
    )
    if not quota_limit_obj:
        return 0.0
    return float(getattr(quota_limit_obj, usage, 0))


def get_datacenters_list():
    """
    Get list of all datacenters

    :return: datacenters
    :rtype: list
    """
    return util.get(absLink=False)
