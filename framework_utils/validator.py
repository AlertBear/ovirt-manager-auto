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

from cStringIO import StringIO
import sys
from framework_utils.apis_utils import data_st as ds
import re


def dump_entity(ds, root_name):
    '''
    Dump DS element to xml format
    '''
    
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    ds.export(mystdout, 0, name_=root_name)
    sys.stdout = old_stdout
    return mystdout.getvalue()


def compareResponseCode(resp, expected, logger):
    try:
        assert resp['status'] in expected
        logger.debug("Response code is valid: %(exp)s " % {'exp': expected })
        return True
    except AssertionError:
        logger.error("Response code is not valid, expected is:  %(exp)s, actual is: %(act)s " % {'exp': expected , 'act': resp['status'] })
        return False


def compareActionStatus(status, expected, logger):
    try:
        assert status in expected
        logger.debug("Action status is valid: %(exp)s " % {'exp': expected })
        return True
    except AssertionError:
        logger.error("Action status is not valid, expected is: %(exp)s, actual is: %(act)s " % {'exp': expected , 'act': status})
        return False


def compareCollectionSize(collection, expectedSize, logger):

    if collection is not None:
        try:
            assert len(collection) == expectedSize
            logger.debug("Collection size is correct: %(exp)s " % {'exp': expectedSize })
            return True
        except AssertionError:
            logger.error("Collection size is wrong, expected is: %(exp)s, actual is: %(act)s " % {'exp': expectedSize , 'act': len(collection)})
            return False
    else:
        logger.error("No collection found for size comparison.")
        return False


def compareActionLink(actions, action,logger):
    try:
        assert action in map(lambda x: x.get_rel(), actions.get_link())
        return True
    except AssertionError:
        logger.error("Required action : '%s' doesn't exist in actions links: %s " % (action, [lambda x: x.get_rel(), actions.get_link()]))
        return False

def getAttibuteValue(elm, attrName):

    return getattr(elm, 'get_' + attrName.rstrip('_'))()

    
def compareElements(expElm, actElm, logger, root):
    '''
    Recursive function for elements comparison,
    elements are compared vis DS scheme
    Parameters:
    * expElm - expected element
    * actElm - actual element
    * logger - logger instance
    * root - name of the root node
    Returns: True is elements are equal, False otherwise
    '''
    ignore = ['href', 'status', 'rel']
    equal = True

    if not actElm:
        logger.warn("Attribute '{0}' doesn't exist in actual results".format(root))
        return True

    elmClass = expElm.__class__.__name__
    if elmClass == 'ClusterNetwork':
        elmClass = 'Network'
    elif elmClass == 'VMCdRom':
        elmClass = 'CdRom'
    elif elmClass == 'RolePermits':
        elmClass = 'Permits'
   
    elmInstance = getattr(ds, elmClass)()

    if elmInstance.superclass:
        # merge element's and its superclass dict items
        elmInstance.member_data_items_.update(elmInstance.superclass.member_data_items_)
    
    attrList = elmInstance.member_data_items_.keys()
   
    for attr in attrList:
        if attr in ignore:
            continue

        try:
            attrExpVal = getAttibuteValue(expElm, attr)
            attrActVal = getAttibuteValue(actElm, attr)
        except AttributeError:
            logger.error("Element '{0}' has no attribute '{1}'".\
                                        format(actElm, attr))
            equal = False
            continue

        attrType = elmInstance.member_data_items_[attr].get_data_type()
        attrContainer = elmInstance.member_data_items_[attr].get_container()
        
        if attrExpVal is not None:
            if attrActVal is None:
                MSG = "Attribute '{0}->{1}' doesn't exist in actual results"
                logger.warn(MSG.format(root, attr))
                continue

            if attrType.startswith('xs:'):
                if attrContainer and isinstance(attrExpVal, list) \
                    and not isinstance(attrActVal, list) :
                    attrExpVal = attrExpVal[0]

                if re.search('boolean', attrType):
                    attrExpVal = str(attrExpVal).lower()
                    attrActVal = str(attrActVal).lower()

                if str(attrExpVal)==str(attrActVal):
                    MSG = "Property '{0}->{1}' has correct value: {2}"
                    logger.info(MSG.format(root, attr, attrExpVal))
                else:
                    equal = False
                    MSG = "Property '{0}->{1}' has wrong value, expected: '{2}'; actual: '{3}'"
                    logger.error(MSG.format(root, attr, attrExpVal, attrActVal))
            else:
                nodeName = "{0}->{1}".format(root, attr)
                if isinstance(attrExpVal, list):
                    for i in range(0,len(attrExpVal)):
                        if i > len(attrActVal)-1:
                            MSG = "Attribute '{0}' with index {1} doesn't exist in actual results"
                            logger.warn(MSG.format(nodeName, i))
                            continue
                        if not compareElements(attrExpVal[i], attrActVal[i], logger, nodeName):
                            equal = False
                else:
                    if not compareElements(attrExpVal, attrActVal, logger, nodeName):
                        equal = False

    return equal

        
def compareStrings(positive,strA=None,strB=None):
    """
    Compare two strings
    return value: True when strings are equal otherwise False

    """
    return strA == strB


class XPathMatch(object):
    """
    This callable class can HTTP-GET the resource specified and perform a XPath
    query on the resource got. Then the result of XPath query is evaluated using
    eval(rslt_eval).

    Normally you actually won't need to set the positivity to any other
    value than 'TRUE', because all the logic can be done in rslt_eval.

    Usage:
    # Instantiate the callable and call it.
    xpathMatch = XPathMatch(host_utils, '/rhevm-api/hosts/')
    xpathMatch('TRUE', 'hosts', 'count(/hosts//ksm/enabled)',
                    rslt_eval='match == 1')
    # Returns True iff exactly one tag matches.

    returns: True iff the test positivity equals the evaluation result.
    """

    def __init__(self, logger, utils, links):
        """
        A callable object that provides generic way to use XPath queries for all
        facilities as Hosts, Clusters and so on.

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
                matching_nodes = self.utils.getAndXpathEval(self.links[link], xpath)

        boolean_positive = positive.lower() == 'true'
        if boolean_positive != eval(rslt_eval, None, {'result' : matching_nodes}):
            E = "XPath '%s' result evaluated using '%s' not equal to %s."
            self.logger.error(E % (xpath, rslt_eval, boolean_positive))
            return False
        else:
            self.logger.debug("XPath evaluation succeed.")
            return True


class XPathLinks(XPathMatch):
    """
    This class is used to verify XPath on reponses which are referenced as links in api

    You have to specify entity_type  e.g. 'hosts' in constructor
    Author: jvorcak
    Usage:
        xpathHostsLinks = XPathLinks('hosts', logger, util, links)
        xpathHostsLinks('TRUE', 'host_address', link_name='storage', xpath='count(/base)')
    See @XPathMatch for more details
    """


    def __init__(self, entity_type, logger, utils, links):
        XPathMatch.__init__(self, logger, utils, links)
        self.entity_type = entity_type


    def __call__(self, positive, entity, link_name, xpath, rslt_eval='0. < result'):
        entityObj = self.utils.find(self.links[self.entity_type], entity)
        return XPathMatch.__call__(self, positive, entityObj.link[link_name].href, xpath, rslt_eval)

