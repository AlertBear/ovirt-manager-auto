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

from core_api import validator
import time
from core_api.apis_exceptions import EntityNotFound
from rhevm_api.data_struct.data_structures import *
from ovirtsdk import api as sdkApi
from ovirtsdk.infrastructure.errors import RequestError
from core_api.apis_utils import APIUtil

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
        if href == '':
            return self.api
            
        self.logger.debug("GET request content is --  collection:%(col)s " \
                        % {'col': collection })
      
        results = None
        try:
            results = self.__getCollection(collection).list()
        except AttributeError as exc:
            raise EntityNotFound("Can't get collection '{0}': {1}".\
                                format(collection, exc.message))

        return results
    

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

        try:
            self.logger.debug("CREATE api content is --  collection:%(col)s element:%(elm)s " \
            % {'col': self.collection_name, 'elm': validator.dump_entity(entity, self.element_name) })
        except Exception:
            pass

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


        dumpedEntity = None
        try:
            dumpedEntity = validator.dump_entity(newEntity, self.element_name)
        except Exception:
            pass

        self.logger.debug("UPDATE api content is --  collection :%(col)s element:%(elm)s " \
            % {
                'col': self.collection_name,
                'elm': dumpedEntity
            })
            
        try:

            if positive:
                response = origEntity.update()
                self.logger.info(self.element_name + " was updated")

                if not validator.compareElements(newEntity, response,
                                    self.logger, self.element_name):
                    return None, False

        except RequestError as e:
            if positive:
                errorMsg = "Failed to update an element, status: {0}, reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e))
                return None, False
 
        return response, True


    def delete(self, entity, positive, body=None, **kwargs):
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
            if body:
                response = entity.delete(body)
            else:
                response = entity.delete()
        except RequestError as e:
            if positive:
                errorMsg = "Failed to delete an element, status: {0},reason: {1}, details: {2}"
                self.logger.error(errorMsg.format(e.status, e.reason, e.detail))
                return None, False
      
        return response, True


    def query(self, constraint, exp_status=None, href=None, event_id=None):
        '''
        Description: run search query
        Author: edolinin
        Parameters:
           * constraint - query for search
        Return: query results
        '''
        collection = href
        if not href:
            collection = self.collection_name
            
        search = None
        self.logger.debug("SEARCH content is --  collection:%(col)s query:%(q)s event id:%(id)s" \
            % {'col': self.collection_name, 'q': constraint, 'id': event_id})
        collection = self.__getCollection(collection)
        
        if event_id is not None:
            search = collection.list(constraint, from_event_id=event_id)
        else:
            search = collection.list(constraint)
            
        self.logger.debug("Response for QUERY request is: %s " % search)

        return search



    def find(self, val, attribute='name', absLink=True, collection=None):
        '''
        Description: find entity by name
        Author: edolinin
        Parameters:
           * val - name of entity to look for
           * attribute - attribute name for searching
           * absLink - absolute link or just a  suffix
        Return: found entity or exception EntityNotFound
        '''

        if not collection:
            collection = self.__getCollection(self.collection_name).list()
  
        results = None
        try:
            if attribute == 'name':
                results = filter(lambda r: r.get_name() == val, collection)[0]
            if attribute == 'id':
                results = filter(lambda r: r.get_id() == val, collection)[0]
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

        try:
            self.logger.info("Running action {0} on {1}"\
            .format(validator.dump_entity(act, 'action'), entity))
        except Exception:
            pass

        try:
            act =getattr(entity, action)(act)
        except RequestError as e:
            if positive:
                errorMsg = "Failed to run an action '{0}', status: {1},reason: {2}, details: {3}"
                self.logger.error(errorMsg.format(action, e.status, e.reason, e.detail))
                return False

        if positive and not async:
            if not validator.compareActionStatus(act.status.state, ["complete"],
                                                                    self.logger):
                return False

        elif positive and async:
            if not validator.compareActionStatus(act.status.state, ["pending", "complete"],
                                                                    self.logger):
                return False
        else:
            if act.status and not validator.compareActionStatus(act.status.state, ["failed"],
                                                                    self.logger):
                return False

        return True
    

    def waitForElemStatus(self, elm, status, timeout=DEF_TIMEOUT,
                            ignoreFinalStates=False, collection=None):
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

            elm = self.find(elm.name, collection=collection)

            elemStat = None
            if hasattr(elm, 'snapshot_status'):
                elemStat = elm.snapshot_status.lower()
            elif hasattr(elm, 'status'):
                elemStat = elm.status.state.lower()
            else:
                self.logger.error("Element %s doesn't have attribute status" % \
                                                        (self.element_name))
                return False

            try:
                self.logger.info("Element {0} Waiting for the status {1}".\
                format(validator.dump_entity(elm, self.element_name), status))
            except Exception:
                pass
            
            if not hasattr(elm, 'status'):
                self.logger.error("Element %s doesn't have attribute status"\
                                % (self.element_name))
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
                self.logger.debug("Waiting for status '%s', currently status is '%s' "\
                                % (status, elemStat))
                time.sleep(DEF_SLEEP)
                handleTimeout = handleTimeout + DEF_SLEEP
                continue

        self.logger.error("Interrupt because of timeout. %s status is '%s'." \
                        % (self.element_name, elemStat))
        return False


APIUtil.register(SdkUtil)