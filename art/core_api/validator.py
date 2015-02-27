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

import sys
import re
from cStringIO import StringIO
from art.core_api.apis_utils import data_st_validate as ds
from art.generateDS.generateds_config import NameTable

ATTR_IGNORE_LIST = ['href', 'link', 'rel']

VALS_IGNORE_DICT = {
    'usage': ['vm'],
}

DS_CLASS_MAPPER = {
    'clusternetwork': 'Network',
    'vmcdrom': 'CdRom',
    'rolepermits': 'Permits',
    'hostnicstatistics': 'Statistics',
    'diskstatistics': 'Statistics',
    'datacenternetworkvnicprofile': 'VnicProfile',
    'jobstep': 'Step',
    'hostniclabels': 'Labels',
    'datacenternetwork': 'Network',
}

primitive = (int, bool, float, long, basestring)


def is_primitive(obj):
    return isinstance(obj, primitive)


def dump_entity(ds, root_name):
    '''
    Dump DS element to xml format
    '''

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    ds.export(mystdout, 0, name_=root_name)
    sys.stdout = old_stdout
    return mystdout.getvalue()


def getObjAttributes(obj, origObj):
    '''
    Get object attributes recursively from all superclasses
    '''
    if obj.superclass:
        # merge element's and its superclass dict items
        origObj.member_data_items_.update(obj.superclass.member_data_items_)
        return getObjAttributes(obj.superclass, origObj)
    else:
        return origObj.member_data_items_.keys()


def cliEntety(elm, node_name):
    """
    Dump DS element to cli format
    """
    output = cli_entity(elm, node_name)
    # reducing complexity of cli_entity by replacing
    # of last ',' in collection to '"'
    # take care if collection is last one in string
    if output.endswith(','):
        output = '%s"' % output.rstrip(',')
    return output.replace(', ', '" ')


def cli_entity(elm, node_name, level=0, collection=False, start=False):
    '''
    Dump DS element to cli format, shouldn't be used directly
    use cliEntety as wrapper for this function
    '''

    dumped_ent = ''
    ignore_list = ['supported_versions', 'valueOf_']
    ignore_list.extend(ATTR_IGNORE_LIST)

    elmClass = elm.__class__.__name__
    elmInstance = getattr(ds, elmClass)()
    attrList = getObjAttributes(elmInstance, elmInstance)

    # cleaning from unneeded attributes
    for attr in ignore_list:
        if attr in attrList:
            attrList.remove(attr)

    for attr in attrList:
        try:
            attrVal = getAttibuteValue(elm, attr)
        except AttributeError:
            continue

        attrType = elmInstance.member_data_items_[attr].get_data_type()
        attrContainer = elmInstance.member_data_items_[attr].get_container()

        if attrVal is not None and attrVal != []:
            if attr.startswith('type'):
                attr = attr.rstrip('_')

            nodeName = "{0}".format(attr)
            if level > 0:
                nodeName = "{0}-{1}".format(node_name, attr)

            # checking if recursion reached its stopping case
            if attrType.startswith('xs:') or is_primitive(attrVal):
                if attrContainer and isinstance(attrVal, list):
                    attrVal = attrVal[0]

                if (
                    re.search('boolean', attrType) or
                    isinstance(attrVal, bool)
                ):
                    attrVal = str(attrVal).lower()

                elif (re.search('(int|long|unsignedShort)', attrType) or
                      isinstance(attrVal, (int, long))):
                    attrVal = "%d" % attrVal

                elif (re.search('(string|dateTime)', attrType) or
                      isinstance(attrVal, basestring)):
                    if collection:
                        attrVal = "%s" % attrVal
                    else:
                        attrVal = "'%s'" % attrVal

                # taking care of collection parsing
                if collection:
                    tmp = nodeName.rsplit('-', 2)
                    base = '-'.join([tmp[0], tmp[1]])
                    collectionData = '.'.join([tmp[1], tmp[2]])

                    # beginning of collection
                    if start:
                        start = False
                        nodeName = ''.join([base, ' "', collectionData])
                        dumped_ent += " --{0}={1},".format(nodeName, attrVal)
                    # Middle of collection
                    else:
                        nodeName = collectionData
                        dumped_ent += "{0}={1},".format(nodeName, attrVal)

                else:
                    # default behavior for unchecked types
                    dumped_ent += " --{0} {1}".format(nodeName, attrVal)
                if level > 0 and attr == 'id':
                    break

            else:
                nextLevel = level + 1
                if not isinstance(attrVal, list):
                    attrVal = [attrVal, ]
                length = len(attrVal)
                # collection ahead
                if attrContainer:
                    for i in range(length):
                        if i == 0:
                            dumped_ent += cli_entity(attrVal[i], nodeName,
                                        nextLevel, collection=True, start=True)
                        else:
                            dumped_ent += cli_entity(attrVal[i], nodeName,
                                        nextLevel, collection=True)
                else:
                    for i in range(length):
                        dumped_ent += cli_entity(attrVal[i], nodeName,
                                             nextLevel)

    return dumped_ent


def compareResponseCode(resp, expected, logger):
    try:
        assert resp in expected
        logger.debug("Response code is valid: %(exp)s ", {'exp': expected})
        return True
    except AssertionError:
        logger.error("Response code is not valid, expected is:"
                     " %(exp)s, actual is: %(act)s ",
                     {'exp': expected, 'act': resp})
        return False


def compareActionStatus(status, expected, logger):
    try:
        assert status in expected
        logger.debug("Action status is valid: %(exp)s " % {'exp': expected})
        return True
    except AssertionError:
        logger.error("Action status is not valid, expected is:"
                     " %(exp)s, actual is: %(act)s " % \
                     {'exp': expected, 'act': status})
        return False


def compareAsyncActionStatus(async, state, logger):
    '''
    Description: compare action status, depends on if it sync or not.
    Author: khakimi
    Parameters:
        * async - True if async False otherwise
        * state - the current state
    Return: True if state in expected, False otherwise
    '''
    expected = ["pending", "complete"] if async else ["complete"]
    return compareActionStatus(state, expected, logger)


def compareCollectionSize(collection, expectedSize, logger):

    if collection is not None:
        try:
            if isinstance(expectedSize, list):
                assert len(collection) in expectedSize
            else:
                assert len(collection) == expectedSize
            logger.debug("Collection size is correct: %(exp)s " % \
                         {'exp': expectedSize})
            return True
        except AssertionError:
            logger.error("Collection size is wrong, expected is:"
                         " %(exp)s, actual is: %(act)s " % \
                         {'exp': expectedSize, 'act': len(collection)})
            return False
    else:
        logger.error("No collection found for size comparison.")
        return False


def compareActionLink(actions, action, logger):
    try:
        actionsList = map(lambda x: x.get_rel(), actions.get_link())
        assert action in actionsList
        return True
    except AssertionError:
        logger.error("Required action : '%s' doesn't exist"
                     " in actions links: %s " % (action, actionsList))
        return False


def getAttibuteValue(elm, attrName):
    '''
    Description: function that gets attribute value and converts it if needed
    Parameters:
       * elm - api entity
       * attrName - api entity attribute name
    Return:api entity attribute value
    '''
    if attrName.startswith('type'):
        attrName = attrName.rstrip('_')

    val = getattr(elm, 'get_{0}'.format(attrName))()
    # TODO: to find some generic way to handle such conversions for all string
    # answers from api backends
    if isinstance(val, unicode):
        val = val.encode('UTF-8', 'replace')
    return val


def getClassName(elmClass):
    return DS_CLASS_MAPPER.get(elmClass.lower(), elmClass)


def compareElements(expElm, actElm, logger, root, equal=True,
                    java_sdk_mode=False):
    '''
    Recursive function for elements comparison,
    elements are compared vis DS scheme
    Parameters:
    * expElm - expected element
    * actElm - actual element
    * logger - logger instance
    * root - name of the root node
    * equal - elements are equal or not till this point
    * java_sdk_mode - run with java sdk backend
    Returns: True is elements are equal, False otherwise
    '''
    ignore_list = ['status', 'role', 'active', 'total', 'required', 'permit']
    ignore_list.extend(ATTR_IGNORE_LIST)

    if not actElm:
        logger.warn("Attribute '{0}' doesn't exist"
                    " in actual results".format(root))
        return True

    if expElm.__class__.__name__ == 'JavaTranslator':
        elmClass = expElm.java_object.__class__.__name__
    else:
        elmClass = expElm.__class__.__name__
    elmClass = getClassName(elmClass)
    elmInstance = getattr(ds, elmClass)()

    attrList = getObjAttributes(elmInstance, elmInstance)

    # the list of changed attributes
    attr_changed_list = NameTable.values()

    for attr in attrList:
        if attr in ignore_list:
            continue

        # check if we changed this attribute as part of generate DS process
        attr_changed = False
        if attr in attr_changed_list:
            orig_attr = NameTable.keys()[attr_changed_list.index(attr)]
            logger.info('Attribute: {0} changed to: {1}'.format(
                        attr, orig_attr))
            attr = orig_attr
            attr_changed = True
        try:
            attrExpVal = getAttibuteValue(expElm, attr)
            attrActVal = getAttibuteValue(actElm, attr)
        except AttributeError:
            if java_sdk_mode:
                # collection case
                if actElm.java_object.__class__.__name__.endswith('s'):
                    logger.warn(
                        "'{0}' is collection - skipping validation".format(
                            actElm.java_object.__class__))
                else:
                    logger.warning(
                        "Element '{0}' has no attribute '{1}'".format(
                            actElm.java_object.__class__.__name__, attr))
                    logger.warning("Possible issue, however it can happen due "
                                   "to difference in implementation since we "
                                   "compare between data_structures.py and "
                                   "java decorator object")
            else:
                # collection case
                if actElm.__class__.__name__.endswith('s'):
                    logger.warn("'{0}' is collection - skipping validation".
                                format(actElm))
                else:
                    logger.error("Element '{0}' has no attribute '{1}'".
                                 format(actElm, attr))
                    equal = False
            continue

        if attr_changed:
            attr = NameTable[attr]
        attrType = elmInstance.member_data_items_[attr].get_data_type()
        attrContainer = elmInstance.member_data_items_[attr].get_container()

        if attrExpVal is not None:
            if attrActVal is None:
                MSG = "Attribute '{0}->{1}' doesn't exist in actual results"
                logger.warn(MSG.format(root, attr))
                continue

            if attrType.startswith('xs:') or is_primitive(attrActVal):
                if attrContainer and isinstance(attrExpVal, list):
                    if not isinstance(attrActVal, list):
                        attrExpVal = attrExpVal[0]
                    else:
                        attrExpVal.sort()
                        attrActVal.sort()
                        if attr in VALS_IGNORE_DICT:
                            ignoreVals = filter(
                                lambda x: x not in attrExpVal
                                and x in VALS_IGNORE_DICT[attr], attrActVal)
                            attrActVal = list(set(attrActVal) -
                                              set(ignoreVals))

                if (re.search('boolean', attrType) or
                        isinstance(attrActVal, bool)):
                    attrExpVal = str(attrExpVal).lower()
                    attrActVal = str(attrActVal).lower()

                if str(attrExpVal) == str(attrActVal):
                    MSG = "Property '{0}->{1}' has correct value: {2}"
                    logger.info(MSG.format(root, attr, attrExpVal))
                else:
                    equal = False
                    MSG = "Property '{0}->{1}' has wrong value, " \
                    " expected: '{2}'; actual: '{3}'"
                    logger.error(MSG.format(root, attr, attrExpVal,
                                            attrActVal))
            else:
                nodeName = "{0}->{1}".format(root, attr)
                if isinstance(attrExpVal, list):
                    try:
                        attrExpVal.sort(key=lambda x: x.name)
                        attrActVal.sort(key=lambda x: x.name)
                    except AttributeError:
                        logger.warn("Can't sort {0} objects list by name".\
                                    format(elmClass))

                    for i in range(0, len(attrExpVal)):
                        if i > len(attrActVal) - 1:
                            MSG = "Attribute '{0}' with index {1} doesn't"
                            " exist in actual results"
                            logger.warn(MSG.format(nodeName, i))
                            continue
                        if not compareElements(attrExpVal[i], attrActVal[i],
                                               logger, nodeName, equal,
                                               java_sdk_mode):
                            equal = False
                else:
                    if not compareElements(attrExpVal, attrActVal, logger,
                                           nodeName, equal, java_sdk_mode):
                        equal = False

    return equal


def compareStrings(positive, strA=None, strB=None):
    """
    Compare two strings
    return value: True when strings are equal otherwise False

    """
    return strA == strB


class XPathMatch(object):
    """
    This callable class can HTTP-GET the resource specified and perform a XPath
    query on the resource got. Then the result of XPath query
    is evaluated using eval(rslt_eval).

    Normally you actually won't need to set the positivity to any other
    value than 'TRUE', because all the logic can be done in rslt_eval.

    Usage:
    # Instantiate the callable and call it.
    xpathMatch = XPathMatch(host_utils, '/rhevm-api/hosts/')
    xpathMatch('TRUE', 'hosts', 'count(/hosts//ksm/enabled)',
                    rslt_eval='match == 1')
    # Returns True if exactly one tag matches.

    returns: True if the test positivity equals the evaluation result.
    """

    def __init__(self, logger, utils, links):
        """
        A callable object that provides generic way to use XPath queries
        for all facilities as Hosts, Clusters and so on.

        param utils: An instance of restutils to use.
        param href:  An URL to HTTP-GET the doc to perform XPath query on.
        param links: A mapping of link and href.

        See the doc for XPathMatch for more details.
        """
        self.logger = logger
        self.utils = utils
        self.links = links

    def __call__(self, positive, link, xpath, rslt_eval='0. < result'):
        """
        See the doc for XPathMatch for more details.
        """
        # A hack to make the XPathMatch able to match against the tags in the
        # RHEVM entry-point url.
        if link.startswith('/'):
            matching_nodes = self.utils.getAndXpathEval(link, xpath)
        else:
            if 'api' == link:
                matching_nodes = self.utils.getAndXpathEval('', xpath)
            else:
                matching_nodes = self.utils.getAndXpathEval(self.links[link],
                                                            xpath)

        boolean_positive = positive.lower() == 'true'
        if boolean_positive != eval(rslt_eval, None,
                                    {'result': matching_nodes}):
            E = "XPath '%s' result evaluated using '%s' not equal to %s."
            self.logger.error(E % (xpath, rslt_eval, boolean_positive))
            return False
        else:
            self.logger.debug("XPath evaluation succeed.")
            return True


class XPathLinks(XPathMatch):
    """
    This class is used to verify XPath on reponses which are referenced
    as links in api

    You have to specify entity_type  e.g. 'hosts' in constructor
    Author: jvorcak
    Usage:
        xpathHostsLinks = XPathLinks('hosts', logger, util, links)
        xpathHostsLinks('TRUE', 'host_address', link_name='storage',
                        xpath='count(/base)')
    See @XPathMatch for more details
    """

    def __init__(self, entity_type, logger, utils, links):
        XPathMatch.__init__(self, logger, utils, links)
        self.entity_type = entity_type

    def __call__(self, positive, entity, link_name, xpath,
                 rslt_eval='0. < result'):
        entityObj = self.utils.find(self.links[self.entity_type], entity)
        return XPathMatch.__call__(self, positive,
                                   entityObj.link[link_name].href, xpath,
                                   rslt_eval)
