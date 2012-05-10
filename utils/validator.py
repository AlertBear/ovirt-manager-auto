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

from xml.dom.minidom import parseString

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
        assert status == expected
        logger.debug("Action status is valid: %(exp)s " % {'exp': expected })
        return True
    except AssertionError:
        logger.error("Action status is not valid, expected is: %(exp)s, actual is: %(act)s " % {'exp': expected , 'act': status})
        return False


def compareCollectionSize(collection, expectedSize,logger):

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


def compareEntitiesDumps(entityExp, entityAct, logger):
    """
    Description: Function to compare 2 xml strings
    Parameters:
     * entityExp - expected xml string
     * entityAct - actual xml string
     * logger - logger instance
    Return: True if comparison succeeded, False otherwise
    """

    try:
        xmlExp = parseString(entityExp)
        xmlAct = parseString(entityAct)

        logger.debug("Running entity validation")

        if not elementEqual(xmlExp.documentElement, xmlExp, xmlAct, logger):
            raise AssertionError

        logger.debug("Compared entities are equal")
        return True

    except AssertionError:
        logger.error("Compared entities are not equal")
        return False


def elementEqual(mainNode, xmlExp, xmlAct, logger):
    """
    Description: Recursive function to compare expected and actual xml objects.
    Compared only nodes that appear in both expected and actual xmls.
    If some nodes don't appear in actual xml objects - comparison
    just skip them since they may appear as links or as nodes attributes.
    Parameters:
     * mainNode - main node to start from
     * xmlExp - expected xml dom object
     * xmlAct - actual xml dom object
     * logger - logger instance
    Return: True if comparison succeeded, False otherwise
    """

    status = True

    # these attributes should not be compared
    exclude_from_check = [['vm','template','id'],]

    for node in mainNode.childNodes:
            # take relevant xml nodes only
            if node.nodeType == 1 and xmlExp.getElementsByTagName(node.tagName) \
            and node.tagName!='link' and node.tagName!='status':

                # expected xml node
                for i in range(0, len(xmlExp.getElementsByTagName(node.tagName))):
                    nodeExp = xmlExp.getElementsByTagName(node.tagName)[i].firstChild
                    # check for existence of this node in xmlAct
                    if xmlAct.getElementsByTagName(node.tagName):
                        try:
                            nodeAct = xmlAct.getElementsByTagName(node.tagName)[i].firstChild

                            if nodeExp and nodeExp.nodeValue:
                                if nodeAct: # if actual node exists - run the comparison
                                    if nodeExp.nodeValue == nodeAct.nodeValue:
                                        logger.debug("Node '{0}->{1}' is OK: {2}".format(mainNode.nodeName,
                                                                        node.tagName, nodeExp.nodeValue))
                                    else:
                                        status = False
                                        logger.error("Node '{0}->{1}' has wrong value, expected: {2}, actual`: {3}".format(
                                                    mainNode.nodeName, node.tagName, nodeExp.nodeValue, nodeAct.nodeValue))
                                else:
                                    continue

                            elif nodeExp: # node has children nodes
                                if not elementEqual(node, xmlExp.getElementsByTagName(node.tagName)[i],
                                xmlAct.getElementsByTagName(node.tagName)[i], logger):
                                    status = False

                            if node.attributes:
                                nodeAtrExp = node
                                nodeAtrAct = xmlAct.getElementsByTagName(node.tagName)[0]
                            else:
                                nodeAtrExp = nodeExp
                                nodeAtrAct = nodeAct

                            # compare nodes attributes
                            if nodeAtrExp and nodeAtrAct:
                                if nodeAtrExp.attributes and nodeAtrAct.attributes:
                                    for attributeName in nodeAtrExp.attributes.keys():
                                        if nodeAtrExp.attributes[attributeName].value == nodeAtrAct.attributes[attributeName].value:
                                            logger.debug("Node '{0}->{1}->{2}' is OK: {3}".format(mainNode.nodeName,
                                                            node.tagName, nodeAtrExp.attributes[attributeName].name,
                                                            nodeAtrExp.attributes[attributeName].value))
                                        else:
                                            if mainNode.nodeName!="supported_versions" and \
                                            [mainNode.nodeName, node.tagName, nodeAtrExp.attributes[attributeName].name] not in exclude_from_check:
                                                logger.error("Node '{0}->{1}->{2}' has wrong value, expected: {3}, actual: {4}".format(
                                                        mainNode.nodeName, node.tagName, nodeAtrExp.attributes[attributeName].name,
                                                        nodeAtrExp.attributes[attributeName].value, nodeAtrAct.attributes[attributeName].value))
                                                status = False
                            elif nodeAtrExp and not nodeAtrAct:
                                logger.error("Node '{0}->{1}->{2}' doesn't exist".format(mainNode.nodeName,
                                                                        node.tagName, nodeAtrExp.nodeName))
                                status = False
                        except IndexError:
                            logger.error("Node '{0}->{1}->{2}' doesn't exist".format(mainNode.nodeName,
                                                                        node.tagName, nodeExp.nodeValue))
                            status = False

    return status


def compareNodesAttributes(doc,nodeName,nodeAttribute,expectedVal,logger):

    docXml = parseString(doc)
    compElement = docXml.getElementsByTagName(nodeName)[0]
    compAttribute = compElement.getElementsByTagName(nodeAttribute)[0].firstChild

    if compAttribute.nodeValue == expectedVal:
        logger.debug("Attributes '" + nodeAttribute + "' are equal for '" + nodeName + "': " + expectedVal)
        status = True
    else:
        logger.error("Attributes '" + nodeAttribute + "' are no equal for '" + nodeName + "', expected: '" + expectedVal + "', actual: '" + compAttribute.nodeValue + "'")
        status = False

    return status


def compareNodesAttributesInSet(doc,nodeName,nodeAttribute,expectedValSet,logger):

    docXml = parseString(doc)
    compElements = docXml.getElementsByTagName(nodeName)
    status = True

    for compElement in compElements:
        compAttribute = compElement.getElementsByTagName(nodeAttribute)[0].firstChild

        if compAttribute.nodeValue in expectedValSet:
            logger.debug("Attributes '" + nodeAttribute + "' are equal for '" + nodeName + "': " + compAttribute.nodeValue)
        else:
            logger.error("Attributes '" + nodeAttribute + "' doesn't exist for '" + nodeName + "', expected: '" + str(expectedValSet) + "', actual: '" + compAttribute.nodeValue+ "'")
            status = False

    if len(compElements) == len(expectedValSet):
        logger.debug("Attributes set size is correct: " + str(len(compElements)))
    else:
        logger.error("Attributes set size is wrong, expected:  %(exp)s, actual: %(act)s" % {'exp': len(expectedValSet) , 'act': len(compElements)})
        status = False

    return status


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

