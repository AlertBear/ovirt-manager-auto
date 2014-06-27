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

from lxml import etree
from art.core_api.apis_exceptions import EngineTypeError


class XPathMatch(object):
    """
    This callable class can HTTP-GET the resource specified and perform a XPath
    query on the resource got. Then the result of XPath query is evaluated
    using eval(rslt_eval).

    Normally you actually won't need to set the positivity to any other
    value than True, because all the logic can be done in rslt_eval.

    Usage:
    # Instantiate the callable and call it.
    xpathMatch = XPathMatch(api)
    xpathMatch(True, 'hosts', 'count(/hosts//ksm/enabled)',
                    rslt_eval='match == 1')
    # Returns True iff exactly one tag matches.

    returns: True iff the test positivity equals the evaluation result.
    """

    def __init__(self, api_util):
        """
        A callable object that provides generic way to use XPath queries for
        all facilities as Hosts, Clusters and so on.

        param utils: An instance of restutils to use.
        param href:  An URL to HTTP-GET the doc to perform XPath query on.
        param links: A mapping of link and href.

        See the doc for XPathMatch for more details.
        """
        self.api = api_util

    def __call__(self, positive, link, xpath, rslt_eval='0. < result',
                 absLink=False):
        """
        See the doc for XPathMatch for more details.
        """
        # A hack to make the XPathMatch able to match against the tags in the
        # RHEVM entry-point url.
        if self.api.opts['engine'] != 'rest':
            raise EngineTypeError(
                "Engine type '%s' not supported by xpath"
                % self.api.opts['engine'])

        if link.startswith('/'):
            matching_nodes = self.getAndXpathEval(link, xpath, absLink)
        else:
            if 'api' == link:
                matching_nodes = self.getAndXpathEval(None, xpath, absLink)
            else:
                matching_nodes = self.getAndXpathEval(link, xpath, absLink)

        if positive != eval(rslt_eval, None, {'result': matching_nodes}):
            E = "XPath '%s' result evaluated using '%s' not equal to %s."
            self.api.logger.error(E % (xpath, rslt_eval, positive))
            return False
        else:
            self.api.logger.debug("XPath evaluation succeed.")
            return True

    def getEtreeParsed(self, link, absLink):
        return etree.fromstring(
            self.api.get(link, absLink=absLink, noParse=True))

    def getAndXpathEval(self, link, xpath, absLink):
        return self.getEtreeParsed(link, absLink).xpath(xpath)


class XPathLinks(XPathMatch):
    """
    This class is used to verify XPath on reponses which are referenced as
    links in api

    You have to specify entity_type  e.g. 'hosts' in constructor
    Author: jvorcak
    Usage:
        xpathHostsLinks = XPathLinks(api)
        xpathHostsLinks(True, 'host_address', link_name='storage',
                        xpath='count(/base)')
    See @XPathMatch for more details
    """

    def __init__(self, api_util):
        XPathMatch.__init__(self, api_util)

    def __call__(self, positive, entity, link_name, xpath,
                 rslt_eval='0. < result'):
        if self.api.opts['engine'] != 'rest':
            raise EngineTypeError(
                "Engine type '%s' not supported by xpath" %
                self.api.opts['engine'])

        entityObj = self.api.find(entity)
        link = self.api.getElemFromLink(entityObj, link_name=link_name,
                                        attr=None, get_href=True)
        return XPathMatch.__call__(
            self, positive, link, xpath, rslt_eval, True)
