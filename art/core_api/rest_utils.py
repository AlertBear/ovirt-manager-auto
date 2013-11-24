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
import os
import re
import time

from art.core_api import http, template_parser, validator, measure_time
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import APIUtil, parse, data_st
from art.test_handler import settings

DEF_TIMEOUT = 900 # default timeout
DEF_SLEEP = 10 # default sleep
NEGATIVE_CODES = [400, 409, 500]
NEGATIVE_CODES_CREATE = NEGATIVE_CODES + [404]

restInit = None


class RestUtil(APIUtil):

    xsd = None
    xsd_schema_errors = []

    '''
    Implements REST APIs methods
    '''
    def __init__(self, element, collection, **kwargs):

        super(RestUtil, self).__init__(element, collection, **kwargs)

        self.entry_point = settings.opts.get('entry_point', 'api')
        standalone = self.opts.get('standalone', False)
        global restInit

        if restInit and not standalone:
            self.api = restInit
        else:
            self.api = http.HTTPProxy(self.opts)
            if not standalone:
                self.api.connect()
                restInit = self.api

        self.links = self.api.HEAD_for_links()

        # load xsd schema file
        if self.xsd is None:
            xsd_schema = etree.parse(settings.opts.get('api_xsd'))
            self.xsd = etree.XMLSchema(xsd_schema)


    def validateResponseViaXSD(self, href, ret):
        '''
        Validate xml response against xsd schema
        Author: jvorcak
        Parameters:
           * href - url of the request
           * ret - reponse object containing the body
        '''
        if ret['body']:
            try:
                doc = etree.fromstring(ret['body'])
                self.xsd.assertValid(doc)
            except etree.DocumentInvalid as err:
                error_obj = (href, ret, err)
                self.xsd_schema_errors.append(error_obj)
            except etree.XMLSyntaxError as err:
                self.logger.error('Failed parsing response for XSD validations'\
                                  'error: %s. body: %s' % (err, ret['body']))


    def buildUrl(self, href, current=None):
        '''
        Description: builds url with matrix parameters
        Parameters:
           * href - initial url for request
           * current - boolean current value (True/False)
        Return: result url
        '''
        url = href
        if current is True:
            url = '%s;current' % href
        return url


    def get(self, href=None, elm=None, absLink=True, listOnly=False,
            noParse=False, validate=True):
        '''
        Description: implements GET method and verify the reponse (codes 200,201)
        Author: edolinin
        Parameters:
           * href - url for get request
           * elm - element name
           * absLink - if href url is absolute url (True) or just a suffix
        Return: parsed GET response
        '''
        if href is None:
            href=self.collection_name

        if not absLink:
            if href:
                href = self.links[href]
            else:
                href = self.opts['uri']

        if not elm:
            elm=self.element_name

        self.logger.debug("GET request content is --  url:%(uri)s " % {'uri': href })
        ret = self.api.GET(href)

        if not validator.compareResponseCode(ret, [200, 201], self.logger):
            return None

        if  validate:
            self.validateResponseViaXSD(href, ret)

        self.logger.debug("Response body for GET request is: %s " % ret['body'])

        if noParse:
            return ret['body']

        parsedResp = None
        try:
            parsedResp = parse(ret['body'])
        except etree.XMLSyntaxError:
            self.logger.error("Cant parse xml response")
            return None

        if hasattr(parsedResp, elm):
            return getattr(parsedResp, elm)
        else:
            if listOnly:
                self.logger.error("Element '{0}' not found at {1}".format(elm, ret['body']))
            return parsedResp


    def create(self, entity, positive,
                expected_pos_status=[200, 201, 202],
                expected_neg_status=NEGATIVE_CODES_CREATE,
                expectedEntity=None, incrementBy=1,
                async=False, collection=None,
                coll_elm_name = None, current=None):
        '''
        Description: implements POST method and verify the response
        Author: edolinin
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_pos_status - list of expected statuses for positive request
           * expected_neg_status - list of expected statuses for negative request
           * expectedEntity - if there are some expected entity different from sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
           * collection - explicitely defined collection where to add an entity
           * coll_elm_name - name of collection element if it's different
           from self.element_name
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        href = collection
        if not href:
            href = self.links[self.collection_name]

        if not coll_elm_name:
            coll_elm_name = self.element_name

        if self.opts['validate']:
            collection = self.get(href, listOnly=True, elm=coll_elm_name)

        entity = validator.dump_entity(entity, self.element_name)

        post_url = self.buildUrl(href, current)
        self.logger.debug("CREATE request content is --  url:%(uri)s body:%(body)s " \
                            % {'uri': post_url, 'body': entity })

        with measure_time('POST'):
            ret = self.api.POST(post_url, entity)

        if not self.opts['validate']:
            return None, True

        collection = self.get(href, listOnly=True, elm=coll_elm_name)

        self.logger.debug("Response body for CREATE request is: %s " % ret['body'])

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return None, False

            if ret['body']:
                self.logger.info("New entity was added")
                actlEntity = validator.dump_entity(parse(ret['body']),
                                                    self.element_name)

                expEntity = entity if not expectedEntity\
                            else validator.dump_entity(expectedEntity,
                                                       self.element_name)
                if not validator.compareElements(parse(expEntity),
                parse(actlEntity), self.logger, self.element_name):
                    return None, False

                if not async:
                    self.find(parse(actlEntity).id, 'id',
                    collection=collection, absLink=False)

            else:
                return ret['body'], True

        else:
            if not validator.compareResponseCode(ret, expected_neg_status, self.logger):
                return None, False

        self.validateResponseViaXSD(href, ret)
        return parse(ret['body']), True


    def update(self, origEntity, newEntity, positive,
                        expected_pos_status=[200, 201],
                        expected_neg_status=NEGATIVE_CODES,
                        current=None):
        '''
        Description: implements PUT method and verify the response
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_pos_status - list of expected statuses for positive request
           * expected_neg_status - list of expected statuses for negative request
        Return: PUT response, status (True if PUT test succeeded, False otherwise)
        '''

        entity = validator.dump_entity(newEntity, self.element_name)

        put_url = self.buildUrl(origEntity.href, current)
        self.logger.debug("PUT request content is --  url:%(uri)s body:%(body)s " \
                                    % {'uri': put_url, 'body': entity })

        with measure_time('PUT'):
            ret = self.api.PUT(put_url, entity)

        if not self.opts['validate']:
            return None, True

        self.logger.debug("Response body for PUT request is: %s " % ret['body'])

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return None, False

            self.logger.info(self.element_name + " was updated")

            if not validator.compareElements(parse(entity),
            parse(ret['body']), self.logger, self.element_name):
                return None, False

        else:
            if not validator.compareResponseCode(ret, expected_neg_status, self.logger):
                return None, False

        self.validateResponseViaXSD(origEntity.href, ret)
        return parse(ret['body']), True


    def delete(self, entity, positive, body=None, element_name=None,
                                expected_pos_status=[200, 202, 204],
                                expected_neg_status=NEGATIVE_CODES):
        '''
        Description: implements DELETE method and verify the reponse
        Author: edolinin
        Parameters:
           * entity - entity to delete
           * positive - if positive or negative verification should be done
           * body - entity for post body
           * element_name - element name
           * expected_pos_status - list of expected statuses for positive request
           * expected_neg_status - list of expected statuses for negative request
        Return: status (True if DELETE test succeeded, False otherwise)
        '''

        if body:
            if not element_name:
                element_name = self.element_name
            body = validator.dump_entity(body, element_name)
            self.logger.debug("DELETE request content is --  url:%(uri)s body:%(body)s " \
                                                        % {'uri': entity.href, 'body': body })

            with measure_time('DELETE'):
                ret = self.api.DELETE(entity.href, body)
        else:
            self.logger.debug("DELETE request content is --  url:%(uri)s" \
                                                            % {'uri': entity.href})
            with measure_time('DELETE'):
                ret = self.api.DELETE(entity.href)

        if not self.opts['validate']:
            return True

        self.logger.debug("Response body for DELETE request is: %s " % ret['body'])

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return False
        else:
            if not validator.compareResponseCode(ret, expected_neg_status, self.logger):
                return False

        self.validateResponseViaXSD(entity.href, ret)
        return True


    def find(self, val, attribute='name', absLink=True, collection=None,
             **kwargs):
        '''
        Description: find entity by name
        Author: edolinin
        Parameters:
           * val - name of entity to look for
           * attribute - attribute name for searching
           * absLink - absolute link or just a  suffix
           * **kwargs - additional search attribute=val pairs (the attribute
                        can be a chain attribute such as 'attr_x.attr_y')
        Return: found entity or exception EntityNotFound
        '''

        href = self.collection_name
        if absLink:
            href = self.links[self.collection_name]

        if not collection:
            collection = self.get(href, listOnly=True)

        if not collection:
            raise EntityNotFound("Empty collection %s" % href)

        results = filter(lambda r: getattr(r, attribute) == val,
                         collection)

        for attr, value in kwargs.iteritems():
            results = filter(lambda r: reduce(getattr,
                                              attr.split('.'), r) == value,
                             results)

        if not results:
            raise EntityNotFound("Entity %s not found on url '%s'." %
                                 (val, href))
        if len(results) > 1:
            raise EntityNotFound("More than one Entities found for %s\
                                  on url '%s'." % (val, href))
        return results[0]


    def query(self, constraint, expected_status=[200, 201], href=None,
            event_id=None, **params):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
           * expected_status - list of expected statuses for positive request
        Return: query results
        '''
        if not href:
            href = self.links[self.collection_name + '/search']

        beforeSearch, afterSearch = href.split('?')
        searchParams = [beforeSearch]
        for p, val in params.iteritems():
            searchParams.append("{0}={1}".format(p, val))

        href = "{0}?{1}".format(";".join(searchParams), afterSearch)

        templ = template_parser.URITemplate(href)
        qhref = templ.sub({"query": constraint})
        if event_id:
            qhref = templ.sub({"query": constraint, "event_id": event_id})
        else:
            qhref = qhref.replace("from=;", '')

        self.logger.debug("SEARCH request content is --  url:%(uri)s" % {'uri': qhref})

        with measure_time('GET'):
            ret = self.api.GET(qhref)

        self.logger.debug("Response body for QUERY request is: %s " % ret['body'])

        if not validator.compareResponseCode(ret, expected_status, self.logger):
            return None

        self.validateResponseViaXSD(href, ret)

        return getattr(parse(ret['body']), self.element_name)


    def syncAction(self, entity, action, positive, async=False,
                positive_async_stat=[200, 202], positive_sync_stat=[200,201],
                negative_stat=NEGATIVE_CODES, **params):
        '''
        Description: run synchronic action
        Author: edolinin
        Parameters:
           * entity - target entity
           * action - desired action
           * positive - if positive or negative verification should be done
           * asynch - synch or asynch action
           * positive_async_stat - asynch expected status
           * positive_sync_stat - synch expected status
           * negative_stat - negative test expected status
        Return: status (True if Action test succeeded, False otherwise)
        '''

        def getActionHref(actions, action):
            results = filter(lambda x: x.get_rel()==action, actions.get_link())
            return results[0].get_href()

        actionHref = getActionHref(entity.actions, action)
        if re.search('^/{0}/.*'.format(self.entry_point), actionHref) is None:
            actionHref = '/{0}{1}'.format(self.entry_point, actionHref)

        actionBody = validator.dump_entity(self.makeAction(async, 10, **params),
                                    'action')

        self.logger.debug("Action request content is --  url:%(uri)s body:%(body)s " \
                                     % {'uri': actionHref, 'body': actionBody })

        with measure_time('POST'):
            ret = self.api.POST(actionHref, actionBody)

        if not self.opts['validate']:
            return True

        self.logger.debug("Response body for action request is: %s " % ret['body'])
        resp_action = None
        try:
            resp_action = parse(ret['body'])
        except etree.XMLSyntaxError:
             self.logger.error("Cant parse xml response")
             return False

        if positive and not async:
            if not validator.compareResponseCode(ret, positive_sync_stat, self.logger):
                return False
            if resp_action and not validator.compareActionStatus(resp_action.status.state,
                                                                    ["complete"],
                                                                    self.logger):
                return False
        elif positive and async:
            if not validator.compareResponseCode(ret, positive_async_stat, self.logger):
                return False
            if resp_action and not validator.compareActionStatus(resp_action.status.state,
                                                                    ["pending", "complete"],
                                                                    self.logger):
                return False
        else:
            if not validator.compareResponseCode(ret, negative_stat, self.logger):
                return False

        self.validateResponseViaXSD(actionHref, ret)
        return validator.compareActionLink(entity.actions, action, self.logger)


    def getElemFromLink(self, elm, link_name=None, attr=None, get_href=False):
        '''
        Description: get element's collection from specified link
        Parameters:
           * elm - element object
           * link_name - link name
           * attr - attribute to get (usually name of desired element)
           * get_href - if to return href link or no
        Return: element obj or None if not found
        '''
        if not link_name:
            link_name = self.collection_name

        if not attr:
            attr = self.element_name

        no_results = None if get_href else []

        for link in elm.get_link():
            if link.get_rel() == link_name:
                if get_href:
                    return link.get_href()

                linkCont = self.get(link.get_href())
                if not linkCont:
                    return no_results

                if isinstance(linkCont, list):
                    return linkCont
                elif isinstance(linkCont, data_st.Fault):
                    raise EntityNotFound("Obtained Fault object for %s "
                                        "element and link_name %s link with"
                                        " response: %s" % (elm, link_name,
                                        linkCont.get_detail()))
                else:
                    return getattr(linkCont, 'get_' + attr)()
        return no_results


    def waitForElemStatus(self, restElement, status, timeout=DEF_TIMEOUT,
                            ignoreFinalStates=False, collection=None):
        '''
        Description: Wait till the rest element (the Host, VM) gets the desired
        status or till timeout.

        Author: edolinin
        Parameters:
            * restElement - rest element to probe for a status
            * status - a string represents status to wait for. it could be
                       multiple statuses as a string with space delimiter
                       Example: "active maintenance inactive"
            * timeout - maximum time to continue status probing
        Return: status (True if element get the desired status, False otherwise)
        '''

        handleTimeout = 0
        while handleTimeout <= timeout:
            restElement = self.get(restElement.href)

            elemStat = None
            if hasattr(restElement, 'snapshot_status'):
                elemStat = restElement.snapshot_status.lower()
            elif hasattr(restElement, 'status'):
                elemStat = restElement.status.state.lower()
            else:
                self.logger.error("Element %s doesn't have attribute status" % \
                                                        (self.element_name))
                return False

            if elemStat in status.lower().split():
                self.logger.info("%s status is '%s'" \
                                % (self.element_name, elemStat))
                return True
            elif elemStat.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, elemStat))
                return False
            elif elemStat == 'up' and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, elemStat))
                return False
            else:
                self.logger.debug("Waiting for status '%s' currently status is '%s' "\
                                % (status, elemStat))
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'."\
                        % (self.element_name, elemStat))
        return False


APIUtil.register(RestUtil)
