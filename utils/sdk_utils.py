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

import validator
import time
from apis_exceptions import EntityNotFound
from utils.data_structures import *
from ovirtsdk import api as sdkApi
from ovirtsdk.infrastructure.errors import RequestError
from utils.apis_utils import APIUtil

sdkInit = None

DEF_TIMEOUT = 900 # default timeout
DEF_SLEEP = 10 # default sleep


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

        href = kwargs.pop('href', None)
        if href is not None:
            return self.api
            
        self.logger.debug("GET request content is --  collection:%(col)s " \
                        % {'col': collection })
      
        return self.__getCollection(collection).list()
    

    def create(self, entity, positive, expectedEntity=None, incrementBy=1,
            async=False, collection=None):
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

        if not collection:
            collection = self.__getCollection(self.collection_name)
           
        initialCollectionSize = len(collection.list())
       
        self.logger.debug("CREATE api content is --  collection:%(col)s element:%(elm)s " \
        % {'col': self.collection_name, 'elm': validator.dump_entity(entity, self.element_name) })

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
            expEntity = entity if not expectedEntity else expectedEntity
            if not validator.compareElements(expEntity, response,
                                self.logger, self.element_name):
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
        Return: PUT response, True if PUT test succeeded, False otherwise
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
            % {
                'col': self.collection_name,
                'elm': validator.dump_entity(origEntity, self.element_name)
            })

            response = origEntity.update()
            self.logger.info(self.element_name + " was updated")

            if not validator.compareElements(newEntity, response,
                                self.logger, self.element_name):
                return None, False

        except RequestError as e:
            if positive:
                errorMsg = "Failed to update an element, status: {0},reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e.detail))
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
    

    def getElemFromLink(self, elm, link_name=None, get_href=False, **kwargs):
        '''
        Description: get element's collection from specified link
        Parameters:
           * elm - element object
           * link_name - link name
        Return: element obj or None if not found
        '''
        if not link_name:
            link_name = self.collection_name
            
        if get_href:
            return getattr(elm, link_name)
        else:
            return getattr(elm, link_name).list()
    

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

        if not validator.compareActionLink(entity.get_actions(), action, self.logger):
            return False

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