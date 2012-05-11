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
from apis_exceptions import EntityNotFound, APITimeout, APICommandError
from lxml import etree
from time import strftime
import os
from cStringIO import StringIO
import sys
from utils.data_structures import parseString as parse
from utils.data_structures import *
import settings
import abc
import logging
from ovirtsdk import api as sdkApi
from ovirtsdk.infrastructure.errors import RequestError

XSD_FILE = os.path.join(os.path.dirname(__file__), '..', 'conf/api.xsd')
MEDIA_TYPE = 'application/xml'
DEF_TIMEOUT = 900
''' A default timeout for waitForXPath, waitForElemStatus, ... '''

DEF_SLEEP = 10
''' A default sleep for waitForXPath, waitForElemStatus, ... '''
api = None
sdkInit = None

def dump_entity(ds, root_name):
    '''
    Dump DS element to xml format
    '''

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    ds.export(mystdout, 0, name_=root_name)
    sys.stdout = old_stdout
    return mystdout.getvalue()


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


class APIUtil(object):
    '''
    Basic class for API functionality
    '''
    __metaclass__ = abc.ABCMeta

    def __init__(self, element, collection, **kwargs):
        self.opts = settings.opts
        self.element_name = element
        self.collection_name = collection
     
    @abc.abstractmethod
    def create(self, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def update(self, hrefAll, href, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def delete(self, entity, positive, **kwargs):
        return

    @abc.abstractmethod
    def find(self, name, **kwargs):
        return

    @abc.abstractmethod
    def get(self, href, **kwargs):
        return

    @abc.abstractmethod
    def query(self, href, constraint, **kwargs):
        return

    @abc.abstractmethod
    def syncAction(self, entity, action, positive, **kwargs):
        return

    @abc.abstractmethod
    def waitForElemStatus(self, elm, status, **kwargs):
        return

    @property
    def logger(self):
        return logging.getLogger(self.collection_name)
    

    def makeAction(self, async, expiry, **params):
        '''
        Description: build action (post body for actions urls)
        Author: edolinin
        Parameters:
           * async - type of action (synchronic or not)
           * expiry - action axpiration time
        Return: action
        '''

        action = Action()
        action.async = str(async).lower()
        action.grace_period = GracePeriod()
        action.grace_period.expiry = expiry
        action.grace_period.absolute = 'false'
        for p in params:
            setattr(action, p, params[p])
        return action



class SdkUtil(APIUtil):
    '''
    Implements SDK APIs methods
    '''

    def __init__(self, element, collection):
        super(SdkUtil, self).__init__(element, collection)

        global sdkInit
       
        if not sdkInit:
            user_with_domain = '{0}@{1}'.format(self.opts['user'], self.opts['user_domain'])
            self.api = sdkApi.API(self.opts['uri'], user_with_domain, self.opts['password'])
            sdkInit = self.api
        else:
            self.api = sdkInit

    def get(self, collection=None, **kwargs):
        '''
        Description: get collection by its name
        Author: edolinin
        Parameters:
           * collection - collection name to get
        Return: parsed GET response
        '''

        if not collection:
            collection = self.collection_name
            
        self.logger.debug("GET request content is --  collection:%(col)s " \
                        % {'col': collection })

        return self.__getCollection(collection).list()


    def create(self, entity, positive, expectedEntity=None, incrementBy=1, async=False):
        '''
        Description: creates a new element
        Author: edolinin
        Parameters:
           * entity - entity for post body
           * positive - if positive or negative verification should be done
           * expectedEntity - if there are some expected entity different from sent
           * incrementBy - increment by number of elements
           * async -sycnh or asynch request
        Return: POST response (None on parse error.),
                status (True if POST test succeeded, False otherwise.)
        '''

        collection = self.__getCollection(self.collection_name)
        initialCollectionSize = len(collection.list())
       
        self.logger.debug("CREATE api content is --  collection:%(col)s element:%(elm)s " \
                            % {'col': self.collection_name, 'elm': entity.__dict__ })

        response = None
        try:
            response = collection.add(entity)
           
            if not async:
                if not self.opts['parallel_run'] and \
                    not validator.compareCollectionSize(collection.list(),
                                                        initialCollectionSize + incrementBy,
                                                        self.logger):
                    return None, False

            self.logger.info("New entity was added successfully")
            expEntity = response if not expectedEntity else expectedEntity
            if not validator.compareEntitiesDumps(dump_entity(expEntity, self.element_name),
                    dump_entity(response, self.element_name),self.logger):
                        return None, False
                
        except RequestError as e:
            if positive:
                errorMsg = "Failed to create a new element, status: {0},reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e.detail))
                return None, False
            else:
                if not validator.compareCollectionSize(collection.list(),
                                                    initialCollectionSize,
                                                    self.logger):
                    return None, False

        except (EntityNotFound, AttributeError):
            self.logger.error("Entity is not added")
          
        return response, True
    

    def __set_property(self, entity, property_name, property_value):
        '''
        Set property for sdk object
        '''
        getattr(entity, 'set_' + property_name)(property_value)


    def update(self, origEntity, newEntity, positive):
        '''
        Description: update an element
        Author: edolinin
        Parameters:
           * origEntity - original entity
           * newEntity - entity for post body
           * positive - if positive or negative verification should be done
        Return: PUT response, status (True if PUT test succeeded, False otherwise)
        '''
                    
        response = None
        for attr in newEntity.__dict__.keys():
            try:
                attrVal = newEntity.__dict__[attr]
                if attrVal:
                    self.__set_property(origEntity, attr, attrVal)
            except AttributeError:
                self.logger.warn("Attribute doesn't exist %s" % attr)
            
        try:
            self.logger.debug("UPDATE api content is --  collection :%(col)s element:%(elm)s " \
                                    % {'col': self.collection_name, 'elm': origEntity.__dict__ })

            response = origEntity.update()
            self.logger.info(response.get_name() + " was updated")

            if not validator.compareEntitiesDumps(dump_entity(newEntity, self.element_name),
                dump_entity(response, self.element_name), self.logger):
                    return None, False

        except RequestError as e:
            if positive:
                errorMsg = "Failed to update an element, status: {0},reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e.detail))
                return None, False

        except (EntityNotFound, AttributeError):
                self.logger.error("Failed to update " + self.element_name)
                return None, False
        
        return response, True


    def delete(self, entity, positive, **kwargs):
        '''
        Description: delete an element
        Author: edolinin
        Parameters:
           * entity - entity to delete
           * positive - if positive or negative verification should be done
        Return: status (True if DELETE test succeeded, False otherwise)
        '''

        response = None
        try:
            self.logger.debug("DELETE entity: {0}".format(entity.get_id()))
            if kwargs:
                response = entity.delete(**kwargs)
            else:
                response = entity.delete()
        except RequestError as e:
            if positive:
                errorMsg = "Failed to delete an element, status: {0},reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e.detail))
                return None, False
      
        return response, True


    def query(self, constraint, **kwargs):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
        Return: query results
        '''

        self.logger.debug("SEARCH content is --  collection:%(col)s query:%(q)s" \
                        % {'col': self.collection_name, 'q': constraint})
        collection = self.__getCollection(self.collection_name)
        search = collection.list(constraint)
        self.logger.debug("Response for QUERY request is: %s " % search)

        return search



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

        
        collection = self.__getCollection(self.collection_name)
        results = None
        try:
            if attribute == 'name':
                results = filter(lambda r: r.get_name() == val, collection.list())[0]
            if attribute == 'id':
                results = filter(lambda r: r.get_id() == val, collection.list())[0]
        except Exception:
            raise EntityNotFound("Entity %s not found  for collection '%s'." \
                                % (val, self.collection_name))

        return results
    

    def __getCollection(self, collection_name):
        '''
        Returns sdk collection object
        '''
        return getattr(self.api, collection_name)
    

    def syncAction(self, entity, action, positive, async=False, **params):
        '''
        Description: run synchronic action
        Author: edolinin
        Parameters:
           * entity - target entity
           * action - desired action
           * positive - if positive or negative verification should be done
           * asynch - synch or asynch action
        Return: status (True if Action test succeeded, False otherwise)
        '''

        act = self.makeAction(async, 10, **params)

        try:
            getattr(entity, action)(act)
        except RequestError as e:
            if positive:
                errorMsg = "Failed to run an action '{0}', status: {1},reason: {2}, details: {3}"
                self.logger.error(errorMsg.format(action, e.status, e.reason, e.detail))
                return False
      
        return True
    

    def waitForElemStatus(self, elm, status, timeout=DEF_TIMEOUT,
                                        ignoreFinalStates=False):
        '''
        Description: Wait till the sdk element (the Host, VM) gets the desired
        status or till timeout.

        Author: edolinin
        Parameters:
            * elm - sdk element to probe for a status
            * status - a string represents status to wait for. it could be
                       multiple statuses as a string with space delimiter
                       Example: "active maintenance inactive"
            * timeout - maximum time to continue status probing
        Return: status (True if element get the desired status, False otherwise)
        '''

        handleTimeout = 0
        while handleTimeout <= timeout:
            
            if not hasattr(elm, 'status'):
                self.logger.error("Element %s doesn't have attribute status"\
                                % (self.element_name))
                return False

            if elm.get_status().state.lower() in status.lower().split():
                self.logger.info("%s status is '%s'" \
                                % (self.element_name, elm.get_status().state))
                return True
            elif elm.status.state.find("fail") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, elm.get_status().state))
                return False
            elif elm.status.state.find("up") != -1 and not ignoreFinalStates:
                self.logger.error("%s status is '%s'"\
                                % (self.element_name, elm.get_status().state))
                return False
            else:
                self.logger.debug("Waiting for status '%s', currently status is '%s' "\
                                % (status, elm.get_status().state))
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'." \
                        % (self.element_name, elm.status.state))
        return False


APIUtil.register(SdkUtil)
            

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
                expectedEntity=None, incrementBy=1, async=False):
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

        href = self.links[self.collection_name]
        collection = self.get(href)
        entity = dump_entity(entity, self.element_name)
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

            try:
                if(parse(ret['body'])):
                    self.logger.info("New entity was added")
                    actlEntity = dump_entity(parse(ret['body']), self.element_name)
                    expEntity = entity if not expectedEntity else expectedEntity
                    if not validator.compareEntitiesDumps(expEntity, actlEntity, self.logger):
                        return None, False

            except (EntityNotFound, AttributeError):
                self.logger.error("Entity is not added")

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

        entity = dump_entity(newEntity, self.element_name)

        self.logger.debug("PUT request content is --  url:%(uri)s body:%(body)s " \
                                    % {'uri': origEntity.href, 'body': entity })
        ret = http.PUT(self.opts, origEntity.href, entity, MEDIA_TYPE)
        self.logger.debug("Response body for PUT request is: %s " % ret['body'])

        self.validateResponseViaXSD(origEntity.href, ret)

        if positive:
            if not validator.compareResponseCode(ret, expected_pos_status, self.logger):
                return None, False
            try:
                updatedEntity = self.find(parse(ret['body']).id, 'id')
                self.logger.info(updatedEntity.name + " was updated")

                if not validator.compareEntitiesDumps(entity,
                                                    dump_entity(updatedEntity, self.element_name),
                                                    self.logger):
                    return None, False

            except (EntityNotFound, AttributeError):
                self.logger.error("Failed to update " + self.element_name)
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
            body = dump_entity(body, element_name)
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


    def query(self, constraint,  expected_status=[200, 201]):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
           * expected_status - list of expected statuses for positive request
        Return: query results
        '''

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
            actionBody = dump_entity(self.makeAction(async, 10, **params),
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

class TimeoutingSampler(object):
    '''
    Samples the function output.

    This is a generator object that at first yields the output of function `func`.
    After the yield, it either raises instance of `timeout_exc_cls` or sleeps
    `sleep` seconds.

    Yielding the output allows you to handle every value as you wish.

    Feel free to set the instance variables.

    Author: jhenner
    '''

    def __init__(self, timeout, sleep, func, *func_args, **func_kwargs):
        '''
        See the doc for TimeoutingSampler.
        '''

        self.timeout = timeout
        ''' Timeout in seconds. '''
        self.sleep = sleep
        ''' Sleep interval seconds. '''

        self.func = func
        ''' A function to sample. '''
        self.func_args = func_args
        ''' Args for func. '''
        self.func_kwargs = func_kwargs
        ''' Kwargs for func. '''

        self.start_time = None
        ''' Time of starting the sampling. '''
        self.last_sample_time = None
        ''' Time of last sample. '''

        self.timeout_exc_cls = APITimeout
        ''' Class of exception to be raised.  '''
        self.timeout_exc_args = ()
        ''' An args for __init__ of the timeout exception. '''
        self.timeout_exc_kwargs = {}
        ''' A kwargs for __init__ of the timeout exception. '''

    def __iter__(self):
        if self.start_time is None:
            self.start_time = time.time()
        while True:
            self.last_sample_time = time.time()
            yield self.func(*self.func_args, **self.func_kwargs)
            if self.timeout < (time.time() - self.start_time):
                raise self.timeout_exc_cls(
                        *self.timeout_exc_args,
                        **self.timeout_exc_kwargs)
            time.sleep(self.sleep)


class RestTestRunnerWrapper():
    '''
    Runs REST APIs functions not from run.py and without settings.conf.
    Required settings options are defined in constructor.

    Usage Example:
        from utils.restutils import RestTestRunnerWrapper
        restWrapper = RestTestRunnerWrapper('10.35.113.80')
        try:
            status = restWrapper.runCommand('rest.datacenters.addDataCenter','true',name='test',storage_type='NFS',version='2.2')
        except APICommandError:
            ...

    Author: edolinin
    '''

    def __init__(self, ip, **kwargs):
        '''
        Defines settings configuration required to run REST APIs functions
        Parameters:
        * ip - vdc ip
        * kwargs - dictionary with settings configurations, keys names are
        the same as in settings.conf, if omitted - defaults are set
        '''

        from rest.settings import opts
        import logging

        opts['host'] = ip

        opts['scheme'] = kwargs.get('scheme', 'https')
        opts['port'] = kwargs.get('port', '8443')
        opts['entry_point'] = kwargs.get('entry_point', 'api')
        opts['user'] = kwargs.get('user', 'vdcadmin')
        opts['user_domain'] = kwargs.get('user_domain', 'qa.lab.tlv.redhat.com')
        opts['password'] = kwargs.get('password', '123456')
        opts['type'] = kwargs.get('type', 'rest')
        opts['debug'] = kwargs.get('debug', 'DEBUG')
        opts['log'] = kwargs.get('log', "/var/tmp/%sTests%s.log" % (opts['type'], strftime('%Y%m%d_%H%M%S')))
        opts['urisuffix'] = ''
        opts['uri'] = '%(scheme)s://%(host)s:%(port)s/%(entry_point)s%(urisuffix)s/' \
            % opts

        opts['in_parallel'] = kwargs.get('in_parallel', [])
        opts['parallel_run'] = True if opts['in_parallel'] else False
        opts['standalone'] = kwargs.get('standalone', False)

        self.logger = logging.getLogger(__name__)
        print "Log file is initialized at {0}".format(opts['log'])


    @classmethod
    def runCommand(cls, action, *args, **kwargs):
        '''
        Runs REST APIs functions

        Parameters:
        * action - full path of the action which should be run
        * args - list of function's non-keyword arguments
        * kwargs - dictionary with function's keyword arguments

        Exceptions: raises APICommandError in case of error

        '''

        actionModulesNames = action.split(".")
        funcPackage = ".".join(actionModulesNames[:-1])
        funcName = actionModulesNames[-1]

        exec("from " + funcPackage + " import " + funcName)

        params = ''
        for arg in args:
            params = "{0},{1!r}".format(params, arg)

        for paramName, paramVal in kwargs.items():
            params = "{0},{1}={2!r}".format(params, paramName, paramVal)
        cmd = funcName + "(" + params.strip(' ,') + ")"

        try:
            return eval(cmd)
        except Exception as e:
            raise APICommandError(cmd, e)
