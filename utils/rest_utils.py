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
import http
import template_parser
import validator
import time
from apis_exceptions import EntityNotFound
from lxml import etree
from utils.data_structures import parseString as parse
from utils.data_structures import *
from utils.apis_utils import APIUtil, TimeoutingSampler
import os

DEF_TIMEOUT = 900 # default timeout
DEF_SLEEP = 10 # default sleep
XSD_FILE = os.path.join(os.path.dirname(__file__), '..', 'conf/api.xsd')
MEDIA_TYPE = 'application/xml'


class RestUtil(APIUtil):

    xsd = None
    xsd_schema_errors = []

    '''
    Implements REST APIs methods
    '''
    def __init__(self, element, collection):

        super(RestUtil, self).__init__(element, collection)
        
        self.links = http.HEAD_for_links(self.opts)
        self.initiated = True

        # load xsd schema file
        if self.xsd is None:
            xsd_schema = etree.parse(XSD_FILE)
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


    def get(self, href=None, elm=None, absLink=True):
        '''
        Description: implements GET method and verify the reponse (codes 200,201)
        Author: edolinin
        Parameters:
           * href - url for get request
           * elm - element name
           * absLink - if href url is absolute url (True) or just a suffix
        Return: parsed GET response
        '''
        if not href:
            href=self.collection_name

        if not absLink:
            href = self.links[href]

        if not elm:
            elm=self.element_name

        self.logger.debug("GET request content is --  url:%(uri)s " % {'uri': href })
        ret = http.GET(self.opts, href, MEDIA_TYPE)

        self.validateResponseViaXSD(href, ret)
        validator.compareResponseCode(ret, [200, 201], self.logger)

        self.logger.debug("Response body for GET request is: %s " % ret['body'])

        if hasattr(parse(ret['body']), elm):
            return getattr(parse(ret['body']), elm)
        else:
            return parse(ret['body'])
        

    def create(self, entity, positive,
                expected_pos_status=[200, 201, 202], expected_neg_status=[500, 400],
                expectedEntity=None, incrementBy=1, async=False, collection=None):
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
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        href = collection
        if not href:
            href = self.links[self.collection_name]

        collection = self.get(href)
        entity = validator.dump_entity(entity, self.element_name)
        initialCollectionSize = len(collection)

        self.logger.debug("CREATE request content is --  url:%(uri)s body:%(body)s " \
                            % {'uri': href, 'body': entity })
        ret = http.POST(self.opts, href, entity, MEDIA_TYPE)

        collection = self.get(href)

        self.validateResponseViaXSD(href, ret)
        self.logger.debug("Response body for CREATE request is: %s " % ret['body'])

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return None, False

            if not async:
                if not self.opts['parallel_run'] and \
                    not validator.compareCollectionSize(collection,
                                                        initialCollectionSize + incrementBy,
                                                        self.logger):
                    return None, False

            if(parse(ret['body'])):
                self.logger.info("New entity was added")
                actlEntity = validator.dump_entity(parse(ret['body']),
                                                    self.element_name)
                expEntity = entity if not expectedEntity else expectedEntity

                if not validator.compareElements(parse(expEntity),
                parse(actlEntity), self.logger, self.element_name):
                    return None, False

        else:
            if not validator.compareResponseCode(ret, expected_neg_status, self.logger):
                return None, False

            if not validator.compareCollectionSize(collection,
                                                    initialCollectionSize,
                                                    self.logger):
                return None, False

        return parse(ret['body']), True


    def update(self, origEntity, newEntity, positive, expected_pos_status=[200, 201],
                                        expected_neg_status=[500, 400]):
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

        self.logger.debug("PUT request content is --  url:%(uri)s body:%(body)s " \
                                    % {'uri': origEntity.href, 'body': entity })
        ret = http.PUT(self.opts, origEntity.href, entity, MEDIA_TYPE)
        self.logger.debug("Response body for PUT request is: %s " % ret['body'])

        self.validateResponseViaXSD(origEntity.href, ret)

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

        return parse(ret['body']), True


    def delete(self, entity, positive, body=None, element_name=None,
                expected_pos_status=[200, 202, 204], expected_neg_status=[500, 400]):
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
                                                        % {'uri': entity.href, 'body': entity })
            ret = http.DELETE(self.opts, entity.href, body, MEDIA_TYPE)
        else:
            self.logger.debug("DELETE request content is --  url:%(uri)s" \
                                                            % {'uri': entity.href})
            ret = http.DELETE(self.opts, entity.href)

        self.logger.debug("Response body for DELETE request is: %s " % ret['body'])
        self.validateResponseViaXSD(entity.href, ret)

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return False
        else:
            if not validator.compareResponseCode(ret, expected_neg_status, self.logger):
                return False

        return True


    def find(self, val, attribute='name', absLink=True):
        '''
        Description: find entity by name
        Author: edolinin
        Parameters:
           * val - name of entity to look for
           * attribute - attribute name for searching
           * absLink - absolute link or just a  suffix
        Return: found entity or exception EntityNotFound
        '''

        href = self.collection_name
        if absLink:
            href = self.links[self.collection_name]
     
        try:
            collection = self.get(href)
            results = filter(lambda r: getattr(r, attribute) == val, collection)[0]
        except Exception:
            raise EntityNotFound("Entity %s not found on url '%s'." % (val, href))

        return results


    def query(self, constraint,  expected_status=[200, 201], href=None):
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
        templ = template_parser.URITemplate(href)
        qhref = templ.sub({"query": constraint})

        self.logger.debug("SEARCH request content is --  url:%(uri)s" % {'uri': qhref})
        ret = http.GET(self.opts, qhref, MEDIA_TYPE)
        self.logger.debug("Response body for QUERY request is: %s " % ret['body'])

        self.validateResponseViaXSD(href, ret)
        validator.compareResponseCode(ret, expected_status, self.logger)

        return getattr(parse(ret['body']), self.element_name)


    def syncAction(self, entity, action, positive, async=False,
                positive_async_stat=[202], positive_sync_stat=[200,201],
                negative_stat=[500, 400], **params):
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

        actions = entity.actions
        if validator.compareActionLink(actions, action, self.logger):

            def getActionHref(actions, action):
                results = filter(lambda x: x.get_rel()==action, actions.get_link())
                return results[0].get_href()

            actionHref = getActionHref(entity.actions, action)
            actionBody = validator.dump_entity(self.makeAction(async, 10, **params),
                                    'action')

            self.logger.debug("Action request content is --  url:%(uri)s body:%(body)s " \
                            % {'uri': actionHref, 'body': actionBody })
            ret = http.POST(self.opts,
                            actionHref,
                            actionBody,
                            MEDIA_TYPE)

            resp_action = parse(ret['body'])
            self.logger.debug("Response body for action request is: %s " % ret['body'])
            self.validateResponseViaXSD(actionHref, ret)

            if positive and not async:
                if not validator.compareResponseCode(ret, positive_sync_stat, self.logger):
                    return False
                if resp_action and not validator.compareActionStatus(resp_action.status.state,
                                                                    "complete",
                                                                    self.logger):
                    return False
            elif positive and async:
                if not validator.compareResponseCode(ret, positive_async_stat, self.logger):
                    return False
                if resp_action and not validator.compareActionStatus(resp_action.status.state,
                                                                    "pending",
                                                                    self.logger):
                    return False
            else:
                if not validator.compareResponseCode(ret, negative_stat, self.logger):
                    return False
                if resp_action and not validator.compareActionStatus(resp_action.status.state,
                                                                    "failed",
                                                                    self.logger):
                    return False

            return True

        else:
            return False


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
            
        for link in elm.get_link():
            if link.get_rel() == link_name:
                if get_href:
                    return link.get_href()

                linkCont = self.get(link.get_href())
                if isinstance(linkCont, list):
                    return linkCont
                else:
                    return getattr(linkCont, 'get_' + attr)()
        return None
    

    def getEtreeParsed(self, link):
        return etree.fromstring(self.getNoParse(link))


    def getAndXpathEval(self, link, xpath):
        return self.getEtreeParsed(link).xpath(xpath)


    def waitForXPath(self, link, xpath, timeout=DEF_TIMEOUT, sleep=DEF_SLEEP):
        '''
        Waits until the query `xpath` on doc specified by `link` is evaluates as
        True.

        Parameters:
            * link - A string specifying the resource, as it is required by
                     getNoParse.
            * xpath - string, a XPath querry to wait to evaluate as True.
            * timeout - Maximal number of seconds to wait.
            * sleep - A sampling period.
        Author: jhenner
        '''

        MSG = 'Waiting for xpath `%s` up to %d seconds, sampling every %d second.'
        self.logger.info(MSG % (xpath, timeout, sleep))
        sampler = TimeoutingSampler(timeout, sleep, self.getAndXpathEval)
        TIMEOUT_MSG_TMPL = "Timeouted when waiting for sampled {0} " \
                           "to match xpath `{1}`."
        sampler.timeout_exc_args = TIMEOUT_MSG_TMPL.format(link, xpath),
        sampler.func_args = link, xpath
        for sampleOk in sampler:
            if sampleOk:
                return True


    def waitForElemStatus(self, restElement, status,
                              timeout=DEF_TIMEOUT, ignoreFinalStates=False):
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

        restElement = self.get(restElement.href)

        handleTimeout = 0
        while handleTimeout <= timeout:
            restElement = self.get(restElement.href)

            if not hasattr(restElement, 'status'):
                self.logger.error("Element %s doesn't have attribute status" % (restElementName))
                return False

            if restElement.status.state.lower() in status.lower().split():
                self.logger.info("%s status is '%s'" \
                                % (self.element_name, restElement.status.state))
                return True
            elif restElement.status.state.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, restElement.status.state))
                return False
            elif restElement.status.state.find("up") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, restElement.status.state))
                return False
            else:
                self.logger.debug("Waiting for status '%s' currently status is '%s' "\
                                % (status, restElement.status.state))
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'."\
                        % (self.element_name, restElement.status.state))
        return False

APIUtil.register(RestUtil)
