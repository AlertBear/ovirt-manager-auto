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
import re
import time
import threading
from contextlib import contextmanager
from art.core_api import http, template_parser, validator, measure_time
from art.core_api.apis_exceptions import EntityNotFound, APIException,\
    APILoginError
from art.core_api.apis_utils import (
    APIUtil, parse, data_st, NEGATIVE_CODES_CREATE, NEGATIVE_CODES,
    DEF_TIMEOUT, DEF_SLEEP, ApiOperation, api_error
)
from art.test_handler import settings


class RespKey(object):
    '''
    Description: Class to represent the Responds Keys (like Enum)
    Author: khakimi
    '''
    status = 'status'
    reason = 'reason'
    body = 'body'
    trace = 'trace'


class RestUtil(APIUtil):

    xsd = None
    xsd_schema_errors = []
    _restInit = None
    context_lock = threading.Lock()

    '''
    Implements REST APIs methods
    '''
    def __init__(self, element, collection, **kwargs):
        super(RestUtil, self).__init__(element, collection, **kwargs)
        self.entry_point = settings.opts.get('entry_point', 'api')
        self.standalone = self.opts.get('standalone', False)
        self.login()

    def login(self):
        """
        Description: login to rest api.
        Author: imeerovi
        Parameters:
        Returns:
        """
        if RestUtil._restInit and not self.standalone:
            self.api = RestUtil._restInit
        else:
            self.api = http.HTTPProxy(self.opts)
            if self.opts['persistent_auth']:
                self.api.headers['Prefer'] = 'persistent-auth'
            self.api.headers['Session-TTL'] = self.opts['session_timeout']
            self.api.headers['Filter'] = str(self.opts['filter'])

            if not self.standalone:
                try:
                    self.api.connect()
                except APIException as e:
                    raise APILoginError(e)

        try:
            self.links = self.api.HEAD_for_links()
        except APIException as ex:
            raise APIException(
                "Failed to Build links matrix from HEAD request. "
                "Exception: %s" % ex
            )
        else:
            if RestUtil._restInit is None:
                RestUtil._restInit = self.api

        # load xsd schema file
        if self.xsd is None:
            xsd_schema = etree.parse(settings.opts.get('api_xsd'))
            self.xsd = etree.XMLSchema(xsd_schema)

        self.max_collection = settings.opts.get('max_collection')

    @classmethod
    def logout(cls):
        """
        Description: logout from rest api.
        Author: imeerovi
        Parameters:
        Returns: True if logout succeeded or False otherwise
        """
        RestUtil._restInit = None

    @contextmanager
    def correlationIdContext(self, api_operation):
        """
        Description: context management for getting correlation id
        Author: imeerovi
        Parameters:
            * api_operation - the api operation performed
        Returns: correlation-id
        """
        with self.__class__.context_lock:
            try:
                self.api.headers['Correlation-Id'] = super(
                    RestUtil, self).getCorrelationId(api_operation)
                self.logger.info("Using Correlation-Id: %s",
                                 self.api.headers['Correlation-Id'])
                yield
            finally:
                self.logger.debug("Cleaning Correlation-Id: %s",
                                  self.api.headers['Correlation-Id'])
                self.api.headers.pop('Correlation-Id')

    def validateResponseViaXSD(self, href, ret):
        '''
        Validate xml response against xsd schema
        Author: jvorcak
        Parameters:
           * href - url of the request
           * ret - reponse object containing the body
        '''
        if ret[RespKey.body]:
            try:
                doc = etree.fromstring(ret[RespKey.body])
                self.xsd.assertValid(doc)
            except etree.DocumentInvalid as err:
                error_obj = (href, ret, err)
                self.xsd_schema_errors.append(error_obj)
            except etree.XMLSyntaxError as err:
                self.logger.error('Failed parsing response for XSD validations'
                                  'error: %s. body: %s' %
                                  (err, ret[RespKey.body]))

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
        Description: implements GET method and verify the response
                     (codes 200,201)
        Author: edolinin
        Parameters:
           * href - url for get request
           * elm - element name
           * absLink - if href url is absolute url (True) or just a suffix
        Return: parsed GET response
        '''
        if href is None:
            href = self.collection_name

        if not absLink:
            if href:
                href = self.links[href]
            else:
                href = self.opts['uri']

        if not elm:
            elm = self.element_name

        self.logger.debug("GET request content is --  url:%(uri)s ",
                          {'uri': href})
        ret = self.api.GET(href)

        if not validator.compareResponseCode(ret[RespKey.status],
                                             [200, 201], self.logger):
            return None

        if validate:
            self.validateResponseViaXSD(href, ret)

        self.logger.debug("Response body for GET request is: %s ",
                          ret[RespKey.body])

        if noParse:
            return ret[RespKey.body]

        parsedResp = None
        try:
            parsedResp = parse(ret[RespKey.body], silence=True)
        except etree.XMLSyntaxError:
            self.logger.error("Cant parse xml response")
            return None

        if hasattr(parsedResp, elm):
            return getattr(parsedResp, elm)
        else:
            if listOnly:
                self.logger.error("Element '{0}' not found at {1} \
                ".format(elm, ret[RespKey.body]))
            return parsedResp

    def parseDetail(self, ret):
        '''
        Description: parsing the error details from ret
        Author: Kobi Hakimi
        Parameter:
            * ret - the string to parse from it the error details
        Return: the error details which we got it as xml node skip the
                last 2 chars '</'
        '''
        try:
            return ret[RespKey.body].split('detail>')[1][:-2]
        except IndexError:
            self.logger.error("Details was not found on body")
            return None

    def responseCodesMatch(self, positive, operation, expected_pos_status,
                           expected_neg_status, ret):
        '''
        Description: print error in case its not positive status and compare
                     the current status with expected positive and negative
                     response codes
        Author: Kobi Hakimi
        Parameter:
            * positive - if positive or negative verification should be done
            * operation - describe from which operation this method called
            * expected_pos_status - LIST OF expected positive status
            * expected_neg_status - LIST OF expected negative status
            * ret - the return value of rest command.
        Return: True if the expected status and the actual status match
                otherwise return False
        '''
        if ret[RespKey.status] not in expected_pos_status:
            reason = ret[RespKey.reason] if(RespKey.reason in
                                            ret.keys()) else None
            self.print_error_msg(operation, ret[RespKey.status], reason,
                                 self.parseDetail(ret), positive=positive)
        expected_statuses = (
            expected_pos_status if positive else expected_neg_status)

        return validator.compareResponseCode(ret[RespKey.status],
                                             expected_statuses, self.logger)

    def create(self, entity, positive,
               expected_pos_status=[200, 201, 202],
               expected_neg_status=NEGATIVE_CODES_CREATE,
               expectedEntity=None, incrementBy=1,
               async=False, collection=None,
               coll_elm_name=None, current=None, compare=True):
        '''
        Description: implements POST method and verify the response
        Author: edolinin
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_pos_status - list of expected statuses for positive
                                   request
           * expected_neg_status - list of expected statuses for negative
                                   request
           * expectedEntity - if there are some expected entity different from
                              sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
           * collection - explicitely defined collection where to add an entity
           * coll_elm_name - name of collection element if it's different
                             from self.element_name
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        href = collection
        if not href:
            href = self.links[self.collection_name]

        if self.max_collection is not None:
            href = '{0};max={1}'.format(href, self.max_collection)

        if not coll_elm_name:
            coll_elm_name = self.element_name

        if self.opts['validate']:
            collection = self.get(href, listOnly=True, elm=coll_elm_name)

        entity = validator.dump_entity(entity, coll_elm_name)

        post_url = self.buildUrl(href, current)
        self.logger.debug(
            "CREATE request content is --  url:%(uri)s body:%(body)s ",
            {'uri': post_url, 'body': entity})

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(ApiOperation.create):
            with measure_time('POST'):
                ret = self.api.POST(post_url, entity)

        if not self.responseCodesMatch(positive, ApiOperation.create,
                                       expected_pos_status,
                                       expected_neg_status, ret):
            return None, False

        if not self.opts['validate']:
            return None, True

        collection = self.get(href, listOnly=True, elm=coll_elm_name)

        self.logger.debug("Response body for CREATE request is: %s ",
                          ret[RespKey.body])

        if positive:
            if ret[RespKey.body]:
                self.logger.info("New entity was added")
                actlEntity = validator.dump_entity(
                    parse(ret[RespKey.body], silence=True), self.element_name)

                expEntity = entity if not expectedEntity else (
                    validator.dump_entity(expectedEntity, self.element_name))

                if compare and not validator.compareElements(
                        parse(expEntity, silence=True),
                        parse(actlEntity, silence=True),
                        self.logger,
                        self.element_name):
                    return None, False

                if not async:
                    self.find(parse(actlEntity, silence=True).id, 'id',
                              collection=collection, absLink=False)

            else:
                return ret[RespKey.body], True
        self.validateResponseViaXSD(href, ret)
        return parse(ret[RespKey.body], silence=True), True

    def update(self, origEntity, newEntity, positive,
               expected_pos_status=[200, 201],
               expected_neg_status=NEGATIVE_CODES, current=None, compare=True):
        '''
        Description: implements PUT method and verify the response
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
           * expected_pos_status - list of expected statuses for positive
                                   request
           * expected_neg_status - list of expected statuses for negative
                                   request
           * compare - True by default and run compareElements,
                       otherwise compareElements doesn't run
        Return: PUT response, status (True if PUT test succeeded,
                                      False otherwise)
        '''

        entity = validator.dump_entity(newEntity, self.element_name)

        put_url = self.buildUrl(origEntity.href, current)
        self.logger.debug(
            "PUT request content is --  url:%(uri)s body:%(body)s ",
            {'uri': put_url, 'body': entity})

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(ApiOperation.update):
            with measure_time('PUT'):
                ret = self.api.PUT(put_url, entity)

        if not self.responseCodesMatch(positive, ApiOperation.update,
                                       expected_pos_status,
                                       expected_neg_status, ret):
            return None, False

        if not self.opts['validate']:
            return None, True

        self.logger.debug("Response body for PUT request is: %s ",
                          ret[RespKey.body])

        if positive:
            self.logger.info(self.element_name + " was updated")

            if compare and not validator.compareElements(
                    parse(entity, silence=True),
                    parse(ret[RespKey.body], silence=True),
                    self.logger, self.element_name):
                return None, False

        self.validateResponseViaXSD(origEntity.href, ret)
        return parse(ret[RespKey.body], silence=True), True

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
           * expected_pos_status - list of expected statuses for positive
                                   request
           * expected_neg_status - list of expected statuses for negative
                                   request
        Return: status (True if DELETE test succeeded, False otherwise)
        '''
        with self.correlationIdContext(ApiOperation.delete):
            if body:
                if not element_name:
                    element_name = self.element_name
                body = validator.dump_entity(body, element_name)
                self.logger.debug(
                    "DELETE request content is --  url:%(uri)s body:%(body)s ",
                    {'uri': entity.href, 'body': body})

                with measure_time('DELETE'):
                    ret = self.api.DELETE(entity.href, body)
            else:
                self.logger.debug("DELETE request content is --  url:%(uri)s",
                                  {'uri': entity.href})
                with measure_time('DELETE'):
                    ret = self.api.DELETE(entity.href)

        if not self.responseCodesMatch(positive, ApiOperation.delete,
                                       expected_pos_status,
                                       expected_neg_status, ret):
            return False

        if not self.opts['validate']:
            return True

        self.logger.debug("Response body for DELETE request is: %s ",
                          ret[RespKey.body])

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

        if self.max_collection is not None:
            href = '{0};max={1}'.format(href, self.max_collection)

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
              event_id=None, all_content=False, **params):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
           * expected_status - list of expected statuses for positive request
           * href - base href for search
           * event_id - even id
           * all_content - all content header
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
            qhref = qhref.replace("from=", '')

        self.logger.debug(
            "SEARCH request content is --  url:%(uri)s" % {'uri': qhref})

        if all_content:
            self.api.headers['All-content'] = all_content

        try:
            with measure_time('GET'):
                ret = self.api.GET(qhref)
        finally:
            if all_content:
                self.api.headers.pop('All-content')

        self.logger.debug(
            "Response body for QUERY request is: %s " % ret[RespKey.body])

        if not validator.compareResponseCode(ret[RespKey.status],
                                             expected_status,
                                             self.logger):
            return None

        self.validateResponseViaXSD(href, ret)

        return getattr(parse(ret[RespKey.body], silence=True),
                       self.element_name)

    def syncAction(
            self, entity, action, positive, async=False,
            positive_async_stat=[200, 202], positive_sync_stat=[200, 201],
            negative_stat=NEGATIVE_CODES, **params
    ):
        '''
        __author__ = edolinin
        run synchronic action
        :param entity: target entity
        :type entity: object
        :param action: desired action
        :type action: str
        :param positive: if positive or negative verification should be done
        :type positive: bool
        :param asynch: synch or asynch action
        :type async: bool
        :param positive_async_stat: asynch expected status
        :type positive_async_stat: list
        :param positive_sync_stat: synch expected status
        :type positive_sync_stat: list
        :param negative_stat: negative test expected status
        :type negative_stat: list
        :return: POST response (None if no response)
                 in case of negative test return api_error object
        :rtype: str
        '''

        def getActionHref(actions, action):
            results = filter(lambda x: x.get_rel() == action,
                             actions.get_link())
            return results[0].get_href()

        actionHref = getActionHref(entity.actions, action)
        if re.search('^/{0}/.*'.format(self.entry_point), actionHref) is None:
            actionHref = '/{0}{1}'.format(self.entry_point, actionHref)

        actionBody = validator.dump_entity(self.makeAction(async, 10,
                                                           **params),
                                           'action')

        self.logger.debug(
            "Action request content is --  url:%(uri)s body:%(body)s ",
            {'uri': actionHref, 'body': actionBody})

        # TODO: fix this nasty nested with when we will move to python 2.7
        with self.correlationIdContext(ApiOperation.syncAction):
            with measure_time('POST'):
                ret = self.api.POST(actionHref, actionBody)

        positive_stat = positive_async_stat if async else positive_sync_stat
        if not self.responseCodesMatch(positive, ApiOperation.syncAction,
                                       positive_stat, negative_stat, ret):
            return None

        if not self.opts['validate']:
            return ret[RespKey.body]

        self.logger.debug("Response body for action request is: %s ",
                          ret[RespKey.body])
        resp_action = None
        try:
            resp_action = parse(ret[RespKey.body], silence=True)
        except etree.XMLSyntaxError:
            self.logger.error("Cant parse xml response")
            return None

        if positive:
            if resp_action and not validator.compareAsyncActionStatus(
                    async, resp_action.status, self.logger):
                return None

        else:
            return api_error(
                reason=ret[RespKey.reason],
                status=ret[RespKey.status],
                detail=self.parseDetail(ret)
            )

        self.validateResponseViaXSD(actionHref, ret)
        valid = validator.compareActionLink(
            entity.actions, action, self.logger
        )

        return ret[RespKey.body] if valid else None

    def extract_attribute(self, response, attr):
        '''
        Extract the attribute from POST response
        :param response: POST response string
        :type response: str
        :param attr: the name of the attribute to extract
        :type attr: str
        :return: list of attribute values
        :rtype: list
        '''
        if response and attr:
            pat = '<{0}>(.*)</{0}>'.format(attr)
            return [str(x) for x in re.findall(pat, response)]
        return None

    def getElemFromLink(self, elm, link_name=None, attr=None, get_href=False,
                        all_content=False):
        """
        Get collection or specific object if attr is passed (link_name or
        self.collection_name) of objects
        from requested element (elm)

        :param elm: Object from which the collection will be retrieved
        :type elm: object
        :param link_name: collection to be retrieved from the elm object
        :type link_name: str
        :param attr: attribute to get (usually name of desired collection)
        :type attr: str
        :param get_href: If True, get the api URL of the object
        :type get_href: bool
        :param all_content: If True, retrieved object should be with all
        content
        :type all_content: bool
        :return: Collection object or None if not found
        :rtype: object or None
        """
        if not link_name:
            link_name = self.collection_name

        if not attr:
            attr = self.element_name

        no_results = None if get_href else []

        if all_content:
            self.api.headers['All-content'] = all_content

        try:
            for link in elm.get_link():
                if link.get_rel() == link_name:
                    if get_href:
                        return link.get_href()

                    link_content = self.get(link.get_href())
                    if not link_content:
                        return no_results

                    if isinstance(link_content, list):
                        return link_content
                    elif isinstance(link_content, data_st.Fault):
                        raise EntityNotFound(
                            "Obtained Fault object for %s element and "
                            "link_name %s link with response: %s"
                            % (elm, link_name, link_content.get_detail())
                        )
                    else:
                        return getattr(link_content, 'get_' + attr)()
        finally:
            # Sets up the default 'all_content' header
            if all_content:
                self.api.headers.pop('All-content')
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
        Return: status (True if element get the desired status,
                        False otherwise)
        '''

        handleTimeout = 0
        while handleTimeout <= timeout:
            restElement = self.get(restElement.href)

            elemStat = None
            if hasattr(restElement, 'snapshot_status'):
                elemStat = restElement.snapshot_status.lower()
            elif hasattr(restElement, 'status'):
                elemStat = restElement.status.lower()
            else:
                self.logger.error("Element %s doesn't have attribute status",
                                  self.element_name)
                return False

            if elemStat in status.lower().split():
                self.logger.info("%s status is '%s'", self.element_name,
                                 elemStat)
                return True
            elif elemStat.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  elemStat)
                return False
            elif elemStat == 'up' and not ignoreFinalStates:
                self.logger.error("%s status is '%s'", self.element_name,
                                  elemStat)
                return False
            else:
                self.logger.debug(
                    "Waiting for status '%s' currently status is '%s' ",
                    status, elemStat)
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'."\
                        % (self.element_name, elemStat))
        return False


APIUtil.register(RestUtil)
