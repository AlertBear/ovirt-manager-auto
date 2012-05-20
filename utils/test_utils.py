#!/usr/bin/env python


# Copyright (C) 2011 Red Hat, Inc.
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

from utils.rest_utils import RestUtil
from utils.sdk_utils import SdkUtil
import settings
from utilities.utils import readConfFile
#The location of all supported elements
elementsConf = "conf/elements.conf"
#The name of section in the element configuration file
elementConfSection = 'elements'
#The location of all supported os

api = None

def get_api(element, collection):
    '''
    Fetch proper API instance based on engine type
    '''

    global api
    if settings.opts['engine'] == 'rest':
        api = RestUtil(element, collection)
    if settings.opts['engine'] == 'sdk':
        api = SdkUtil(element, collection)

    return api


def split(s):
    '''
    Split `s` by comma and/or by whitespace.

    Parameters: s -- A string-like object to split.
    Return: A sequence of strings-like objects.
    '''
    return s.replace(',', ' ').split()


def getStat(name, elm_name, collection_name, stat_types):
    '''
    Description: gets the given statistic from a host
    Parameters:
      * name - name of a host or vm
      * obj_type - "hosts" or "vms"
      * stat_type - a list of any stat that REST API gives back,
        for example 'memory.used', 'swap.total', etc.
    Return: a dictionary with the requested and found stats
    '''
    util = get_api(elm_name, collection_name)
    elm_obj = util.find(name)
    statistics = util.getElemFromLink(elm_obj, link_name='statistics', attr='statistic')
    values = {}
    for stat in statistics:
        if stat.get_name() in stat_types:
            datum =  stat.get_values().get_value()[0].get_datum()
            if stat.get_values().get_type() == "INTEGER":
                values[stat.get_name()] = int(float(datum))
                #return int(stat.values.value.datum)
            elif stat.get_values().get_type() == "DECIMAL":
                values[stat.get_name()] = float(datum)
    return values



def validateElementStatus(positive, element, collection, elementName,
                                        expectedStatus, dcName=None):
    '''
    The function validateElementStatus compare the status of given element with expected status.
        element = specific element (host,datacenter...)
        elementName = the name of element (<host name> in case of given element is a host)
        expectedStatus = expected status(es) of element (The status of element that we are expecting)
        dcName = the name of Data Center (to retrieve the status of storage domain entity, None by default)
    return values : Boolean value (True/False ) True in case of succes otherwise False
    '''
    attribute = "state"
    try:
        supportedElements = readConfFile(elementsConf, elementConfSection)
    except Exception as err:
        util.logger.error(err)
        return False

    util = get_api(element, collection)

    if element not in supportedElements:
        msg = "Unknown element {0}, supported elements are {1}"
        util.logger.error(msg.format(element, supportedElements.keys()))
        return False

    elementObj = None
    MSG = "Can't find element {0} of type {1} - {2}"

    if element.lower() == "storagedomain":
        if dcName is None:
            ERR = "name of Data Center is missing"
            util.logger.warning(MSG.format(elementName, element, ERR))
            return False

        try:    # Fetch Data Center object in order to get storage domain status
            dcUtil = get_api('data_center', 'datacenters')
            dcObj = dcUtil.find(dcName)
        except EntityNotFound:
            ERR = "Data Center object is needed in order to get storage domain status"
            util.logger.warning(MSG.format(dcName, "datacenter", ERR))
            return False

        elementObj = util.getElemFromElemColl(dcObj, 'storagedomains',
                                'storagedomain', element)
    else:
        try:
            elementObj = util.find(elementName)
        except Exception as err:
            util.logger.error(MSG.format(elementName, elementToFind, err))
            return False

        if not hasattr(elementObj.get_status(), attribute):
            msg = "Element {0} doesn't have attribute \'{1}\'"
            util.logger.error(msg.format(element, attribute))
            return False

    expectedStatuses = [status.strip().upper() for status in expectedStatus.split(',')]
    result = elementObj.get_status().get_state().upper() in expectedStatuses

    MSG = "Status of element {0} is \'{1}\' expected statuses are {2}"
    util.logger.warning(MSG.format(elementName,
        elementObj.get_status().get_state().upper(), expectedStatuses))

    return result